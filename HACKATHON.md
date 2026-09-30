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
| UI strings | `src/i18n/locales/*.json` |

## Optional: on-device LLM (stretch goal)

See `src/ai/strategies/onDeviceLLM.ts`. It needs a development build (`npx eas-cli@latest build --profile development --platform android`)
and a small quantized model (about 0.5B parameters). Only enable it if it's stable on the demo phone; the offline matcher is the guaranteed offline path.
