import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { GuidanceEntryView } from '@/components/GuidanceEntryView';
import { Card } from '@/components/ui';
import { guidanceByTopic } from '@/intake/guidance';
import { useGuidanceRegistry } from '@/intake/guidanceStore';
import { spacing, usePackContext } from '@/theme';

/** Clinic view: the whole guidance registry, grouped by condition, for reference at any time. */
export default function Guidance() {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const registry = useGuidanceRegistry();
  const groups = guidanceByTopic(registry);
  const [open, setOpen] = useState<string | null>(null);

  return (
    <ScrollView style={{ backgroundColor: theme.background }} contentContainerStyle={styles.content}>
      <Text style={[styles.title, { color: theme.text }]}>{t('guidance.tabTitle')}</Text>
      <Text style={{ color: theme.textMuted }}>{t('guidance.tabIntro')}</Text>

      {groups.map((g) => {
        const expanded = open === g.topic;
        return (
          <Card key={g.topic}>
            <Pressable accessibilityRole="button" onPress={() => setOpen(expanded ? null : g.topic)} style={styles.head}>
              <Text style={[styles.topic, { color: theme.text }]}>{g.topic}</Text>
              <Text style={{ color: theme.primary, fontWeight: '700' }}>
                {g.entries.length} {expanded ? '▲' : '▼'}
              </Text>
            </Pressable>
            {expanded &&
              g.entries.map((e) => (
                <View key={e.id} style={styles.entry}>
                  <GuidanceEntryView entry={e} source={registry.sources[e.sourceId]} />
                </View>
              ))}
          </Card>
        );
      })}

      <Text style={[styles.footer, { color: theme.warning }]}>
        {registry.reviewStatus !== 'clinically_reviewed' ? `${t('guidance.draft')} ` : ''}
        {t('guidance.footer', { version: registry.version, updated: registry.updated })}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  title: { fontSize: 20, fontWeight: '800' },
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md },
  topic: { fontSize: 17, fontWeight: '700', flexShrink: 1 },
  entry: { marginTop: spacing.md },
  footer: { fontSize: 13 },
});
