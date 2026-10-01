import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Image, StyleSheet, Text, TextInput, View } from 'react-native';

import type { FormField, FormValues } from '@/packs/types';
import { tr } from '@/packs/types';
import { radius, spacing, usePackContext } from '@/theme';

import { Button, Chip } from './ui';

type Props = {
  field: FormField;
  value: FormValues[string];
  onChange: (value: FormValues[string]) => void;
  /** Photo fields report their base64 separately so it isn't stored in the fields JSON. */
  onPhoto?: (base64: string | undefined) => void;
};

const PICKER_OPTS: ImagePicker.ImagePickerOptions = {
  mediaTypes: ['images'],
  quality: 0.3, // small uploads for slow links
  base64: true,
};

/** Renders any declarative pack form field. */
export function FormFieldInput({ field, value, onChange, onPhoto }: Props) {
  const { locale, theme } = usePackContext();
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const label = tr(field.label, locale) + (field.required ? ' *' : '');

  const pickPhoto = async (camera: boolean) => {
    const perm = camera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) return;
    const res = camera
      ? await ImagePicker.launchCameraAsync(PICKER_OPTS)
      : await ImagePicker.launchImageLibraryAsync(PICKER_OPTS);
    if (res.canceled) return;
    const asset = res.assets[0];
    onChange(asset.uri);
    onPhoto?.(asset.base64 ?? undefined);
  };

  const getLocation = async () => {
    setBusy(true);
    try {
      const perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) return;
      // Last known position works without data connection; fall back to a fresh GPS fix.
      const pos =
        (await Location.getLastKnownPositionAsync()) ??
        (await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }));
      onChange({ lat: pos.coords.latitude, lng: pos.coords.longitude });
    } catch (e) {
      Alert.alert(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.field}>
      <Text style={[styles.label, { color: theme.text }]}>{label}</Text>

      {(field.type === 'text' || field.type === 'number') && (
        <TextInput
          style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.card }]}
          value={value === undefined ? '' : String(value)}
          onChangeText={(v) => onChange(field.type === 'number' ? (v === '' ? undefined : Number(v)) : v)}
          keyboardType={field.type === 'number' ? 'numeric' : 'default'}
          placeholder={'placeholder' in field ? tr(field.placeholder, locale) : undefined}
          placeholderTextColor={theme.textMuted}
        />
      )}

      {field.type === 'select' && (
        <View style={styles.chips}>
          {field.options.map((o) => (
            <Chip key={o.value} label={tr(o.label, locale)} selected={value === o.value} onPress={() => onChange(o.value)} />
          ))}
        </View>
      )}

      {field.type === 'photo' && (
        <View style={{ gap: spacing.sm }}>
          {typeof value === 'string' && <Image source={{ uri: value }} style={styles.photo} />}
          <View style={styles.chips}>
            <Button label={`📷 ${t('capture.pickPhoto')}`} variant="outline" onPress={() => pickPhoto(true)} />
            <Button label={`🖼️ ${t('capture.choosePhoto')}`} variant="outline" onPress={() => pickPhoto(false)} />
          </View>
        </View>
      )}

      {field.type === 'location' && (
        <View style={{ gap: spacing.sm }}>
          {value && typeof value === 'object' && (
            <Text style={{ color: theme.textMuted }}>
              📍 {value.lat.toFixed(4)}, {value.lng.toFixed(4)}
            </Text>
          )}
          <Button label={`📍 ${t('capture.getLocation')}`} variant="outline" loading={busy} onPress={getLocation} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: spacing.sm, marginBottom: spacing.lg },
  label: { fontSize: 15, fontWeight: '700' },
  input: { borderWidth: 1, borderRadius: radius.md, paddingHorizontal: spacing.md, minHeight: 48, fontSize: 16 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  photo: { width: '100%', height: 180, borderRadius: radius.md },
});
