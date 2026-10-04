"""
Clean-up and typo handling for free-text answers, applied before the extraction model sees them.

The model (ml/src/extraction_pipeline.py) accepts a symptom only when an exact-wording regex matches the raw text, and it
recognises a denial only from a fixed list of cues. Real typing breaks both: a curly or missing apostrophe turns
"I don't have fever" into fever, `didn't` and `hamna` are not cues at all, a double space splits "cannot  drink", and one
wrong letter drops a symptom with nothing to tell the user. ml/src is hash-frozen, so the fixes live here:

  normalize_text      Unicode, apostrophes, invisible characters, whitespace, contractions, a few missing negation cues
  strip_leading_none  "no, he cannot drink": judge the part after the leading "no" on its own
  near_miss           a word one typo away from a symptom word: FLAG it for review, never assert it

Backtest: ml/robustness/edge_cases.py (before and after numbers in ml/robustness/EDGE_CASES.md).
"""

import re
import unicodedata

_APOSTROPHES = str.maketrans({c: "'" for c in "’‘ʼ`´′‵ʹ＇"})
# zero-width, soft hyphen and bidi control characters: invisible, but they split words and phrases
_INVISIBLE = {ord(c): None for c in "​‌‍⁠﻿­‎‏‪‫‬‭‮⁦⁧⁨⁩"}

_CONTRACTION = re.compile(r"\b(do|does|did|had|has|have|is|was|were|are|would|could|should)n['\s]?t\b", re.I)
_CANT = re.compile(r"\bcan['\s]?t\b", re.I)
_WONT = re.compile(r"\bwon['\s]?t\b", re.I)
_IM_AGE = re.compile(r"\bI['\s]?m(?=\s+\d{1,3}\s+years?\b)", re.I)
_UNIT_GLUE = re.compile(r"(\d)(days?|siku|weeks?|wiki|months?|miezi|years?|miaka)\b", re.I)

# Cues the model does not know, rewritten to ones it does. Deliberately NOT rewritten: aren't/weren't/won't/wouldn't,
# because "aren't drinking" and "won't drink" are findings in their own right (poor drinking), not denials.
_CUE_REWRITES = [
    (re.compile(r"\bnot only\b", re.I), "also"),  # "not only fever but also cough" affirms both: not a denial
    (re.compile(r"\b(?:neither|nor)\b", re.I), "no"),
    (re.compile(r"\b(?:didn't|hadn't)\b", re.I), "doesn't"),
    (re.compile(r"\bnone of\b[:\s]*", re.I), "no "),
    (re.compile(r"\bcan not\b", re.I), "cannot"),
    (re.compile(r"\bnakohoa\b", re.I), "ninakohoa"),  # colloquial "I cough"
    (re.compile(r"\bnatapika\b", re.I), "ninatapika"),  # colloquial "I vomit"
    (re.compile(r"\b(?:sio|siyo)\b", re.I), "not"),
    (re.compile(r"\b(?:hamna|haina)\b", re.I), "hakuna"),
    (re.compile(r"\bbila\b", re.I), "without"),
    (re.compile(r"\b(?:hawana|hatuna)\b", re.I), "hana"),
]
_LEADING_NONE = re.compile(r"^\s*(?:no|nope|hapana|hakuna|none|nothing)\s*[,.;:!\-]+\s*(?=\S)", re.I)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text.translate(_APOSTROPHES)).translate(_INVISIBLE).translate(_APOSTROPHES)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Every kind of space becomes one space. Newlines are kept: the model treats them as sentence breaks.
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r" ?\n[ \n]*", "\n", text).strip()

    text = _CONTRACTION.sub(lambda m: f"{m.group(1)}n't", text)
    text = _CANT.sub("can't", text)
    text = _WONT.sub("won't", text)
    text = _IM_AGE.sub("I'm", text)
    text = _UNIT_GLUE.sub(r"\1 \2", text)
    for pattern, replacement in _CUE_REWRITES:
        text = pattern.sub(replacement, text)
    return text


def strip_leading_none(text: str) -> str:
    """'no, he cannot drink' -> 'he cannot drink'. A bare 'no.' or 'none' is left alone."""
    return _LEADING_NONE.sub("", text, count=1)


# --------------------------------------------------------------------------------------------------------------
# Near-miss detection: flag, never assert
# --------------------------------------------------------------------------------------------------------------

# word -> (kind, app code). Only words the user could mistype into something the exact-wording gate rejects.
NEAR_VOCAB = {
    **{w: ("symptom", "fever") for w in ("fever", "feverish", "homa")},
    **{w: ("symptom", "cough") for w in ("cough", "coughing", "kikohozi", "kukohoa", "anakohoa", "ninakohoa", "nakohoa")},
    **{w: ("symptom", "diarrhoea") for w in ("diarrhoea", "diarrhea", "kuhara", "kuharisha", "anaharisha", "ninaharisha")},
    **{w: ("symptom", "vomiting") for w in ("vomiting", "vomit", "kutapika", "anatapika", "ninatapika", "natapika")},
    **{w: ("symptom", "headache") for w in ("headache", "kichwa")},
    **{w: ("symptom", "abdominal_pain") for w in ("stomach", "abdominal", "tumbo")},
    **{w: ("symptom", "difficulty_breathing") for w in ("breathing", "kupumua")},
    **{w: ("symptom", "weakness") for w in ("weakness", "weak", "tired", "fatigue", "exhausted", "dhaifu", "udhaifu", "uchovu")},
    **{w: ("sign", "convulsions") for w in ("convulsions", "convulsion", "seizure", "seizures", "degedege")},
    "bleeding": ("sign", "vaginal_bleeding"),
}
# Ordinary words one edit away from a vocabulary word. Without this, "never had fever" would flag "never" as a typo of "fever".
COMMON_WORDS = frozenset(
    "never ever fewer lever sever tough rough couch tried tires tiled tired week weeks home hope hole holy hama wear beak peak "
    "leak weal seek weed heal head heads ached bleed breed feeding feeling feels heading hearing leading reading dealing "
    "weaker weaken weakly vomits tire fiver fibre ham".split()
)
NEGATION_TOKENS = frozenset(
    "no not never without denies denied doesn't don't didn't isn't wasn't hasn't haven't hadn't hakuna hana sina si "
    "hamna haina bila sio siyo none nothing nor neither".split()
)
_TOKEN = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?", re.UNICODE)


def osa_distance(a: str, b: str, limit: int) -> int:
    """Edit distance counting a swap of two neighbouring letters as one edit. Skips the work (returns limit + 1) when the lengths alone differ by more than `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            if prev2 is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cost = min(cost, prev2[j - 2] + 1)
            cur.append(cost)
        prev2, prev = prev, cur
    return prev[-1]


# Sentences the model treats as uncertain or past: a "possible typo" there would contradict its decision.
_HEDGED = re.compile(
    r"\b(?:maybe|perhaps|possibly|might|unsure|not sure|could be|labda|huenda|sina uhakika|used to|last year|previously|"
    r"resolved|stopped|no longer|imeisha|zamani)\b",
    re.I,
)
_SENTENCE = re.compile(r"[.!?;\n]+")


def sentences(text: str) -> list[str]:
    return [part for part in _SENTENCE.split(normalize_text(text)) if part.strip()]


def near_miss(text: str, known_words: frozenset[str] = frozenset()) -> list[tuple[str, str, str]]:
    """
    Words that look like a mistyped symptom or sign word: [(word as typed, kind, app code)].
    A word counts when it is not itself recognised (not in the vocabulary, the model's phrase table `known_words`, or
    COMMON_WORDS) and is one edit away (two for words of 8+ letters). Words just after a negation cue, and whole
    hedged or past-tense sentences, are skipped.
    """
    found: list[tuple[str, str, str]] = []
    for sentence in sentences(text):
        if _HEDGED.search(sentence):
            continue
        since_negation = 99
        for raw in _TOKEN.findall(sentence.lower()):
            if raw in NEGATION_TOKENS:
                since_negation = 0
                continue
            since_negation += 1
            token = raw.replace("'", "")
            if token in NEAR_VOCAB or token in known_words or token in COMMON_WORDS or since_negation <= 4:
                continue
            if len(token) == 3:
                # "hoa", "oma", "hom": three-letter typos of "homa" (fever), the commonest symptom word in Swahili.
                if osa_distance(token, "homa", 1) <= 1 and (raw, "symptom", "fever") not in found:
                    found.append((raw, "symptom", "fever"))
                continue
            if len(token) < 4:
                continue
            for word, (kind, code) in NEAR_VOCAB.items():
                limit = 2 if len(word) >= 8 else 1
                if osa_distance(token, word, limit) <= limit:
                    if (raw, kind, code) not in found:
                        found.append((raw, kind, code))
                    break
    return found


_CANNOT_CUES = ("cannot", "unable", "hawezi", "siwezi", "can't")
_DRINK_WORDS = ("drink", "kunywa")


_REDUCED = ("much", "well", "enough", "vizuri")  # the model's own exclusion: "hawezi kunywa vizuri" is reduced drinking


def inability_to_drink(text: str) -> str | None:
    """
    "he cannot drink" with a typo in either word, or with a word in between ("cannot even drink"), which the model's
    exact phrase misses. Returns the phrase as typed, or None. Skips a negation cue before it, a hedged sentence, and
    "cannot drink well/much/enough" (the model treats that as reduced drinking, not inability).
    """
    for sentence in sentences(text):
        if _HEDGED.search(sentence):
            continue
        tokens = _TOKEN.findall(sentence.lower())
        for i, tok in enumerate(tokens):
            is_cue = tok in _CANNOT_CUES or any(len(c) >= 5 and osa_distance(tok, c, 1) <= 1 for c in _CANNOT_CUES)
            if not is_cue or any(t in NEGATION_TOKENS for t in tokens[max(0, i - 3) : i]):
                continue
            for j in range(i + 1, min(i + 4, len(tokens))):
                nxt = tokens[j]
                if len(nxt) >= 4 and any(osa_distance(nxt, w, 1) <= 1 for w in _DRINK_WORDS):
                    if j + 1 < len(tokens) and tokens[j + 1] in _REDUCED:
                        break
                    return " ".join(tokens[i : j + 1])
    return None
