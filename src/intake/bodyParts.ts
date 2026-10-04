import type { DangerSign, Extraction, Symptom } from './types';

/**
 * Body diagram: tapping a body part offers the common problems for that part, so someone who cannot
 * speak or type easily can still describe the complaint. The options are symptoms and danger signs
 * from the fixed code lists, never illnesses: the app does not diagnose.
 */
export const BODY_PARTS = ['head', 'throat', 'chest', 'abdomen', 'limbs', 'skin'] as const;
export type BodyPart = (typeof BODY_PARTS)[number];

export const BODY_PART_OPTIONS: Record<BodyPart, { symptoms: Symptom[]; dangerSigns: DangerSign[] }> = {
  head: { symptoms: ['headache', 'fever'], dangerSigns: ['severe_headache_blurred_vision', 'convulsions', 'lethargic'] },
  throat: { symptoms: ['sore_throat', 'cough'], dangerSigns: ['unable_to_drink'] },
  chest: { symptoms: ['cough', 'difficulty_breathing', 'chest_pain'], dangerSigns: ['chest_indrawing'] },
  abdomen: {
    symptoms: ['abdominal_pain', 'diarrhoea', 'vomiting'],
    dangerSigns: ['vomits_everything', 'blood_in_stool', 'vaginal_bleeding', 'reduced_fetal_movement'],
  },
  limbs: { symptoms: ['limb_pain', 'weakness'], dangerSigns: [] },
  skin: { symptoms: ['rash', 'fever', 'weakness'], dangerSigns: [] },
};

export type BodyPicks = { parts: BodyPart[]; symptoms: Symptom[]; dangerSigns: DangerSign[] };
export const NO_PICKS: BodyPicks = { parts: [], symptoms: [], dangerSigns: [] };

const union = <T,>(a: T[], b: T[]) => [...a, ...b.filter((x) => !a.includes(x))];

/** Adds what the patient tapped on the diagram to the extraction. A tapped item is an explicit answer, so it is trusted. */
export function applyBodyPicks(ex: Extraction, picks: BodyPicks): Extraction {
  const symptoms = union(ex.symptoms.value, picks.symptoms);
  return {
    ...ex,
    symptoms: {
      ...ex.symptoms,
      value: symptoms,
      confidence: picks.symptoms.length && !ex.symptoms.value.length ? 'high' : ex.symptoms.confidence,
    },
    dangerSigns: { ...ex.dangerSigns, value: union(ex.dangerSigns.value, picks.dangerSigns) },
  };
}
