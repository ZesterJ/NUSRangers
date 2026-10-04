import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { DANGER_SIGNS, SYMPTOMS, type ConfirmedIntake, type PatientGroup } from '@/intake/types';
import { radius, spacing, usePackContext } from '@/theme';

import { Chip } from '../ui';

const GROUPS: PatientGroup[] = ['child_u5', 'child_5plus', 'pregnant', 'adult'];
const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

/** The visit note's clinical fields as editable chips, for the nurse to correct. */
export function NoteEditor({ note, onChange }: { note: ConfirmedIntake; onChange: (note: ConfirmedIntake) => void }) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const input = [styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.background }];
  const label = (text: string) => <Text style={[styles.label, { color: theme.textMuted }]}>{text}</Text>;

  return (
    <View style={styles.wrap}>
      {label(t('intake.who'))}
      <View style={styles.chips}>
        {GROUPS.map((g) => (
          <Chip key={g} label={t(`intake.group.${g}`)} selected={note.patientGroup === g} onPress={() => onChange({ ...note, patientGroup: g })} />
        ))}
      </View>

      {label(t('intake.symptoms'))}
      <View style={styles.chips}>
        {SYMPTOMS.map((s) => (
          <Chip
            key={s}
            label={t(`intake.sym.${s}`)}
            selected={note.symptoms.includes(s)}
            onPress={() => onChange({ ...note, symptoms: toggle(note.symptoms, s) })}
          />
        ))}
      </View>

      {label(t('intake.duration'))}
      <TextInput
        style={[input, styles.short]}
        keyboardType="numeric"
        value={note.durationDays === null ? '' : String(note.durationDays)}
        onChangeText={(v) => {
          const digits = v.replace(/\D/g, '');
          onChange({ ...note, durationDays: digits === '' ? null : Number(digits) });
        }}
      />

      {label(t('intake.danger'))}
      <View style={styles.chips}>
        {DANGER_SIGNS.map((d) => (
          <Chip
            key={d}
            label={t(`intake.ds.${d}`)}
            selected={note.dangerSigns.includes(d)}
            onPress={() => onChange({ ...note, dangerSigns: toggle(note.dangerSigns, d) })}
          />
        ))}
      </View>

      {label(t('intake.notes'))}
      <TextInput style={input} value={note.notes} onChangeText={(notes) => onChange({ ...note, notes })} multiline />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  label: { fontSize: 13, fontWeight: '700', marginTop: spacing.xs },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  input: { borderWidth: 1, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontSize: 16 },
  short: { width: 96 },
});
