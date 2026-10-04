"""Conservative, inspectable extraction rules, version rules-v1.1.

No clinical interpretation. These rules deliberately abstain for obvious conflicting
subjects/timing. Evidence uses original substrings. Negation/scope handling is only
heuristic; diagnostics document limits. No data-driven fitting occurs here.
"""
import re

VERSION = 'rules-v1.1'
NUMBERS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
           'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
           'moja': 1, 'mbili': 2, 'tatu': 3, 'nne': 4, 'tano': 5,
           'sita': 6, 'saba': 7, 'nane': 8, 'tisa': 9, 'kumi': 10}
NUMBER = r'(?:\d+(?:\.\d+)?|' + '|'.join(NUMBERS) + ')'
DURATION = re.compile(r'\b(?:for\s+(?:the\s+last\s+)?|since\s+)?(' + NUMBER + r')\s+days?\b|\bsiku\s+(' + NUMBER + r')\b', re.I)
CONTEXT_BLOCK = re.compile(r'\b(?:maybe|perhaps|possibly|might|may|not sure|unsure|used to|last year|previously|resolved|no longer|labda|huenda|sina uhakika)\b', re.I)
NEGATION = re.compile(r"\b(?:no|not|never|without|denies|denied|doesn't|isn't|hasn't|sina|hana|hakuna|si)\b", re.I)
APPROXIMATE = re.compile(r'\b(?:about|nearly|around|approximately|almost|karibu|takriban)\b', re.I)
RELATIVE = re.compile(r'\b(?:today|yesterday|leo|jana|hours?|weeks?|months?|masaa?|wiki|miezi)\b', re.I)
PATIENT = {
    'pregnant': r'\b(?:pregnant|pregnancy|mjamzito|ujauzito)\b',
    'child': r'\b(?:my child|the child|my baby|my little one|mtoto wangu)\b',
    'adult': r'\b(?:adult|mtu mzima)\b',
}
SIGNS = {
    'cannot_drink': r"\b(?:cannot drink|can't drink|unable to drink|hawezi kunywa)\b(?!\s+(?:well|much|vizuri))",
    'convulsions': r'\b(?:convulsions?|seizures?|degedege)\b',
    'bleeding': r'\b(?:bleeding|natokwa (?:na )?damu|ninatokwa (?:na )?damu|ninatokwa damu|damu inayotoka)\b',
}
HYDRATION_TRUE = re.compile(
    r"\b(?:(?:not|aren't|isn't) drinking(?: much| well)?|(?:cannot|can't|unable to) drink|"
    r"(?:difficulty|trouble) drinking|difficulty (?:in )?drinking|drinking (?:less|poorly)|"
    r"not been drinking(?: well| much)?|hawezi kunywa(?: vizuri)?|hanywi(?: maji)?(?: vizuri)?|"
    r"shida ya kunywa)\b", re.I)
HYDRATION_FALSE = re.compile(
    r'\b(?:drinking (?:normally|well)|(?:no|without) (?:difficulty|trouble) drinking|anakunywa (?:maji )?vizuri)\b', re.I)


def clauses(text):
    # Only contrast boundaries split scope. Keeping and/na preserves uncertainty
    # across conjunctions and phrases such as Swahili "natokwa na damu".
    return [x for x in re.split(r'[.!?;\n]|\b(?:but|however|lakini)\b', text, flags=re.I) if x.strip()]


def multiple_subjects(text):
    child = re.search(r'\b(?:my child|the child|mtoto wangu)\b', text, re.I)
    first_person = re.search(r'\bI (?:have|am|feel|keep)\b|\bmimi\b', text, re.I)
    two_people = re.search(r'\b(?:my (?:mother|father|wife|husband|sister|brother)|children|both|watoto)\b', text, re.I)
    # fetal movement during explicit pregnancy is not a separate child patient.
    return bool((child and first_person and not re.search(PATIENT['pregnant'], text, re.I)) or two_people)


def affirmed_matches(pattern, text, allow_negative=False):
    result = []
    for clause in clauses(text):
        if CONTEXT_BLOCK.search(clause):
            continue
        for match in re.finditer(pattern, clause, re.I):
            prefix = clause[:match.start()]
            if not allow_negative and NEGATION.search(prefix):
                continue
            result.append(match.group())
    return result


def extract_rules(text):
    result = {'patientType': None, 'durationDays': None, 'hydrationIssue': None,
              'reportedSigns': [], 'evidence': {}, 'abstentions': []}
    if not isinstance(text, str):
        raise TypeError('text must be a string')
    if not text.strip():
        return result
    if multiple_subjects(text):
        result['abstentions'].append('multiple_or_ambiguous_subjects')
        return result
    candidates = {kind: affirmed_matches(pattern, text) for kind, pattern in PATIENT.items()}
    candidates = {k: v for k, v in candidates.items() if v}
    ages = re.findall(r'\b(?:I am|I\x27m)\s+(\d{1,3})\s+(?:years? old|years? of age)\b', text, re.I)
    if ages and not CONTEXT_BLOCK.search(text) and not NEGATION.search(text):
        for age in ages:
            candidates.setdefault('adult' if int(age) >= 18 else 'child', []).append(f'{age} years')
    if len(candidates) == 1:
        result['patientType'] = next(iter(candidates))
        # Record actual source evidence, including full age mention where applicable.
        result['evidence']['patientType'] = next(iter(candidates.values()))
    elif len(candidates) > 1:
        result['abstentions'].append('conflicting_patient_types')

    matches = list(DURATION.finditer(text))
    values = []
    for match in matches:
        token = next(g for g in match.groups() if g is not None).lower()
        values.append(float(token) if token[0].isdigit() else NUMBERS[token])
    if matches and not (APPROXIMATE.search(text) or RELATIVE.search(text) or CONTEXT_BLOCK.search(text)
                        or NEGATION.search(text)) and len(set(values)) == 1 and values[0] > 0:
        result['durationDays'] = values[0]
        result['evidence']['durationDays'] = [m.group() for m in matches]
    elif matches:
        result['abstentions'].append('ambiguous_or_qualified_duration')

    positive, negative = [], []
    for clause in clauses(text):
        if CONTEXT_BLOCK.search(clause):
            continue
        for m in HYDRATION_TRUE.finditer(clause):
            # The lexical negative "not drinking" is positive evidence of difficulty;
            # a preceding denial of that whole proposition still blocks it.
            if not NEGATION.search(clause[:m.start()]):
                positive.append(m.group())
        for m in HYDRATION_FALSE.finditer(clause):
            if not NEGATION.search(clause[:m.start()]):
                negative.append(m.group())
    if positive and not negative:
        result['hydrationIssue'] = True
        result['evidence']['hydrationIssue'] = positive
    elif negative and not positive:
        result['hydrationIssue'] = False
        result['evidence']['hydrationIssue'] = negative
    elif positive and negative:
        result['abstentions'].append('conflicting_hydration')
    for sign, pattern in SIGNS.items():
        evidence = affirmed_matches(pattern, text)
        if evidence:
            result['reportedSigns'].append(sign)
            result['evidence'][f'reportedSigns.{sign}'] = evidence
    return result
