import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, View } from 'react-native';

import { BODY_PART_OPTIONS, BODY_PARTS, type BodyPart, type BodyPicks } from '@/intake/bodyParts';
import { spacing, usePackContext } from '@/theme';

import { Chip, SectionTitle } from './ui';

type Props = { picks: BodyPicks; onChange: (picks: BodyPicks) => void };

const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

/** Each shape of the figure and the body part it selects. Arms and legs both select "limbs". */
const SHAPES: { part: BodyPart; style: object }[] = [
  { part: 'head', style: { left: 68, top: 0, width: 64, height: 64, borderRadius: 32 } },
  { part: 'throat', style: { left: 84, top: 62, width: 32, height: 22, borderRadius: 6 } },
  { part: 'chest', style: { left: 52, top: 82, width: 96, height: 70, borderTopLeftRadius: 24, borderTopRightRadius: 24 } },
  { part: 'abdomen', style: { left: 52, top: 154, width: 96, height: 70, borderBottomLeftRadius: 16, borderBottomRightRadius: 16 } },
  { part: 'limbs', style: { left: 20, top: 86, width: 28, height: 132, borderRadius: 14 } },
  { part: 'limbs', style: { left: 152, top: 86, width: 28, height: 132, borderRadius: 14 } },
  { part: 'limbs', style: { left: 52, top: 226, width: 46, height: 114, borderRadius: 16 } },
  { part: 'limbs', style: { left: 102, top: 226, width: 46, height: 114, borderRadius: 16 } },
];

/** Body diagram for the complaint question: tap a part, then tap the common problems that apply. */
export function BodyPicker({ picks, onChange }: Props) {
  const { theme } = usePackContext();
  const { t } = useTranslation();
  const [active, setActive] = useState<BodyPart | null>(null);

  const selectPart = (part: BodyPart) => {
    setActive(part);
    if (!picks.parts.includes(part)) onChange({ ...picks, parts: [...picks.parts, part] });
  };
  const options = active ? BODY_PART_OPTIONS[active] : null;

  return (
    <View style={styles.wrap}>
      <SectionTitle>{t('intake.bodyTitle')}</SectionTitle>
      <View style={styles.figure}>
        {SHAPES.map((shape, i) => {
          const on = picks.parts.includes(shape.part);
          return (
            <Pressable
              key={i}
              accessibilityRole="button"
              accessibilityLabel={t(`intake.part.${shape.part}`)}
              onPress={() => selectPart(shape.part)}
              style={[
                styles.shape,
                shape.style,
                {
                  backgroundColor: on ? theme.primary : theme.card,
                  borderColor: active === shape.part ? theme.text : theme.primary,
                },
              ]}
            />
          );
        })}
      </View>

      {/* The same parts as labelled buttons: clearer than the figure alone, and the only way to pick "skin". */}
      <View style={styles.chips}>
        {BODY_PARTS.map((part) => (
          <Chip key={part} label={t(`intake.part.${part}`)} selected={picks.parts.includes(part)} onPress={() => selectPart(part)} />
        ))}
      </View>

      {active && options && (
        <>
          <SectionTitle>{t('intake.bodyOptions', { part: t(`intake.part.${active}`) })}</SectionTitle>
          <View style={styles.chips}>
            {options.symptoms.map((s) => (
              <Chip
                key={s}
                label={t(`intake.sym.${s}`)}
                selected={picks.symptoms.includes(s)}
                onPress={() => onChange({ ...picks, symptoms: toggle(picks.symptoms, s) })}
              />
            ))}
            {options.dangerSigns.map((d) => (
              <Chip
                key={d}
                label={`⚠ ${t(`intake.ds.${d}`)}`}
                selected={picks.dangerSigns.includes(d)}
                onPress={() => onChange({ ...picks, dangerSigns: toggle(picks.dangerSigns, d) })}
              />
            ))}
          </View>
          <Chip
            label={t('intake.bodyRemove', { part: t(`intake.part.${active}`) })}
            onPress={() => {
              onChange({ ...picks, parts: picks.parts.filter((p) => p !== active) });
              setActive(null);
            }}
          />
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  figure: { width: 200, height: 340, alignSelf: 'center' },
  shape: { position: 'absolute', borderWidth: 2 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
});
