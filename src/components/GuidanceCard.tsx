import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import { guidanceFor } from '@/intake/guidance';
import { useGuidanceRegistry } from '@/intake/guidanceStore';
import type { ConfirmedIntake } from '@/intake/types';
import { spacing, usePackContext } from '@/theme';

import { GuidanceEntryView } from './GuidanceEntryView';
import { Card } from './ui';

/** Clinic side: reminders from the guidance registry that match this patient's visit note. */
export function GuidanceCard({ intake }: { intake: ConfirmedIntake }) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const registry = useGuidanceRegistry();
  const entries = guidanceFor(intake, registry);
  if (entries.length === 0) return null;

  return (
    <Card>
      <Text style={[styles.heading, { color: theme.text }]}>📋 {t('guidance.title')}</Text>
      <Text style={{ color: theme.textMuted }}>{t('guidance.intro')}</Text>
      {entries.map((e) => (
        <View key={e.id} style={styles.entry}>
          <GuidanceEntryView entry={e} source={registry.sources[e.sourceId]} />
        </View>
      ))}
      <Text style={[styles.footer, { color: theme.warning }]}>
        {registry.reviewStatus !== 'clinically_reviewed' ? `${t('guidance.draft')} ` : ''}
        {t('guidance.footer', { version: registry.version, updated: registry.updated })}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  heading: { fontSize: 18, fontWeight: '800' },
  entry: { marginTop: spacing.md },
  footer: { fontSize: 13, marginTop: spacing.md },
});
