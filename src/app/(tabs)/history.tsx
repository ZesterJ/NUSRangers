import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlatList, StyleSheet, Text, View } from 'react-native';

import { flushOutbox, useSyncStore } from '@/ai/sync';
import { AssessmentCard } from '@/components/AssessmentCard';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Button, SectionTitle } from '@/components/ui';
import { listReports, type StoredReport } from '@/db';
import { useIsOnline } from '@/store/connectivity';
import { spacing, usePackContext } from '@/theme';

export default function History() {
  const { pack, theme } = usePackContext();
  const { t } = useTranslation();
  const online = useIsOnline();
  const { pending, syncing, version } = useSyncStore();
  const [reports, setReports] = useState<StoredReport[]>([]);

  const load = useCallback(() => {
    listReports(pack.id).then(setReports);
  }, [pack.id]);

  useFocusEffect(load);
  // Reload after a background sync finishes.
  useEffect(load, [load, version]);

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <OfflineBanner />
      <FlatList
        data={reports}
        keyExtractor={(r) => String(r.id)}
        contentContainerStyle={styles.content}
        ListHeaderComponent={
          <View style={{ gap: spacing.sm }}>
            {pending > 0 && (
              <>
                <Text style={{ color: theme.warning, fontWeight: '700' }}>⏳ {t('history.pending', { count: pending })}</Text>
                <Button
                  label={syncing ? t('history.syncing') : t('history.syncNow')}
                  variant="outline"
                  disabled={!online}
                  loading={syncing}
                  onPress={flushOutbox}
                />
              </>
            )}
            <SectionTitle>{t('history.reports')}</SectionTitle>
          </View>
        }
        ListEmptyComponent={<Text style={{ color: theme.textMuted }}>{t('history.empty')}</Text>}
        renderItem={({ item }) => (
          <View style={{ gap: spacing.xs }}>
            <Text style={{ color: theme.textMuted, fontSize: 12 }}>
              #{item.id} · {new Date(item.createdAt).toLocaleString()} ·{' '}
              {Object.entries(item.fields)
                .filter(([, v]) => typeof v !== 'object')
                .map(([k, v]) => `${k}: ${v}`)
                .join(', ')}
            </Text>
            {item.result ? (
              <AssessmentCard assessment={item.result} source={item.resultSource} />
            ) : (
              <Text style={{ color: theme.textMuted }}>{t('history.noResult')}</Text>
            )}
          </View>
        )}
        ItemSeparatorComponent={() => <View style={{ height: spacing.lg }} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg },
});
