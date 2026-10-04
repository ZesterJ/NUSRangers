import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, TextInput, View } from 'react-native';

import {
  askPregnancy,
  dangerOptions,
  DURATION_OPTIONS,
  WHO_OPTIONS,
  type Choices,
  type Pregnant,
} from '@/intake/choices';
import type { Sex } from '@/intake/types';
import { useBilingual } from '@/i18n/bilingual';
import { radius, spacing, usePackContext } from '@/theme';

import { Chip, SectionTitle } from './ui';

type Props = { choices: Choices; onChange: (choices: Choices) => void };

const SEXES: Sex[] = ['female', 'male'];
const PREGNANT: Pregnant[] = ['yes', 'no', 'unsure'];

/** "Who is the patient?": relationship, name, sex, and pregnancy where it applies. */
export function WhoOptions({ choices, onChange }: Props) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const bi = useBilingual();
  return (
    <View style={styles.wrap}>
      <View style={styles.chips}>
        {WHO_OPTIONS.map((w) => (
          <Chip key={w} label={bi(`intake.whoOpt.${w}`)} selected={choices.who === w} onPress={() => onChange({ ...choices, who: w })} />
        ))}
      </View>

      <SectionTitle>{bi('intake.name')}</SectionTitle>
      <TextInput
        style={[styles.input, { color: theme.text, borderColor: theme.border, backgroundColor: theme.card }]}
        value={choices.name}
        onChangeText={(name) => onChange({ ...choices, name })}
        placeholder={t('intake.namePlaceholder')}
        placeholderTextColor={theme.textMuted}
        autoCapitalize="words"
      />

      <SectionTitle>{bi('intake.sex')}</SectionTitle>
      <View style={styles.chips}>
        {SEXES.map((s) => (
          <Chip key={s} label={bi(`intake.sexOpt.${s}`)} selected={choices.sex === s} onPress={() => onChange({ ...choices, sex: s })} />
        ))}
      </View>

      {askPregnancy(choices) && (
        <>
          <SectionTitle>{bi('intake.pregnantQ')}</SectionTitle>
          <View style={styles.chips}>
            {PREGNANT.map((p) => (
              <Chip
                key={p}
                label={bi(`intake.pregnantOpt.${p}`)}
                selected={choices.pregnant === p}
                onPress={() => onChange({ ...choices, pregnant: p })}
              />
            ))}
          </View>
        </>
      )}
    </View>
  );
}

/** "How long?": common durations, or a number of days under "Other". */
export function DurationOptions({ choices, onChange }: Props) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const bi = useBilingual();
  const isPreset = choices.durationDays !== null && DURATION_OPTIONS.includes(choices.durationDays);
  const [other, setOther] = useState(choices.durationDays !== null && !isPreset);
  return (
    <View style={styles.wrap}>
      <View style={styles.chips}>
        {DURATION_OPTIONS.map((d) => (
          <Chip
            key={d}
            label={bi(`intake.dur.d${d}`)}
            selected={!other && choices.durationDays === d}
            onPress={() => {
              setOther(false);
              onChange({ ...choices, durationDays: d });
            }}
          />
        ))}
        <Chip
          label={bi('intake.dur.other')}
          selected={other}
          onPress={() => {
            setOther(true);
            onChange({ ...choices, durationDays: null });
          }}
        />
      </View>
      {other && (
        <TextInput
          style={[styles.input, styles.short, { color: theme.text, borderColor: theme.border, backgroundColor: theme.card }]}
          keyboardType="numeric"
          value={choices.durationDays === null ? '' : String(choices.durationDays)}
          onChangeText={(v) => {
            const digits = v.replace(/\D/g, '');
            onChange({ ...choices, durationDays: digits === '' ? null : Number(digits) });
          }}
          placeholder={t('intake.dur.otherDays')}
          placeholderTextColor={theme.textMuted}
        />
      )}
    </View>
  );
}

/** Danger-sign checklist, with an explicit "None of these". */
export function DangerOptions({ choices, onChange }: Props) {
  const bi = useBilingual();
  return (
    <View style={styles.chips}>
      {dangerOptions(choices).map((d) => {
        const on = choices.dangerSigns.includes(d);
        return (
          <Chip
            key={d}
            label={bi(`intake.ds.${d}`)}
            selected={on}
            onPress={() =>
              onChange({
                ...choices,
                noDanger: false,
                dangerSigns: on ? choices.dangerSigns.filter((x) => x !== d) : [...choices.dangerSigns, d],
              })
            }
          />
        );
      })}
      <Chip
        label={bi('intake.noneOfThese')}
        selected={choices.noDanger}
        onPress={() => onChange({ ...choices, noDanger: !choices.noDanger, dangerSigns: [] })}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  input: { borderWidth: 1, borderRadius: radius.md, padding: spacing.md, minHeight: 48, fontSize: 16 },
  short: { width: 180 },
});
