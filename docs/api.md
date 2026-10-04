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

---

# Health intake endpoints (speech → structured record)

The app's Intake tab calls these. While they don't exist (or the phone is offline), the app falls back to
typing / demo answers and to the on-phone rule-based extractor (`src/intake/extractRules.ts`).
Types: `src/intake/types.ts`. Run `npm run check:intake` to see the offline pipeline on scripted patients.

## `POST /transcribe` (speech-to-text, Jia Wei)
`multipart/form-data` with:
- `audio`: one recorded answer, `audio/m4a` (Expo `RecordingPresets.LOW_QUALITY`, mono, typically 5–20 s)
- `locale`: `sw` or `en`

Response: `{ "text": "Ana homa kali na anakohoa" }`. Return `{ "text": "" }` or a non-200 when unsure; the app then asks the user to type.

## `POST /extract` (text → JSON, jw's parser)
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
- `patientGroup`: `child_u5 | pregnant | adult | null`
- `symptoms`: `fever, cough, difficulty_breathing, diarrhoea, vomiting, headache, abdominal_pain, rash, weakness`
- `dangerSigns`: `unable_to_drink, vomits_everything, convulsions, lethargic, chest_indrawing, vaginal_bleeding, severe_headache_blurred_vision, reduced_fetal_movement, blood_in_stool`
- `dangerSigns` with an empty list must be `"low"` unless the patient clearly said there were none. The app treats low-confidence "no danger signs" as **unsure → ask a health worker**.
- Anything you can't map goes in `unmapped` (shown to the clinician, never used for triage).

## `POST /records` (store-and-forward)
Body: the full `IntakeRecord` JSON. Response `{ "ok": true }`. Sent from the outbox when signal returns. Map it to DHIS2 on the server.
