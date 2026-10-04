/**
 * Runs the offline intake pipeline (rules extraction → triage → clinic ranking) on scripted
 * patients and checks the outcomes. Run after changing keywords, rules or facility data:
 * `npm run check:intake`
 */
import { extractWithRules } from '@/intake/extractRules';
import { SAMPLE_FACILITIES } from '@/intake/facilities';
import { recommend } from '@/intake/recommend';
import { triage } from '@/intake/triage';
import type { ConfirmedIntake, TriageLevel } from '@/intake/types';

type Case = { name: string; answers: Record<string, string>; expect: TriageLevel };

const CASES: Case[] = [
  {
    name: 'Child, fever + cough 3 days, danger: cannot drink',
    answers: { who: 'Mtoto wangu wa miaka miwili', complaint: 'Ana homa kali na anakohoa', duration: 'Siku tatu', danger: 'Hawezi kunywa na anatapika kila kitu' },
    expect: 'refer_now',
  },
  {
    name: 'Pregnant, headache + blurred vision',
    answers: { who: 'Mimi, nina mimba ya miezi saba', complaint: 'Ninaumwa sana kichwa na naona ukungu', duration: 'Tangu jana', danger: 'Hakuna' },
    expect: 'refer_now',
  },
  {
    name: 'Child, fever since yesterday, no danger signs',
    answers: { who: 'Mtoto wangu', complaint: 'Ana homa', duration: 'Tangu jana', danger: 'Hakuna' },
    expect: 'refer_24h',
  },
  {
    name: 'Adult, mild cough today, no danger signs',
    answers: { who: 'Mimi', complaint: 'Nakohoa kidogo', duration: 'Leo', danger: 'Hakuna' },
    expect: 'home_care',
  },
  {
    name: 'Unclear answers, danger not answered',
    answers: { who: 'yeye', complaint: 'hajisikii vizuri', duration: 'muda', danger: 'sijui' },
    expect: 'unsure',
  },
];

let failed = 0;
for (const c of CASES) {
  const ex = extractWithRules(c.answers);
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
