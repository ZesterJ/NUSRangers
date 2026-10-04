"""Text → structured intake fields, using the team's extraction model in ml/.

The model (ml/src/extraction_pipeline.py + a joblib bundle) reads one free-text statement.
This adapter runs it once per guided answer and maps its vocabulary onto the app's `Extraction`
contract (src/intake/types.ts, docs/api.md). It proposes fields for a person to verify; it never
diagnoses or triages. Only load trusted artifacts: joblib deserialization can execute Python code.
"""

import importlib
import re
import sys
from pathlib import Path
from typing import Any, Protocol

from .schemas import ExtractRequest, Extraction, ExtractionField

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = REPO_ROOT / "ml/artifacts/experimental_health_ie_final.joblib"
DEFAULT_CODE_PATH = REPO_ROOT / "ml/src"

# Model label → app symptom code. Labels missing here are handled as danger signs or notes below.
SYMPTOM_MAP = {
    "fever": "fever",
    "cough": "cough",
    "breathing_difficulty": "difficulty_breathing",
    "diarrhoea": "diarrhoea",
    "vomiting": "vomiting",
    "headache": "headache",
    "abdominal_pain": "abdominal_pain",
    "weakness": "weakness",
    "fatigue": "weakness",
}
# Model findings that the app treats as danger signs. "bleeding" follows the on-phone rules.
DANGER_MAP = {
    "cannot_drink": "unable_to_drink",
    "convulsions": "convulsions",
    "bleeding": "vaginal_bleeding",
    "blurred_vision": "severe_headache_blurred_vision",
    "reduced_fetal_movement": "reduced_fetal_movement",
}
# Findings with no app code: passed to the clinician as a note, and "no danger signs" is not trusted.
NOTE_ONLY = {"fluid_loss": "Possible leaking of fluid in pregnancy"}

SAID_NONE = re.compile(r"^\W*(?:hakuna|hapana|none|no|nothing|hamna)\b", re.I)
AGE_WORDS = {
    "mmoja": 1, "moja": 1, "miwili": 2, "mbili": 2, "mitatu": 3, "tatu": 3, "minne": 4, "nne": 4,
    "mitano": 5, "tano": 5, "sita": 6, "saba": 7, "minane": 8, "nane": 8, "tisa": 9, "kumi": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}  # fmt: skip
_NUM = r"(\d{1,3}|" + "|".join(AGE_WORDS) + ")"
AGE_YEARS = re.compile(rf"\b(?:miaka|mwaka)\s+{_NUM}\b|\b{_NUM}[\s-]+years?\b", re.I)
AGE_MONTHS = re.compile(rf"\b(?:miezi|mwezi)\s+{_NUM}\b|\b{_NUM}[\s-]+months?\b", re.I)


class ExtractorUnavailableError(Exception):
    """Extraction code or artifact could not be loaded."""


class TextPipeline(Protocol):
    """What the adapter needs from ml/src/extraction_pipeline.ExtractionPipeline."""

    def extract(self, text: str) -> dict[str, Any]: ...


def _number(match: re.Match[str]) -> int:
    token = next(g for g in match.groups() if g is not None).lower()
    return int(token) if token.isdigit() else AGE_WORDS[token]


def child_is_under_five(text: str) -> bool | None:
    """True/False when an age is stated, None when it is not."""
    years = AGE_YEARS.search(text)
    if years:
        return _number(years) < 5
    months = AGE_MONTHS.search(text)
    if months:
        return _number(months) < 60
    return None


class IntakeExtractor:
    def __init__(self, pipeline: TextPipeline):
        self.pipeline = pipeline

    def _run(self, text: str) -> dict[str, Any] | None:
        return self.pipeline.extract(text) if text.strip() else None

    def extract(self, req: ExtractRequest) -> Extraction:
        answers = req.answers
        who = self._run(answers.who)
        complaint = self._run(answers.complaint)
        duration = self._run(answers.duration)
        danger = self._run(answers.danger)
        clinical = [r for r in (complaint, danger) if r is not None]

        symptoms: list[str] = []
        signs: list[str] = []
        notes: list[str] = []
        negated: list[str] = []
        unsure = False  # the model abstained or hedged somewhere in the clinical answers
        for result in clinical:
            unsure = unsure or bool(result.get("abstentions"))
            findings = [*result.get("symptoms", []), *result.get("reportedSigns", [])]
            for label in findings:
                if label in SYMPTOM_MAP and SYMPTOM_MAP[label] not in symptoms:
                    symptoms.append(SYMPTOM_MAP[label])
                if label in DANGER_MAP and DANGER_MAP[label] not in signs:
                    signs.append(DANGER_MAP[label])
                if label in NOTE_ONLY and NOTE_ONLY[label] not in notes:
                    notes.append(NOTE_ONLY[label])
            for label, decision in result.get("symptomDecisions", {}).items():
                code = SYMPTOM_MAP.get(label)
                if decision.get("state") == "negated" and code and code not in negated:
                    negated.append(code)
            states = result.get("reportedSignStates", {})
            unsure = unsure or any(s.get("state") == "uncertain" for s in states.values())

        said_none = bool(SAID_NONE.search(answers.danger))
        danger_sure = not unsure and not notes and (bool(signs) or said_none)

        if not symptoms and not signs:
            notes.extend(a for a in (answers.complaint, answers.danger) if a.strip() and not SAID_NONE.search(a))

        return Extraction(
            patientGroup=self._patient_group(who, answers.who),
            symptoms=ExtractionField(
                value=symptoms, confidence="high" if symptoms and not unsure else "low", evidence=answers.complaint
            ),
            durationDays=self._duration(duration, complaint, answers.duration),
            dangerSigns=ExtractionField(
                value=signs, confidence="high" if danger_sure else "low", evidence=answers.danger
            ),
            unmapped=notes,
            negatedSymptoms=[s for s in negated if s not in symptoms],
            source="model",
        )

    @staticmethod
    def _patient_group(result: dict[str, Any] | None, text: str) -> ExtractionField:
        kind = result.get("patientType") if result else None
        if kind == "pregnant":
            return ExtractionField(value="pregnant", confidence="high", evidence=text)
        if kind == "adult":
            return ExtractionField(value="adult", confidence="high", evidence=text)
        if kind == "child":
            # The model says "child", the app's group is "under 5": only sure when an age is given.
            under_five = child_is_under_five(text)
            if under_five is False:
                return ExtractionField(value=None, confidence="low", evidence=text)
            return ExtractionField(value="child_u5", confidence="high" if under_five else "low", evidence=text)
        return ExtractionField(value=None, confidence="low", evidence=text)

    @staticmethod
    def _duration(duration: dict[str, Any] | None, complaint: dict[str, Any] | None, text: str) -> ExtractionField:
        # Prefer the answer to the duration question; fall back to a duration stated with the complaint.
        for result in (duration, complaint):
            days = result.get("durationDays") if result else None
            if days is not None:
                return ExtractionField(value=round(days), confidence="high", evidence=text)
        return ExtractionField(value=None, confidence="low", evidence=text)


def load_extractor(model_path: str | None = None, code_path: str | None = None) -> IntakeExtractor:
    artifact = Path(model_path) if model_path and model_path.strip() else DEFAULT_MODEL_PATH
    code = Path(code_path) if code_path and code_path.strip() else DEFAULT_CODE_PATH
    if not artifact.is_file():
        raise ExtractorUnavailableError(f"Extraction model artifact not found: {artifact}")
    if not (code / "extraction_pipeline.py").is_file():
        raise ExtractorUnavailableError(f"Extraction code not found in: {code}")
    try:
        import joblib

        if str(code) not in sys.path:
            sys.path.insert(0, str(code))
        module = importlib.import_module("extraction_pipeline")
        return IntakeExtractor(module.ExtractionPipeline(joblib.load(artifact)))
    except Exception as exc:
        raise ExtractorUnavailableError(
            "Extraction model could not be loaded; check scikit-learn matches ml/requirements.txt"
        ) from exc
