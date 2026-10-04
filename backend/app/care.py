"""Confirmed visit note → proposed care services + Kilifi facility candidates.

Wraps the team's rules-first care policy and facility router in ml/src (care_policy.py,
verified_facility_demo.py). Nothing here diagnoses or claims a facility is open: capabilities come
from a historical public-source snapshot, distance is straight-line, and every result needs a person
to verify it. "unknown" capability is never treated as false or true.
"""

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from .schemas import AssessRequest, AssessResponse, FacilityCandidate, VisitNote

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CODE_PATH = REPO_ROOT / "ml/src"
DEFAULT_DATA_PATH = REPO_ROOT / "ml/data/facilities"
# Where distances are measured from when the phone sends no usable location.
ANCHOR_NAME = "KILIFI DISTRICT HOSPITAL"

# App codes (src/intake/types.ts) → the care policy's vocabulary.
PATIENT_TYPE = {"child_u5": "child", "child_5plus": "child", "pregnant": "pregnant", "adult": "adult"}
SYMPTOM = {"difficulty_breathing": "breathing_difficulty"}
SIGN = {"unable_to_drink": "cannot_drink", "convulsions": "convulsions", "vaginal_bleeding": "bleeding"}
# App danger signs the policy knows only as symptoms it treats as outside its scope.
SIGN_AS_SYMPTOM = {
    "severe_headache_blurred_vision": "blurred_vision",
    "reduced_fetal_movement": "reduced_fetal_movement",
    "chest_indrawing": "breathing_difficulty",
}
GROUP_SERVICE = {"child": "childHealth", "pregnant": "maternal"}


class CareUnavailableError(Exception):
    """Care policy code or facility data could not be loaded."""


def to_policy_patient(note: VisitNote) -> tuple[dict[str, Any], bool]:
    """The visit note in the care policy's input shape, and whether it has danger signs the policy cannot express."""
    symptoms = [SYMPTOM.get(s, s) for s in note.symptoms]
    signs = [SIGN[d] for d in note.dangerSigns if d in SIGN]
    for d in note.dangerSigns:
        if d in SIGN_AS_SYMPTOM and SIGN_AS_SYMPTOM[d] not in symptoms:
            symptoms.append(SIGN_AS_SYMPTOM[d])
    unexpressed = any(d not in SIGN and d not in SIGN_AS_SYMPTOM for d in note.dangerSigns)
    patient = {
        "patientType": PATIENT_TYPE.get(note.patientGroup or ""),
        "symptoms": symptoms,
        "durationDays": note.durationDays,
        "hydrationIssue": None,
        "reportedSigns": signs,
        "reportedSignStates": {
            s: {"state": "affirmed" if s in signs else "not_mentioned"} for s in ("cannot_drink", "convulsions", "bleeding")
        },
        # The patient confirmed the note on the review screen, so the subject is settled.
        "subject": {"status": "resolved"},
        "abstentions": [],
    }
    return patient, unexpressed


class CareRouter:
    def __init__(self, policy: Any, demo: Any, data_path: Path):
        self.policy = policy
        self.demo = demo
        self.data_path = data_path
        catalogue = json.loads((data_path / "catalogue.json").read_text())
        anchor = next((r for r in catalogue if r["facilityName"] == ANCHOR_NAME), None)
        if anchor is None or anchor["latitude"] is None:
            raise CareUnavailableError("Demo anchor facility is missing from the catalogue")
        self.anchor = {"latitude": anchor["latitude"], "longitude": anchor["longitude"]}
        lats = [r["latitude"] for r in catalogue if r["latitude"] is not None]
        lons = [r["longitude"] for r in catalogue if r["longitude"] is not None]
        # A phone outside the area the catalogue covers gets the demo anchor instead of absurd distances.
        self.bounds = (min(lats) - 0.5, max(lats) + 0.5, min(lons) - 0.5, max(lons) + 0.5)
        self.demo.load_subset(data_path)  # fail at startup, not on the first request

    def _origin(self, req: AssessRequest) -> tuple[dict[str, float], str]:
        c = req.coordinates
        if c is not None:
            south, north, west, east = self.bounds
            if south <= c.latitude <= north and west <= c.longitude <= east:
                return {"latitude": c.latitude, "longitude": c.longitude}, "patient"
        return self.anchor, "demo_anchor"

    def assess(self, req: AssessRequest) -> AssessResponse:
        patient, unexpressed = to_policy_patient(req.note)
        services = [] if unexpressed else list(self.policy.rules_predict(patient))
        status = "proposed" if services else "unclear"
        if not services and (unexpressed or self.policy.gate(patient)[0] == "unknown"):
            # The care policy abstains when danger signs are present. The patient is still told to go to
            # a clinic, so list facilities with documented services for this patient group, marked unclear.
            services = ["generalOutpatient"]
            if patient["patientType"] in GROUP_SERVICE:
                services.append(GROUP_SERVICE[patient["patientType"]])
        origin, origin_type = self._origin(req)
        routing = self.demo.route_verified(services, origin, self.data_path)
        return AssessResponse(
            requiredServices=services,
            assessmentStatus=status,
            routingStatus=routing["status"],
            candidates=[
                FacilityCandidate(
                    facilityId=c["facilityId"],
                    facilityName=c["facilityName"],
                    rank=c["rank"],
                    distanceKm=c["distanceKm"],
                    matchedServices=c["matchedServices"],
                )
                for c in routing["candidates"]
            ],
            origin=origin_type,
            limitations=routing["limitations"],
        )


def load_care_router(code_path: str | None = None, data_path: str | None = None) -> CareRouter:
    code = Path(code_path) if code_path and code_path.strip() else DEFAULT_CODE_PATH
    data = Path(data_path) if data_path and data_path.strip() else DEFAULT_DATA_PATH
    if not (code / "verified_facility_demo.py").is_file():
        raise CareUnavailableError(f"Care routing code not found in: {code}")
    if not (data / "catalogue.json").is_file():
        raise CareUnavailableError(f"Facility data not found in: {data}")
    try:
        if str(code) not in sys.path:
            sys.path.insert(0, str(code))
        return CareRouter(importlib.import_module("care_policy"), importlib.import_module("verified_facility_demo"), data)
    except CareUnavailableError:
        raise
    except Exception as exc:
        raise CareUnavailableError("Care routing could not be loaded; check ml/src and ml/data/facilities") from exc
