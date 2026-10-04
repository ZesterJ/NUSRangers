"""/assess runs the team's real care policy and Kilifi facility data from ml/ (no model file needed)."""

import pytest
from fastapi.testclient import TestClient

from app import care, main
from app.schemas import AssessRequest


@pytest.fixture(scope="module")
def router():
    return care.load_care_router()


def assess(router, **note):
    return router.assess(AssessRequest(note=note))


def test_child_with_fever_is_routed_to_child_health(router):
    out = assess(router, patientGroup="child_u5", symptoms=["fever", "cough"], durationDays=3)
    assert out.requiredServices == ["generalOutpatient", "childHealth"]
    assert out.assessmentStatus == "proposed"
    assert out.routingStatus == "candidates_found"
    assert 1 <= len(out.candidates) <= 3
    assert all(set(c.matchedServices) == {"generalOutpatient", "childHealth"} for c in out.candidates)
    assert out.requiresVerification is True


def test_distances_use_the_demo_anchor_without_coordinates(router):
    out = assess(router, patientGroup="adult", symptoms=["headache"])
    assert out.origin == "demo_anchor"
    distances = [c.distanceKm for c in out.candidates]
    assert distances == sorted(distances)


def test_coordinates_outside_kilifi_fall_back_to_the_anchor(router):
    singapore = {"latitude": 1.3, "longitude": 103.8}
    out = router.assess(AssessRequest(note={"patientGroup": "adult", "symptoms": ["cough"]}, coordinates=singapore))
    assert out.origin == "demo_anchor"
    near = {"latitude": router.anchor["latitude"] + 0.01, "longitude": router.anchor["longitude"]}
    out = router.assess(AssessRequest(note={"patientGroup": "adult", "symptoms": ["cough"]}, coordinates=near))
    assert out.origin == "patient"


def test_danger_signs_are_unclear_but_still_list_facilities(router):
    for signs in (["convulsions"], ["vomits_everything"], ["severe_headache_blurred_vision"]):
        out = assess(router, patientGroup="pregnant", symptoms=["headache"], dangerSigns=signs)
        assert out.assessmentStatus == "unclear"
        assert out.requiredServices == ["generalOutpatient", "maternal"]
        assert out.candidates


def test_no_findings_means_no_routing(router):
    out = assess(router, patientGroup="adult")
    assert out.requiredServices == []
    assert out.candidates == []


def test_endpoint(router):
    with TestClient(main.app) as client:
        res = client.post("/assess", json={"note": {"patientGroup": "adult", "symptoms": ["fever"]}})
    assert res.status_code == 200
    body = res.json()
    assert body["requiredServices"] == ["generalOutpatient"]
    assert body["candidates"][0]["facilityName"]
