/**
 * Edge-case test of the on-phone typed-input path: the rule extractor, the merge with the backend model, and tap overrides.
 * Every probe is judged by what the USER SEES, not by raw detection:
 *   correct       the output matches the truth
 *   flagged       wrong or incomplete, but the app warns the user (low confidence, or the raw text is shown in notes)
 *   silent        wrong or incomplete at HIGH confidence with nothing flagged: the dangerous outcome
 * `ambiguous` probes have no single right answer and `byDesign` ones follow a documented policy; both are listed, not counted.
 *
 *   npm run check:typed            # fails on any silent error or failed merge/tap check
 *
 * The backend counterpart is ml/robustness/edge_cases.py (same categories, same judging).
 */
import { applyChoices, NO_CHOICES } from '@/intake/choices';
import { extractWithRules } from '@/intake/extractRules';
import { mergeExtractions } from '@/intake/mergeExtraction';
import type { Extraction } from '@/intake/types';

type Field = 'who' | 'complaint' | 'duration' | 'danger';
type Expect = {
  symptoms?: string[];
  forbidSymptoms?: string[];
  signs?: string[];
  forbidSigns?: string[];
  days?: number | null;
  group?: string | null;
  forbidGroup?: string[];
};
type Probe = { cat: string; sub: string; field: Field; text: string; expect: Expect; ambiguous?: boolean; byDesign?: boolean };
type Outcome = 'correct' | 'flagged' | 'silent';

const RANK: Record<Outcome, number> = { correct: 0, flagged: 1, silent: 2 };
const worst = (a: Outcome, b: Outcome): Outcome => (RANK[a] >= RANK[b] ? a : b);

const NEIGHBOURS: Record<string, string> = {
  q: 'wa', w: 'qes', e: 'wrd', r: 'etf', t: 'ryg', y: 'tuh', u: 'yij', i: 'uok', o: 'ipl', p: 'ol', a: 'qsz', s: 'awdx',
  d: 'serf', f: 'drtg', g: 'ftyh', h: 'gyuj', j: 'huik', k: 'jiol', l: 'kop', z: 'asx', x: 'zsdc', c: 'xdfv', v: 'cfgb',
  b: 'vghn', n: 'bhjm', m: 'njk',
}; // fmt: skip

/** Every single-character typo at every position: delete, duplicate, transpose, QWERTY-neighbour substitute. */
function singleEdits(word: string): Map<string, string> {
  const out = new Map<string, string>();
  for (let i = 0; i < word.length; i++) {
    out.set(`delete${i}`, word.slice(0, i) + word.slice(i + 1));
    out.set(`duplicate${i}`, word.slice(0, i) + word[i] + word.slice(i));
    for (const nb of NEIGHBOURS[word[i].toLowerCase()] ?? '') out.set(`neighbour${i}${nb}`, word.slice(0, i) + nb + word.slice(i + 1));
    if (i + 1 < word.length && word[i] !== word[i + 1]) out.set(`transpose${i}`, word.slice(0, i) + word[i + 1] + word[i] + word.slice(i + 2));
  }
  for (const [k, v] of out) if (!v || v === word) out.delete(k);
  return out;
}

const APOSTROPHES: Record<string, string> = {
  straight: "'", dropped: '', curly: '’', left_curly: '‘', backtick: '`', acute: '´', modifier: 'ʼ', prime: '′', space: ' ',
}; // fmt: skip
const kindsFor = (text: string) => (text.includes("'") ? APOSTROPHES : { straight: "'" });

const COMPLAINT_BASES: [string, string[], string[]][] = [
  ['I have fever', ['fever'], ['fever']],
  ['my child has a cough', ['cough'], ['cough']],
  ['he has diarrhoea', ['diarrhoea'], ['diarrhoea']],
  ['she is vomiting', ['vomiting'], ['vomiting']],
  ['I have a headache', ['headache'], ['headache']],
  ['stomach pain', ['stomach', 'pain'], ['abdominal_pain']],
  ['difficulty breathing', ['difficulty', 'breathing'], ['difficulty_breathing']],
  ['I am weak', ['weak'], ['weakness']],
  ['feeling very tired', ['tired'], ['weakness']],
  ['fever and cough', ['fever', 'cough'], ['fever', 'cough']],
  ['fever, cough and diarrhoea', ['fever', 'cough', 'diarrhoea'], ['fever', 'cough', 'diarrhoea']],
  ['headache and vomiting', ['headache', 'vomiting'], ['headache', 'vomiting']],
  ['ana homa', ['homa'], ['fever']],
  ['nina homa na kikohozi', ['homa', 'kikohozi'], ['fever', 'cough']],
  ['anatapika', ['anatapika'], ['vomiting']],
  ['mtoto ana kuhara', ['kuhara'], ['diarrhoea']],
  ['kichwa kinauma', ['kichwa', 'kinauma'], ['headache']],
  ['maumivu ya tumbo', ['maumivu', 'tumbo'], ['abdominal_pain']],
  ['ana shida ya kupumua', ['shida', 'kupumua'], ['difficulty_breathing']],
  ['ana udhaifu', ['udhaifu'], ['weakness']],
  ['nina uchovu', ['uchovu'], ['weakness']],
  ['ninakohoa', ['ninakohoa'], ['cough']],
  ['nakohoa', ['nakohoa'], ['cough']],
  ['mtoto ana homa kali na anakohoa', ['homa', 'anakohoa'], ['fever', 'cough']],
  ['ana upele', ['upele'], ['rash']],
]; // fmt: skip
const DANGER_BASES: [string, string[], string[]][] = [
  ['he cannot drink', ['cannot', 'drink'], ['unable_to_drink']],
  ['unable to drink', ['unable', 'drink'], ['unable_to_drink']],
  ['he has convulsions', ['convulsions'], ['convulsions']],
  ['she had a seizure', ['seizure'], ['convulsions']],
  ['ana degedege', ['degedege'], ['convulsions']],
  ['hawezi kunywa', ['hawezi', 'kunywa'], ['unable_to_drink']],
  ['heavy bleeding', ['bleeding'], ['vaginal_bleeding']],
  ['kutoka damu', ['damu'], ['vaginal_bleeding']],
  ['cannot drink and convulsions', ['drink', 'convulsions'], ['unable_to_drink', 'convulsions']],
]; // fmt: skip

const NEG_SYMPTOMS: [string, string][] = [
  ['fever', 'fever'], ['cough', 'cough'], ['diarrhoea', 'diarrhoea'], ['vomiting', 'vomiting'], ['headache', 'headache'],
  ['homa', 'fever'], ['kikohozi', 'cough'], ['kuhara', 'diarrhoea'], ['kutapika', 'vomiting'],
]; // fmt: skip
const NEG_EN: Record<string, string> = {
  no: 'no {s}', have_no: 'I have no {s}', dont: "I don't have {s}", doesnt: "he doesn't have {s}", didnt: "she didn't have {s}",
  havent: "I haven't had {s}", hasnt: "he hasn't had {s}", hadnt: "she hadn't had {s}", isnt: "it isn't {s}", wasnt: "it wasn't {s}",
  without: 'without {s}', never: 'never had {s}', denies: 'denies {s}', not: 'not {s}', do_not: 'I do not have {s}',
  does_not: 'he does not have {s}', did_not: 'she did not have {s}', no_longer: 'no longer has {s}',
}; // fmt: skip
const NEG_SW: Record<string, string> = {
  sina: 'sina {s}', hana: 'hana {s}', hakuna: 'hakuna {s}', hamna: 'hamna {s}', bila: 'bila {s}', haina: 'haina {s}',
  mtoto_hana: 'mtoto hana {s}', hakuna_kabisa: 'hakuna {s} kabisa',
}; // fmt: skip
const SW_WORDS = new Set(['homa', 'kikohozi', 'kuhara', 'kutapika']);

const SCOPE: [string, string[], boolean][] = [
  ['no fever but cough', ['cough'], false], ['no fever, only a cough', ['cough'], false], ['fever but no cough', ['fever'], false],
  ["I have fever and I don't have cough", ['fever'], false], ['no fever and no cough', [], false], ['no fever or cough', [], false],
  ['fever and cough but no vomiting', ['fever', 'cough'], false], ['no vomiting but diarrhoea and fever', ['diarrhoea', 'fever'], false],
  ['fever. no cough.', ['fever'], false], ['no fever. cough.', ['cough'], false], ['cough without fever', ['cough'], false],
  ['fever and cough and no diarrhoea', ['fever', 'cough'], false], ['no fever, no cough, no vomiting', [], false],
  ['fever; cough; no headache', ['fever', 'cough'], false], ["I don't have fever but I do have a cough", ['cough'], false],
  ['not only fever but also cough', ['fever', 'cough'], false], ['fever, no cough, vomiting', ['fever', 'vomiting'], true], ['fever, no fever', [], true], ['neither fever nor cough', [], false],
  ['ana homa lakini hana kikohozi', ['fever'], false], ['hana homa lakini anakohoa', ['cough'], false],
  ['ana homa na kikohozi', ['fever', 'cough'], false], ['homa bila kikohozi', ['fever'], false],
  ['hakuna homa, hakuna kikohozi', [], false], ['nina homa lakini sina kikohozi', ['fever'], false],
  ['sina homa wala kikohozi', [], false],
]; // fmt: skip
const HEDGED = [
  'maybe fever', 'perhaps fever', 'might have fever', 'possibly fever', 'not sure if fever', 'could be fever', 'labda homa',
  'huenda ana homa', 'sina uhakika kama ana homa', 'had fever last year', 'fever resolved', 'used to have fever',
  'fever stopped', 'previously had fever', 'fever no longer', 'homa imeisha', 'zamani alikuwa na homa',
]; // fmt: skip

const FORMATS: Record<string, (s: string) => string> = {
  upper: (s) => s.toUpperCase(), lower: (s) => s.toLowerCase(), leading_trailing_space: (s) => `   ${s}   `,
  double_space: (s) => s.replace(/ /g, '  '), tabs: (s) => s.replace(/ /g, '\t'), nbsp: (s) => s.replace(/ /g, ' '),
  thin_space: (s) => s.replace(/ /g, ' '), zero_width_between_words: (s) => s.replace(/ /g, ' ​'),
  zero_width_in_word: (s) => `${s.slice(0, 2)}​${s.slice(2)}`, soft_hyphen_in_word: (s) => `${s.slice(0, 3)}­${s.slice(3)}`,
  bidi_marks: (s) => `‏${s}‎`, fullwidth: (s) => [...s].map((c) => (c >= '!' && c <= '~' ? String.fromCharCode(c.charCodeAt(0) + 0xfee0) : c)).join(''),
  trailing_bangs: (s) => `${s}!!!`, trailing_dots: (s) => `${s}...`, leading_dash: (s) => `- ${s}`, bullet: (s) => `• ${s}`,
  quoted: (s) => `"${s}"`, parentheses: (s) => `(${s})`, emoji_suffix: (s) => `${s} \u{1f912}`, emoji_prefix: (s) => `\u{1f912} ${s}`,
  repeat_twice: (s) => `${s} ${s}`, filler_prefix: (s) => `umm ${s}`, polite_prefix: (s) => `please help: ${s}`,
  trailing_newline: (s) => `${s}\n`, html_bold: (s) => `<b>${s}</b>`, markdown_bold: (s) => `**${s}**`,
  url_suffix: (s) => `${s} http://example.com/a?b=c`, json_wrapped: (s) => `{"text": "${s}"}`, long_padding: (s) => s + ' '.repeat(1500),
  digits_prefix: (s) => `12345 ${s}`, title: (s) => s.replace(/\b\w/g, (c) => c.toUpperCase()),
}; // fmt: skip
const FORMAT_CORE: [Field, string, Expect][] = [
  ['complaint', 'I have fever', { symptoms: ['fever'] }],
  ['complaint', 'my child has fever and cough', { symptoms: ['fever', 'cough'] }],
  ['complaint', 'ana homa na kikohozi', { symptoms: ['fever', 'cough'] }],
  ['complaint', "I don't have fever", { forbidSymptoms: ['fever'] }],
  ['complaint', 'hakuna homa', { forbidSymptoms: ['fever'] }],
  ['danger', 'he cannot drink', { signs: ['unable_to_drink'] }],
  ['danger', 'hakuna', { signs: [] }],
]; // fmt: skip
const GARBAGE: [string, string][] = [
  ['empty', ''], ['spaces', '     '], ['dots', '...'], ['questions', '????'], ['digits', '12345'], ['emoji_only', '\u{1f912}'],
  ['gibberish', 'asdfghjkl'], ['lorem', 'Lorem ipsum dolor sit amet'], ['script_tag', '<script>alert(1)</script>'],
  ['sql', "'; DROP TABLE patients;--"], ['path', '../../etc/passwd'], ['only_newlines', '\n\n\n'], ['rtl_arabic', 'حمى'],
  ['chinese', '发烧'], ['hindi', 'बुखार'], ['single_char', 'a'], ['long_word', 'a'.repeat(1500)],
  ['punctuation_soup', '!@#$%^&*()_+{}|:<>?'], ['template_injection', '{{7*7}} ${7*7}'], ['unicode_combining', `e${'́'.repeat(50)}`],
]; // fmt: skip

function buildCatalog(): Probe[] {
  const probes: Probe[] = [];
  for (const [text, , sym] of COMPLAINT_BASES) probes.push({ cat: 'control', sub: 'complaint', field: 'complaint', text, expect: { symptoms: sym } });
  for (const [text, , sg] of DANGER_BASES) probes.push({ cat: 'control', sub: 'danger', field: 'danger', text, expect: { signs: sg } });

  for (const [bases, field, key] of [[COMPLAINT_BASES, 'complaint', 'symptoms'], [DANGER_BASES, 'danger', 'signs']] as const) {
    for (const [text, words, expected] of bases) {
      for (const word of words) {
        if (word.length < 4) continue;
        for (const [k, typo] of singleEdits(word)) {
          // Deleting the f of "fever" leaves the real word "ever", which is deliberately not flagged (it would put false alarms on "has he ever had...").
          const knownLimit = typo === 'ever';
          probes.push({ cat: 'typo', sub: k.replace(/\d.*/, ''), field, text: text.replace(word, typo), expect: { [key]: expected }, byDesign: knownLimit });
        }
      }
    }
  }

  for (const [cueName, tpl] of Object.entries({ ...NEG_EN, ...NEG_SW })) {
    const sw = cueName in NEG_SW;
    for (const [word, code] of NEG_SYMPTOMS) {
      if (SW_WORDS.has(word) !== sw) continue;
      for (const [kind, ap] of Object.entries(kindsFor(tpl))) {
        probes.push({ cat: 'negation', sub: `${cueName}/${kind}`, field: 'complaint', text: tpl.replace('{s}', word).replace(/'/g, ap), expect: { forbidSymptoms: [code] } });
      }
    }
  }
  for (const [text, exp, amb] of SCOPE) {
    for (const [kind, ap] of Object.entries(kindsFor(text))) {
      probes.push({ cat: 'scope', sub: kind, field: 'complaint', text: text.replace(/'/g, ap), expect: { symptoms: exp }, ambiguous: amb });
    }
  }
  for (const text of HEDGED) probes.push({ cat: 'uncertainty', sub: 'hedged_or_past', field: 'complaint', text, expect: { forbidSymptoms: ['fever'] } });

  // negated danger signs: the rules over-assert danger signs ON PURPOSE (a wrong extra one is corrected on review, a missed one is not)
  for (const [tpl, name] of [['no {s}', 'no'], ['hakuna {s}', 'hakuna'], ['hana {s}', 'hana']] as const) {
    for (const [word, sign] of [['convulsions', 'convulsions'], ['degedege', 'convulsions'], ['bleeding', 'vaginal_bleeding']] as const) {
      probes.push({ cat: 'negation', sub: `sign_${name}/straight`, field: 'danger', text: tpl.replace('{s}', word), expect: { forbidSigns: [sign] }, byDesign: true });
    }
  }

  for (const [field, text, exp] of FORMAT_CORE) {
    for (const [name, fn] of Object.entries(FORMATS)) probes.push({ cat: 'format', sub: name, field, text: fn(text), expect: exp });
  }
  for (const [name, text] of GARBAGE) {
    probes.push({ cat: 'garbage', sub: name, field: 'complaint', text, expect: { forbidSymptoms: ['fever', 'cough', 'vomiting', 'diarrhoea'] } });
  }
  for (const [text, days] of [['3 days', 3], ['three days', 3], ['siku tatu', 3], ['siku 3', 3], ['siku moja', 1], ['10 days', 10], ['2-3 days', null], ['3 or 4 days', null], ['siku mbili au tatu', null], ['two or three days', null]] as const) {
    probes.push({ cat: 'duration', sub: 'plain', field: 'duration', text, expect: { days } });
  }
  for (const [text, group] of [['I am pregnant', 'pregnant'], ['mimi ni mjamzito', 'pregnant'], ['Mtoto wangu wa miaka miwili', 'child_u5']] as const) {
    probes.push({ cat: 'group', sub: 'plain', field: 'who', text, expect: { group } });
  }
  for (const text of ['I am not pregnant', "I'm not pregnant", 'sio mjamzito', 'sina mimba', 'not pregnant']) {
    probes.push({ cat: 'group', sub: 'forbid_pregnant', field: 'who', text, expect: { forbidGroup: ['pregnant'] } });
  }
  // short keywords must not fire inside unrelated words ("hot" in "photo", "koo" in "kikoo", "son" in "person")
  for (const text of ['I took a photo', 'a ghost story', 'my shot was yesterday', 'at the hotel', 'whole day']) {
    probes.push({ cat: 'substring', sub: 'hot', field: 'complaint', text, expect: { forbidSymptoms: ['fever'] } });
  }
  for (const text of ['kikoo', 'nimenunua kikoo', 'mkoo']) {
    probes.push({ cat: 'substring', sub: 'koo', field: 'complaint', text, expect: { forbidSymptoms: ['sore_throat'] } });
  }
  for (const text of ['my person', 'this season', 'the reason', 'possible poisoning']) {
    probes.push({ cat: 'substring', sub: 'son', field: 'who', text, expect: { forbidGroup: ['child_u5'] } });
  }
  return probes;
}

function judgeSet(got: string[], conf: string, exact: string[] | undefined, forbid: string[] | undefined, noted: boolean): Outcome {
  if (exact) {
    if (got.length === exact.length && exact.every((x) => got.includes(x))) return 'correct';
  } else if (!(forbid ?? []).some((x) => got.includes(x))) return 'correct';
  return conf === 'low' || noted ? 'flagged' : 'silent';
}

function judge(p: Probe, ex: Extraction): Outcome {
  const noted = !!p.text.trim() && ex.unmapped.some((n) => n.includes(p.text.trim()));
  let out: Outcome = 'correct';
  const e = p.expect;
  if (e.symptoms || e.forbidSymptoms) out = worst(out, judgeSet(ex.symptoms.value, ex.symptoms.confidence, e.symptoms, e.forbidSymptoms, noted));
  if (e.signs || e.forbidSigns) out = worst(out, judgeSet(ex.dangerSigns.value, ex.dangerSigns.confidence, e.signs, e.forbidSigns, noted));
  if ('group' in e || e.forbidGroup) {
    const g = ex.patientGroup;
    if (e.forbidGroup) out = worst(out, !e.forbidGroup.includes(g.value as string) ? 'correct' : g.confidence === 'low' ? 'flagged' : 'silent');
    else if (g.value !== e.group) out = worst(out, g.confidence === 'low' || g.value === null ? 'flagged' : 'silent');
  }
  if ('days' in e && ex.durationDays.value !== e.days) {
    out = worst(out, ex.durationDays.confidence === 'low' || ex.durationDays.value === null ? 'flagged' : 'silent');
  }
  return out;
}

// ---- merge with the backend model, and tap overrides -------------------------------------------------------------
const hi = <T,>(value: T) => ({ value, confidence: 'high' as const });
const lo = <T,>(value: T) => ({ value, confidence: 'low' as const });
const model = (
  symptoms: Extraction['symptoms'], danger: Extraction['dangerSigns'], group: Extraction['patientGroup'] = lo(null),
  days: Extraction['durationDays'] = lo(null), unmapped: string[] = [],
): Extraction => ({ patientGroup: group, symptoms, durationDays: days, dangerSigns: danger, unmapped, source: 'model' }); // fmt: skip

type Check = { name: string; ok: boolean };
function structuralChecks(): Check[] {
  const checks: Check[] = [];
  const add = (name: string, ok: boolean) => checks.push({ name, ok });
  const rules = (answers: Parameters<typeof extractWithRules>[0]) => extractWithRules(answers);

  // merge: the model's confident answer wins; danger signs are never dropped; empty inputs do not crash
  const m1 = mergeExtractions(model(hi(['fever']), hi([])), rules({ complaint: 'fever and cough' }));
  add('merge: confident model keeps its own symptoms', m1.symptoms.value.join() === 'fever');
  const m2 = mergeExtractions(model(lo([]), lo([])), rules({ complaint: 'fever and cough', danger: 'he cannot drink' }));
  add('merge: unsure model + rules are unioned and stay low confidence', m2.symptoms.value.length === 2 && m2.symptoms.confidence === 'low');
  add('merge: a danger sign from the rules is never dropped when the model is unsure', m2.dangerSigns.value.includes('unable_to_drink'));
  const m3 = mergeExtractions(model(hi([]), hi([])), rules({ danger: 'hakuna degedege, very sleepy' }));
  add('merge: a confident model overrides the rules on signs it can judge (the rules over-assert "no convulsions")', !m3.dangerSigns.value.includes('convulsions'));
  add('merge: signs only the rules know (very sleepy) are kept even when the model is confident', m3.dangerSigns.value.includes('lethargic'));
  const empty = mergeExtractions(model(lo([]), lo([])), rules({}));
  add('merge: all-empty input does not crash and stays low confidence', empty.symptoms.confidence === 'low' && empty.dangerSigns.confidence === 'low');

  // tap overrides
  const base = rules({ complaint: 'ana homa', danger: 'he cannot drink' });
  const noneTapped = applyChoices(base, { ...NO_CHOICES, noDanger: true });
  add('taps: "none of these" tapped while the text names a danger sign must not read as a sure "none"', !(noneTapped.dangerSigns.value.includes('unable_to_drink') && noneTapped.dangerSigns.confidence === 'high'));
  const childTap = applyChoices(rules({ who: 'mimi mjamzito' }), { ...NO_CHOICES, who: 'child_u5' });
  add('taps: tapped patient overrides the typed one', childTap.patientGroup.value === 'child_u5');
  const durTap = applyChoices(rules({ duration: 'siku tano' }), { ...NO_CHOICES, durationDays: 2 });
  add('taps: tapped duration overrides the typed one', durTap.durationDays.value === 2);
  return checks;
}


const probes = buildCatalog();
const table = new Map<string, Record<Outcome | 'total', number>>();
const silentList: Probe[] = [];
const bySub = new Map<string, number>();
let counted = 0;
for (const p of probes) {
  const ex = extractWithRules({ [p.field]: p.text });
  const outcome = judge(p, ex);
  if (p.ambiguous || p.byDesign) continue;
  counted++;
  const row = table.get(p.cat) ?? { correct: 0, flagged: 0, silent: 0, total: 0 };
  row[outcome]++;
  row.total++;
  table.set(p.cat, row);
  if (outcome === 'silent') {
    silentList.push(p);
    bySub.set(`${p.cat}/${p.sub}`, (bySub.get(`${p.cat}/${p.sub}`) ?? 0) + 1);
  }
}

console.log(`${probes.length} probes (${counted} counted)\n`);
console.log('| category | probes | correct | flagged | silent error |\n|---|---:|---:|---:|---:|');
const total = { correct: 0, flagged: 0, silent: 0, total: 0 };
for (const [cat, r] of table) {
  console.log(`| ${cat} | ${r.total} | ${r.correct} | ${r.flagged} | ${r.silent} |`);
  for (const k of ['correct', 'flagged', 'silent', 'total'] as const) total[k] += r[k];
}
console.log(`| **all** | ${total.total} | ${total.correct} | ${total.flagged} | **${total.silent}** |`);
console.log('\nsilent errors by sub-category:');
for (const [k, n] of [...bySub].sort((a, b) => b[1] - a[1]).slice(0, 25)) console.log(`  ${String(n).padStart(4)}  ${k}`);
console.log('\nexamples:');
for (const p of silentList.filter((_, i) => i % Math.max(1, Math.floor(silentList.length / 12)) === 0).slice(0, 12)) {
  const ex = extractWithRules({ [p.field]: p.text });
  console.log(`  ${JSON.stringify(p.text).slice(0, 52).padEnd(52)} expect ${JSON.stringify(p.expect)} got symptoms=${JSON.stringify(ex.symptoms.value)} danger=${JSON.stringify(ex.dangerSigns.value)}`);
}

console.log('\nmerge and tap checks:');
let failedChecks = 0;
for (const c of structuralChecks()) {
  if (!c.ok) failedChecks++;
  console.log(`  ${c.ok ? 'ok  ' : 'FAIL'} ${c.name}`);
}

const failed = total.silent > 0 || failedChecks > 0;
console.log(failed ? `\nFAILED: ${total.silent} silent errors, ${failedChecks} failed checks` : '\nall good');
process.exit(failed ? 1 : 0);
