import type { Classification, Triage } from './types';

/**
 * Combines the backend classification model with the on-phone triage rules.
 * The model may raise the urgency ("home care" → "see a clinic") but can never lower it:
 * danger signs and the "not sure, ask a person" outcome always stand.
 */
export function applyClassification(triage: Triage, classification: Classification | null): Triage {
  if (!classification?.seeDoctor || triage.level !== 'home_care') return triage;
  return { ...triage, level: 'refer_24h', reasons: ['Assessment model recommends seeing a health worker'] };
}

/** The app shows at most three groups, most likely first. */
export const topGroups = (c: Classification | null | undefined) => (c?.diagnosisGroups ?? []).slice(0, 3).map((g) => g.group);
