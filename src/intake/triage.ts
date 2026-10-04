import type { Capability, ConfirmedIntake, Extraction, Triage } from './types';

/**
 * Constrained triage: a fixed list of outcomes from WHO community case management danger signs.
 * It never diagnoses. "unsure" sends the decision to a health worker instead of guessing.
 */
export function triage(intake: ConfirmedIntake, extraction?: Extraction): Triage {
  const reasons: string[] = [];
  const needs: Capability[] = [];
  const g = intake.patientGroup;

  if (g === 'pregnant') needs.push('maternity');
  if (g === 'child_u5') needs.push('under5');

  if (intake.dangerSigns.length > 0) {
    reasons.push(`Danger sign: ${intake.dangerSigns.map((d) => d.replace(/_/g, ' ')).join(', ')}`);
    needs.push('emergency');
    return { level: 'refer_now', reasons, needs };
  }

  // Not enough information to rule danger signs out → a person decides.
  const missing: string[] = [];
  if (!g) missing.push('who is sick');
  if (intake.symptoms.length === 0 && !intake.notes.trim()) missing.push('main problem');
  if (extraction && extraction.dangerSigns.confidence === 'low' && extraction.dangerSigns.value.length === 0)
    missing.push('danger signs not confirmed');
  if (missing.length) {
    reasons.push(`Not enough information: ${missing.join(', ')}`);
    return { level: 'unsure', reasons, needs: [...needs, 'general'] };
  }

  const d = intake.durationDays ?? 0;
  const feverChild = g === 'child_u5' && intake.symptoms.includes('fever');
  if (intake.symptoms.includes('difficulty_breathing')) reasons.push('Difficulty breathing');
  if (feverChild) reasons.push('Child under 5 with fever: malaria test recommended');
  if (g === 'pregnant') reasons.push('Pregnancy: any illness should be assessed at a clinic');
  if (d >= 3) reasons.push(`Symptoms for ${d} days`);

  if (reasons.length) {
    if (feverChild) needs.push('lab');
    return { level: 'refer_24h', reasons, needs: needs.length ? needs : ['general'] };
  }

  reasons.push('No danger signs; symptoms are mild and recent');
  return { level: 'home_care', reasons, needs: ['general'] };
}
