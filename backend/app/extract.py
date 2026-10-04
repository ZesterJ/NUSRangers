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
from .typed_input import inability_to_drink, near_miss, normalize_text, strip_leading_none

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
_RANGE_UNIT = r"(?:days?|siku|weeks?|wiki|months?|miezi|hours?|masaa)"
# "2-3 days", "3 or 4 days", "siku mbili au tatu": a range is not one number of days. Like "about 3 days", it stays unknown.
DURATION_RANGE = re.compile(
    rf"\b{_NUM}\s*(?:-|\u2013|\u2014|to|or|au|hadi)\s*{_NUM}\s*{_RANGE_UNIT}\b"
    rf"|\b(?:siku|wiki|miezi)\s+{_NUM}\s*(?:-|\u2013|\u2014|to|or|au|hadi)\s*{_NUM}\b",
    re.I,
)
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
    def __init__(self, pipeline: TextPipeline, known_words: frozenset[str] = frozenset()):
        self.pipeline = pipeline
        # Words the model's own phrase table already recognises (including known misspellings): never flagged as typos.
        self.known_words = known_words

    def _run(self, text: str) -> dict[str, Any] | None:
        return self.pipeline.extract(text) if text.strip() else None

    def _suggestions(self, result: dict[str, Any], text: str, symptoms: list[str], signs: list[str]):
        """
        Findings the exact-wording gate rejected but that deserve a look. They are returned for LOW confidence display
        and are never presented as sure:
          - the wording matched and only the classifier vetoed it (that veto was wrong for every fever/cough/pain case
            in the team's labelled data); and
          - a word one typo away from a symptom word.
        The classifier score alone is NOT used: on clean text it adds false symptoms ("my child has a cough" -> fever).
        """
        add_symptoms: list[str] = []
        add_signs: list[str] = []
        notes: list[str] = []
        if result.get("abstentions"):  # the model declined to pick a subject: do not second-guess it
            return add_symptoms, add_signs, notes
        for label, decision in result.get("symptomDecisions", {}).items():
            if decision.get("state") == "affirmed" and decision.get("reasons") == ["below_threshold"]:
                if label in SYMPTOM_MAP:
                    add_symptoms.append(SYMPTOM_MAP[label])
                elif label in DANGER_MAP:
                    add_signs.append(DANGER_MAP[label])
        for word, kind, code in near_miss(text, self.known_words):
            if code in symptoms or code in signs:  # already found from other wording: nothing to flag
                continue
            (add_symptoms if kind == "symptom" else add_signs).append(code)
            notes.append(f'Unclear word: "{word}"')
        # "cannot even drink" or a typo in "cannot drink": only when the model did not see the phrase at all
        if result.get("reportedSignStates", {}).get("cannot_drink", {}).get("state") == "not_mentioned":
            phrase = inability_to_drink(text)
            if phrase:
                add_signs.append("unable_to_drink")
                notes.append(f'Unclear wording: "{phrase}"')
        return (
            [c for c in dict.fromkeys(add_symptoms) if c not in symptoms],
            [c for c in dict.fromkeys(add_signs) if c not in signs],
            notes,
        )

    def extract(self, req: ExtractRequest) -> Extraction:
        answers = req.answers
        # Clean what the model sees (Unicode, apostrophes, spacing, missing negation cues). The patient's own words stay
        # untouched in `evidence` and `unmapped`.
        who_text = normalize_text(answers.who)
        complaint_text = normalize_text(answers.complaint)
        duration_text = normalize_text(answers.duration)
        danger_clean = normalize_text(answers.danger)
        danger_text = strip_leading_none(danger_clean)  # "no, he cannot drink": judge the part after "no"

        who = self._run(who_text)
        complaint = self._run(complaint_text)
        duration = self._run(duration_text)
        danger = self._run(danger_text)
        clinical = [r for r in (complaint, danger) if r is not None]

        symptoms: list[str] = []
        signs: list[str] = []
        notes: list[str] = []
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
            states = result.get("reportedSignStates", {})
            unsure = unsure or any(s.get("state") == "uncertain" for s in states.values())

        said_none = bool(SAID_NONE.search(danger_clean))
        danger_sure = not unsure and not notes and (bool(signs) or said_none)

        if not symptoms and not signs:
            notes.extend(a for a in (answers.complaint, answers.danger) if a.strip() and not SAID_NONE.search(normalize_text(a)))
        elif answers.danger.strip() and not signs and not said_none and answers.danger not in notes:
            notes.append(answers.danger)  # a danger answer nothing could use is still the patient's word: show it

        # Low-confidence suggestions (see _suggestions). Computed after the checks above so they never raise confidence.
        extra_symptoms: list[str] = []
        extra_signs: list[str] = []
        for result, text in ((complaint, complaint_text), (danger, danger_text)):
            if result is None:
                continue
            more_symptoms, more_signs, more_notes = self._suggestions(
                result, text, symptoms + extra_symptoms, signs + extra_signs
            )
            extra_symptoms += more_symptoms
            extra_signs += more_signs
            notes.extend(n for n in more_notes if n not in notes)
        symptoms += extra_symptoms
        signs += extra_signs

        return Extraction(
            patientGroup=self._patient_group(who, answers.who, who_text),
            symptoms=ExtractionField(
                value=symptoms,
                confidence="high" if symptoms and not unsure and not extra_symptoms else "low",
                evidence=answers.complaint,
            ),
            durationDays=(
                ExtractionField(value=None, confidence="low", evidence=answers.duration)
                if DURATION_RANGE.search(duration_text) or DURATION_RANGE.search(complaint_text)
                else self._duration(duration, complaint, answers.duration)
            ),
            dangerSigns=ExtractionField(
                value=signs, confidence="high" if danger_sure and not extra_signs else "low", evidence=answers.danger
            ),
            unmapped=notes,
            source="model",
        )

    @staticmethod
    def _patient_group(result: dict[str, Any] | None, text: str, clean: str) -> ExtractionField:
        kind = result.get("patientType") if result else None
        if kind == "pregnant":
            return ExtractionField(value="pregnant", confidence="high", evidence=text)
        if kind == "adult":
            return ExtractionField(value="adult", confidence="high", evidence=text)
        if kind == "child":
            # The model says "child", the app's group is "under 5": only sure when an age is given.
            under_five = child_is_under_five(clean)
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
        lexical = importlib.import_module("lexical_config")
        known = frozenset(word for phrase in lexical.PHRASES for word in phrase.lower().split())
        return IntakeExtractor(module.ExtractionPipeline(joblib.load(artifact)), known)
    except Exception as exc:
        raise ExtractorUnavailableError(
            "Extraction model could not be loaded; check scikit-learn matches ml/requirements.txt"
        ) from exc
