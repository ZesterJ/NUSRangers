import { useTranslation } from 'react-i18next';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import type { GuidanceEntry, GuidanceSource } from '@/intake/guidance';
import { spacing, usePackContext } from '@/theme';

/** One guidance entry: its points and a link to the source document. */
export function GuidanceEntryView({ entry, source }: { entry: GuidanceEntry; source: GuidanceSource }) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  return (
    <View style={styles.entry}>
      <Text style={[styles.title, { color: theme.text }]}>{entry.title}</Text>
      {entry.points.map((p) => (
        <Text key={p} style={{ color: theme.text }}>
          • {p}
        </Text>
      ))}
      <Pressable onPress={() => Linking.openURL(source.url)}>
        <Text style={[styles.source, { color: theme.primary }]}>
          {t('guidance.source')}: {source.publisher}, {source.title} ({source.year})
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  entry: { gap: spacing.xs },
  title: { fontSize: 16, fontWeight: '700' },
  source: { fontSize: 13 },
});
