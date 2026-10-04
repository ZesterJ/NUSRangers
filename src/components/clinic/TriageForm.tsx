import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import {
  PRIORITIES,
  suggestedPriority,
  VITAL_KEYS,
  vitalFlags,
  type ClinicVisit,
  type NursePriority,
  type NurseTriage,
  type VitalKey,
  type Vitals,
} from '@/intake/clinic';
import { radius, spacing, usePackContext } from '@/theme';

import { Button, Card, Chip, SectionTitle } from '../ui';

type Props = { visit: ClinicVisit; onSave: (triage: NurseTriage) => void };

const toText = (v: Vitals): Partial<Record<VitalKey, string>> =>
  Object.fromEntries(Object.entries(v).map(([k, n]) => [k, String(n)]));

const toVitals = (text: Partial<Record<VitalKey, string>>): Vitals => {
  const vitals: Vitals = {};
  for (const key of VITAL_KEYS) {
    const n = Number((text[key] ?? '').replace(',', '.'));
    if (text[key]?.trim() && Number.isFinite(n) && n > 0) vitals[key] = n;
  }
  return vitals;
};

/** Nurse step: record vital signs, set the triage priority, add notes. */
export function TriageForm({ visit, onSave }: Props) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const [text, setText] = useState(toText(visit.triage?.vitals ?? {}));
  const [priority, setPriority] = useState<NursePriority | null>(visit.triage?.priority ?? null);
  const [notes, setNotes] = useState(visit.triage?.notes ?? '');

  const vitals = toVitals(text);
  const flags = vitalFlags(visit.note, vitals);
  const suggested = suggestedPriority(visit, vitals);
  const input = [styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.background }];

  return (
    <Card>
      <Text style={[styles.heading, { color: theme.text }]}>🩺 {t('clinic.nurseTitle')}</Text>

      <SectionTitle>{t('clinic.vitals')}</SectionTitle>
      {VITAL_KEYS.map((key) => (
        <View key={key} style={styles.row}>
          <Text style={[styles.label, { color: theme.text }]}>{t(`clinic.v.${key}`)}</Text>
          <TextInput
            style={[input, styles.number]}
            keyboardType="decimal-pad"
            value={text[key] ?? ''}
            onChangeText={(v) => setText({ ...text, [key]: v })}
          />
        </View>
      ))}
      {flags.map((f) => (
        <Text key={f} style={{ color: theme.danger, fontWeight: '700' }}>
          ⚠ {t(`clinic.flag.${f}`)}
        </Text>
      ))}

      <SectionTitle>{t('clinic.priority')}</SectionTitle>
      <Text style={{ color: theme.textMuted }}>
        {t('clinic.suggested', { priority: t(`clinic.priorityOpt.${suggested}`) })}
      </Text>
      <View style={styles.chips}>
        {PRIORITIES.map((p) => (
          <Chip key={p} label={t(`clinic.priorityOpt.${p}`)} selected={priority === p} onPress={() => setPriority(p)} />
        ))}
      </View>

      <SectionTitle>{t('clinic.nurseNotes')}</SectionTitle>
      <TextInput style={[input, styles.notes]} value={notes} onChangeText={setNotes} multiline />

      <Button
        label={t('clinic.saveReport')}
        disabled={!priority}
        onPress={() => priority && onSave({ vitals, priority, notes: notes.trim(), triagedAt: Date.now() })}
      />
    </Card>
  );
}

const styles = StyleSheet.create({
  heading: { fontSize: 18, fontWeight: '800' },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, marginTop: spacing.xs },
  label: { flex: 1, fontSize: 15 },
  input: { borderWidth: 1, borderRadius: radius.md, paddingHorizontal: spacing.md, paddingVertical: spacing.sm, fontSize: 16 },
  number: { width: 96, textAlign: 'right' },
  notes: { minHeight: 72, marginBottom: spacing.md },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
});
