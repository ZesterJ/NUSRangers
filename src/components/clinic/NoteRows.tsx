import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import type { ConfirmedIntake } from '@/intake/types';
import { spacing, usePackContext } from '@/theme';

/** The visit note's fields as plain rows, without the patient-facing next-step banner. */
export function NoteRows({ note }: { note: ConfirmedIntake }) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const row = (label: string, value: string) => (
    <View style={styles.row}>
      <Text style={[styles.label, { color: theme.textMuted }]}>{label}</Text>
      <Text style={[styles.value, { color: theme.text }]}>{value || '—'}</Text>
    </View>
  );
  return (
    <View style={styles.wrap}>
      {!!note.patientName && row(t('intake.name'), note.patientName)}
      {row(t('intake.who'), note.patientGroup ? t(`intake.group.${note.patientGroup}`) : '')}
      {!!note.sex && row(t('intake.sex'), t(`intake.sexOpt.${note.sex}`))}
      {row(t('intake.symptoms'), note.symptoms.map((s) => t(`intake.sym.${s}`)).join(', '))}
      {row(t('intake.duration'), note.durationDays === null ? '' : String(note.durationDays))}
      {row(t('intake.danger'), note.dangerSigns.length ? note.dangerSigns.map((d) => t(`intake.ds.${d}`)).join(', ') : t('intake.none'))}
      {!!note.notes && row(t('intake.notes'), note.notes)}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  row: { flexDirection: 'row', gap: spacing.md },
  label: { width: 110, fontSize: 14 },
  value: { flex: 1, fontSize: 15, fontWeight: '600' },
});
