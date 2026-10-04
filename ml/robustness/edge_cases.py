"""
Systematic edge-case test of typed input through the real /extract adapter (backend/app/extract.py).

Every probe is judged by what the USER SEES, not by raw detection:
  correct        the output matches the truth
  flagged        wrong or incomplete, but the app warns the user (low confidence, or the raw text is surfaced in notes)
  silent_error   wrong or incomplete at HIGH confidence with nothing flagged: the dangerous outcome
  crash          the adapter raised
  rejected       the request schema refused it (e.g. over 2000 characters); the app then falls back to its rules

Categories: control, typo (every single-character edit at every position of the key words), negation (every cue,
every apostrophe spelling), scope, uncertainty, group, duration, danger, format, garbage, locale.
`ambiguous` probes have no single right answer; they are reported but excluded from the headline numbers.

Usage (from the repo root; needs the backend deps, scikit-learn and the extraction artifact):
  python ml/robustness/edge_cases.py --artifact path/to/experimental_health_ie_final.joblib --out ml/robustness/edge_report
"""

import argparse
import collections
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ML = HERE.parent
sys.path.insert(0, str(HERE))
from perturb import NEIGHBOURS  # noqa: E402

MISSING = object()
RANK = {"correct": 0, "flagged": 1, "silent_error": 2, "crash": 3}


@dataclass
class Probe:
    category: str
    sub: str
    field: str  # who | complaint | duration | danger
    text: str
    expect: dict = field(default_factory=dict)  # symptoms/signs (exact sets), forbid_*, group, days
    ambiguous: bool = False


# --------------------------------------------------------------------------------------------------------------
# Probe catalog
# --------------------------------------------------------------------------------------------------------------

# (text, key words to corrupt, expected symptoms)
COMPLAINT_BASES = [
    ("I have fever", ["fever"], {"fever"}),
    ("my child has a cough", ["cough"], {"cough"}),
    ("he has diarrhoea", ["diarrhoea"], {"diarrhoea"}),
    ("she is vomiting", ["vomiting"], {"vomiting"}),
    ("I have a headache", ["headache"], {"headache"}),
    ("stomach pain", ["stomach", "pain"], {"abdominal_pain"}),
    ("difficulty breathing", ["difficulty", "breathing"], {"difficulty_breathing"}),
    ("I am weak", ["weak"], {"weakness"}),
    ("feeling very tired", ["tired"], {"weakness"}),
    ("fever and cough", ["fever", "cough"], {"fever", "cough"}),
    ("fever, cough and diarrhoea", ["fever", "cough", "diarrhoea"], {"fever", "cough", "diarrhoea"}),
    ("headache and vomiting", ["headache", "vomiting"], {"headache", "vomiting"}),
    ("ana homa", ["homa"], {"fever"}),
    ("nina homa na kikohozi", ["homa", "kikohozi"], {"fever", "cough"}),
    ("anatapika", ["anatapika"], {"vomiting"}),
    ("mtoto ana kuhara", ["kuhara"], {"diarrhoea"}),
    ("kichwa kinauma", ["kichwa", "kinauma"], {"headache"}),
    ("maumivu ya tumbo", ["maumivu", "tumbo"], {"abdominal_pain"}),
    ("ana shida ya kupumua", ["shida", "kupumua"], {"difficulty_breathing"}),
    ("ana udhaifu", ["udhaifu"], {"weakness"}),
    ("nina uchovu", ["uchovu"], {"weakness"}),
    ("ninakohoa", ["ninakohoa"], {"cough"}),
    ("mtoto ana homa kali na anakohoa", ["homa", "anakohoa"], {"fever", "cough"}),
]
# (text, key words, expected signs) typed into the danger box
DANGER_BASES = [
    ("he cannot drink", ["cannot", "drink"], {"unable_to_drink"}),
    ("unable to drink", ["unable", "drink"], {"unable_to_drink"}),
    ("he has convulsions", ["convulsions"], {"convulsions"}),
    ("she had a seizure", ["seizure"], {"convulsions"}),
    ("ana degedege", ["degedege"], {"convulsions"}),
    ("hawezi kunywa", ["hawezi", "kunywa"], {"unable_to_drink"}),
    ("heavy bleeding", ["bleeding"], {"vaginal_bleeding"}),
    ("kutokwa na damu", ["kutokwa", "damu"], {"vaginal_bleeding"}),
    ("cannot drink and convulsions", ["drink", "convulsions"], {"unable_to_drink", "convulsions"}),
]


def single_edits(word: str):
    """Every single-character typo at every position: delete, transpose, duplicate, QWERTY-neighbour substitute."""
    out = {}
    for i, ch in enumerate(word):
        out[("delete", i)] = word[:i] + word[i + 1 :]
        out[("duplicate", i)] = word[:i] + ch + word[i:]
        for j, nb in enumerate(NEIGHBOURS.get(ch.lower(), "")):
            out[(f"neighbour", f"{i}{nb}")] = word[:i] + nb + word[i + 1 :]
        if i + 1 < len(word) and word[i] != word[i + 1]:
            out[("transpose", i)] = word[:i] + word[i + 1] + word[i] + word[i + 2 :]
    return {k: v for k, v in out.items() if v and v != word}


def typo_probes():
    probes = []
    for bases, fld, key in ((COMPLAINT_BASES, "complaint", "symptoms"), (DANGER_BASES, "danger", "signs")):
        for text, words, expected in bases:
            for word in words:
                if len(word) < 4:
                    continue
                for (kind, _), typo in single_edits(word).items():
                    # Deleting the f of "fever" leaves the real word "ever": deliberately not flagged (documented limit).
                    probes.append(Probe("typo", f"{kind}", fld, text.replace(word, typo, 1), {key: set(expected)}, ambiguous=typo == "ever"))
    return probes


APOSTROPHES = {
    "straight": "'", "dropped": "", "curly": "’", "left_curly": "‘", "backtick": "`", "acute": "´",
    "modifier": "ʼ", "prime": "′", "space": " ",
}  # fmt: skip

NEG_SYMPTOMS_EN = [("fever", "fever"), ("cough", "cough"), ("diarrhoea", "diarrhoea"), ("vomiting", "vomiting"), ("headache", "headache")]
NEG_SYMPTOMS_SW = [("homa", "fever"), ("kikohozi", "cough"), ("kuhara", "diarrhoea"), ("kutapika", "vomiting")]
NEG_TEMPLATES_EN = {
    "no": "no {s}", "have_no": "I have no {s}", "dont": "I don't have {s}", "doesnt": "he doesn't have {s}",
    "didnt": "she didn't have {s}", "havent": "I haven't had {s}", "hasnt": "he hasn't had {s}",
    "hadnt": "she hadn't had {s}", "isnt": "it isn't {s}", "wasnt": "it wasn't {s}", "without": "without {s}",
    "never": "never had {s}", "denies": "denies {s}", "not": "not {s}", "do_not": "I do not have {s}",
    "does_not": "he does not have {s}", "did_not": "she did not have {s}", "no_longer": "no longer has {s}",
}  # fmt: skip
NEG_TEMPLATES_SW = {
    "sina": "sina {s}", "hana": "hana {s}", "hakuna": "hakuna {s}", "hamna": "hamna {s}", "bila": "bila {s}",
    "haina": "haina {s}", "mtoto_hana": "mtoto hana {s}", "hakuna_kabisa": "hakuna {s} kabisa",
}  # fmt: skip


def negation_probes():
    probes = []
    for name, tpl in NEG_TEMPLATES_EN.items():
        for word, code in NEG_SYMPTOMS_EN:
            kinds = APOSTROPHES if "'" in tpl else {"straight": "'"}
            for kind, ap in kinds.items():
                probes.append(Probe("negation", f"{name}/{kind}", "complaint", tpl.format(s=word).replace("'", ap), {"forbid_symptoms": {code}}))
    for name, tpl in NEG_TEMPLATES_SW.items():
        for word, code in NEG_SYMPTOMS_SW:
            probes.append(Probe("negation", f"sw_{name}/straight", "complaint", tpl.format(s=word), {"forbid_symptoms": {code}}))
    # negated danger signs and "can drink" (the opposite of unable to drink)
    for tpl_name, tpl in {"no": "no {s}", "dont": "he doesn't have {s}", "none_of": "none of: {s}", "sw_hakuna": "hakuna {s}", "sw_hana": "hana {s}"}.items():
        for word, sign in (("convulsions", "convulsions"), ("seizures", "convulsions"), ("degedege", "convulsions"), ("bleeding", "vaginal_bleeding")):
            kinds = APOSTROPHES if "'" in tpl else {"straight": "'"}
            for kind, ap in kinds.items():
                probes.append(Probe("negation", f"sign_{tpl_name}/{kind}", "danger", tpl.format(s=word).replace("'", ap), {"forbid_signs": {sign}}))
    for text in ("he can drink", "he can drink water", "anakunywa vizuri", "he is drinking normally", "anakunywa maji kama kawaida", "he can swallow and drink"):
        probes.append(Probe("negation", "can_drink", "danger", text, {"forbid_signs": {"unable_to_drink"}}))
    return probes


SCOPE_EN = [  # (text, expected exact symptoms, ambiguous)
    ("no fever but cough", {"cough"}, False), ("no fever, only a cough", {"cough"}, False),
    ("fever but no cough", {"fever"}, False), ("I have fever and I don't have cough", {"fever"}, False),
    ("no fever and no cough", set(), False), ("no fever or cough", set(), False),
    ("fever and cough but no vomiting", {"fever", "cough"}, False),
    ("no vomiting but diarrhoea and fever", {"diarrhoea", "fever"}, False),
    ("he has fever, he does not have cough", {"fever"}, False), ("fever. no cough.", {"fever"}, False),
    ("no fever. cough.", {"cough"}, False), ("cough without fever", {"cough"}, False),
    ("without fever but with cough", {"cough"}, False), ("fever, no cough, vomiting", {"fever", "vomiting"}, True),
    ("fever, no fever", set(), True), ("not only fever but also cough", {"fever", "cough"}, False),
    ("fever and cough and no diarrhoea", {"fever", "cough"}, False),
    ("no fever, no cough, no vomiting", set(), False), ("fever; cough; no headache", {"fever", "cough"}, False),
    ("I don't have fever but I do have a cough", {"cough"}, False), ("neither fever nor cough", set(), False),
]
SCOPE_SW = [
    ("ana homa lakini hana kikohozi", {"fever"}, False), ("hana homa lakini anakohoa", {"cough"}, False),
    ("sina homa wala kikohozi", set(), False), ("ana homa na kikohozi", {"fever", "cough"}, False),
    ("homa bila kikohozi", {"fever"}, False), ("hakuna homa, hakuna kikohozi", set(), False),
    ("nina homa lakini sina kikohozi", {"fever"}, False), ("hana homa na hana kikohozi", set(), False),
]


def scope_probes():
    probes = []
    for text, exp, amb in SCOPE_EN + SCOPE_SW:
        kinds = APOSTROPHES if "'" in text else {"straight": "'"}
        for kind, ap in kinds.items():
            probes.append(Probe("scope", kind, "complaint", text.replace("'", ap), {"symptoms": set(exp)}, amb))
    return probes


def uncertainty_probes():
    forbid = {"fever"}
    texts = [
        "maybe fever", "perhaps fever", "might have fever", "possibly fever", "not sure if fever", "could be fever",
        "labda homa", "huenda ana homa", "sina uhakika kama ana homa",
        "had fever last year", "fever resolved", "used to have fever", "fever stopped", "previously had fever",
        "fever no longer", "homa imeisha", "zamani alikuwa na homa",
    ]  # fmt: skip
    return [Probe("uncertainty", "hedged_or_past", "complaint", t, {"forbid_symptoms": forbid}) for t in texts]


GROUP_CASES = [  # (text, true group value, ambiguous)
    ("Mtoto wangu wa miaka miwili", "child_u5", False), ("my child, 3 years old", "child_u5", False),
    ("my child, 18 months old", "child_u5", False), ("mtoto wa miezi 6", "child_u5", False),
    ("my baby", "child_u5", False), ("my 2 year old child", "child_u5", False),
    ("my child, 9 years old", "child_5plus", False), ("mtoto wa miaka 7", "child_5plus", False),
    ("I am pregnant", "pregnant", False), ("mimi ni mjamzito", "pregnant", False), ("nina ujauzito", "pregnant", False),
    ("nina mimba ya miezi saba", "pregnant", False), ("my wife is pregnant", "pregnant", False),
    ("I am 30 years old", "adult", False), ("I'm 25 years old", "adult", False), ("adult", "adult", False),
    ("mtu mzima", "adult", False), ("my child and I", None, True),
]
GROUP_FORBID = [
    ("I am not pregnant", "pregnant"), ("I'm not pregnant", "pregnant"), ("sio mjamzito", "pregnant"),
    ("sina mimba", "pregnant"), ("not pregnant", "pregnant"), ("I am not pregnant", "pregnant"),
    ("my child is not 2, he is 9 years old", "child_u5"),
]


def group_probes():
    probes = []
    for text, truth, amb in GROUP_CASES:
        kinds = APOSTROPHES if "'" in text else {"straight": "'"}
        for kind, ap in kinds.items():
            probes.append(Probe("group", kind, "who", text.replace("'", ap), {"group": truth}, amb))
    for text, bad in GROUP_FORBID:
        kinds = APOSTROPHES if "'" in text else {"straight": "'"}
        for kind, ap in kinds.items():
            probes.append(Probe("group", f"forbid/{kind}", "who", text.replace("'", ap), {"forbid_group": {bad}}))
    return probes


DURATION_CASES = [  # (text, days or None when it cannot be a single number of days, ambiguous)
    ("3 days", 3, False), ("three days", 3, False), ("for 3 days", 3, False), ("3 DAYS", 3, False), ("tree days", 3, False),
    ("1 day", 1, False), ("one day", 1, False), ("2 days", 2, False), ("10 days", 10, False), ("seven days", 7, False),
    ("siku tatu", 3, False), ("siku 3", 3, False), ("siku moja", 1, False), ("siku mbili", 2, False),
    ("siku saba", 7, False), ("siku kumi", 10, False), ("kwa siku nne", 4, False),
    ("a week", 7, True), ("2 weeks", 14, True), ("wiki moja", 7, True), ("wiki mbili", 14, True),
    ("one month", 30, True), ("mwezi mmoja", 30, True), ("since yesterday", 1, True), ("tangu jana", 1, True),
    ("today", 0, True), ("leo", 0, True), ("6 hours", 0, True), ("a few days", None, True), ("siku chache", None, True),
    ("about 3 days", None, True), ("karibu siku tatu", None, True), ("siku mbili au tatu", None, False), ("two or three days", None, False), ("2-3 days", None, False), ("3 or 4 days", None, False),
    ("not 3 days", None, True), ("3days", 3, False), ("3 dys", 3, False), ("thre days", 3, False), ("tre days", 3, False),
    ("three days ago", 3, False), ("for the past 5 days", 5, False),
]


def duration_probes():
    probes = [Probe("duration", "plain", "duration", t, {"days": d}, a) for t, d, a in DURATION_CASES]
    probes += [
        Probe("duration", "in_complaint", "complaint", "fever for 3 days", {"days": 3, "symptoms": {"fever"}}),
        Probe("duration", "in_complaint", "complaint", "homa kwa siku tatu", {"days": 3, "symptoms": {"fever"}}),
        Probe("duration", "conflict", "complaint", "fever for 3 days, cough for 5 days", {"days": None}, True),
        Probe("duration", "negated", "complaint", "fever, not for 3 days", {"days": None}, True),
    ]
    return probes


NONE_WORDS = ["hakuna", "none", "no", "nothing", "hapana", "hamna", "none of these", "no danger signs", "nope", "hakuna kati ya hayo", "No.", "NONE", "hakuna!", "  hakuna  "]


def danger_probes():
    probes = [Probe("danger", "said_none", "danger", t, {"signs": set()}) for t in NONE_WORDS]
    probes += [Probe("danger", "said_none_typo", "danger", t, {"signs": set()}) for t in ("hakna", "non", "nothin", "hkuna", "hakunaa", "haukna")]
    probes += [
        Probe("danger", "sign_and_none", "danger", "no, he cannot drink", {"signs": {"unable_to_drink"}}),
        Probe("danger", "sign_and_none", "danger", "hapana, ana degedege", {"signs": {"convulsions"}}),
        Probe("danger", "sign_and_none", "danger", "nothing else but he cannot drink", {"signs": {"unable_to_drink"}}),
        Probe("danger", "mixed", "danger", "cannot drink and no convulsions", {"signs": {"unable_to_drink"}}),
        Probe("danger", "mixed", "danger", "no convulsions but cannot drink", {"signs": {"unable_to_drink"}}),
        Probe("danger", "mixed", "danger", "hawezi kunywa na hana degedege", {"signs": {"unable_to_drink"}}),
        Probe("danger", "mixed", "danger", "hana degedege lakini hawezi kunywa", {"signs": {"unable_to_drink"}}),
        Probe("danger", "reduced_not_unable", "danger", "drinking less than usual", {"forbid_signs": {"unable_to_drink"}}),
        Probe("danger", "reduced_not_unable", "danger", "anakunywa maji kidogo", {"forbid_signs": {"unable_to_drink"}}),
        Probe("danger", "cannot_drink_forms", "danger", "he cannot even drink", {"signs": {"unable_to_drink"}}),
        Probe("danger", "cannot_drink_forms", "danger", "he can not drink", {"signs": {"unable_to_drink"}}),
        Probe("danger", "cannot_drink_forms", "danger", "hawezi hata kunywa", {"signs": {"unable_to_drink"}}),
        Probe("danger", "cannot_drink_forms", "danger", "unable to even drink water", {"signs": {"unable_to_drink"}}),
        Probe("danger", "dont_know", "danger", "sijui", {"signs": set()}),
        Probe("danger", "dont_know", "danger", "I don't know", {"signs": set()}),
        Probe("danger", "dont_know", "danger", "not sure", {"signs": set()}),
    ]
    return probes


FORMAT_CORE = [  # (field, text, expect)
    ("complaint", "I have fever", {"symptoms": {"fever"}}),
    ("complaint", "my child has fever and cough", {"symptoms": {"fever", "cough"}}),
    ("complaint", "ana homa na kikohozi", {"symptoms": {"fever", "cough"}}),
    ("complaint", "I don't have fever", {"forbid_symptoms": {"fever"}}),
    ("complaint", "hakuna homa", {"forbid_symptoms": {"fever"}}),
    ("danger", "he cannot drink", {"signs": {"unable_to_drink"}}),
    ("danger", "hakuna", {"signs": set()}),
]
FORMATS = {
    "upper": str.upper, "lower": str.lower, "title": str.title, "swapcase": str.swapcase,
    "leading_trailing_space": lambda s: "   " + s + "   ", "double_space": lambda s: s.replace(" ", "  "),
    "tabs": lambda s: s.replace(" ", "\t"), "newlines": lambda s: s.replace(" ", "\n"), "crlf": lambda s: s.replace(" ", "\r\n"),
    "nbsp": lambda s: s.replace(" ", " "), "thin_space": lambda s: s.replace(" ", " "),
    "zero_width_between_words": lambda s: s.replace(" ", " ​"), "zero_width_in_word": lambda s: s[:2] + "​" + s[2:],
    "soft_hyphen_in_word": lambda s: s[:3] + "­" + s[3:], "bidi_marks": lambda s: "‏" + s + "‎",
    "fullwidth": lambda s: "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in s),
    "trailing_bangs": lambda s: s + "!!!", "trailing_dots": lambda s: s + "...", "trailing_question": lambda s: s + "?",
    "leading_dash": lambda s: "- " + s, "bullet": lambda s: "• " + s, "quoted": lambda s: '"' + s + '"',
    "parentheses": lambda s: "(" + s + ")", "no_spaces_after_commas": lambda s: s.replace(", ", ","),
    "emoji_suffix": lambda s: s + " \U0001f912", "emoji_prefix": lambda s: "\U0001f912 " + s, "emoji_between": lambda s: s.replace(" ", " \U0001f622 ", 1),
    "repeat_twice": lambda s: s + " " + s, "filler_prefix": lambda s: "umm " + s, "polite_prefix": lambda s: "please help: " + s,
    "trailing_newline": lambda s: s + "\n", "html_bold": lambda s: "<b>" + s + "</b>", "markdown_bold": lambda s: "**" + s + "**",
    "url_suffix": lambda s: s + " http://example.com/a?b=c", "json_wrapped": lambda s: '{"text": "' + s + '"}', "backslashes": lambda s: s.replace(" ", "\\ "),
    "ascii_art_separator": lambda s: s.replace(" ", " ~ "), "long_padding": lambda s: s + " " * 1500, "digits_prefix": lambda s: "12345 " + s,
}  # fmt: skip


def format_probes():
    probes = []
    for fld, text, exp in FORMAT_CORE:
        for name, fn in FORMATS.items():
            # A newline between every word is an artificial hard-wrap; the model deliberately treats a newline as a
            # sentence break ("no fever\ncough"), so these are reported but not counted.
            probes.append(Probe("format", name, fld, fn(text), exp, ambiguous=name in ("newlines", "crlf")))
    return probes


GARBAGE = [
    ("empty", ""), ("spaces", "     "), ("dots", "..."), ("questions", "????"), ("digits", "12345"), ("emoji_only", "\U0001f912"),
    ("gibberish", "asdfghjkl"), ("lorem", "Lorem ipsum dolor sit amet consectetur"), ("script_tag", "<script>alert(1)</script>"),
    ("sql", "'; DROP TABLE patients;--"), ("path", "../../etc/passwd"), ("null_byte", "fever\x00"), ("only_newlines", "\n\n\n"),
    ("rtl_arabic", "حمى"), ("chinese", "发烧"), ("hindi", "बुखार"), ("french", "j'ai de la fievre"),
    ("single_char", "a"), ("long_word", "a" * 1500), ("punctuation_soup", "!@#$%^&*()_+{}|:<>?"), ("percent_format", "%s %d {0} {x}"),
    ("template_injection", "{{7*7}} ${7*7}"), ("unicode_combining", "e" + "́" * 50), ("zalgo_fever", "f̵e̶v̷e̸r̹"),
    ("very_long_ok", "fever " * 330), ("exactly_2000", ("fever " * 400)[:2000]), ("over_limit", "fever " * 400 + "x"),
]


def garbage_probes():
    probes = []
    for name, text in GARBAGE:
        exp = {"symptoms": {"fever"}} if name in ("very_long_ok", "exactly_2000", "over_limit") else {"forbid_symptoms": {"fever", "cough", "vomiting", "diarrhoea"}}
        if name == "null_byte":
            exp = {"symptoms": {"fever"}}
        probes.append(Probe("garbage", name, "complaint", text, exp, ambiguous=name in ("french", "zalgo_fever")))
    for name, text in (("sql_danger", "'; DROP TABLE patients;--"), ("script_danger", "<script>alert(1)</script>"), ("emoji_danger", "\U0001f912"), ("long_danger", "x" * 1900)):
        probes.append(Probe("garbage", name, "danger", text, {"forbid_signs": {"unable_to_drink", "convulsions", "vaginal_bleeding"}}))
    return probes


def control_probes():
    probes = [Probe("control", "complaint", "complaint", t, {"symptoms": set(s)}) for t, _, s in COMPLAINT_BASES]
    probes += [Probe("control", "danger", "danger", t, {"signs": set(s)}) for t, _, s in DANGER_BASES]
    return probes


def locale_probes():
    return [Probe("locale", loc, "complaint", "I have fever", {"symptoms": {"fever"}}) for loc in ("en", "sw", "fr", "", "sw-KE", "EN", "xx")]


def build_catalog():
    return (control_probes() + typo_probes() + negation_probes() + scope_probes() + uncertainty_probes() + group_probes()
            + duration_probes() + danger_probes() + format_probes() + garbage_probes() + locale_probes())  # fmt: skip


# --------------------------------------------------------------------------------------------------------------
# Judging
# --------------------------------------------------------------------------------------------------------------

def worst(a: str, b: str) -> str:
    return a if RANK[a] >= RANK[b] else b


def judge_set(got: set, conf: str, exp: set | None, forbid: set | None, flagged_by_notes: bool) -> str:
    if exp is not None:
        if got == exp:
            return "correct"
    else:
        if not (forbid & got):
            return "correct"
    return "flagged" if (conf == "low" or flagged_by_notes) else "silent_error"


def judge_scalar(got, conf: str, exp, forbid) -> str:
    if forbid is not None:
        if got not in forbid:
            return "correct"
        return "flagged" if conf == "low" else "silent_error"
    if got == exp:
        return "correct"
    return "flagged" if (conf == "low" or got is None) else "silent_error"


def run_probe(extractor, ExtractRequest, p: Probe) -> dict:
    answers = {"who": "", "complaint": "", "duration": "", "danger": ""}
    answers[p.field] = p.text
    locale = p.sub if p.category == "locale" else "sw"
    try:
        req = ExtractRequest(locale=locale, answers=answers)
    except Exception as e:  # schema rejection
        return {"outcome": "rejected", "detail": str(e).splitlines()[0][:80]}
    try:
        out = extractor.extract(req)
    except Exception as e:
        return {"outcome": "crash", "detail": f"{type(e).__name__}: {e}"[:200]}

    notes_text = " ".join(out.unmapped)
    flagged_by_notes = bool(p.text.strip()) and p.text.strip() in notes_text
    outcome, detail = "correct", {}
    e = p.expect
    if "symptoms" in e or "forbid_symptoms" in e:
        got = set(out.symptoms.value)
        j = judge_set(got, out.symptoms.confidence, e.get("symptoms"), e.get("forbid_symptoms"), flagged_by_notes)
        outcome, detail["symptoms"] = worst(outcome, j), sorted(got)
    if "signs" in e or "forbid_signs" in e:
        got = set(out.dangerSigns.value)
        j = judge_set(got, out.dangerSigns.confidence, e.get("signs"), e.get("forbid_signs"), flagged_by_notes)
        outcome, detail["signs"] = worst(outcome, j), sorted(got)
    if "group" in e or "forbid_group" in e:
        j = judge_scalar(out.patientGroup.value, out.patientGroup.confidence, e.get("group"), e.get("forbid_group"))
        outcome, detail["group"] = worst(outcome, j), out.patientGroup.value
    if "days" in e:
        j = judge_scalar(out.durationDays.value, out.durationDays.confidence, e.get("days"), None)
        outcome, detail["days"] = worst(outcome, j), out.durationDays.value
    detail["conf"] = {"symptoms": out.symptoms.confidence, "signs": out.dangerSigns.confidence, "group": out.patientGroup.confidence}
    detail["notes"] = out.unmapped[:2]
    return {"outcome": outcome, "detail": detail}


def summarise(results):
    table = collections.OrderedDict()
    for p, r in results:
        if p.ambiguous:
            continue
        row = table.setdefault(p.category, collections.Counter())
        row[r["outcome"]] += 1
        row["total"] += 1
    return table


def render(results) -> str:
    out = ["| category | probes | correct | flagged | silent error | crash | rejected |", "|---|---:|---:|---:|---:|---:|---:|"]
    total = collections.Counter()
    for cat, row in summarise(results).items():
        out.append(f"| {cat} | {row['total']} | {row['correct']} | {row['flagged']} | {row['silent_error']} | {row['crash']} | {row['rejected']} |")
        total.update(row)
    out.append(f"| **all** | {total['total']} | {total['correct']} | {total['flagged']} | **{total['silent_error']}** | {total['crash']} | {total['rejected']} |")
    amb = collections.Counter(r["outcome"] for p, r in results if p.ambiguous)
    out.append(f"\nAmbiguous probes (no single right answer, excluded above): {sum(amb.values())} ({dict(amb)})")

    out.append("\n### Silent errors by sub-category (the dangerous outcome)\n")
    by_sub = collections.Counter(f"{p.category}/{p.sub}" for p, r in results if r["outcome"] == "silent_error" and not p.ambiguous)
    sub_total = collections.Counter(f"{p.category}/{p.sub}" for p, r in results if not p.ambiguous)
    out.append("| sub-category | silent errors | of probes |\n|---|---:|---:|")
    for key, n in by_sub.most_common():
        out.append(f"| {key} | {n} | {sub_total[key]} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--artifact", type=Path, required=True)
    ap.add_argument("--backend", type=Path, default=ML.parent / "backend")
    ap.add_argument("--out", type=Path, default=None, help="directory for edge_cases.json / edge_cases.md")
    ap.add_argument("--label", default="run")
    ap.add_argument("--code", type=Path, default=None, help="path to ml/src (needed when --backend is a copy elsewhere)")
    args = ap.parse_args()

    sys.path.insert(0, str(args.backend))
    from app.extract import load_extractor
    from app.schemas import ExtractRequest

    extractor = load_extractor(str(args.artifact), str(args.code) if args.code else None)
    catalog = build_catalog()
    results = [(p, run_probe(extractor, ExtractRequest, p)) for p in catalog]
    text = render(results)
    print(f"{len(catalog)} probes\n")
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        rows = [{"category": p.category, "sub": p.sub, "field": p.field, "text": p.text[:200], "ambiguous": p.ambiguous,
                 "expect": {k: sorted(v) if isinstance(v, set) else v for k, v in p.expect.items()}, **r} for p, r in results]
        (args.out / f"edge_cases_{args.label}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        (args.out / f"edge_cases_{args.label}.md").write_text(f"{len(catalog)} probes\n\n{text}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
