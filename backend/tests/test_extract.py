"""/extract adapter tests. Mapping tests use a stub pipeline; one test runs the real model if it has been built."""

import pytest
from fastapi.testclient import TestClient

from app import extract as ex
from app import main
from app.schemas import ExtractRequest


def result(**overrides):
    base = {"patientType": None, "durationDays": None, "reportedSigns": [], "symptoms": [],
            "reportedSignStates": {}, "abstentions": []}  # fmt: skip
    return {**base, **overrides}


class StubPipeline:
    def __init__(self, by_text):
        self.by_text = by_text

    def extract(self, text):
        return self.by_text.get(text, result())


def run(by_text, **answers):
    extractor = ex.IntakeExtractor(StubPipeline(by_text))
    return extractor.extract(ExtractRequest(locale="sw", answers=answers))


def test_maps_model_labels_to_app_codes():
    out = run(
        {
            "who": result(patientType="child"),
            "complaint": result(symptoms=["fever", "breathing_difficulty", "fatigue"]),
            "duration": result(durationDays=3.0),
            "danger": result(reportedSigns=["cannot_drink"]),
        },
        who="who", complaint="complaint", duration="duration", danger="danger",
    )  # fmt: skip
    assert out.symptoms.value == ["fever", "difficulty_breathing", "weakness"]
    assert out.symptoms.confidence == "high"
    assert out.durationDays.value == 3
    assert out.dangerSigns.value == ["unable_to_drink"]
    assert out.dangerSigns.confidence == "high"
    assert out.source == "model"


def test_child_without_age_is_low_confidence():
    assert run({"Mtoto wangu": result(patientType="child")}, who="Mtoto wangu").patientGroup.confidence == "low"
    young = run({"Mtoto wangu wa miaka miwili": result(patientType="child")}, who="Mtoto wangu wa miaka miwili")
    assert (young.patientGroup.value, young.patientGroup.confidence) == ("child_u5", "high")
    older = run({"My child, 9 years old": result(patientType="child")}, who="My child, 9 years old")
    assert older.patientGroup.value is None


def test_no_danger_signs_is_only_trusted_when_patient_said_none():
    assert run({}, complaint="x", danger="Hakuna").dangerSigns.confidence == "high"
    assert run({}, complaint="x", danger="sijui").dangerSigns.confidence == "low"
    assert run({}, complaint="x").dangerSigns.confidence == "low"


def test_model_uncertainty_or_abstention_lowers_confidence():
    hedged = run({"d": result(reportedSignStates={"convulsions": {"state": "uncertain"}})}, danger="d")
    assert hedged.dangerSigns.confidence == "low"
    abstained = run({"c": result(symptoms=["fever"], abstentions=["multiple_subjects"])}, complaint="c", danger="Hakuna")
    assert abstained.symptoms.confidence == "low"
    assert abstained.dangerSigns.confidence == "low"


def test_pregnancy_findings_become_danger_signs_or_notes():
    out = run({"c": result(symptoms=["blurred_vision", "reduced_fetal_movement", "fluid_loss"])}, complaint="c", danger="Hakuna")
    assert out.dangerSigns.value == ["severe_headache_blurred_vision", "reduced_fetal_movement"]
    assert out.unmapped == ["Possible leaking of fluid in pregnancy"]
    # A finding with no app code must not pass as "no danger signs".
    only_fluid = run({"c": result(symptoms=["fluid_loss"])}, complaint="c", danger="Hakuna")
    assert only_fluid.dangerSigns.confidence == "low"


def test_unmapped_keeps_text_the_model_could_not_use():
    out = run({}, complaint="hajisikii vizuri", danger="sijui")
    assert out.unmapped == ["hajisikii vizuri", "sijui"]


def test_endpoint_returns_503_without_model_and_200_with_one():
    with TestClient(main.app) as client:
        main.app.dependency_overrides.pop(main.get_extractor, None)
        main.app.state.extractor = None
        assert client.post("/extract", json={"locale": "sw", "answers": {"who": "Mimi"}}).status_code == 503
        main.app.dependency_overrides[main.get_extractor] = lambda: ex.IntakeExtractor(StubPipeline({}))
        try:
            res = client.post("/extract", json={"locale": "sw", "answers": {"who": "Mimi", "danger": "Hakuna"}})
        finally:
            main.app.dependency_overrides.clear()
    assert res.status_code == 200
    assert res.json()["source"] == "model"


def test_real_model_on_scripted_patient():
    pytest.importorskip("sklearn")
    if not ex.DEFAULT_MODEL_PATH.is_file():
        pytest.skip("extraction artifact not built (see ml/README.md)")
    extractor = ex.load_extractor()
    out = extractor.extract(
        ExtractRequest(
            locale="sw",
            answers={
                "who": "Mtoto wangu wa miaka miwili",
                "complaint": "Ana homa kali na anakohoa",
                "duration": "Siku tatu",
                "danger": "Hawezi kunywa na anatapika kila kitu",
            },
        )
    )
    assert out.patientGroup.value == "child_u5"
    assert {"fever", "cough"} <= set(out.symptoms.value)
    assert out.durationDays.value == 3
    assert "unable_to_drink" in out.dangerSigns.value


def test_denied_symptoms_are_reported_so_the_app_does_not_add_them_back():
    decisions = {"fever": {"state": "negated"}, "cough": {"state": "affirmed"}, "headache": {"state": "not_mentioned"}}
    out = run({"c": result(symptoms=["cough"], symptomDecisions=decisions)}, complaint="c")
    assert out.negatedSymptoms == ["fever"]
