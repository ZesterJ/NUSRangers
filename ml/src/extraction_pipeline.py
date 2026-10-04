"""Evidence-gated extraction around the FROZEN experimental classifier.

No fit/training and no clinical decisions. Scores are uncalibrated classifier scores,
not clinical confidence. Rules/lexicon are inspectable development heuristics.
Evidence offsets are Python Unicode code-point offsets [start, end), not UTF-16.
"""
import math
import re
from dataclasses import dataclass

from baseline_rules import DURATION as BASE_DURATION, NUMBERS as BASE_NUMBERS
from lexical_config import PHRASES, RULE_ADDITIONS, extend_patterns, normalize_model_text

NUMBERS = {**BASE_NUMBERS, 'tree': 3}
DURATION = re.compile(BASE_DURATION.pattern.replace('one|two', 'tree|one|two'), re.I)

VERSION = 'evidence-v3'
# Deliberate phrase vocabulary, not fuzzy matching: arbitrary typo correction can
# turn a denial or unrelated word into an asserted symptom. Missing phrases abstain.
SYMPTOMS = {
    'abdominal_pain': r'\b(?:(?:abdominal|stomach|belly|tummy) (?:pain|aches?|hurts?)|(?:my )?belly hurts|maumivu ya tumbo|tumbo (?:langu )?linauma|ninaumwa tumbo)\b',
    'bleeding': r'\b(?:bleed(?:ing)?|(?:nina|na|ana)tokwa (?:na )?damu|damu inayotoka|sitokwi damu)\b',
    'blurred_vision': r'\b(?:blurred vision|(?:vision|sight) (?:is )?blurred|seeing blurry|seeing blurred|naona ukungu|ninaona ukungu|kuona ukungu|macho[^.!?;]{0,35}ukungu)\b',
    'breathing_difficulty': r'\b(?:(?:difficulty|trouble) breathing|(?:struggling|hard|difficult) to breathe|breathing with difficulty|(?:anahangaika|ninahangaika) kupumua|(?:anapata|ninapata|anapumua|kupumua|anapumua) (?:kwa )?shida|shida ya kupumua|vigumu kwangu kupumua)\b',
    'cough': r'\b(?:cough(?:s|ing|ed)?|kikohozi|(?:nina|ana|a?mekuwa a?ki|nimekuwa niki)kohoa|ninakohoa|anakohoa|sikohoi|hakohoi)\b',
    'diarrhoea': r'\b(?:diarrh[oe]+a|loose stools|watery stools|kuhara|kuharisha|(?:nina|ana|amekuwa aki|nimekuwa niki)harisha|ninaendesha|choo cha maji|siharishi|haharishi)\b',
    'fatigue': r'\b(?:fatigue|tired|tiredness|exhausted|mchovu|nimechoka|uchovu)\b',
    'fever': r'\b(?:fever(?:ish)?|homa|(?:feels?|feeling) hot|(?:child|baby) has been hot|ana joto)\b',
    'fluid_loss': r'\b(?:water (?:is )?leaking|water (?:has |have )?broken(?: early)?|maji (?:ya uzazi )?(?:yanavuja|yanatoka))\b',
    'headache': r'\b(?:headache|head hurts|kichwa (?:changu )?kinauma|maumivu (?:makali )?ya kichwa|ninaumwa kichwa)\b',
    'reduced_fetal_movement': r'\b(?:baby (?:is )?moving less|mtoto (?:tumboni )?anacheza kidogo)\b',
    'vomiting': r'\b(?:vomit(?:ing|s|ed)?|throw(?:ing)? up|kutapika|(?:nina|ana|amekuwa aki|nimekuwa niki)tapika|nimetapika|sitapiki|hatapiki)\b',
    'weakness': r'\b(?:weak(?:ness)?|dhaifu|udhaifu)\b',
}
SYMPTOMS = extend_patterns(SYMPTOMS)
SIGNS = {
    'cannot_drink': r"\b(?:(?:cannot|can't|unable to) drink|hawezi kunywa)\b(?!\s+(?:much|well|enough|vizuri))",
    'convulsions': r'\b(?:convulsions?|seizures?|degedege)\b',
    'bleeding': SYMPTOMS['bleeding'],
}
for _sign in ('cannot_drink', 'convulsions'):
    SIGNS[_sign] = '(?:' + SIGNS[_sign] + r'|\b(?:' + '|'.join(RULE_ADDITIONS[_sign]) + r')\b)'

UNCERTAIN = re.compile(r'\b(?:maybe|perhaps|possibly|might|may|unsure|not sure|not certain|labda|huenda|sina uhakika|could be)\b', re.I)
NEGATED = re.compile(r"\b(?:no|not|never|without|denies|denied|doesn't|don't|isn't|wasn't|hasn't|haven't|sina|hana|hakuna|si)\b", re.I)
NEGATIVE_WORD = re.compile(r'\b(?:sikohoi|hakohoi|sitapiki|hatapiki|siharishi|haharishi|sitokwi)\b', re.I)
HISTORICAL = re.compile(r'\b(?:used to|last year|previously|resolved|stopped|no longer|imeisha|zamani)\b', re.I)
SUBJECT_PATTERNS = {
    'child': r'\b(?:my child|the child|my baby|my little one|mtoto(?: wangu)?(?!\s+(?:tumboni|anacheza kidogo)))\b',
    'husband': r'\b(?:my husband|mume wangu)\b',
    'wife': r'\b(?:my wife|mke wangu)\b',
    'mother': r'\b(?:my mother|mama yangu)\b',
    'father': r'\b(?:my father|baba yangu)\b',
    'sister': r'\b(?:my sister|dada yangu)\b',
    'brother': r'\b(?:my brother|kaka yangu)\b',
    'speaker': r"\b(?:I|I'm|mimi|nina\w*|nime\w*|sina|sikohoi|sitapiki|siharishi)\b",
}
# Split explicit subject changes even without ASR punctuation. Other conjunctions
# retain denial/uncertainty scope, e.g. "no fever or cough".
BOUNDARY = re.compile(r'[.!?;\n](?!\d)|\b(?:but|however|lakini)\b|,\s*(?:only|just)\b|\b(?:and|na)\s+(?=(?:I\b|my\b|the child\b|mtoto wangu\b|mimi\b))', re.I)


@dataclass(frozen=True)
class Config:
    threshold: float = .3  # fallback for labels without validation support
    thresholds: dict[str, float] | None = None

    def for_label(self, label):
        return (self.thresholds or {}).get(label, self.threshold)

    def __post_init__(self):
        if not math.isfinite(self.threshold) or not 0 <= self.threshold <= 1:
            raise ValueError('threshold must be finite and between 0 and 1')
        if self.thresholds is not None:
            for label, value in self.thresholds.items():
                if label not in SYMPTOMS or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError('Invalid per-label threshold')


def span(text, start, end):
    return {'text': text[start:end], 'start': start, 'end': end}


def clauses(text):
    start = 0
    for boundary in BOUNDARY.finditer(text):
        if text[start:boundary.start()].strip():
            yield start, boundary.start(), text[start:boundary.start()]
        start = boundary.end()
    if text[start:].strip():
        yield start, len(text), text[start:]


def subjects(text):
    return {name for name, pattern in SUBJECT_PATTERNS.items() if re.search(pattern, text, re.I)}


def scoped_clauses(text, target=None):
    detected = subjects(text)
    if target is not None and target not in SUBJECT_PATTERNS:
        raise ValueError('Unsupported target_subject')
    # Multiple explicit people => no automatic owner choice. Caller may name a target;
    # then only clauses explicitly naming that person are eligible (no pronoun guess).
    pronouns = set(re.findall(r'\b(?:he|she|they)\b', text.lower()))
    if len(pronouns) > 1 or (pronouns and 'speaker' in detected and len(detected) > 1):
        return [], {'status': 'ambiguous', 'value': None}, ['ambiguous_pronouns']
    if len(detected) > 1 and target is None:
        return [], {'status': 'ambiguous', 'value': None}, ['multiple_subjects']
    if re.search(r'\b(?:children|both|watoto)\b', text, re.I):
        return [], {'status': 'ambiguous', 'value': None}, ['multiple_subjects']
    if target is not None and target not in detected:
        return [], {'status': 'ambiguous', 'value': None}, ['target_not_explicit']
    owner = target or (next(iter(detected)) if detected else None)
    eligible = []
    for start, end, clause in clauses(text):
        local = subjects(clause)
        if len(local) > 1 or (target and len(detected) > 1 and local != {target}):
            continue
        eligible.append((start, end, clause))
    if owner:
        evidence = [span(text, m.start(), m.end()) for m in re.finditer(SUBJECT_PATTERNS[owner], text, re.I)]
        subject = {'status': 'resolved', 'value': owner, 'evidence': evidence}
    else:
        subject = {'status': 'unspecified', 'value': None}
    return eligible, subject, []


def mentions(text, pattern, eligible):
    result = []
    for start, end, clause in eligible:
        for m in re.finditer(pattern, clause, re.I):
            before = clause[:m.start()]
            # Negation applies up to the finding; lexical negatives include their own cue.
            if HISTORICAL.search(clause):
                state = 'uncertain'  # temporal scope not safe enough to assert current finding
            elif UNCERTAIN.search(clause):
                state = 'uncertain'
            elif NEGATED.search(before) or NEGATIVE_WORD.search(m.group()):
                state = 'negated'
            else:
                state = 'affirmed'
            result.append({'state': state, 'evidence': span(text, start+m.start(), start+m.end()) if state == 'affirmed' else span(text, start, end),
                           'mention': span(text, start+m.start(), start+m.end())})
    return result


def finding(text, pattern, eligible):
    found = mentions(text, pattern, eligible)
    states = {x['state'] for x in found}
    state = next(iter(states)) if len(states) == 1 else 'uncertain' if states else 'not_mentioned'
    return {'state': state, 'evidence': [x['evidence'] for x in found],
            'mentions': [x['mention'] for x in found]}


def parse_duration(text, eligible):
    found, blocked = [], False
    for start, end, clause in eligible:
        for m in DURATION.finditer(clause):
            # Local prefix rather than whole-text negation: unrelated "not drinking"
            # after the duration no longer erases an explicitly stated time interval.
            prefix = clause[:m.start()]
            if (re.search(r'\b(?:about|around|nearly|approximately|almost|karibu|takriban)\b', prefix, re.I)
                    or NEGATED.search(prefix) or UNCERTAIN.search(clause)):
                blocked = True
                continue
            token = next(g for g in m.groups() if g is not None).lower()
            number = float(token) if token[0].isdigit() else NUMBERS[token]
            if math.isfinite(number) and number > 0:
                found.append((number, span(text, start+m.start(), start+m.end())))
        if re.search(r'\b(?:since|tangu)\s+(?:yesterday|today|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|jana|leo|Jumatatu|Jumanne|Jumatano|Alhamisi|Ijumaa|Jumamosi|Jumapili)\b|\b(?:a few|several|siku chache|hours?|weeks?|months?|wiki|miezi)\b', clause, re.I):
            blocked = True
    # Relative weekday/day onsets do not determine an elapsed duration without an
    # anchor/time and a clinical definition of days. Retain the phrase, never guess 1.
    temporal = []
    for start, end, clause in eligible:
        if DURATION.search(clause) or re.search(r'\b(?:since|tangu|days|siku)\b', clause, re.I):
            temporal.append(span(text, start, end))
    if not blocked and found and len({v for v, _ in found}) == 1:
        return found[0][0], [s for _, s in found], temporal
    return None, [], temporal


def extract_rules(text, target_subject=None):
    if not isinstance(text, str):
        raise TypeError('text must be a string')
    eligible, subject, abstentions = scoped_clauses(text, target_subject)
    result = {'patientType': None, 'durationDays': None, 'hydrationIssue': None,
              'reportedSigns': [], 'reportedSignStates': {}, 'subject': subject,
              'evidence': {}, 'abstentions': abstentions}
    patterns = {'child': r'\b(?:my child|the child|my baby|my little one|mtoto(?: wangu)?(?!\s+(?:tumboni|anacheza kidogo)))\b',
                'pregnant': r'\b(?:pregnant|pregnancy|mjamzito|ujauzito)\b',
                'adult': r'\b(?:adult|mtu mzima)\b'}
    candidates = {}
    for name, pattern in patterns.items():
        status = finding(text, pattern, eligible)
        if name == 'child':
            # Uncertainty about a symptom does not erase an explicit child subject.
            # Negation/uncertainty BEFORE the subject ("maybe my child") still blocks it.
            evidence = []
            for start, end, clause in eligible:
                for m in re.finditer(pattern, clause, re.I):
                    prefix = clause[:m.start()]
                    if not (NEGATED.search(prefix) or UNCERTAIN.search(prefix)):
                        evidence.append(span(text, start+m.start(), start+m.end()))
            if evidence:
                candidates[name] = evidence
        elif status['state'] == 'affirmed':
            candidates[name] = status['evidence']
    for start, end, clause in eligible:
        m = re.search(r"\b(?:I am|I'm)\s+(\d{1,3})\s+years?\s+(?:old|of age)\b", clause, re.I)
        if m and not (NEGATED.search(clause[:m.start()]) or UNCERTAIN.search(clause)):
            age = int(m.group(1))
            if 0 < age <= 120:
                candidates['adult' if age >= 18 else 'child'] = [span(text, start+m.start(), start+m.end())]
    if len(candidates) == 1:
        result['patientType'] = next(iter(candidates))
        result['evidence']['patientType'] = next(iter(candidates.values()))
    elif len(candidates) > 1:
        result['abstentions'].append('conflicting_patient_type')
    duration, evidence, temporal = parse_duration(text, eligible)
    result['durationDays'] = duration
    if evidence:
        result['evidence']['durationDays'] = evidence
    result['durationMentions'] = temporal
    if temporal and duration is None:
        result['abstentions'].append('ambiguous_duration')
    # Negative wording internal to a positive difficulty phrase is handled as a
    # lexical concept; negation before that whole phrase still blocks it.
    positive = r"\b(?:(?:not|isn't|aren't) (?:been )?drinking(?: much| well)?|(?:cannot|can't|unable to) drink|(?:difficulty|trouble) drinking|drinking (?:less|poorly)|hawezi kunywa(?: vizuri)?|hanywi(?: maji)?(?: vizuri)?|shida ya kunywa)\b"
    negative = r'\b(?:drinking (?:normally|well)|(?:no|without) (?:difficulty|trouble) drinking|anakunywa (?:maji )?vizuri)\b'
    positive = '(?:' + positive + r'|\b(?:' + '|'.join(RULE_ADDITIONS['hydration_true']) + r')\b)'
    negative = '(?:' + negative + r'|\b(?:' + '|'.join(RULE_ADDITIONS['hydration_false']) + r')\b)'
    yes = finding(text, positive, eligible)
    no = finding(text, negative, eligible)
    yes_ok, no_ok = yes['state'] == 'affirmed', no['state'] == 'affirmed'
    if yes_ok != no_ok and 'uncertain' not in (yes['state'], no['state']):
        result['hydrationIssue'] = yes_ok
        result['evidence']['hydrationIssue'] = (yes if yes_ok else no)['evidence']
    for sign, pattern in SIGNS.items():
        status = finding(text, pattern, eligible)
        if not eligible and abstentions:
            status['state'] = 'uncertain' if re.search(pattern, text, re.I) else 'not_mentioned'
            if status['state'] == 'uncertain':
                status['evidence'] = [span(text, 0, len(text))]
        result['reportedSignStates'][sign] = status
        if status['state'] == 'affirmed':
            result['reportedSigns'].append(sign)
            result['evidence'][f'reportedSigns.{sign}'] = status['evidence']
    return result


class ExtractionPipeline:
    def __init__(self, bundle, config=None):
        self.bundle = bundle
        self.config = config or Config(threshold=bundle['threshold'], thresholds=bundle.get('thresholds'))

    def extract(self, text, target_subject=None, scores=None):
        result = extract_rules(text, target_subject)
        eligible, _, _ = scoped_clauses(text, target_subject)
        if scores is None:
            scores = self.bundle['pipeline'].predict_proba([normalize_model_text(text)])[0]
        if len(scores) != len(self.bundle['labels']) or any(not math.isfinite(float(s)) or not 0 <= s <= 1 for s in scores):
            raise ValueError('Expected one finite score between 0 and 1 per symptom label')
        result['symptoms'] = []
        result['symptomDecisions'] = {}
        for label, score in zip(self.bundle['labels'], scores):
            threshold = self.config.for_label(label)
            status = finding(text, SYMPTOMS[label], eligible)
            accepted = bool(score >= threshold and status['state'] == 'affirmed' and eligible)
            reasons = []
            if not eligible:
                reasons.append('unresolved_subject_or_empty_input')
            if status['state'] != 'affirmed':
                reasons.append(status['state'])
            if score < threshold:
                reasons.append('below_threshold')
            result['symptomDecisions'][label] = {'score': float(score), 'threshold': threshold,
                                               'accepted': accepted, 'state': status['state'], 'reasons': reasons}
            if accepted:
                result['symptoms'].append(label)
                result['evidence'][f'symptoms.{label}'] = status['evidence']
        result.update({'sourceText': text, 'modelVersion': self.bundle['modelVersion'],
                       'extractionVersion': VERSION, 'requiresVerification': True,
                       'scoreMeaning': 'uncalibrated classifier score; evidence and subject checks also required'})
        return result
