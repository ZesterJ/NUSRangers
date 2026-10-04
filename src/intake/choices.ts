import type { DangerSign, Extraction, PatientGroup, Sex } from './types';

/**
 * Tap-to-answer options for the guided questions, as an alternative to speaking or typing.
 * A tapped option is an explicit answer, so it overrides what was extracted from free text.
 */
export type WhoOption = 'self' | 'child_u5' | 'child_5plus' | 'other_adult';
export const WHO_OPTIONS: WhoOption[] = ['self', 'child_u5', 'child_5plus', 'other_adult'];
export type Pregnant = 'yes' | 'no' | 'unsure';

export type Choices = {
  who: WhoOption | null;
  name: string;
  sex: Sex | null;
  pregnant: Pregnant | null;
  durationDays: number | null;
  dangerSigns: DangerSign[];
  /** The patient tapped "None of these" on the danger-sign checklist. */
  noDanger: boolean;
};
export const NO_CHOICES: Choices = {
  who: null,
  name: '',
  sex: null,
  pregnant: null,
  durationDays: null,
  dangerSigns: [],
  noDanger: false,
};

/** Duration shortcuts in days; anything else is entered as a number under "Other". */
export const DURATION_OPTIONS = [1, 2, 3, 7];

const GENERAL_SIGNS: DangerSign[] = ['unable_to_drink', 'vomits_everything', 'convulsions', 'lethargic', 'chest_indrawing', 'blood_in_stool'];
const PREGNANCY_SIGNS: DangerSign[] = ['vaginal_bleeding', 'severe_headache_blurred_vision', 'reduced_fetal_movement'];

/** The pregnancy question only applies to a female patient who is not a child. */
export const askPregnancy = (c: Choices) => c.sex === 'female' && (c.who === 'self' || c.who === 'other_adult');

/** Pregnancy danger signs are offered when the patient is pregnant, or when we do not know who the patient is. */
export const dangerOptions = (c: Choices): DangerSign[] =>
  c.who === null || (askPregnancy(c) && c.pregnant !== 'no') ? [...GENERAL_SIGNS, ...PREGNANCY_SIGNS] : GENERAL_SIGNS;

const union = <T,>(a: T[], b: T[]) => [...a, ...b.filter((x) => !a.includes(x))];

export function applyChoices(ex: Extraction, c: Choices): Extraction {
  let patientGroup = ex.patientGroup;
  if (c.who === 'child_u5' || c.who === 'child_5plus') patientGroup = { value: c.who, confidence: 'high' };
  else if (c.who) {
    const group: PatientGroup = askPregnancy(c) && c.pregnant === 'yes' ? 'pregnant' : 'adult';
    // A woman whose pregnancy question was skipped or answered "not sure" is flagged for checking.
    const open = askPregnancy(c) && c.pregnant !== 'yes' && c.pregnant !== 'no';
    patientGroup = { value: group, confidence: open ? 'low' : 'high' };
  }

  const dangerSigns = union(ex.dangerSigns.value, c.dangerSigns);
  return {
    ...ex,
    patientGroup,
    durationDays: c.durationDays !== null ? { value: c.durationDays, confidence: 'high' } : ex.durationDays,
    dangerSigns: {
      ...ex.dangerSigns,
      value: dangerSigns,
      // "None of these" tapped while the typed text names a danger sign is a contradiction: the sign stays, but ask for a check.
      confidence: c.dangerSigns.length ? 'high' : c.noDanger ? (dangerSigns.length ? 'low' : 'high') : ex.dangerSigns.confidence,
    },
  };
}
