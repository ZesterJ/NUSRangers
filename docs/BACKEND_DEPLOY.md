# Backend: build, run and deploy

**For:** the backend engineer. **Goal:** a public HTTPS URL the mobile app can call **before kickoff (Oct 3)**. After that, the hackathon is only prompt and data work.

A working starter is already in [`backend/`](../backend). It's FastAPI + Claude, has tests, and the Docker build is verified. You own it from here: deploy it first, then extend it.

---

## 1. What the backend is for

The app answers questions with a **hybrid "Small AI" router** (`src/ai/AiRouter.ts`):

```
User question
  └─► 1. On-phone knowledge (keyword match, works offline)   ── strong match? answer, done
  └─► 2. POST /chat  ◄── THIS BACKEND (Claude)               ── only if online and no strong on-phone match
  └─► 3. On-device LLM (optional, off by default)
  └─► 4. Saved answer from an earlier /chat reply
  └─► 5. Queue for later + "Send by SMS"  ──► POST /sms/webhook ◄── THIS BACKEND
```

Report forms (crop problem, household visit, booking) go to `POST /analyze`. Offline, the phone runs simple rules and retries `/analyze` when the connection comes back.

**If the backend is down or slow, the app still works:** it falls back to on-phone answers and queues the request. So a 503 is never a demo-killer, but a working backend is what makes answers good.

| Endpoint | Called when | Contract |
|---|---|---|
| `GET /health` | Before the demo, to warm up | `{"ok": true, "provider": "anthropic"}` |
| `POST /chat` | The chatbot needs a cloud answer | [`docs/api.md`](api.md#post-chat) |
| `POST /analyze` | A report is submitted, or synced after being offline | [`docs/api.md`](api.md#post-analyze) |
| `POST /sms/webhook` | Someone texts the SMS number (basic phones) | Twilio form post in, TwiML out |

Request and response shapes **must** match `src/api/types.ts` in the app (camelCase: `packId`, `imageBase64`, `riskLevel`). `backend/tests/test_api.py` locks this down, so run it after every change.

---

## 2. Code tour (`backend/`)

| File | What it does |
|---|---|
| `app/main.py` | FastAPI routes, errors mapped to 503 (retryable) or 502, SMS prefix parsing, TwiML reply |
| `app/llm.py` | `AnthropicProvider` (Claude) and `EchoProvider` (no key, canned replies). Chooses one from `LLM_PROVIDER` |
| `app/prompts.py` | Server-side persona per pack, plus mobile, analysis and SMS rules. **Add an entry when the app adds a pack** |
| `app/schemas.py` | Pydantic models (the request/response contract) with size limits |
| `tests/` | Contract tests and Claude request-building tests with a fake client (no network, no key) |

How the Claude calls are set up (`app/llm.py`):
- **Model:** `claude-opus-5-5` by default. You can change it with `ANTHROPIC_MODEL` (see §7 for cost/speed options).
- **Effort:** `low` by default (`ANTHROPIC_EFFORT`). This keeps chat replies fast on slow networks. Try `medium` for `/analyze` if answers feel shallow.
- **Refusal fallback:** on by default (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). If Claude's safety classifier declines a request (possible with health questions), the API retries on Anthropic's recommended fallback model instead of failing. If the whole chain refuses, the user gets a polite "contact a local expert" reply.
- **Structured output for `/analyze`:** `client.beta.messages.parse(output_format=Assessment)` returns a validated `{summary, riskLevel, actions}`. Photos are sent as an image block.
- **Chat history:** the app sends the last 8 turns, which don't always start with the user or alternate. `to_api_messages()` normalises them before the call.

---

## 3. Run it locally (5 minutes)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                                        # 13 tests, no API key needed

# No key yet: canned replies
LLM_PROVIDER=echo uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Real Claude
cp .env.example .env                          # put your ANTHROPIC_API_KEY in .env
set -a && source .env && set +a
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Get an API key at https://platform.claude.com (Settings → API keys), and **set a monthly spend limit** there before sharing the URL.

### Smoke tests

```bash
URL=http://localhost:8000   # later: your Render URL

curl -s $URL/health

curl -s -X POST $URL/chat -H 'Content-Type: application/json' -d '{
  "packId": "agri", "locale": "sw", "systemPrompt": "You are ShambaMate, an agronomy assistant.",
  "messages": [{"role": "user", "content": "Mahindi yangu yana majani ya njano, nifanye nini?"}]
}'

curl -s -X POST $URL/analyze -H 'Content-Type: application/json' -d '{
  "packId": "agri", "locale": "en",
  "fields": {"crop": "maize", "symptom": "holes", "affected": 7, "location": {"lat": -1.29, "lng": 36.82}}
}'

curl -s -X POST $URL/sms/webhook -d 'Body=HEALTH: child has fever for 3 days&From=+254700000000'
```

What to expect: `/chat` → `{"reply": "...", "sources": null}` in Swahili. `/analyze` → `{"summary", "riskLevel", "actions"}`. SMS → `<Response><Message>…</Message></Response>` with at most 160 characters.

---

## 4. Deploy to Render (recommended, about 10 minutes)

The image is built from the **repository root**, because the backend serves the extraction model, care
routing data and guidance registry that live outside `backend/`. The build trains the extraction model
itself (about 15 seconds), so no model file needs to be committed. The running service uses about 140 MB,
within the free tier's 512 MB.

Render must be able to see the GitHub repository. `ZesterJ/NUSRangers` is private, so either the repo owner
does these steps, or they grant Render's GitHub app access to the repo for your Render account.

**With the Blueprint (`render.yaml`, simplest):**
1. Sign in at https://render.com with GitHub.
2. **New + → Blueprint** → pick `ZesterJ/NUSRangers` and the branch to deploy.
3. Render reads `render.yaml` and creates `njia-ya-afya-backend`. Click **Apply**.

**By hand (if you prefer the form):** **New + → Web Service** → pick the repo, then:
   - **Language / Runtime:** `Docker`
   - **Root Directory:** leave empty
   - **Dockerfile Path:** `./backend/Dockerfile`
   - **Docker Build Context Directory:** `.`
   - **Health Check Path:** `/health`
   - **Environment variable:** `LLM_PROVIDER` = `echo` (no API key needed; the visit-note flow does not use the chat endpoints). Use `anthropic` plus `ANTHROPIC_API_KEY` only if you want the chat endpoints to answer.

When the deploy log shows `Uvicorn running`, copy the URL (e.g. `https://njia-ya-afya-backend.onrender.com`)
and check `$URL/health`, then `$URL/guidance`.

**Current deployment:** `https://njia-ya-afya-nus-rangers.onrender.com` (from `main`, added by public repository
URL, so it does not redeploy on its own: use **Manual Deploy** after merging). Installed builds use this address
through the `env` block in `eas.json`.

Every push to the deployed branch redeploys automatically.

⚠️ **Free tier sleeps after about 15 minutes idle**, and the first request then takes 30–60s. The intake gives up on the backend after 8 seconds and uses the on-phone rules instead. **Open `$URL/health` a minute before any demo or judging slot.** Stored visit records are kept in memory only and are lost when the service sleeps or redeploys.

To test the image locally first:
```bash
docker build -f backend/Dockerfile -t njia-ya-afya-backend .
docker run --rm -p 8000:8000 -e LLM_PROVIDER=echo njia-ya-afya-backend
```

### Alternative: Railway

Go to **New Project → Deploy from GitHub repo** → pick the repo. Leave the root directory at the repository root and set the Dockerfile path to `backend/Dockerfile`. Add the same **Variables**, then **Networking → Generate Domain**. Railway doesn't sleep like Render's free tier, but it bills by usage after the trial credit.

### Alternative: your laptop on venue wifi (backup plan)

Run `uvicorn app.main:app --host 0.0.0.0 --port 8000` and find your LAN IP (`ipconfig getifaddr en0` on macOS, `hostname -I` on Linux). In the app, set **Settings → Backend URL** to `http://<ip>:8000`. This only works if the phone is on the same wifi and the venue doesn't isolate clients. `npx expo start --tunnel` doesn't tunnel the backend; use `ngrok http 8000` for that.

---

## 5. Connect the app

Choose either option:

- **At build time:** in the app's `.env`:
  ```
  EXPO_PUBLIC_API_URL=https://njia-ya-afya-backend.onrender.com
  EXPO_PUBLIC_USE_MOCK=0
  ```
  Then restart `npx expo start`.
- **At runtime (no rebuild):** go to **Settings → Developer**, turn off **Use mock backend**, and paste the URL into **Backend URL**.

Check it by asking something that isn't in the pack's offline knowledge (e.g. "What is intercropping?"). The reply should carry the ☁️ **Cloud AI** badge. Replies saying `[mock cloud · …]` mean the app is still on the mock; `[echo:…]` means the backend is running with `LLM_PROVIDER=echo`.

---

## 6. SMS (optional, for the "works on a basic phone" story)

The app's **Send by SMS** button composes `"<PACKID>: <question>"` to the pack's `smsNumber` (currently a placeholder `+10000000000` in `src/packs/*.ts`).

**Twilio** (works as-is):
1. Get a trial number with SMS capability.
2. Go to **Phone Numbers → your number → Messaging → A message comes in**, choose **Webhook**, `POST`, and enter `https://<your-backend>/sms/webhook`.
3. Put that number in the pack's `smsNumber`.

Trial accounts can only text verified numbers, so verify the demo phone.

**Africa's Talking** (better coverage in East Africa) posts different fields (`from`, `text`) and replies through their send API rather than TwiML. Add a separate `/sms/at-webhook` route if you go that way.

Replies are capped at 160 characters (one SMS segment).

---

## 7. Cost, speed and model choice

- Each `/chat` call is a few hundred input tokens plus a short reply at `low` effort. For a hackathon's worth of testing this is cents to low dollars, but **set a spend limit** anyway, because the endpoint is public and has no authentication.
- If replies feel slow on the demo network, first check it's not a Render cold start. Then you can switch `ANTHROPIC_MODEL` to a faster, cheaper model (e.g. `claude-sonnet-5-5` or `claude-haiku-4-5`) **as a team decision**, since it trades off answer quality. The code already skips effort and fallback settings on models that don't support them.
- `LLM_TIMEOUT_SECONDS` (25s) is kept below the app's 30s timeout, so the app gets a clean 503 and falls back rather than hanging.

---

## 8. After kickoff: what to change

1. **`app/prompts.py`:** add or adjust the chosen pack's persona (keep it in step with `systemPrompt` in `src/packs/<id>.ts`) and tune `ANALYZE_RULES` for the real form fields.
2. **Real data beats a bigger model.** Add retrieval over the dataset for the problem (FAO GAEZ, WHO guidance, national tourism stats): load a CSV or JSON at startup, pick the relevant rows for the question, and append them to the system prompt. Return their names in `ChatResponse.sources`.
3. **Problem-specific endpoints**, e.g. `GET /forecast?packId=agri&market=…` for price or demand numbers on the home cards. Tell the FE engineer the shape, and the card can be wired to it.
4. Keep `pytest` green and re-run the smoke tests after each deploy.

## Hackathon-day checklist

- [ ] Backend deployed, `/health` returns `"provider": "anthropic"`
- [ ] Spend limit set in the Claude Console
- [ ] `ANTHROPIC_API_KEY` only in Render's env vars (not in git, not in the app)
- [ ] App pointed at the URL (`EXPO_PUBLIC_USE_MOCK=0` or Settings) and ☁️ Cloud AI replies confirmed
- [ ] `DEFAULT_PACK` and `app/prompts.py` updated for the chosen problem
- [ ] `/health` opened 1 minute before judging (cold start)
- [ ] Backup: laptop backend on LAN, or the app's mock and offline mode
