/**
 * Runs the offline intake pipeline (rules extraction → triage → clinic ranking) on scripted
 * patients and checks the outcomes. Run after changing keywords, rules or facility data:
 * `npm run check:intake`
 */
import { extractWithRules } from '@/intake/extractRules';
import { mergeExtractions } from '@/intake/mergeExtraction';
import { SAMPLE_FACILITIES } from '@/intake/facilities';
import { recommend } from '@/intake/recommend';
import { triage } from '@/intake/triage';
import type { ConfirmedIntake, Extraction, TriageLevel } from '@/intake/types';

/** `model` is what the backend /extract returned for these answers (recorded from the real model). */
type Case = { name: string; answers: Record<string, string>; expect: TriageLevel; model: Extraction };

const model = (
  group: Extraction['patientGroup'],
  symptoms: Extraction['symptoms'],
  days: Extraction['durationDays'],
  danger: Extraction['dangerSigns'],
  unmapped: string[] = [],
): Extraction => ({ patientGroup: group, symptoms, durationDays: days, dangerSigns: danger, unmapped, source: 'model' });
const hi = <T,>(value: T) => ({ value, confidence: 'high' as const });
const lo = <T,>(value: T) => ({ value, confidence: 'low' as const });

const CASES: Case[] = [
  {
    name: 'Child, fever + cough 3 days, danger: cannot drink',
    answers: { who: 'Mtoto wangu wa miaka miwili', complaint: 'Ana homa kali na anakohoa', duration: 'Siku tatu', danger: 'Hawezi kunywa na anatapika kila kitu' },
    expect: 'refer_now',
    model: model(hi('child_u5'), hi(['cough', 'fever', 'vomiting']), hi(3), hi(['unable_to_drink'])),
  },
  {
    name: 'Pregnant, headache + blurred vision',
    answers: { who: 'Mimi, nina mimba ya miezi saba', complaint: 'Ninaumwa sana kichwa na naona ukungu', duration: 'Tangu jana', danger: 'Hakuna' },
    expect: 'refer_now',
    model: model(lo(null), lo([]), lo(null), hi(['severe_headache_blurred_vision'])),
  },
  {
    name: 'Child, fever since yesterday, no danger signs',
    answers: { who: 'Mtoto wangu', complaint: 'Ana homa', duration: 'Tangu jana', danger: 'Hakuna' },
    expect: 'refer_24h',
    model: model(lo('child_u5'), hi(['fever']), lo(null), hi([])),
  },
  {
    name: 'Adult, mild cough today, no danger signs',
    answers: { who: 'Mimi', complaint: 'Nakohoa kidogo', duration: 'Leo', danger: 'Hakuna' },
    expect: 'home_care',
    model: model(lo(null), lo([]), lo(null), hi([]), ['Nakohoa kidogo']),
  },
  {
    name: 'Unclear answers, danger not answered',
    answers: { who: 'yeye', complaint: 'hajisikii vizuri', duration: 'muda', danger: 'sijui' },
    expect: 'unsure',
    model: model(lo(null), lo([]), lo(null), lo([]), ['hajisikii vizuri', 'sijui']),
  },
];

let failed = 0;
const RUNS = CASES.flatMap((c) => {
  const rules = extractWithRules(c.answers);
  return [
    { ...c, name: `${c.name} [offline rules]`, ex: rules },
    { ...c, name: `${c.name} [backend model + rules]`, ex: mergeExtractions(c.model, rules) },
  ];
});

for (const c of RUNS) {
  const ex = c.ex;
  const intake: ConfirmedIntake = {
    patientGroup: ex.patientGroup.value,
    symptoms: ex.symptoms.value,
    durationDays: ex.durationDays.value,
    dangerSigns: ex.dangerSigns.value,
    notes: ex.unmapped.join(' · '),
  };
  const t = triage(intake, ex);
  const recs = recommend(SAMPLE_FACILITIES, t);
  const ok = t.level === c.expect;
  if (!ok) failed++;
  console.log(`${ok ? '✓' : '✗'} ${c.name}`);
  console.log(`   extracted: ${intake.patientGroup} | ${intake.symptoms.join(',') || '-'} | ${intake.durationDays ?? '?'}d | danger: ${intake.dangerSigns.join(',') || 'none'}`);
  console.log(`   triage: ${t.level} (expected ${c.expect}) — ${t.reasons.join('; ')}`);
  console.log(`   clinics: ${recs.map((r) => `${r.facility.name} [${r.score}${r.stale ? ', call ahead' : ''}]`).join(' > ') || 'none in range'}`);
}
if (failed) {
  console.log(`\n${failed} case(s) failed`);
  process.exit(1);
}
console.log('\nAll intake cases OK');
