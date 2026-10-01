# NUSRangers — Small AI mobile app

A domain-agnostic Expo (React Native) app with a **hybrid AI chatbot**, built ahead of the World Bank *Small AI for Development* hackathon. The chatbot answers on the phone when there's no signal, uses the cloud when there is, and falls back to SMS.

At kickoff we plug the chosen problem into a **domain pack** (`src/packs/`) instead of building from scratch.

- **Chat:** hybrid router with a source badge on every answer (📱 on-phone / ☁️ cloud / 💾 saved / ⏳ queued), read-aloud, SMS fallback
- **Report:** declarative form with photo and location. Instant offline assessment, then a cloud assessment when back online
- **History:** reports plus a sync queue that flushes automatically on reconnect
- **Settings:** language, AI mode (Auto / Offline only / Cloud only), simulate no signal, pack switcher, mock/real backend, backend URL
- Offline-first storage (SQLite) and multilingual UI (en / sw / es)

Sample packs: 🌱 `agri` (ShambaMate), 🩺 `health` (CHW Companion), 🏡 `tourism` (HostMate).

## Quick start

```bash
npm install
cp .env.example .env
npx expo start     # open in Expo Go
```

- Backend (FastAPI + Claude) in [`backend/`](backend). Deploy guide: [`docs/BACKEND_DEPLOY.md`](docs/BACKEND_DEPLOY.md). Contract: [`docs/api.md`](docs/api.md)
- Pivot steps, demo script and file map: [`HACKATHON.md`](HACKATHON.md)

Checks: `npm run typecheck && npm run lint && npm run check:packs`
