"""
Realistic input corruptions for backtesting the text extraction pipeline.

Every perturbation is a function (text, ctx) -> text, where ctx carries a seeded `rng` and, for the targeted
ones, `spans`: the evidence spans the pipeline found on the CLEAN text. Targeted perturbations corrupt exactly the
words the pipeline relies on (a symptom word, a negation cue), which is the worst case for a typo.

Perturbations are deterministic given the seed. A perturbation that leaves the text unchanged is reported as a
no-op by the caller and excluded from the rates (we only count cases that were really corrupted).
"""

import random
import re
from dataclasses import dataclass, field

# QWERTY neighbours: the typo a thumb on a phone keyboard makes.
NEIGHBOURS = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij", "i": "uok", "o": "ipl",
    "p": "ol", "a": "qsz", "s": "awdx", "d": "serf", "f": "drtg", "g": "ftyh", "h": "gyuj", "j": "huik",
    "k": "jiol", "l": "kop", "z": "asx", "x": "zsdc", "c": "xdfv", "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk",
}
VOWELS = "aeiouAEIOU"
WORD = re.compile(r"[A-Za-z]{4,}")


@dataclass
class Ctx:
    rng: random.Random
    spans: list[dict] = field(default_factory=list)  # evidence spans {text, start, end} from the clean text


def _edit_word(word: str, rng: random.Random, kind: str | None = None) -> str:
    """One character-level typo inside a word (never the first letter for delete/swap, as people rarely drop it)."""
    if len(word) < 3:
        return word
    kind = kind or rng.choice(["delete", "swap", "dup", "neighbour"])
    i = rng.randrange(1, len(word) - 1)
    if kind == "delete":
        return word[:i] + word[i + 1 :]
    if kind == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    if kind == "dup":
        return word[:i] + word[i] + word[i:]
    ch = word[i].lower()
    sub = rng.choice(NEIGHBOURS[ch]) if ch in NEIGHBOURS else ch
    return word[:i] + (sub.upper() if word[i].isupper() else sub) + word[i + 1 :]


def _replace_spans(text: str, spans: list[tuple[int, int]], fn) -> str:
    """Apply fn to text[start:end] for each span, right to left so offsets stay valid."""
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + fn(text[start:end]) + text[end:]
    return text


def _words_in(text: str, start=0, end=None):
    return [(m.start() + start, m.end() + start) for m in WORD.finditer(text[start:end])]


# ---- random typos -----------------------------------------------------------------------------------------

def typo_random_1(text: str, ctx: Ctx) -> str:
    words = _words_in(text)
    if not words:
        return text
    s, e = ctx.rng.choice(words)
    return text[:s] + _edit_word(text[s:e], ctx.rng) + text[e:]


def typo_random_3(text: str, ctx: Ctx) -> str:
    for _ in range(3):
        text = typo_random_1(text, ctx)
    return text


# ---- targeted typos: corrupt exactly the words the pipeline needs ------------------------------------------

def typo_in_evidence(text: str, ctx: Ctx) -> str:
    """One typo inside one matched symptom/sign word (the worst case for a regex that wants exact words)."""
    spans = [(sp["start"], sp["end"]) for sp in ctx.spans if _words_in(text, sp["start"], sp["end"])]
    if not spans:
        return text
    s, e = ctx.rng.choice(spans)
    words = _words_in(text, s, e)
    ws, we = ctx.rng.choice(words)
    return text[:ws] + _edit_word(text[ws:we], ctx.rng) + text[we:]


def vowel_drop_in_evidence(text: str, ctx: Ctx) -> str:
    """SMS-style: 'homa' -> 'hma', 'kikohozi' -> 'kikhz'. Drops the non-initial vowels of one matched word."""
    spans = [(sp["start"], sp["end"]) for sp in ctx.spans if _words_in(text, sp["start"], sp["end"])]
    if not spans:
        return text
    s, e = ctx.rng.choice(spans)
    ws, we = ctx.rng.choice(_words_in(text, s, e))
    word = text[ws:we]
    return text[:ws] + word[0] + "".join(c for c in word[1:] if c not in VOWELS) + text[we:]


NEGATION_CUES = re.compile(
    r"\b(?:no|not|never|without|denies|denied|doesn't|don't|isn't|wasn't|hasn't|haven't|sina|hana|hakuna|si)\b", re.I
)


def typo_in_negation(text: str, ctx: Ctx) -> str:
    """Corrupt one negation cue. Dangerous direction: a lost denial turns 'no fever' into 'fever'."""
    cues = [(m.start(), m.end()) for m in NEGATION_CUES.finditer(text)]
    if not cues:
        return text
    s, e = ctx.rng.choice(cues)
    cue = text[s:e]
    # Short cues (no, si) only have a neighbour-key or a drop; longer ones take any edit.
    new = cue[:-1] if len(cue) <= 3 else _edit_word(cue, ctx.rng)
    return text[:s] + new + text[e:]


# ---- keyboard / formatting artefacts (deterministic) --------------------------------------------------------

def apostrophe_dropped(text: str, ctx: Ctx) -> str:
    """don't -> dont, can't -> cant. Very common when typing fast."""
    return text.replace("'", "")


def apostrophe_curly(text: str, ctx: Ctx) -> str:
    """don't -> don’t. Phone keyboards and autocorrect insert U+2019 by default."""
    return text.replace("'", "’")


def all_caps(text: str, ctx: Ctx) -> str:
    return text.upper()


def all_lower(text: str, ctx: Ctx) -> str:
    return text.lower()


def no_punctuation(text: str, ctx: Ctx) -> str:
    """Like a speech transcript or a hurried message: no sentence punctuation (apostrophes kept)."""
    return re.sub(r"[.,;:!?]", "", text)


def messy_spacing(text: str, ctx: Ctx) -> str:
    return "  " + re.sub(r" ", "  ", text) + " \n"


def swap_number_format(text: str, ctx: Ctx) -> str:
    """'2 days' <-> 'two days', 'siku 2' <-> 'siku mbili': digits and words are both normal."""
    words = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight",
             "9": "nine", "10": "ten"}
    sw = {"1": "moja", "2": "mbili", "3": "tatu", "4": "nne", "5": "tano", "6": "sita", "7": "saba", "8": "nane",
          "9": "tisa", "10": "kumi"}
    out = re.sub(r"\b(10|[1-9])(?=\s+(?:days?|siku))", lambda m: words[m.group(1)], text, flags=re.I)
    if out == text:
        out = re.sub(r"(?<=siku )(10|[1-9])\b", lambda m: sw[m.group(1)], text, flags=re.I)
    if out == text:
        rev = {v: k for k, v in words.items()}
        out = re.sub(r"\b(" + "|".join(rev) + r")(?=\s+days?\b)", lambda m: rev[m.group(1).lower()], text, flags=re.I)
    return out


def composite(text: str, ctx: Ctx) -> str:
    """A realistic bad message: curly apostrophes, no punctuation, lowercase, one typo in a matched word."""
    text = typo_in_evidence(text, ctx)
    return all_lower(apostrophe_curly(no_punctuation(text, ctx), ctx), ctx)


# name -> (function, random?, description). Random ones are repeated over several seeds by the backtest.
PERTURBATIONS = {
    "apostrophe_dropped": (apostrophe_dropped, False, "don't -> dont"),
    "apostrophe_curly": (apostrophe_curly, False, "don't -> don’t (phone keyboard default)"),
    "all_caps": (all_caps, False, "WHOLE MESSAGE IN CAPITALS"),
    "all_lower": (all_lower, False, "all lowercase"),
    "no_punctuation": (no_punctuation, False, "punctuation removed"),
    "messy_spacing": (messy_spacing, False, "double spaces, leading/trailing whitespace, newline"),
    "number_format": (swap_number_format, False, "'2 days' <-> 'two days', 'siku 2' <-> 'siku mbili'"),
    "typo_random_1": (typo_random_1, True, "one random typo in a random word"),
    "typo_random_3": (typo_random_3, True, "three random typos"),
    "typo_in_evidence": (typo_in_evidence, True, "one typo inside a matched symptom/sign word"),
    "vowel_drop": (vowel_drop_in_evidence, True, "SMS-style vowel drop in a matched word (homa -> hma)"),
    "typo_in_negation": (typo_in_negation, True, "one typo in a negation cue"),
    "composite": (composite, True, "curly quotes + no punctuation + lowercase + one typo in a matched word"),
}
