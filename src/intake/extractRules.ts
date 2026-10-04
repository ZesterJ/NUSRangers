import type { DangerSign, Extraction, PatientGroup, Symptom } from './types';

/**
 * Offline, rule-based extractor: the guaranteed fallback when the trained parser (backend /extract)
 * is unreachable. Keyword lists cover Swahili and English. Anything matched only weakly is marked
 * `low` confidence so the patient is asked to check it.
 *
 * Swahili keywords need review by a native speaker; extend them with the parser team's error analysis.
 */

const norm = (s: string) =>
  s
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const has = (text: string, words: string[]) => words.some((w) => text.includes(w));

const GROUP: Record<PatientGroup, string[]> = {
  pregnant: ['mimba', 'mjamzito', 'pregnant', 'pregnancy'],
  child_u5: ['mtoto', 'mwanangu', 'mtoto mchanga', 'child', 'baby', 'son', 'daughter', 'toddler'],
  child_5plus: [], // only set from the tap-to-answer options, where the age band is explicit
  adult: ['mimi', 'mume', 'mke', 'baba', 'mama', 'myself', 'husband', 'wife', 'father', 'mother', 'me '],
};

const SYMPTOM_WORDS: Record<Symptom, string[]> = {
  fever: ['homa', 'joto', 'fever', 'hot'],
  cough: ['kikohozi', 'anakohoa', 'nakohoa', 'kukohoa', 'cough'],
  difficulty_breathing: ['kupumua', 'pumzi', 'shida ya kupumua', 'breath', 'breathing'],
  diarrhoea: ['kuhara', 'harisha', 'diarrhoea', 'diarrhea', 'loose stool'],
  vomiting: ['kutapika', 'anatapika', 'natapika', 'vomit'],
  headache: ['kichwa', 'headache', 'head ache'],
  abdominal_pain: ['tumbo', 'stomach', 'abdominal', 'belly'],
  rash: ['upele', 'vipele', 'rash'],
  weakness: ['udhaifu', 'dhaifu', 'uchovu', 'weak', 'tired'],
  sore_throat: ['koo', 'sore throat', 'throat hurts'],
  chest_pain: ['maumivu ya kifua', 'kifua kinauma', 'chest pain', 'chest hurts'],
  limb_pain: ['maumivu ya viungo', 'mguu unauma', 'mkono unauma', 'joint pain', 'leg pain', 'arm pain'],
};

const DANGER_WORDS: Record<DangerSign, string[]> = {
  unable_to_drink: ['hawezi kunywa', 'siwezi kunywa', 'hanywi', 'cannot drink', 'can t drink', 'unable to drink', 'not drinking'],
  vomits_everything: ['kila kitu', 'vomits everything', 'vomiting everything'],
  convulsions: ['degedege', 'kifafa', 'convulsion', 'fits', 'seizure'],
  lethargic: ['usingizi mzito', 'hajitambui', 'lethargic', 'very sleepy', 'unconscious', 'hard to wake'],
  chest_indrawing: ['kifua kinavutika', 'chest indrawing', 'chest pulls in'],
  vaginal_bleeding: ['kutoka damu', 'natoka damu', 'damu ukeni', 'bleeding'],
  severe_headache_blurred_vision: ['ukungu', 'blurred', 'blurry'],
  reduced_fetal_movement: ['hachezi', 'mtoto hachezi', 'baby not moving', 'less movement'],
  blood_in_stool: ['damu kwenye choo', 'blood in stool', 'bloody stool'],
};

const NONE_WORDS = ['hakuna', 'none', 'no ', 'nothing'];

const NUMBER_WORDS: Record<string, number> = {
  moja: 1, mbili: 2, tatu: 3, nne: 4, tano: 5, sita: 6, saba: 7, nane: 8, tisa: 9, kumi: 10,
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
};

function parseDuration(text: string): { days: number | null; sure: boolean } {
  if (has(text, ['leo', 'today'])) return { days: 0, sure: true };
  if (has(text, ['jana', 'yesterday'])) return { days: 1, sure: true };
  const unit = has(text, ['wiki', 'week']) ? 7 : has(text, ['mwezi', 'month']) ? 30 : has(text, ['siku', 'day']) ? 1 : null;
  const digit = text.match(/\b(\d{1,2})\b/);
  const word = Object.keys(NUMBER_WORDS).find((w) => new RegExp(`\\b${w}\\b`).test(text));
  const n = digit ? Number(digit[1]) : word ? NUMBER_WORDS[word] : unit ? 1 : null;
  if (n === null) return { days: null, sure: false };
  return { days: n * (unit ?? 1), sure: unit !== null };
}

/** answers: one string per guided question, keyed by question id. */
export function extractWithRules(answers: Partial<Record<'who' | 'complaint' | 'duration' | 'danger', string>>): Extraction {
  const who = norm(answers.who ?? '');
  const complaint = norm(answers.complaint ?? '');
  const duration = norm(answers.duration ?? '');
  const danger = norm(answers.danger ?? '');
  const all = ` ${who} ${complaint} ${duration} ${danger} `;

  // Pregnancy wins over "mimi"/"me", child over adult when both appear.
  const groupHit = (['pregnant', 'child_u5', 'adult'] as PatientGroup[]).find((g) => has(` ${who} `, GROUP[g]));
  const groupAnywhere = groupHit ?? (['pregnant', 'child_u5'] as PatientGroup[]).find((g) => has(all, GROUP[g]));

  const symptoms = (Object.keys(SYMPTOM_WORDS) as Symptom[]).filter((s) => has(all, SYMPTOM_WORDS[s]));
  const dangerSigns = (Object.keys(DANGER_WORDS) as DangerSign[]).filter((d) => has(all, DANGER_WORDS[d]));
  const saidNone = has(` ${danger} `, NONE_WORDS);
  const dur = parseDuration(duration);

  const unmapped = [answers.complaint, answers.danger].filter(
    (a): a is string => !!a && symptoms.length === 0 && dangerSigns.length === 0,
  );

  return {
    patientGroup: { value: groupAnywhere ?? null, confidence: groupHit ? 'high' : 'low', evidence: answers.who },
    symptoms: { value: symptoms, confidence: symptoms.length ? 'high' : 'low', evidence: answers.complaint },
    durationDays: { value: dur.days, confidence: dur.sure ? 'high' : 'low', evidence: answers.duration },
    dangerSigns: {
      value: dangerSigns,
      // Only trust "no danger signs" when the patient explicitly said none.
      confidence: dangerSigns.length || saidNone ? 'high' : 'low',
      evidence: answers.danger,
    },
    unmapped,
    source: 'rules',
  };
}
