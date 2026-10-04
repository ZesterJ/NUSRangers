# Backend API contract

The mobile app talks to these endpoints. Until the backend is up, the app uses an in-app mock
(`src/api/mock.ts`, toggle **Settings → Use mock backend**). Types live in `src/api/types.ts` — keep both in sync.

Base URL: `EXPO_PUBLIC_API_URL` (or **Settings → Backend URL** at runtime — handy for pointing at a teammate's laptop IP on hackathon wifi, e.g. `http://192.168.1.23:8000`).

All bodies are JSON. Keep responses small: users are on slow, expensive connections.

A reference implementation lives in [`backend/`](../backend), and the deploy steps are in [`BACKEND_DEPLOY.md`](BACKEND_DEPLOY.md).

**Errors:** `422` = the request doesn't match the schema, `503` = the model provider is busy or unreachable (retry later), `502` = the model provider rejected the request. On any error or timeout (30s), the app falls back to on-phone answers and queues the request.

## `GET /health`
`200 {"ok": true, "provider": "anthropic"}` (`"echo"` means the backend is running without a model)

## `POST /chat`
The cloud half of the hybrid chatbot. Called only when the on-phone knowledge had no strong match.

Request:
```json
{
  "packId": "agri",
  "locale": "sw",
  "systemPrompt": "You are ShambaMate, ...",
  "messages": [
    { "role": "user", "content": "Nipande mahindi lini?" },
    { "role": "assistant", "content": "..." },
    { "role": "user", "content": "Na maharagwe je?" }
  ],
  "context": {}
}
```
- `systemPrompt` comes from the active domain pack; use it as the system message. The server may append its own rules, such as safety, brevity or retrieval context.
- `messages` holds at most the last 8 turns plus the new question.
- Reply in `locale`.

Response:
```json
{ "reply": "Panda maharagwe ...", "sources": ["FAO GAEZ v4"] }
```
`sources` is optional (shown in future UI).

## `POST /analyze`
Assessment of a report submitted from the **Report** tab. The fields come from the pack's `captureForm`.

Request:
```json
{
  "packId": "agri",
  "locale": "en",
  "fields": { "crop": "maize", "symptom": "holes", "affected": 7, "location": { "lat": -1.29, "lng": 36.82 } },
  "imageBase64": "<optional JPEG base64, quality 0.3>"
}
```
Response:
```json
{
  "summary": "Likely fall armyworm.",
  "riskLevel": "med",
  "actions": ["Treat within 2 days", "Scout again in 3 days"]
}
```
`riskLevel` is `low | med | high`, optional.

When the phone is offline, the app computes the same shape locally with the pack's `offlineAssess()` rules. It then queues the report and calls `/analyze` once it reconnects, and the cloud result replaces the local one.

## `POST /sms/webhook` (backend only)
Inbound SMS from the gateway (Twilio or Africa's Talking) for users with no data or no smartphone.
The app's "Send by SMS" button composes `"<PACKID>: <question>"` to the pack's `smsNumber`.
Parse the prefix to pick the pack, answer with the same logic as `/chat`, and keep the reply within **160 characters**.

## `GET /packs/:id` (optional)
Return a `DomainPack` as JSON (without the `offlineAssess` function) for remote config. It isn't wired in the app yet.

## `POST /predict`

Backend-local ML inference: the model runs inside FastAPI, **not on the phone**.
The app still needs network access. This is separate from `/chat`, `/analyze`,
Claude, and the offline AI router; none of those paths call `/predict`.

Initial request (one sample):
```json
{ "features": [1.2, 3.4, 5.6] }
```
`features` is a required, non-empty array of finite numbers. Strings, booleans,
nulls, NaN, infinity, and unknown request fields are rejected. Feature count must
match the loaded pipeline's metadata when available. Order and units must match
training; the eventual task must document them.

Response:
```json
{ "prediction": 0.73, "modelVersion": "v1" }
```
`prediction` is initially a finite number or string scalar. `modelVersion` is a
required non-blank version from the artifact. No confidence score is fabricated.
This initial contract is intentionally isolated in `PredictRequest` /
`PredictResponse` and mirrored in `src/api/types.ts`; revise both for images,
sequences, vectors, or other task-specific inputs/outputs when the task is known.

Errors: `422` for invalid inputs or feature count, `503` when no usable model is
loaded, `500` for inference failures or unsupported model output. Missing/invalid
artifacts leave existing endpoints available. `/health` describes the existing
LLM service, not ML readiness. The app's mock backend returns the fixed API fixture
`{ "prediction": "[mock prediction]", "modelVersion": "mock-v1" }`.

### Supplying the trained model

Train separately and export a **trusted joblib bundle** with:
- `model`: a fitted pipeline implementing `predict(rows)`, including all fitted
  preprocessing; one scalar result per input row.
- `modelVersion`: non-blank string identifying the trained artifact.
- `featureCount`: optional positive integer; otherwise use pipeline
  `n_features_in_` when available. If both exist, they must agree.

Set `ML_MODEL_PATH` to the artifact path inside the backend environment.
FastAPI lifespan loads it once per worker at startup into application state;
`/predict` obtains the service through dependency injection and runs synchronous
inference in FastAPI's thread pool. Restart workers after replacing an artifact.
Each worker holds its own model copy. Ensure the eventual runtime supports
concurrent inference, or add serialization inside its adapter.

`backend/app/ml.py` contains the `Predictor` interface and initial joblib adapter.
To adopt another runtime, implement that interface and change the loader there;
the route does not need runtime-specific logic. There is no training code or
production placeholder model. Install the eventual model's matching runtime
(e.g. the training-compatible scikit-learn version) in backend dependencies;
joblib alone cannot deserialize every training pipeline. Load only trusted
artifacts because joblib deserialization can execute code.

For production, publish versioned artifacts separately from Git and mount a
read-only artifact directory into the container, for example `/models`, with
`ML_MODEL_PATH=/models/model.joblib`. Alternatively, deployment can download a
verified artifact from controlled storage before starting Uvicorn. The existing
Dockerfile needs no change for a runtime mount; it only copies application code.
Do not commit large artifacts or training data. Supply the real trained pipeline,
version, feature contract, runtime dependencies, and evaluation fixtures once the
hackathon task is known.

---

# Health intake endpoints (answers → structured record)

The app's Intake tab calls these. While they don't exist (or the phone is offline), the app falls back to
typing / demo answers and to the on-phone rule-based extractor (`src/intake/extractRules.ts`).
Types: `src/intake/types.ts`. Run `npm run check:intake` to see the offline pipeline on scripted patients.

## `POST /extract` (text → JSON, jw's parser)
Implemented in `backend/app/extract.py`, which wraps the extraction model in `ml/` (build the artifact
first, see `ml/README.md`; override locations with `EXTRACT_MODEL_PATH` / `EXTRACT_CODE_PATH`). It returns
`503` when the model is not loaded, and the app then uses its on-phone rules. When it does answer, the app
combines the result with the on-phone rules (`src/intake/mergeExtraction.ts`): the model is preferred where
it is confident, the rules fill gaps, and danger signs found by either are kept.

Request:
```json
{
  "locale": "sw",
  "answers": {
    "who": "Mtoto wangu wa miaka miwili",
    "complaint": "Ana homa kali na anakohoa",
    "duration": "Siku tatu",
    "danger": "Hawezi kunywa"
  }
}
```
Response (`Extraction`). Only use the listed codes, and mark guesses `"low"`:
```json
{
  "patientGroup": { "value": "child_u5", "confidence": "high", "evidence": "Mtoto wangu" },
  "symptoms": { "value": ["fever", "cough"], "confidence": "high" },
  "durationDays": { "value": 3, "confidence": "high" },
  "dangerSigns": { "value": ["unable_to_drink"], "confidence": "high" },
  "unmapped": [],
  "source": "model"
}
```
- `patientGroup`: `child_u5 | pregnant | adult | null` (the app also has `child_5plus`, set only from its tap-to-answer options)
- `symptoms`: `fever, cough, difficulty_breathing, diarrhoea, vomiting, headache, abdominal_pain, rash, weakness, sore_throat, chest_pain, limb_pain` (the last three are set by the on-phone rules and the body diagram; the model does not emit them)
- `dangerSigns`: `unable_to_drink, vomits_everything, convulsions, lethargic, chest_indrawing, vaginal_bleeding, severe_headache_blurred_vision, reduced_fetal_movement, blood_in_stool`
- `dangerSigns` with an empty list must be `"low"` unless the patient clearly said there were none. The app treats low-confidence "no danger signs" as **unsure → ask a health worker**.
- Anything you can't map goes in `unmapped` (shown to the clinician, never used for triage).

## `POST /assess` (visit note → care services + Kilifi facility candidates)
Implemented in `backend/app/care.py`, which wraps the care policy and facility router in `ml/src`
(`care_policy.py`, `verified_facility_demo.py`) and the Kilifi data in `ml/data/facilities`. No model file is
needed. The app calls it after the patient confirms the visit note; on any non-200 it shows its on-phone
sample clinic list instead.

Request (the confirmed note, from taps and free text alike; the patient's name is not sent):
```json
{
  "locale": "sw",
  "note": {
    "patientGroup": "child_u5",
    "symptoms": ["fever", "cough"],
    "durationDays": 3,
    "dangerSigns": [],
    "notes": ""
  },
  "coordinates": { "latitude": -3.63, "longitude": 39.85 }
}
```
Response:
```json
{
  "requiredServices": ["generalOutpatient", "childHealth"],
  "assessmentStatus": "proposed",
  "routingStatus": "candidates_found",
  "candidates": [
    { "facilityId": "arcgis:…", "facilityName": "KILIFI DISTRICT HOSPITAL", "rank": 1, "distanceKm": 0.0, "matchedServices": ["childHealth", "generalOutpatient"] }
  ],
  "origin": "demo_anchor",
  "limitations": ["Not current capability verification or clinical suitability"],
  "requiresVerification": true
}
```
- `coordinates` is optional. Without it, or when it lies outside the area the catalogue covers, distances are
  measured from Kilifi District Hospital and `origin` is `demo_anchor`. The app does not send coordinates yet.
- `distanceKm` is straight-line distance, not travel time. Only facilities whose required services are
  documented are returned; an `unknown` capability is never treated as present.
- `assessmentStatus: "unclear"`: the care policy abstains when danger signs are present. The adapter then
  lists facilities by patient group (general outpatient, plus child health or maternal care).
- Urgency ("go now", "within 24 hours", …) is not decided here; it stays with the app's on-phone triage rules.

## `POST /records` (store-and-forward)
Body: the full `IntakeRecord` JSON. Response `{ "ok": true }`. Sent from the outbox when signal returns. Map it to DHIS2 on the server.
