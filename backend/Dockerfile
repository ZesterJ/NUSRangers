# Build from the REPOSITORY ROOT, because the backend serves code and data that live outside backend/:
#   docker build -f backend/Dockerfile -t njia-ya-afya-backend .
# On Render: Dockerfile Path `./backend/Dockerfile`, Docker Build Context `.` (see render.yaml).

# ---- Stage 1: train the text-extraction model (the artifact is not kept in git) ----
FROM python:3.13-slim AS model
WORKDIR /srv
COPY ml/requirements.txt ml/requirements.txt
RUN pip install --no-cache-dir -r ml/requirements.txt
COPY ml/src ml/src
COPY ml/data ml/data
RUN mkdir -p ml/artifacts ml/reports ml/data/processed \
 && python ml/src/train_symptom_model.py > /dev/null \
 && python ml/src/tune_final.py > /dev/null \
 && python ml/src/evaluate_final_tuning.py > /dev/null \
 && test -f ml/artifacts/experimental_health_ie_final.joblib

# ---- Stage 2: the API ----
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Same layout as the repository, so the code's default paths (ml/src, ml/artifacts, ml/data/facilities,
# src/intake/guidanceRegistry.json) resolve without extra environment variables.
WORKDIR /srv/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY ml/src /srv/ml/src
COPY ml/data/facilities /srv/ml/data/facilities
COPY src/intake/guidanceRegistry.json /srv/src/intake/guidanceRegistry.json
COPY --from=model /srv/ml/artifacts/experimental_health_ie_final.joblib /srv/ml/artifacts/experimental_health_ie_final.joblib

# Render, Railway and Fly inject $PORT; default to 8000 locally.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
