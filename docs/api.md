# Backend API contract

The mobile app talks to these endpoints. Until the backend is up, the app uses an in-app mock
(`src/api/mock.ts`, toggle **Settings → Use mock backend**). Types live in `src/api/types.ts` — keep both in sync.

Base URL: `EXPO_PUBLIC_API_URL` (or **Settings → Backend URL** at runtime — handy for pointing at a teammate's laptop IP on hackathon wifi, e.g. `http://192.168.1.23:8000`).

All bodies are JSON. Keep responses small: users are on slow, expensive connections.

## `GET /health`
`200 {"ok": true}`

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
