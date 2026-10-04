"""Backend-local inference. Training and artifact creation happen outside this service.

The initial adapter loads a trusted joblib bundle:
{"model": fitted_pipeline, "modelVersion": "v1", "featureCount": 3}
featureCount is optional if the pipeline exposes n_features_in_. The pipeline must
include all preprocessing and implement predict(rows), returning one scalar per row.
Only load trusted artifacts: joblib deserialization can execute Python code.
"""

from numbers import Integral
from pathlib import Path
from typing import Protocol

import joblib

from .schemas import PredictRequest, PredictResponse


class ModelUnavailableError(Exception):
    """Model configuration or artifact could not be loaded."""


class PredictionInputError(Exception):
    """Input does not match the loaded model's feature contract."""


class PredictionError(Exception):
    """Inference failed or returned an unsupported output."""


class Predictor(Protocol):
    """API-facing interface; alternative runtimes can implement this directly."""

    def predict(self, req: PredictRequest) -> PredictResponse: ...


class JoblibPredictor:
    def __init__(self, bundle: object):
        if not isinstance(bundle, dict):
            raise ModelUnavailableError("ML artifact must be a bundle dictionary")
        self.model = bundle.get("model")
        self.version = bundle.get("modelVersion")
        if not callable(getattr(self.model, "predict", None)):
            raise ModelUnavailableError("ML bundle must contain a fitted pipeline with predict(rows)")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ModelUnavailableError("ML bundle requires a non-empty modelVersion")
        inferred = getattr(self.model, "n_features_in_", None)
        count = bundle.get("featureCount", inferred)
        if count is not None:
            # Accept integral runtime metadata (e.g. numpy integers), never truncate floats.
            if isinstance(count, bool) or not isinstance(count, Integral) or count <= 0:
                raise ModelUnavailableError("featureCount must be a positive integer")
            if inferred is not None and count != inferred:
                raise ModelUnavailableError("featureCount disagrees with model n_features_in_")
            count = int(count)
        self.feature_count = count

    def predict(self, req: PredictRequest) -> PredictResponse:
        if self.model is None:
            raise ModelUnavailableError("ML model is not loaded")
        if self.feature_count is not None and len(req.features) != self.feature_count:
            raise PredictionInputError(f"Expected {self.feature_count} features, received {len(req.features)}")
        try:
            values = self.model.predict([req.features])
            if len(values) != 1:
                raise ValueError("Expected one prediction")
            value = values[0]
            # Convert numpy scalar outputs without coupling the API to numpy.
            if hasattr(value, "item"):
                value = value.item()
            return PredictResponse(prediction=value, modelVersion=self.version)
        except Exception as exc:
            raise PredictionError("ML inference failed or returned an invalid scalar prediction") from exc


def load_model_service(path: str | None) -> Predictor:
    """Loader boundary: replace this adapter when a different runtime is selected."""
    if not path or not path.strip():
        raise ModelUnavailableError("ML_MODEL_PATH is not configured")
    artifact = Path(path)
    if not artifact.is_file():
        raise ModelUnavailableError("ML_MODEL_PATH does not point to an available model artifact")
    try:
        return JoblibPredictor(joblib.load(artifact))
    except ModelUnavailableError:
        raise
    except Exception as exc:
        raise ModelUnavailableError("ML artifact could not be loaded; check format and runtime dependencies") from exc
