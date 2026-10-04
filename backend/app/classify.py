"""Confirmed visit note → "see a doctor" + primary diagnosis groups.

This is the seam for the team's classification model: the route, contract and app wiring exist, the
model does not yet. Implement `Classifier` for the trained model and return it from `load_classifier`;
until then /classify answers 503 and the app keeps its on-phone triage rules.
The output is decision support for a health worker, never a diagnosis shown as fact.
"""

from typing import Protocol

from .schemas import ClassifyRequest, ClassifyResponse


class ClassifierUnavailableError(Exception):
    """No classification model is configured or it could not be loaded."""


class Classifier(Protocol):
    def classify(self, req: ClassifyRequest) -> ClassifyResponse: ...


def load_classifier(path: str | None) -> Classifier:
    """Loader boundary: build the model adapter here once the classification model exists."""
    if not path or not path.strip():
        raise ClassifierUnavailableError("CLASSIFY_MODEL_PATH is not configured")
    raise ClassifierUnavailableError("No classification model adapter is implemented yet (backend/app/classify.py)")
