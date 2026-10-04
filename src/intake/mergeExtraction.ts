import type { DangerSign, Extraction, Symptom } from './types';

/** Codes the backend model has no label for; these always come from the on-phone rules. */
const RULES_ONLY_SIGNS: DangerSign[] = ['vomits_everything', 'lethargic', 'chest_indrawing', 'blood_in_stool'];
const RULES_ONLY_SYMPTOMS: Symptom[] = ['rash'];

const union = <T,>(a: T[], b: T[]) => [...a, ...b.filter((x) => !a.includes(x))];

/**
 * Combines the backend model's extraction with the on-phone rules. The model is preferred where it
 * is confident (it handles negation and who the statement is about); the rules fill what it leaves
 * empty. Where the model is not confident, both are shown and the field is marked for the patient to verify.
 * Danger signs are never dropped: a wrong extra one is corrected on the review screen, a missed one is not.
 */
export function mergeExtractions(model: Extraction, rules: Extraction): Extraction {
  const sure = (f: { confidence: string }) => f.confidence === 'high';

  let patientGroup = model.patientGroup;
  if (rules.patientGroup.value === 'pregnant' && sure(rules.patientGroup)) patientGroup = rules.patientGroup;
  else if (model.patientGroup.value === null) patientGroup = rules.patientGroup;
  else if (!sure(model.patientGroup) && rules.patientGroup.value && rules.patientGroup.value !== model.patientGroup.value)
    patientGroup = { ...rules.patientGroup, confidence: 'low' };

  // The keyword rules cannot tell "fever" from "no fever"; the model can, so its denials win.
  const denied = model.negatedSymptoms ?? [];
  const fromRules = rules.symptoms.value.filter((s) => !denied.includes(s));
  const symptoms = sure(model.symptoms)
    ? union(model.symptoms.value, fromRules.filter((s) => RULES_ONLY_SYMPTOMS.includes(s)))
    : union(model.symptoms.value, fromRules);

  const dangerSigns = sure(model.dangerSigns)
    ? union(model.dangerSigns.value, rules.dangerSigns.value.filter((d) => RULES_ONLY_SIGNS.includes(d)))
    : union(model.dangerSigns.value, rules.dangerSigns.value);

  return {
    patientGroup,
    symptoms: { ...model.symptoms, value: symptoms },
    durationDays: model.durationDays.value !== null ? model.durationDays : rules.durationDays,
    dangerSigns: { ...model.dangerSigns, value: dangerSigns },
    unmapped: model.unmapped,
    source: 'model',
  };
}
