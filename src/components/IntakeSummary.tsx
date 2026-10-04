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

/** "Home care, check again in 2 days" as a date the patient can act on. */
const FOLLOW_UP_DAYS = 2;
function followUpDate(madeAt: number, locale: string) {
  const date = new Date(madeAt + FOLLOW_UP_DAYS * 24 * 60 * 60 * 1000);
  return date.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long' });
}

/** Triage result + confirmed answers. Used on the result screen, the clinic scan screen and records. */
export function IntakeSummary({
  intake,
  triage,
  services = [],
  madeAt,
}: {
  intake: ConfirmedIntake;
  triage: Triage;
  /** Care services proposed by the backend, if it ran. */
  services?: string[];
  /** When the note was made; gives "home care" a date to check again. */
  madeAt?: number;
}) {
  const { theme, scale, locale } = usePackContext();
  const { t } = useTranslation();
  const color =
    triage.level === 'refer_now'
      ? theme.danger
      : triage.level === 'refer_24h' || triage.level === 'unsure'
        ? theme.warning
        : theme.success;

  const row = (label: string, value: string) => (
    <View style={styles.row}>
      <Text style={[styles.label, { color: theme.textMuted, fontSize: 14 * scale }]}>{label}</Text>
      <Text style={[styles.value, { color: theme.text, fontSize: 15 * scale }]}>{value || '—'}</Text>
    </View>
  );

  return (
    <Card style={{ borderColor: color, borderWidth: 2 }}>
      <Text style={[styles.level, { color, fontSize: 20 * scale }]}>
        {LEVEL_ICON[triage.level]} {t(`intake.level.${triage.level}`)}
      </Text>
      {triage.reasons.map((r) => (
        <Text key={r} style={{ color: theme.text, fontSize: 15 * scale }}>
          • {r}
        </Text>
      ))}
      {triage.level === 'home_care' && madeAt !== undefined && (
        <Text style={{ color: theme.text, fontWeight: '700', fontSize: 15 * scale }}>
          📅 {t('intake.followUp', { date: followUpDate(madeAt, locale) })}
        </Text>
      )}
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
