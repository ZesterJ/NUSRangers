import { useFocusEffect } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import { flushOutbox, useSyncStore } from '@/ai/sync';
import { AssessmentCard } from '@/components/AssessmentCard';
import { IntakeSummary, LEVEL_ICON } from '@/components/IntakeSummary';
import { Button, Card, SectionTitle } from '@/components/ui';
import { listIntakes, listReports, type StoredReport } from '@/db';
import { encodeHandoff } from '@/intake/handoff';
import type { IntakeRecord } from '@/intake/types';
import { useIsOnline } from '@/store/connectivity';
import { useSettings } from '@/store/settings';
import { radius, spacing, usePackContext } from '@/theme';

export default function History() {
  const { pack, theme } = usePackContext();
  const { t } = useTranslation();
  const online = useIsOnline();
  const { pending, syncing, version } = useSyncStore();
  const [reports, setReports] = useState<StoredReport[]>([]);
  const role = useSettings((s) => s.role);
  const [allIntakes, setIntakes] = useState<IntakeRecord[]>([]);
  // A shared phone must not show one view's patients to the other. Notes from before this rule count as the patient's.
  const intakes = allIntakes.filter((rec) => (rec.owner ?? 'patient') === role);
  const [open, setOpen] = useState<{ id: string; qr: string } | null>(null);

  const load = useCallback(() => {
    listReports(pack.id).then(setReports);
    listIntakes().then(setIntakes);
  }, [pack.id]);

  useFocusEffect(load);
  // Reload after a background sync finishes.
  useEffect(load, [load, version]);

  const toggle = async (rec: IntakeRecord) => {
    if (open?.id === rec.id) return setOpen(null);
    setOpen({ id: rec.id, qr: await encodeHandoff(rec) });
  };

  return (
    <View style={{ flex: 1, backgroundColor: theme.background }}>
      <ScrollView contentContainerStyle={styles.content}>
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

        <SectionTitle>{t('history.intakes')}</SectionTitle>
        {intakes.length === 0 && <Text style={{ color: theme.textMuted }}>{t('history.empty')}</Text>}
        {intakes.map((rec) => (
          <View key={rec.id} style={{ gap: spacing.sm }}>
            <Pressable onPress={() => toggle(rec)}>
              <Card>
                <View style={styles.row}>
                  <Text style={[styles.rowTitle, { color: theme.text }]}>
                    {LEVEL_ICON[rec.triage.level]} {t(`intake.level.${rec.triage.level}`)}
                  </Text>
                  <Text style={{ color: rec.status === 'received' ? theme.success : theme.textMuted, fontSize: 12 }}>
                    {rec.status === 'received' ? `✓ ${t('scan.received')}` : `#${rec.id}`}
                  </Text>
                </View>
                <Text style={{ color: theme.textMuted, fontSize: 13 }}>
                  {new Date(rec.createdAt).toLocaleString()} ·{' '}
                  {rec.intake.patientGroup ? t(`intake.group.${rec.intake.patientGroup}`) : '—'}
                </Text>
              </Card>
            </Pressable>
            {open?.id === rec.id && (
              <>
                <IntakeSummary intake={rec.intake} triage={rec.triage} services={rec.services} />
                {rec.transcript.length > 0 && (
                  <Card>
                    <Text style={{ color: theme.textMuted, fontWeight: '700' }}>{t('intake.transcript')}</Text>
                    {rec.transcript.map((line, i) => (
                      <Text key={i} style={{ color: theme.text }}>
                        “{line}”
                      </Text>
                    ))}
                  </Card>
                )}
                <View style={styles.qrBox}>
                  <QRCode value={open.qr} size={220} ecl="M" />
                </View>
              </>
            )}
          </View>
        ))}

        {reports.length > 0 && (
          <>
            <SectionTitle>{t('history.reports')}</SectionTitle>
            {reports.map((item) => (
              <View key={item.id} style={{ gap: spacing.xs }}>
                <Text style={{ color: theme.textMuted, fontSize: 12 }}>
                  #{item.id} · {new Date(item.createdAt).toLocaleString()}
                </Text>
                {item.result ? (
                  <AssessmentCard assessment={item.result} source={item.resultSource} />
                ) : (
                  <Text style={{ color: theme.textMuted }}>{t('history.noResult')}</Text>
                )}
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: spacing.xl * 2 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.sm },
  rowTitle: { fontSize: 16, fontWeight: '700', flexShrink: 1 },
  qrBox: { backgroundColor: '#FFFFFF', padding: 16, borderRadius: radius.md, alignSelf: 'center' },
});
