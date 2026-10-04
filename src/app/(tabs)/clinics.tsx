import * as Location from 'expo-location';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Linking, Platform, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button, Card, KeyboardScrollView } from '@/components/ui';
import { distanceKm, origin, type Coordinates } from '@/intake/careRouting';
import directory from '@/intake/kilifiDirectory.json';
import { radius, spacing, usePackContext } from '@/theme';

type Facility = (typeof directory.facilities)[number];
const FACILITIES = directory.facilities;
const PAGE = 15;

// The map is a plot of the facilities' own coordinates, so it needs no map download and works offline.
const LAT = FACILITIES.map((f) => f.latitude);
const LON = FACILITIES.map((f) => f.longitude);
const PAD = 0.05;
const BOX = {
  south: Math.min(...LAT) - PAD,
  north: Math.max(...LAT) + PAD,
  west: Math.min(...LON) - PAD,
  east: Math.max(...LON) + PAD,
};
const ASPECT = (BOX.north - BOX.south) / (BOX.east - BOX.west);

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

/** Patient view: every clinic and hospital in the facility records, nearest first, with a simple map. */
export default function Clinics() {
  const { theme, scale } = usePackContext();
  const { t } = useTranslation();
  const [mine, setMine] = useState<Coordinates | undefined>(undefined);
  const [locating, setLocating] = useState(false);
  const [denied, setDenied] = useState(false);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [shown, setShown] = useState(PAGE);
  const [mapWidth, setMapWidth] = useState(0);

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

  const mapHeight = mapWidth * ASPECT;
  const x = (lon: number) => ((lon - BOX.west) / (BOX.east - BOX.west)) * mapWidth;
  const y = (lat: number) => ((BOX.north - lat) / (BOX.north - BOX.south)) * mapHeight;

  // A tap on the map selects the facility nearest to the finger.
  const tapMap = (px: number, py: number) => {
    let best: Facility | null = null;
    let bestD = Infinity;
    for (const f of FACILITIES) {
      const d = (x(f.longitude) - px) ** 2 + (y(f.latitude) - py) ** 2;
      if (d < bestD) {
        bestD = d;
        best = f;
      }
    }
    if (best) setSelected(best.id);
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

      {/* Map */}
      <Pressable
        onLayout={(e) => setMapWidth(e.nativeEvent.layout.width)}
        onPress={(e) => tapMap(e.nativeEvent.locationX, e.nativeEvent.locationY)}
        style={[styles.map, { height: mapHeight || 200, borderColor: theme.border, backgroundColor: theme.card }]}>
        {mapWidth > 0 &&
          FACILITIES.map((f) => (
            <View
              key={f.id}
              pointerEvents="none"
              style={[
                styles.dot,
                { left: x(f.longitude) - 4, top: y(f.latitude) - 4, backgroundColor: f.services.length ? theme.primary : theme.textMuted },
                f.id === selected && styles.dotSelected,
                f.id === selected && { left: x(f.longitude) - 8, top: y(f.latitude) - 8, borderColor: theme.text, backgroundColor: theme.primary },
              ]}
            />
          ))}
        {mapWidth > 0 && (
          <Text pointerEvents="none" style={[styles.you, { left: x(from.point.longitude) - 9, top: y(from.point.latitude) - 18 }]}>
            📍
          </Text>
        )}
      </Pressable>
      <Text style={{ color: theme.textMuted, fontSize: 13 * scale }}>{t('clinics.mapHint')}</Text>
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
  map: { borderWidth: 1, borderRadius: radius.md, overflow: 'hidden' },
  dot: { position: 'absolute', width: 8, height: 8, borderRadius: 4 },
  dotSelected: { width: 16, height: 16, borderRadius: 8, borderWidth: 2 },
  you: { position: 'absolute', fontSize: 18 },
  input: { borderWidth: 1, borderRadius: radius.md, paddingHorizontal: spacing.md, minHeight: 48 },
});
