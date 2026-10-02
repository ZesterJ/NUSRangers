"""Local inference tests use in-memory fixtures only; no production model or network."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import main, ml
from app.schemas import PredictRequest


class FixturePipeline:
    n_features_in_ = 3

    def predict(self, rows):
        assert rows == [[1.2, 3.4, 5.6]]
        return [0.73]


@pytest.fixture
def service():
    return ml.JoblibPredictor({"model": FixturePipeline(), "modelVersion": "test-v1"})


@pytest.fixture
def client(service):
    main.app.dependency_overrides[main.get_model_service] = lambda: service
    with TestClient(main.app) as client:
        yield client
    main.app.dependency_overrides.clear()


def test_prediction_shape_and_version(client):
    response = client.post("/predict", json={"features": [1.2, 3.4, 5.6]})
    assert response.status_code == 200
    assert response.json() == {"prediction": 0.73, "modelVersion": "test-v1"}


@pytest.mark.parametrize("body", [{}, {"features": []}, {"features": None}, {"features": "bad"},
    {"features": [True]}, {"features": ["1"]}, {"features": [None]},
    {"features": [1], "unexpected": 1}])
def test_invalid_request(client, body):
    assert client.post("/predict", json=body).status_code == 422


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_features(value):
    with pytest.raises(ValidationError):
        PredictRequest(features=[value])


def test_wrong_feature_count(client):
    response = client.post("/predict", json={"features": [1, 2]})
    assert response.status_code == 422
    assert "Expected 3 features" in response.json()["detail"]


@pytest.mark.parametrize("path", [None, "", "/missing/model.joblib"])
def test_unavailable_artifact(path):
    with pytest.raises(ml.ModelUnavailableError):
        ml.load_model_service(path)


def test_corrupt_artifact(tmp_path):
    artifact = tmp_path / "invalid.joblib"
    artifact.write_text("invalid artifact")
    with pytest.raises(ml.ModelUnavailableError, match="could not be loaded"):
        ml.load_model_service(str(artifact))


@pytest.mark.parametrize("bundle", [{}, {"model": FixturePipeline()},
    {"model": FixturePipeline(), "modelVersion": " "},
    {"model": FixturePipeline(), "modelVersion": "v1", "featureCount": 2},
    {"model": FixturePipeline(), "modelVersion": "v1", "featureCount": 2.5}])
def test_invalid_bundle(bundle):
    with pytest.raises(ml.ModelUnavailableError):
        ml.JoblibPredictor(bundle)


def test_loader_adapter(tmp_path, monkeypatch):
    artifact = tmp_path / "bundle.joblib"
    artifact.touch()  # The loader is mocked; no serialized dummy model is created.
    monkeypatch.setattr(ml.joblib, "load", lambda path: {"model": FixturePipeline(), "modelVersion": "test-v1"})
    service = ml.load_model_service(str(artifact))
    assert service.predict(PredictRequest(features=[1.2, 3.4, 5.6])).prediction == 0.73


def test_startup_loads_once_and_cleans_up(monkeypatch, service):
    calls = []
    def load(path):
        calls.append(path)
        return service
    monkeypatch.setenv("ML_MODEL_PATH", "/models/real.joblib")
    monkeypatch.setattr(main, "load_model_service", load)
    with TestClient(main.app) as client:
        for _ in range(2):
            assert client.post("/predict", json={"features": [1.2, 3.4, 5.6]}).status_code == 200
        assert main.app.state.model_service is service
    assert calls == ["/models/real.joblib"]
    assert main.app.state.model_service is None


def test_missing_model_preserves_other_routes(monkeypatch):
    monkeypatch.delenv("ML_MODEL_PATH", raising=False)
    with TestClient(main.app) as client:
        response = client.post("/predict", json={"features": [1]})
        assert response.status_code == 503
        assert "ML_MODEL_PATH" in response.json()["detail"]
        assert client.get("/health").status_code == 200
        assert client.post("/chat", json={"packId": "agri", "messages": [{"role": "user", "content": "hi"}]}).status_code == 200


@pytest.mark.parametrize("value", [float("nan"), float("inf"), [1, 2], None, True])
def test_invalid_model_output(client, service, value):
    service.model.predict = lambda rows: [value]
    assert client.post("/predict", json={"features": [1.2, 3.4, 5.6]}).status_code == 500


def test_string_prediction(client, service):
    service.model.predict = lambda rows: ["label"]
    assert client.post("/predict", json={"features": [1.2, 3.4, 5.6]}).json()["prediction"] == "label"


def test_unloaded_service(service):
    service.model = None
    with pytest.raises(ml.ModelUnavailableError):
        service.predict(PredictRequest(features=[1, 2, 3]))
