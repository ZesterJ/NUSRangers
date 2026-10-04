# Hackathon runbook

World Bank **Small AI for Development** hackathon (via Hack-Nation), Oct 3–4. Tracks: Agriculture, Health, Tourism.

## At kickoff: pivot to the problem statement (about 2 hours)

1. **Copy the closest sample pack:** `src/packs/agri.ts`, `health.ts` or `tourism.ts` → `src/packs/<name>.ts`.
2. Edit it, top to bottom:
   - `appName`, `emoji`, `tagline`, `theme.primary`
   - `locales`: every locale needs a UI strings file in `src/i18n/locales/<code>.json` (copy `en.json`).
   - `systemPrompt`: persona, audience and safety rules. Health: never diagnose.
   - `offlineKnowledge`: 10–20 of the most common questions, with 3+ phrasings each, in each locale. Source answers from real public data (FAO, WHO, World Bank, national stats) and cite them in the pitch.
   - `quickReplies`: must be answerable offline. `npm run check:packs` enforces this.
   - `homeCards`: the dashboard (alerts, metrics, tips, action shortcuts).
   - `captureForm` + `offlineAssess`: the "report" flow and its offline rules.
3. Register the pack in `src/packs/index.ts` and set `EXPO_PUBLIC_PACK=<id>` in `.env`.
4. Run `npm run check:packs && npm run typecheck && npm run lint`.

## Commands

```bash
npm install
cp .env.example .env        # set EXPO_PUBLIC_API_URL / USE_MOCK / PACK
npx expo start              # scan the QR code with Expo Go (same wifi), or press a / i
npx expo start --tunnel     # if venue wifi blocks LAN
npm run typecheck && npm run lint && npm run check:packs
```

Everything in the app runs in **Expo Go** except the optional on-device LLM (see below).

## Demo script (the "Small AI" story)

1. **Online:** ask something not in the offline pack. The reply has a ☁️ **Cloud AI** badge.
2. **Settings → Simulate no signal** (or airplane mode on a dev build). The orange offline banner appears.
3. Tap a quick reply. The answer is instant, with a 📱 **On-phone knowledge** badge.
4. Ask the earlier cloud question again. It comes back with a 💾 **Saved answer** badge (cached).
5. Ask something new. You get ⏳ **Queued** plus a ✉️ **Send by SMS** button for basic phones.
6. **Report tab:** submit a report. You get an instant on-phone risk assessment, and the History tab shows "1 waiting to sync".
7. Turn the signal back on. It syncs automatically: the queued question gets a cloud answer in the chat, and the report gets the cloud assessment.
8. Switch the language. The UI, pack content and 🔊 read-aloud all follow.

Pro tip: record this as a backup video before judging.

## Health intake demo (Noor's journey, about 2 minutes)

Uses the default `health` pack. Nobody needs to speak Swahili: tap the **demo answers** under each question.

1. **Settings → Simulate no signal** on. Everything below works offline.
2. **Intake tab:** 4 guided questions (🔊 reads each one aloud). Tap the demo answers: child, fever + cough, 3 days, "cannot drink".
3. **Check the answers:** the form is pre-filled from what was said. Point out the ⚠ "please check" items and the 📱 "read on this phone" label.
4. **Confirm → result:** 🚨 "Go to a clinic now", the reasons, and "a health worker makes the final decision".
5. **Recommended clinics:** real Kilifi facilities whose services are documented, nearest first (straight-line distance). Computed on the phone, so it works with no signal. Opening hours and staffing are not known.
6. **Create clinic handoff → QR.** On a second phone, open the **Clinic** tab, scan it, see ✓ Verified, and tap Mark as received.
7. **Records tab:** "1 waiting to sync". Turn the signal back on: it syncs.
8. Run it once more with vague answers (e.g. "sijui") to show **"Not sure. Ask a health worker"**: the brief's pass/fail fail-safe.

Answers are tapped or typed; speech-to-text was removed because a Swahili speech model is too large for the phone.
`npm run check:intake` runs scripted patients through extraction → triage → clinic ranking.

## Where things live

| What | Where |
|---|---|
| Problem-specific content | `src/packs/*.ts` |
| Hybrid AI order (offline → cloud → on-device → cache → queue/SMS) | `src/ai/AiRouter.ts` |
| Offline matcher and thresholds | `src/ai/strategies/offlineMatcher.ts` |
| Backend calls / mock | `src/api/client.ts`, `src/api/mock.ts`, contract in `docs/api.md` |
| Backend (FastAPI + Claude) | `backend/`, deploy guide in `docs/BACKEND_DEPLOY.md` |
| Offline storage and sync queue | `src/db/index.ts`, `src/ai/sync.ts` |
| Screens | `src/app/(tabs)/*.tsx` |
| Health intake: questions, extraction rules, triage, clinic ranking, QR | `src/intake/*` |
| UI strings | `src/i18n/locales/*.json` |

## Optional: on-device LLM (stretch goal)

See `src/ai/strategies/onDeviceLLM.ts`. It needs a development build (`npx eas-cli@latest build --profile development --platform android`)
and a small quantized model (about 0.5B parameters). Only enable it if it's stable on the demo phone; the offline matcher is the guaranteed offline path.
