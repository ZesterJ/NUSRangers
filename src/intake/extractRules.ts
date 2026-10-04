import type { DangerSign, Extraction, PatientGroup, Symptom } from './types';

/**
 * Offline, rule-based extractor: the guaranteed fallback when the trained parser (backend /extract)
 * is unreachable. Keyword lists cover Swahili and English. Anything matched only weakly is marked
 * `low` confidence so the patient is asked to check it.
 *
 * Typed input is messy, so symptoms are read with three safeguards (backtest: scripts/check-typed-input.ts):
 *  - a symptom is not asserted when a denial comes before it in the same sentence ("no fever", "sina homa", "dont have
 *    fever"), or when the sentence is hedged or past ("maybe fever", "labda homa", "had fever last year");
 *  - apostrophe look-alikes, invisible characters and full-width letters are cleaned first;
 *  - a word one typo away from a symptom word is suggested at LOW confidence and noted, never asserted.
 * Danger signs deliberately stay over-asserted: a wrong extra one is corrected on the review screen, a missed one is not.
 *
 * Swahili keywords need review by a native speaker; extend them with the parser team's error analysis.
 */

const APOSTROPHES = /[’‘ʼ`´′‵ʹ＇]/g;
const INVISIBLE = /[​-‍⁠﻿­‎‏‪-‮⁦-⁩]/g;

const norm = (s: string) =>
  s
    .replace(APOSTROPHES, "'") // before NFKC, which would turn U+00B4 into a space plus an accent
    .normalize('NFKC')
    .replace(INVISIBLE, '')
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

// ---- denial and hedging ---------------------------------------------------------------------------------------

/** Sentence breaks, plus "but"/"lakini" and ", only": a denial does not carry across them. Newlines count as breaks. */
const SEGMENT = /[.;!?\n]+|,\s*(?:only|just)\b|\b(?:but|however|lakini)\b/gi;
/** Denial cues, on normalised text (apostrophes became spaces or vanished: "don't" -> "don t", "dont"). */
const NEGATION =
  /\b(?:no|not|never|without|none|nothing|nor|neither|denies|denied|(?:do|does|did|is|was|has|had|have)\s?n\s?t|sina|hana|hakuna|hamna|haina|hawana|hatuna|bila|sio|siyo|si)\b/g;
const HEDGED =
  /\b(?:maybe|perhaps|possibly|might|unsure|not sure|could be|labda|huenda|sina uhakika|used to|last year|previously|resolved|stopped|no longer|imeisha|zamani)\b/;

type Segment = { text: string; hedged: boolean; denialEnds: number[] };

/** Splits a typed answer into sentences and finds, in each, where every denial cue ends. */
function segments(raw: string): Segment[] {
  return raw
    .split(SEGMENT)
    .map((part) => norm(part).replace(/\bnot only\b/g, 'also'))
    .filter(Boolean)
    .map((text) => ({
      text,
      hedged: HEDGED.test(text),
      denialEnds: [...text.matchAll(NEGATION)].map((m) => (m.index ?? 0) + m[0].length),
    }));
}

/**
 * Where `word` occurs in `text`. Keywords of four letters or fewer ("koo", "hot", "homa") must be whole words, otherwise "koo"
 * fires inside the typo "kikoohozi" and reads as a sore throat; longer keywords still match inside words (Swahili verbs).
 */
function occurrences(text: string, word: string): number[] {
  const at: number[] = [];
  const whole = word.trim().length <= 4;
  for (let i = text.indexOf(word); i !== -1; i = text.indexOf(word, i + 1)) {
    const before = text[i - 1];
    const after = text[i + word.length];
    if (!whole || ((before === undefined || before === ' ') && (after === undefined || after === ' '))) at.push(i);
  }
  return at;
}

/** Patient-group words: short ones ("son", "mke", "me") are whole words, so "son" is not found in "person" or "poisoning". */
const hasWord = (text: string, words: string[]) => words.some((w) => occurrences(text, w.trim()).length > 0);

/** True when some word occurs un-denied in a non-hedged sentence. A denial counts for everything after it in the sentence. */
function affirmed(segs: Segment[], words: string[]): boolean {
  return segs.some(
    (seg) => !seg.hedged && words.some((w) => occurrences(seg.text, w).some((i) => !seg.denialEnds.some((end) => end <= i))),
  );
}

// ---- typos: suggest, never assert -----------------------------------------------------------------------------

type Near = { kind: 'symptom'; code: Symptom } | { kind: 'sign'; code: DangerSign };
const NEAR: Record<string, Near> = {};
const addNear = (code: Symptom, words: string[]) => words.forEach((w) => (NEAR[w] = { kind: 'symptom', code }));
addNear('fever', ['fever', 'feverish', 'homa']);
addNear('cough', ['cough', 'coughing', 'kikohozi', 'kukohoa', 'anakohoa', 'ninakohoa', 'nakohoa']);
addNear('diarrhoea', ['diarrhoea', 'diarrhea', 'kuhara', 'kuharisha', 'anaharisha', 'ninaharisha']);
addNear('vomiting', ['vomiting', 'vomit', 'kutapika', 'anatapika', 'ninatapika', 'natapika']);
addNear('headache', ['headache', 'kichwa']);
addNear('abdominal_pain', ['stomach', 'abdominal', 'tumbo']);
addNear('difficulty_breathing', ['breathing', 'kupumua']);
addNear('weakness', ['weakness', 'weak', 'tired', 'fatigue', 'exhausted', 'dhaifu', 'udhaifu', 'uchovu']);
addNear('rash', ['rash', 'upele', 'vipele']);
for (const w of ['convulsions', 'convulsion', 'seizure', 'seizures', 'degedege', 'kifafa']) NEAR[w] = { kind: 'sign', code: 'convulsions' };
NEAR.bleeding = { kind: 'sign', code: 'vaginal_bleeding' };

/** Ordinary words one edit from a symptom word: without this, "never had fever" would flag "never" as a typo of "fever". */
const COMMON = new Set(
  ('never ever fewer lever sever tough rough couch tried tires tiled week weeks home hope hole holy hama wear beak peak leak ' +
    'seek weed heal head heads ached bleed breed feeding feeling feels heading hearing leading reading dealing weaker weaken ' +
    'weakly vomits tire fiver fibre ham').split(' '),
);
const KEYWORD_WORDS = Object.values(SYMPTOM_WORDS).flat();

/** Edit distance counting a swap of two neighbouring letters as one edit; gives up (limit + 1) once it must exceed `limit`. */
function osa(a: string, b: string, limit: number): number {
  if (Math.abs(a.length - b.length) > limit) return limit + 1;
  let prev2: number[] | null = null;
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    for (let j = 1; j <= b.length; j++) {
      let cost = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      if (prev2 && i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) cost = Math.min(cost, prev2[j - 2] + 1);
      cur.push(cost);
    }
    prev2 = prev;
    prev = cur;
  }
  return prev[b.length];
}

type Suggestion = { word: string } & Near;

function nearMisses(segs: Segment[]): Suggestion[] {
  const found: Suggestion[] = [];
  for (const seg of segs) {
    if (seg.hedged) continue;
    for (const m of seg.text.matchAll(/\p{L}+/gu)) {
      const token = m[0];
      const at = m.index ?? 0;
      if (token in NEAR || COMMON.has(token) || KEYWORD_WORDS.some((w) => occurrences(token, w).length)) continue;
      const lastEnd = Math.max(-1, ...seg.denialEnds.filter((e) => e <= at));
      if (lastEnd >= 0 && seg.text.slice(lastEnd, at).trim().split(' ').filter(Boolean).length <= 3) continue;
      let hit: Near | null = null;
      if (token.length === 3) {
        // "hoa", "oma", "hom": three-letter typos of "homa" (fever), the commonest symptom word in Swahili.
        if (osa(token, 'homa', 1) <= 1) hit = NEAR.homa;
      } else if (token.length >= 4) {
        for (const [word, near] of Object.entries(NEAR)) {
          if (osa(token, word, word.length >= 8 ? 2 : 1) <= (word.length >= 8 ? 2 : 1)) {
            hit = near;
            break;
          }
        }
      }
      if (hit && !found.some((f) => f.word === token)) found.push({ word: token, ...hit });
    }
  }
  return found;
}

const CANNOT_CUES = ['cannot', 'unable', 'hawezi', 'siwezi'];
const DRINK_WORDS = ['drink', 'kunywa'];
const REDUCED = ['much', 'well', 'enough', 'vizuri']; // "cannot drink well" is reduced drinking, not inability

/** "cannot drink" with a typo, or "cannot even drink", which the exact phrases miss. Returns the phrase as typed. */
function inabilityToDrink(segs: Segment[]): string | null {
  for (const seg of segs) {
    if (seg.hedged) continue;
    const tokens = seg.text.split(' ');
    for (let i = 0; i < tokens.length; i++) {
      const isCue = CANNOT_CUES.some((c) => tokens[i] === c || (c.length >= 5 && osa(tokens[i], c, 1) <= 1));
      if (!isCue || /\b(?:no|not|never|without)\b/.test(tokens.slice(Math.max(0, i - 3), i).join(' '))) continue;
      for (let j = i + 1; j < Math.min(i + 4, tokens.length); j++) {
        if (tokens[j].length >= 4 && DRINK_WORDS.some((w) => osa(tokens[j], w, 1) <= 1)) {
          if (REDUCED.includes(tokens[j + 1])) break;
          return tokens.slice(i, j + 1).join(' ');
        }
      }
    }
  }
  return null;
}

const NUM = `(?:\\d{1,2}|${Object.keys(NUMBER_WORDS).join('|')})`;
/** "2-3 days", "3 or 4 days", "siku mbili au tatu": a range is not one number of days, so it stays unknown like "about 3 days". */
const DURATION_RANGE = new RegExp(
  `\\b${NUM}\\s*(?:-|\u2013|\u2014|to|or|au|hadi)\\s*${NUM}\\s*(?:days?|siku|weeks?|wiki|months?|miezi)\\b|\\b(?:siku|wiki|miezi)\\s+${NUM}\\s*(?:-|\u2013|\u2014|au|hadi|or|to)\\s*${NUM}\\b`,
  'i',
);

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
  const fields = [answers.who ?? '', answers.complaint ?? '', answers.duration ?? '', answers.danger ?? ''];
  const segs = fields.flatMap(segments);
  const clinical = [answers.complaint ?? '', answers.danger ?? ''].flatMap(segments);

  // Pregnancy wins over "mimi"/"me", child over adult when both appear. "not pregnant" is not pregnant.
  const pregnantIn = (raws: string[]) => affirmed(raws.flatMap(segments), GROUP.pregnant);
  const groupHit = (['pregnant', 'child_u5', 'adult'] as PatientGroup[]).find((g) =>
    g === 'pregnant' ? pregnantIn([answers.who ?? '']) : hasWord(who, GROUP[g]),
  );
  const groupAnywhere =
    groupHit ?? (['pregnant', 'child_u5'] as PatientGroup[]).find((g) => (g === 'pregnant' ? pregnantIn(fields) : hasWord(all, GROUP[g])));

  const symptoms = (Object.keys(SYMPTOM_WORDS) as Symptom[]).filter((s) => affirmed(segs, SYMPTOM_WORDS[s]));
  const dangerSigns = (Object.keys(DANGER_WORDS) as DangerSign[]).filter((d) => has(all, DANGER_WORDS[d]));
  const saidNone = has(` ${danger} `, NONE_WORDS);
  const dur = DURATION_RANGE.test(answers.duration ?? '') ? { days: null, sure: false } : parseDuration(duration);

  const unmapped = [answers.complaint, answers.danger].filter(
    (a): a is string => !!a && symptoms.length === 0 && dangerSigns.length === 0,
  );

  // Typos and phrases the exact keywords miss: suggested at low confidence, with a note, never asserted.
  const suggestedSymptoms: Symptom[] = [];
  const suggestedSigns: DangerSign[] = [];
  for (const s of nearMisses(clinical)) {
    const list: string[] = s.kind === 'symptom' ? symptoms : dangerSigns;
    const extra: string[] = s.kind === 'symptom' ? suggestedSymptoms : suggestedSigns;
    if (list.includes(s.code) || extra.includes(s.code)) continue;
    extra.push(s.code);
    unmapped.push(`Unclear word: "${s.word}"`);
  }
  if (!dangerSigns.includes('unable_to_drink') && !suggestedSigns.includes('unable_to_drink')) {
    const phrase = inabilityToDrink(clinical);
    if (phrase) {
      suggestedSigns.push('unable_to_drink');
      unmapped.push(`Unclear wording: "${phrase}"`);
    }
  }

  return {
    patientGroup: { value: groupAnywhere ?? null, confidence: groupHit ? 'high' : 'low', evidence: answers.who },
    symptoms: {
      value: [...symptoms, ...suggestedSymptoms],
      confidence: symptoms.length && !suggestedSymptoms.length ? 'high' : 'low',
      evidence: answers.complaint,
    },
    durationDays: { value: dur.days, confidence: dur.sure ? 'high' : 'low', evidence: answers.duration },
    dangerSigns: {
      value: [...dangerSigns, ...suggestedSigns],
      // Only trust "no danger signs" when the patient explicitly said none.
      confidence: (dangerSigns.length || saidNone) && !suggestedSigns.length ? 'high' : 'low',
      evidence: answers.danger,
    },
    unmapped,
    source: 'rules',
  };
}
