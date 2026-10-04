/**
 * Evidence: how often the text extraction gets the visit-note fields right, on the team's 1,200
 * labelled synthetic statements (ml/data/raw). Compares the on-phone rules alone (what runs offline)
 * with the backend model combined with the rules (what runs with signal).
 *
 *   npm run evaluate            on-phone rules only
 *   npm run evaluate -- http://127.0.0.1:8000    also the backend model + rules
 *
 * Each dataset entry is one free-text statement, while the app asks four questions. The whole statement
 * is given as the answer to every question, so this measures reading of free text, not the guided flow.
 * The data is synthetic and team-generated: these numbers say nothing about real patients.
 */
import { readFileSync, writeFileSync } from 'node:fs';

import { extractWithRules } from '@/intake/extractRules';
import { mergeExtractions } from '@/intake/mergeExtraction';
import type { Extraction } from '@/intake/types';

type Row = {
  id: string;
  language: string;
  text: string;
  labels: { patient_type: string; symptoms: string[]; duration_days: number; danger_signs: string[] };
};

// Dataset labels → app codes. Labels with no app symptom code (they are danger signs in the app) are left out.
const SYMPTOM: Record<string, string> = {
  fever: 'fever', cough: 'cough', vomiting: 'vomiting', weakness: 'weakness', fatigue: 'weakness', diarrhoea: 'diarrhoea',
  abdominal_pain: 'abdominal_pain', headache: 'headache', breathing_difficulty: 'difficulty_breathing',
}; // prettier-ignore
const SYMPTOM_CODES = [...new Set(Object.values(SYMPTOM))];
const DANGER: Record<string, string> = {
  cannot_drink: 'unable_to_drink', convulsions: 'convulsions', bleeding: 'vaginal_bleeding',
  reduced_fetal_movement: 'reduced_fetal_movement', blurred_vision: 'severe_headache_blurred_vision',
}; // prettier-ignore
const DANGER_CODES = [...new Set(Object.values(DANGER))];
const group = (g: string | null) => (g === 'child_u5' || g === 'child_5plus' ? 'child' : g);

type Tally = { n: number; patient: number; duration: number; tp: number; fp: number; fn: number; dtp: number; dfp: number; dfn: number; exact: number };
const empty = (): Tally => ({ n: 0, patient: 0, duration: 0, tp: 0, fp: 0, fn: 0, dtp: 0, dfp: 0, dfn: 0, exact: 0 });

function score(t: Tally, row: Row, ex: Extraction) {
  const wantS = new Set(row.labels.symptoms.map((s) => SYMPTOM[s]).filter(Boolean));
  const gotS = new Set(ex.symptoms.value.filter((s) => SYMPTOM_CODES.includes(s)));
  const wantD = new Set(row.labels.danger_signs.map((s) => DANGER[s]).filter(Boolean));
  const gotD = new Set(ex.dangerSigns.value.filter((s) => DANGER_CODES.includes(s)));
  t.n++;
  if (group(ex.patientGroup.value) === row.labels.patient_type) t.patient++;
  if (ex.durationDays.value === row.labels.duration_days) t.duration++;
  for (const s of gotS) wantS.has(s) ? t.tp++ : t.fp++;
  for (const s of wantS) if (!gotS.has(s)) t.fn++;
  for (const s of gotD) wantD.has(s) ? t.dtp++ : t.dfp++;
  for (const s of wantD) if (!gotD.has(s)) t.dfn++;
  if (gotS.size === wantS.size && [...gotS].every((s) => wantS.has(s))) t.exact++;
}

const pct = (a: number, b: number) => (b ? `${((100 * a) / b).toFixed(1)}%` : 'n/a');
const line = (name: string, t: Tally) =>
  `| ${name} | ${t.n} | ${pct(t.patient, t.n)} | ${pct(t.duration, t.n)} | ${pct(t.tp, t.tp + t.fp)} | ${pct(t.tp, t.tp + t.fn)} | ${pct(t.exact, t.n)} | ${pct(t.dtp, t.dtp + t.dfp)} | ${pct(t.dtp, t.dtp + t.dfn)} |`;

async function main() {
  const backend = process.argv[2];
  const rows: Row[] = readFileSync('ml/data/raw/health_triage_ie_synthetic_v1.jsonl', 'utf8').trim().split('\n').map((l) => JSON.parse(l));
  // The model was fitted on part of this data; "held out" is the part it never saw (the ml/ derived test split).
  let heldOut = new Set<string>();
  try {
    const manifest = JSON.parse(readFileSync('ml/data/processed/baseline_split_manifest.json', 'utf8'));
    heldOut = new Set(manifest.records.filter((r: { derivedSplit: string }) => r.derivedSplit === 'test').map((r: { id: string }) => r.id));
  } catch {
    console.warn('No derived split manifest (run ml/src/train_symptom_model.py); held-out rows not reported.');
  }

  const tallies: Record<string, Tally> = {};
  const add = (name: string, row: Row, ex: Extraction) => score((tallies[name] ??= empty()), row, ex);
  let failed = 0;
  for (const row of rows) {
    const answers = { who: row.text, complaint: row.text, duration: row.text, danger: row.text };
    const rules = extractWithRules(answers);
    const sets = ['all', row.language === 'sw' ? 'Swahili' : 'English', ...(heldOut.has(row.id) ? ['held out'] : [])];
    for (const set of sets) add(`On-phone rules, ${set}`, row, rules);
    if (backend) {
      try {
        const res = await fetch(`${backend}/extract`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ locale: row.language, answers }) });
        if (!res.ok) throw new Error(String(res.status));
        const merged = mergeExtractions((await res.json()) as Extraction, rules);
        for (const set of sets) add(`Backend model + rules, ${set}`, row, merged);
      } catch {
        failed++;
      }
    }
  }

  const out = [
    '| Extractor, data | Statements | Patient type | Duration (exact days) | Symptom precision | Symptom recall | All symptoms right | Danger-sign precision | Danger-sign recall |',
    '|---|---|---|---|---|---|---|---|---|',
    ...Object.keys(tallies).sort().map((k) => line(k, tallies[k])),
  ].join('\n');
  console.log(out);
  if (failed) console.log(`\n${failed} backend calls failed and were left out.`);
  writeFileSync('docs/evidence-extraction.md', `<!-- Generated by scripts/evaluate-extraction.ts; do not edit. -->\n${out}\n`);
}

main();
