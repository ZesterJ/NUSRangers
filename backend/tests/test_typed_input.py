"""Typed-input handling for /extract: cleaning, typo flags, and what the user is shown.

Pure-function and stub-pipeline tests run everywhere. The last group runs the real model when the artifact is built
(EXTRACT_MODEL_PATH or ml/artifacts/experimental_health_ie_final.joblib) and is skipped otherwise.
Full backtest with before/after numbers: ml/robustness/edge_cases.py and ml/robustness/EDGE_CASES.md.
"""

import os
from pathlib import Path

import pytest

from app import extract as ex
from app.schemas import ExtractRequest
from app.typed_input import inability_to_drink, near_miss, normalize_text, osa_distance, strip_leading_none

# ---------------------------------------------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "typed, expected",
    [
        ("I don’t have fever", "I don't have fever"),  # curly apostrophe (phone keyboards)
        ("I don´t have fever", "I don't have fever"),  # acute accent: NFKC would turn it into a space
        ("I donʼt have fever", "I don't have fever"),
        ("I dont have fever", "I don't have fever"),
        ("he doesnt have a cough", "he doesn't have a cough"),
        ("I don t have fever", "I don't have fever"),
        ("she didnt have fever", "she doesn't have fever"),  # didn't is not a cue the model knows; doesn't is
        ("she hadn't had fever", "she doesn't had fever"),
        ("he cant drink", "he can't drink"),
        ("he can not drink", "he cannot drink"),
        ("Im 25 years old", "I'm 25 years old"),
        ("3days", "3 days"),
        ("hamna homa", "hakuna homa"),
        ("bila homa", "without homa"),
        ("sio mjamzito", "not mjamzito"),
        ("nakohoa", "ninakohoa"),
        ("none of: seizures", "no seizures"),
        ("neither fever nor cough", "no fever no cough"),
        ("not only fever but also cough", "also fever but also cough"),  # affirms both: not a denial
    ],
)
def test_normalize_text_repairs_what_breaks_the_model(typed, expected):
    assert normalize_text(typed) == expected


def test_normalize_text_whitespace_and_invisible_characters():
    assert normalize_text("a b\tc d") == "a b c d"
    assert normalize_text("  a   b  ") == "a b"
    assert normalize_text("fe​ver") == "fever"
    assert normalize_text("hak­una") == "hakuna"
    assert normalize_text("ｆｅｖｅｒ") == "fever"  # full-width letters
    # A newline is a sentence break for the model ("no fever\ncough"), so it is kept, once.
    assert normalize_text("no fever\r\n\r\ncough") == "no fever\ncough"


def test_normalize_text_leaves_findings_that_are_not_denials():
    # "aren't drinking" and "won't drink" are findings (poor drinking), not denials: never rewritten.
    assert normalize_text("they aren't drinking") == "they aren't drinking"
    assert normalize_text("he won't drink") == "he won't drink"
    assert normalize_text("he cannot drink well") == "he cannot drink well"


@pytest.mark.parametrize("text", ["I don’t have fever", "she didnt have fever", "nina homa na kikohozi", "", "  ", "3days ​"])
def test_normalize_text_is_idempotent(text):
    assert normalize_text(normalize_text(text)) == normalize_text(text)


def test_strip_leading_none():
    assert strip_leading_none("no, he cannot drink") == "he cannot drink"
    assert strip_leading_none("hakuna, hana degedege") == "hana degedege"
    assert strip_leading_none("No. He has convulsions") == "He has convulsions"
    assert strip_leading_none("no") == "no"  # a bare answer is left alone
    assert strip_leading_none("No.") == "No."
    assert strip_leading_none("no convulsions") == "no convulsions"  # no punctuation: that is a denial of the sign


# ---------------------------------------------------------------------------------------------------------------
# near_miss and inability_to_drink: flag, never assert
# ---------------------------------------------------------------------------------------------------------------


def test_osa_distance_counts_a_swap_as_one_edit():
    assert osa_distance("fevre", "fever", 2) == 1
    assert osa_distance("cogh", "cough", 2) == 1
    assert osa_distance("abc", "xyz", 1) > 1
    assert osa_distance("fever", "fevers and more", 1) == 2  # lengths differ by more than the limit: skipped


@pytest.mark.parametrize(
    "text, expected",
    [
        ("feever and cough", [("feever", "symptom", "fever")]),
        ("fever and cogh", [("cogh", "symptom", "cough")]),
        ("hedache", [("hedache", "symptom", "headache")]),
        ("nina hoa na kikohozi", [("hoa", "symptom", "fever")]),
        ("convulsoins", [("convulsoins", "sign", "convulsions")]),
        ("fever and cough", []),  # exact words are the model's business
        ("never had fever", []),  # "never" is one edit from "fever" but is an ordinary word
        ("a week at home", []),
        ("no feever", []),  # right after a denial: do not contradict it
        ("maybe feever", []),  # hedged sentence
        ("had feever last year", []),  # past
    ],
)
def test_near_miss(text, expected):
    assert near_miss(text) == expected


def test_near_miss_skips_words_the_model_already_knows():
    assert near_miss("fevr", known_words=frozenset({"fevr"})) == []
    assert near_miss("fevr") == [("fevr", "symptom", "fever")]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("he cannot even drink", "cannot even drink"),
        ("he cannot rink", "cannot rink"),
        ("hawezi hata kunywa", "hawezi hata kunywa"),
        ("he cannot drink well", None),  # reduced drinking, not inability (the model's own rule)
        ("hawezi kunywa vizuri", None),
        ("he can drink", None),
        ("he does not say he cannot drink", None),  # a denial comes first
        ("maybe he cannot drink", None),
    ],
)
def test_inability_to_drink(text, expected):
    assert inability_to_drink(text) == expected


# ---------------------------------------------------------------------------------------------------------------
# The adapter, with a stub pipeline
# ---------------------------------------------------------------------------------------------------------------


def result(**overrides):
    base = {"patientType": None, "durationDays": None, "reportedSigns": [], "symptoms": [], "reportedSignStates": {},
            "abstentions": [], "symptomDecisions": {}}  # fmt: skip
    return {**base, **overrides}


def decision(state="affirmed", reasons=("below_threshold",)):
    return {"state": state, "reasons": list(reasons), "score": 0.1, "threshold": 0.3, "accepted": False}


class Stub:
    def __init__(self, by_text=None):
        self.by_text, self.seen = by_text or {}, []

    def extract(self, text):
        self.seen.append(text)
        return self.by_text.get(text, result())


def run(stub, known=frozenset(), **answers):
    return ex.IntakeExtractor(stub, known).extract(ExtractRequest(locale="sw", answers=answers))


def test_the_model_sees_cleaned_text_but_evidence_keeps_the_patients_words():
    stub = Stub()
    out = run(stub, complaint="I dont  have fever")
    assert stub.seen == ["I don't have fever"]
    assert out.symptoms.evidence == "I dont  have fever"


def test_leading_no_is_judged_separately_from_the_rest_of_a_danger_answer():
    stub = Stub({"he cannot drink": result(reportedSigns=["cannot_drink"])})
    out = run(stub, danger="no, he cannot drink")
    assert stub.seen == ["he cannot drink"]
    assert out.dangerSigns.value == ["unable_to_drink"]
    assert out.dangerSigns.confidence == "high"


def test_wording_matched_but_classifier_vetoed_is_suggested_at_low_confidence():
    stub = Stub({"fever and cough": result(symptoms=["fever"], symptomDecisions={"cough": decision()})})
    out = run(stub, complaint="fever and cough")
    assert out.symptoms.value == ["fever", "cough"]
    assert out.symptoms.confidence == "low"  # never presented as sure


@pytest.mark.parametrize(
    "decisions",
    [
        {"cough": decision(state="negated", reasons=("negated", "below_threshold"))},
        {"cough": decision(state="uncertain", reasons=("uncertain",))},
        {"cough": decision(reasons=("below_threshold", "unresolved_subject_or_empty_input"))},
        {"cough": decision(state="not_mentioned", reasons=("not_mentioned", "below_threshold"))},
    ],
)
def test_nothing_is_suggested_when_the_model_had_another_reason(decisions):
    out = run(Stub({"fever and cough": result(symptoms=["fever"], symptomDecisions=decisions)}), complaint="fever and cough")
    assert out.symptoms.value == ["fever"]
    assert out.symptoms.confidence == "high"


def test_nothing_is_suggested_when_the_model_declined_to_choose_a_subject():
    stub = Stub({"fever and cough": result(symptoms=["fever"], abstentions=["multiple_subjects"], symptomDecisions={"cough": decision()})})
    assert run(stub, complaint="fever and cough").symptoms.value == ["fever"]


def test_a_typo_is_flagged_not_asserted_as_sure():
    out = run(Stub(), complaint="fever and cogh")
    assert out.symptoms.value == ["cough"]
    assert out.symptoms.confidence == "low"
    assert 'Unclear word: "cogh"' in out.unmapped
    assert "fever and cogh" in out.unmapped  # nothing was confirmed, so the patient's words are shown too


def test_a_typo_next_to_a_found_symptom_makes_the_whole_answer_low_confidence():
    out = run(Stub({"fever and cogh": result(symptoms=["fever"])}), complaint="fever and cogh")
    assert out.symptoms.value == ["fever", "cough"]
    assert out.symptoms.confidence == "low"


def test_a_near_miss_of_something_already_found_adds_no_note_and_keeps_confidence():
    # "akiharisha" is a valid Swahili form one edit from a vocabulary word; diarrhoea was found from other wording.
    out = run(Stub({"akiharisha na kuhara": result(symptoms=["diarrhoea"])}), complaint="akiharisha na kuhara")
    assert out.symptoms.confidence == "high"
    assert out.unmapped == []


def test_cannot_even_drink_is_suggested_only_when_the_model_did_not_see_the_phrase():
    text = "he cannot even drink"
    unseen = result(reportedSignStates={"cannot_drink": {"state": "not_mentioned"}})
    out = run(Stub({text: unseen}), danger=text)
    assert out.dangerSigns.value == ["unable_to_drink"]
    assert out.dangerSigns.confidence == "low"
    negated = result(reportedSignStates={"cannot_drink": {"state": "negated"}})
    assert run(Stub({text: negated}), danger=text).dangerSigns.value == []


def test_a_duration_range_stays_unknown_like_an_approximate_one():
    for text in ("2-3 days", "3 or 4 days", "siku mbili au tatu", "two or three days"):
        out = run(Stub({normalize_text(text): result(durationDays=3.0)}), duration=text)
        assert (out.durationDays.value, out.durationDays.confidence) == (None, "low"), text
    # a single number, and an age range elsewhere in the answer, are not ranges
    assert run(Stub({"3 days": result(durationDays=3.0)}), duration="3 days").durationDays.value == 3
    ageish = "my child 2-3 years old, sick for 3 days"
    assert run(Stub({ageish: result(durationDays=3.0)}), complaint=ageish).durationDays.value == 3


def test_a_danger_answer_nothing_could_use_is_shown_even_when_symptoms_were_found():
    out = run(Stub({"fever": result(symptoms=["fever"])}), complaint="fever", danger="ana shida kubwa")
    assert out.unmapped == ["ana shida kubwa"]
    assert out.dangerSigns.confidence == "low"
    said_none = run(Stub({"fever": result(symptoms=["fever"])}), complaint="fever", danger="hakuna")
    assert said_none.unmapped == []


# ---------------------------------------------------------------------------------------------------------------
# The real model (skipped when the artifact has not been built)
# ---------------------------------------------------------------------------------------------------------------

ARTIFACT = Path(os.getenv("EXTRACT_MODEL_PATH") or ex.DEFAULT_MODEL_PATH)


@pytest.fixture(scope="module")
def real():
    pytest.importorskip("sklearn")
    if not ARTIFACT.is_file():
        pytest.skip("extraction artifact not built (see ml/README.md)")
    extractor = ex.load_extractor(str(ARTIFACT))

    def go(**answers):
        return extractor.extract(ExtractRequest(locale="sw", answers=answers))

    return go


@pytest.mark.parametrize("apostrophe", ["'", "’", "‘", "`", "´", "ʼ", "′", "", " "])
@pytest.mark.parametrize("template", ["I don{a}t have fever", "he doesn{a}t have fever", "I haven{a}t had fever", "it isn{a}t fever"])
def test_real_model_a_denial_survives_every_apostrophe_spelling(real, apostrophe, template):
    assert real(complaint=template.format(a=apostrophe)).symptoms.value == []


@pytest.mark.parametrize(
    "text",
    ["she didn't have fever", "she hadn't had fever", "hamna homa", "bila homa", "haina homa", "sina homa", "hana homa", "no fever", "without fever"],
)
def test_real_model_every_denial_cue_is_understood(real, text):
    assert "fever" not in real(complaint=text).symptoms.value


def test_real_model_denial_scope(real):
    assert real(complaint="fever and cough and no diarrhoea").symptoms.value.count("diarrhoea") == 0
    assert set(real(complaint="no fever but cough").symptoms.value) == {"cough"}
    assert set(real(complaint="homa bila kikohozi").symptoms.value) == {"fever"}


def test_real_model_danger_answers(real):
    assert real(danger="no, he cannot drink").dangerSigns.value == ["unable_to_drink"]
    assert real(danger="none of: seizures").dangerSigns.value == []
    assert real(danger="none of: seizures").dangerSigns.confidence == "high"
    assert real(danger="he cannot  drink").dangerSigns.value == ["unable_to_drink"]
    assert real(danger="he cannot even drink").dangerSigns.value == ["unable_to_drink"]
    # reduced drinking is not inability (the model's own rule)
    assert real(danger="hawezi kunywa vizuri").dangerSigns.value == []


def test_real_model_neither_nor_and_not_only(real):
    assert real(complaint="neither fever nor cough").symptoms.value == []
    assert set(real(complaint="not only fever but also cough").symptoms.value) == {"fever", "cough"}


def test_real_model_duration_range_is_unknown(real):
    assert real(duration="2-3 days").durationDays.value is None
    assert real(duration="3 days").durationDays.value == 3


def test_real_model_pregnancy_denied_in_swahili(real):
    assert real(who="sio mjamzito").patientGroup.value != "pregnant"


def test_real_model_formatting_does_not_matter(real):
    for text in ("I have fever", "I  have   fever", "\tI have fever\n", "I have f​ever", "Ｉ ｈａｖｅ ｆｅｖｅｒ"):
        assert real(complaint=text).symptoms.value == ["fever"], text


def test_real_model_a_symptom_the_model_lost_on_clean_text_is_now_recovered_and_flagged(real):
    out = real(complaint="I have fever, cough and diarrhoea.")
    assert set(out.symptoms.value) == {"fever", "cough", "diarrhoea"}


def test_real_model_typos_are_flagged_never_silent(real):
    out = real(complaint="fever and cogh")
    assert set(out.symptoms.value) == {"fever", "cough"}
    assert out.symptoms.confidence == "low"
    typo_only = real(complaint="nina hoa na kikohozi")  # the only fever word is the typo
    assert set(typo_only.symptoms.value) == {"fever", "cough"}
    assert typo_only.symptoms.confidence == "low"
    # a typo of something that is also spelled correctly elsewhere flags nothing
    assert real(complaint="homa na hoa").symptoms.confidence == "high"


def test_real_model_hedged_and_past_statements_are_not_flagged_as_typos(real):
    out = real(complaint="I used to have headaches last year. Not now.")
    assert out.symptoms.value == []


def test_real_model_clean_text_is_unchanged(real):
    out = real(who="Mtoto wangu wa miaka miwili", complaint="Ana homa kali na anakohoa", duration="Siku tatu", danger="Hawezi kunywa na anatapika kila kitu")
    assert out.patientGroup.value == "child_u5"
    assert {"fever", "cough"} <= set(out.symptoms.value)
    assert out.durationDays.value == 3
    assert "unable_to_drink" in out.dangerSigns.value
