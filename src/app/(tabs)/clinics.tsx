import * as Location from 'expo-location';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Linking, Platform, Pressable, StyleSheet, Text, TextInput } from 'react-native';

import { ClinicMap } from '@/components/ClinicMap';
import { Button, Card, KeyboardScrollView } from '@/components/ui';
import { distanceKm, origin, type Coordinates } from '@/intake/careRouting';
import directory from '@/intake/kilifiDirectory.json';
import { radius, spacing, usePackContext } from '@/theme';

type Facility = (typeof directory.facilities)[number];
const FACILITIES = directory.facilities;
const PAGE = 15;

function openInMaps(f: Facility) {
  const label = encodeURIComponent(f.name);
  const url =
    Platform.OS === 'ios'
      ? `http://maps.apple.com/?ll=${f.latitude},${f.longitude}&q=${label}`
      : `geo:${f.latitude},${f.longitude}?q=${f.latitude},${f.longitude}(${label})`;
  Linking.openURL(url).catch(() =>
    Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${f.latitude},${f.longitude}`),
  );
}

/** Patient view: every clinic and hospital in the facility records, nearest first, with an offline map. */
export default function Clinics() {
  const { theme, scale } = usePackContext();
  const { t } = useTranslation();
  const [mine, setMine] = useState<Coordinates | undefined>(undefined);
  const [locating, setLocating] = useState(false);
  const [denied, setDenied] = useState(false);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [shown, setShown] = useState(PAGE);

  const from = origin(mine);
  const sorted = useMemo(
    () => FACILITIES.map((f) => ({ f, km: distanceKm(from.point, f) })).sort((a, b) => a.km - b.km),
    [from.point],
  );
  const q = query.trim().toLowerCase();
  const matches = q ? sorted.filter(({ f }) => f.name.toLowerCase().includes(q) || (f.area ?? '').toLowerCase().includes(q)) : sorted;
  const picked = selected ? sorted.find(({ f }) => f.id === selected) : undefined;

  const locate = async () => {
    setLocating(true);
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      setDenied(!perm.granted);
      if (!perm.granted) return;
      // Last known position works without a data connection; fall back to a fresh GPS fix.
      const pos =
        (await Location.getLastKnownPositionAsync()) ??
        (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }));
      setMine({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
    } catch (e) {
      console.warn('[clinics] could not get a location', e);
      setDenied(true);
    } finally {
      setLocating(false);
    }
  };

  const body = { fontSize: 15 * scale };
  const card = ({ f, km }: { f: Facility; km: number }, highlight = false) => (
    <Card key={f.id} style={highlight ? { borderColor: theme.primary, borderWidth: 2 } : undefined}>
      <Text style={[styles.name, { color: theme.text, fontSize: 17 * scale }]}>{f.name}</Text>
      <Text style={[body, { color: theme.textMuted }]}>
        {f.area ? `${f.area} · ` : ''}
        {t('clinics.km', { km: km.toFixed(1) })}
      </Text>
      <Text style={[body, { color: theme.textMuted }]}>
        {f.services.length
          ? t('intake.documented', { services: f.services.map((s) => t(`intake.service.${s}`, { defaultValue: s })).join(', ') })
          : t('clinics.servicesUnknown')}
      </Text>
      <Pressable onPress={() => openInMaps(f)}>
        <Text style={[body, { color: theme.primary, fontWeight: '700' }]}>🗺️ {t('clinics.openMap')}</Text>
      </Pressable>
    </Card>
  );

  return (
    <KeyboardScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.content}>
      <Text style={[styles.title, { color: theme.text, fontSize: 20 * scale }]}>{t('clinics.title')}</Text>
      <Text style={[body, { color: theme.textMuted }]}>{t('clinics.intro', { count: FACILITIES.length })}</Text>

      <Button label={`📍 ${t(mine ? 'clinics.locateAgain' : 'clinics.locate')}`} variant="outline" loading={locating} onPress={locate} />
      <Text style={[body, { color: denied ? theme.warning : theme.textMuted }]}>
        {denied
          ? t('clinics.noLocation')
          : from.type === 'patient'
            ? t('clinics.fromYou')
            : mine
              ? t('clinics.outside')
              : t('clinics.fromAnchor')}
      </Text>

      <ClinicMap selected={selected} onSelect={setSelected} from={from.point} fromIsUser={from.type === 'patient'} />
      {picked && card(picked, true)}

      <TextInput
        style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.card, fontSize: 16 * scale }]}
        value={query}
        onChangeText={(v) => {
          setQuery(v);
          setShown(PAGE);
        }}
        placeholder={t('clinics.search')}
        placeholderTextColor={theme.textMuted}
        autoCorrect={false}
      />
      {matches.length === 0 && <Text style={[body, { color: theme.textMuted }]}>{t('clinics.none')}</Text>}
      {matches.slice(0, shown).map((m) => card(m))}
      {matches.length > shown && (
        <Button label={t('clinics.more', { count: matches.length - shown })} variant="outline" onPress={() => setShown(shown + PAGE)} />
      )}

      <Text style={{ color: theme.warning, fontSize: 13 * scale }}>{t('clinics.dataNote')}</Text>
    </KeyboardScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  title: { fontWeight: '800' },
  name: { fontWeight: '700' },
  input: { borderWidth: 1, borderRadius: radius.md, paddingHorizontal: spacing.md, minHeight: 48 },
});
