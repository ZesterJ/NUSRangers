import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import type { AiSource } from '@/ai/types';
import type { Assessment } from '@/packs/types';
import { usePackContext } from '@/theme';

import { SourceBadge } from './SourceBadge';
import { Card } from './ui';

export function AssessmentCard({ assessment, source }: { assessment: Assessment; source: AiSource | null }) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const riskColor =
    assessment.riskLevel === 'high' ? theme.danger : assessment.riskLevel === 'med' ? theme.warning : theme.success;

  return (
    <Card>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.text }]}>{t('capture.result')}</Text>
        {source && <SourceBadge source={source} />}
      </View>
      {assessment.riskLevel && (
        <Text style={[styles.risk, { color: riskColor }]}>● {t(`capture.risk.${assessment.riskLevel}`)}</Text>
      )}
      <Text style={{ color: theme.text, fontSize: 16 }}>{assessment.summary}</Text>
      {assessment.actions.map((a) => (
        <Text key={a} style={{ color: theme.text, fontSize: 15 }}>
          ✅ {a}
        </Text>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 17, fontWeight: '800' },
  risk: { fontSize: 16, fontWeight: '800' },
});
