"""Versioned, bounded lexical additions. No edit-distance or broad fuzzy matching.

Keys are exact source phrases (case-insensitive whole-token boundaries). Values are
(label, canonical model-input phrase). Original source/evidence is never rewritten.
These are development mappings, not native-speaker-validated medical terminology.
"""
import re

VERSION = 'lexical-v3'
PHRASES = {
    'stomach ache': ('abdominal_pain', 'stomach pain'),
    'tummy ache': ('abdominal_pain', 'belly pain'),
    'kutokwa na damu': ('bleeding', 'ninatokwa na damu'),
    'bleeds': ('bleeding', 'bleeding'),
    'blurry vision': ('blurred_vision', 'vision is blurred'),
    'vision is blurry': ('blurred_vision', 'vision is blurred'),
    'naona kwa ukungu': ('blurred_vision', 'naona ukungu'),
    'short of breath': ('breathing_difficulty', 'difficulty breathing'),
    "can't catch my breath": ('breathing_difficulty', 'difficulty breathing'),
    'napumua kwa shida': ('breathing_difficulty', 'ninapata shida ya kupumua'),
    'caugh': ('cough', 'cough'),
    'kikohzi': ('cough', 'kikohozi'),
    'diarrhea': ('diarrhoea', 'diarrhoea'),
    'diarhoea': ('diarrhoea', 'diarrhoea'),
    'feeling exhausted': ('fatigue', 'feeling very tired'),
    'nimechoka sana': ('fatigue', 'nimechoka sana'),
    'fevr': ('fever', 'fever'),
    'fevar': ('fever', 'fever'),
    'hma': ('fever', 'homa'),
    'my waters broke': ('fluid_loss', 'my water has broken'),
    'maji ya uzazi yanavuja': ('fluid_loss', 'maji ya uzazi yanavuja'),
    'head aches': ('headache', 'head hurts'),
    'kichwa kinauma': ('headache', 'kichwa changu kinauma'),
    'baby moving less': ('reduced_fetal_movement', 'baby is moving less'),
    'mtoto tumboni anacheza kidogo': ('reduced_fetal_movement', 'mtoto tumboni anacheza kidogo'),
    'vomitting': ('vomiting', 'vomiting'),
    'vomitingg': ('vomiting', 'vomiting'),
    'throwing up': ('vomiting', 'vomiting'),
    'feeling weak': ('weakness', 'feel very weak'),
    'nahisi dhaifu': ('weakness', 'ninahisi dhaifu sana'),
}
# Conservative additions for deterministic fields; names explain exact semantics.
RULE_ADDITIONS = {
    'hydration_true': [r'anakunywa maji kidogo', r'hanywi maji', r'hanywi vizuri'],
    'hydration_false': [r'anakunywa maji kama kawaida', r'anakunywa kama kawaida'],
    'cannot_drink': [r'hawezi kunywa kabisa'],
    'convulsions': [r'ametapatwa na degedege'],
    'negation': [r'sitapiki', r'hatapiki', r'sikohoi', r'hakohoi', r'siharishi', r'haharishi'],
}
NORMALIZATION = {phrase: canonical for phrase, (_, canonical) in PHRASES.items()}
PATTERN = re.compile(r'\b(?:'+'|'.join(re.escape(p) for p in sorted(PHRASES,key=len,reverse=True))+r')\b', re.I)


def normalize_model_text(text):
    text = PATTERN.sub(lambda m: NORMALIZATION[m.group().lower()], text)
    # ONLY this exact duration phrase, never arbitrary tree -> three replacement.
    return re.sub(r'\btree(?=\s+days?\b)', 'three', text, flags=re.I)


def extend_patterns(patterns):
    return {label: '(?:'+pattern+'|'+r'\b(?:'+'|'.join(re.escape(p) for p,(kind,_) in PHRASES.items() if kind==label)+r')\b)'
            for label,pattern in patterns.items()}
