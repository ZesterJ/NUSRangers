import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import type { ConfirmedIntake, Triage } from '@/intake/types';
import { spacing, usePackContext } from '@/theme';

import { Card } from './ui';

export const LEVEL_ICON: Record<Triage['level'], string> = {
  refer_now: '🚨',
  refer_24h: '🏥',
  home_care: '🏠',
  unsure: '❓',
};

/** Triage result + confirmed answers. Used on the result screen, the clinic scan screen and records. */
export function IntakeSummary({
  intake,
  triage,
  services = [],
}: {
  intake: ConfirmedIntake;
  triage: Triage;
  /** Care services proposed by the backend, if it ran. */
  services?: string[];
}) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const color =
    triage.level === 'refer_now'
      ? theme.danger
      : triage.level === 'refer_24h' || triage.level === 'unsure'
        ? theme.warning
        : theme.success;

  const row = (label: string, value: string) => (
    <View style={styles.row}>
      <Text style={[styles.label, { color: theme.textMuted }]}>{label}</Text>
      <Text style={[styles.value, { color: theme.text }]}>{value || '—'}</Text>
    </View>
  );

  return (
    <Card style={{ borderColor: color, borderWidth: 2 }}>
      <Text style={[styles.level, { color }]}>
        {LEVEL_ICON[triage.level]} {t(`intake.level.${triage.level}`)}
      </Text>
      {triage.reasons.map((r) => (
        <Text key={r} style={{ color: theme.text }}>
          • {r}
        </Text>
      ))}
      <View style={{ height: spacing.sm }} />
      {!!intake.patientName && row(t('intake.name'), intake.patientName)}
      {row(t('intake.who'), intake.patientGroup ? t(`intake.group.${intake.patientGroup}`) : '')}
      {!!intake.sex && row(t('intake.sex'), t(`intake.sexOpt.${intake.sex}`))}
      {row(t('intake.symptoms'), intake.symptoms.map((s) => t(`intake.sym.${s}`)).join(', '))}
      {row(t('intake.duration'), intake.durationDays === null ? '' : String(intake.durationDays))}
      {row(
        t('intake.danger'),
        intake.dangerSigns.length ? intake.dangerSigns.map((d) => t(`intake.ds.${d}`)).join(', ') : t('intake.none'),
      )}
      {!!intake.notes && row(t('intake.notes'), intake.notes)}
      {services.length > 0 && (
        <>
          {row(t('intake.services'), services.map((s) => t(`intake.service.${s}`, { defaultValue: s })).join(', '))}
          <Text style={[styles.disclaimer, { color: theme.textMuted }]}>{t('intake.servicesNote')}</Text>
        </>
      )}
      <Text style={[styles.disclaimer, { color: theme.textMuted }]}>{t('intake.humanDecides')}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  level: { fontSize: 20, fontWeight: '800' },
  row: { flexDirection: 'row', gap: spacing.md },
  label: { width: 110, fontSize: 14 },
  value: { flex: 1, fontSize: 15, fontWeight: '600' },
  disclaimer: { fontSize: 13, fontStyle: 'italic', marginTop: spacing.sm },
});
