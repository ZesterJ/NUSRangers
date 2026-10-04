import { StyleSheet, Text, View } from 'react-native';

import { useSettings } from '@/store/settings';
import { spacing, usePackContext } from '@/theme';

import { Chip } from './ui';

/** Language choice, shown at the top right of the first screen and of the visit note. */
export function LanguageSwitch() {
  const { pack, locale, theme } = usePackContext();
  const set = useSettings((s) => s.set);
  return (
    <View style={styles.row}>
      <Text style={{ color: theme.textMuted }}>🌐</Text>
      {pack.locales.map((l) => (
        <Chip key={l.code} label={l.label} selected={locale === l.code} onPress={() => set({ locale: l.code })} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', gap: spacing.sm },
});
