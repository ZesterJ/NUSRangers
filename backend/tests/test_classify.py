"""/classify contract tests with a stub classifier; no model exists yet."""

from fastapi.testclient import TestClient

from app import main
from app.schemas import ClassifyResponse

NOTE = {"locale": "sw", "note": {"patientGroup": "adult", "symptoms": ["fever", "cough"], "durationDays": 3, "dangerSigns": []}}


class StubClassifier:
    def classify(self, req):
        assert req.note.symptoms == ["fever", "cough"]
        return ClassifyResponse(
            seeDoctor=True, diagnosisGroups=[{"group": "respiratory_infection", "score": 0.7}], modelVersion="stub-v1"
        )


def test_returns_503_until_a_model_is_configured():
    with TestClient(main.app) as client:
        assert client.post("/classify", json=NOTE).status_code == 503


def test_returns_the_classifier_result():
    main.app.dependency_overrides[main.get_classifier] = lambda: StubClassifier()
    try:
        with TestClient(main.app) as client:
            res = client.post("/classify", json=NOTE)
    finally:
        main.app.dependency_overrides.clear()
    assert res.status_code == 200
    assert res.json() == {
        "seeDoctor": True,
        "diagnosisGroups": [{"group": "respiratory_infection", "score": 0.7}],
        "modelVersion": "stub-v1",
    }
