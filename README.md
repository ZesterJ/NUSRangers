# Njia ya Afya

**Njia ya Afya** ("path to health") helps a patient arrive at a clinic with their visit note already written, and helps the clinic act on it. Built by NUSRangers for the World Bank × Hack-Nation *Small AI for Development* hackathon (Health track), set in Kilifi County, Kenya.

- **Patient or caregiver:** answers four guided questions in Swahili or English by tapping or typing, gets a next step and a suggested clinic, and shows a QR code at the clinic.
- **Clinic:** reception scans the code, the nurse confirms the note and adds vital signs to make a triage report, and the doctor reads it alongside WHO guidance reminders.
- **Works offline.** Everything above runs on the phone with no signal. A connection adds a small text-parsing model and uploads the record.

This app does not diagnose and does not give medical advice. A health worker makes every medical decision.

## Try it

### Option 1: install the Android app
1. On an Android phone, open the releases page and download the `.apk` file from the latest release: <https://github.com/ZesterJ/NUSRangers/releases/latest>
   (The same build is also on Expo: <https://expo.dev/accounts/mushroomyyy/projects/nusrangers/builds/601b5265-69c8-43e1-af2f-00b91b0786d3>, tap **Install**.)
2. Allow installation from your browser when asked.
3. Open **Njia ya Afya**.

There is no iPhone build (it needs a paid Apple Developer account). On an iPhone, use option 2.

### Option 2: run it from source in Expo Go (iPhone or Android)
You need Node 20.19 or newer and the **Expo Go** app on your phone.

```bash
git clone https://github.com/ZesterJ/NUSRangers.git
cd NUSRangers
npm install
cp .env.example .env
npx expo start
```

Scan the QR code shown in the terminal with your phone's camera (iPhone) or with Expo Go (Android). The phone and the computer must be on the same Wi-Fi; if they cannot see each other, run `npx expo start --tunnel` instead.

From source, the app starts on its built-in mock backend, so the whole flow runs on the phone. To use the deployed backend: sign in as Clinic Staff, open **Settings**, turn **Use mock backend** off and set **Backend URL** to `https://njia-ya-afya-nus-rangers.onrender.com`.

## A five-minute walkthrough

**First launch:** choose a language, read the privacy and consent notice, and tap **I understand and agree**.

**As a patient**
1. On Home, tap **Patient or Caregiver**, then **Start a visit note**.
2. Question 1: tap who is sick, enter a full name, and tap Female or Male.
3. Question 2: type what is wrong (for example `fever and cough`, or `Ana homa kali na anakohoa`), or tap the body diagram and pick the problems.
4. Question 3: tap how long it has lasted. Question 4: tap any danger signs, or **None of these**.
5. Check the summary, tap **Confirm visit note**, read the next step and the recommended clinics, then tap **Get my clinic code**.
6. Other tabs: **Clinics** (every facility in Kilifi County on an offline map) and **Records** (your saved notes, with a delete button).

**As the clinic** (a second phone is best; one phone also works)
1. On Home, tap **Sign out**, then **Clinic Staff**. The PIN is **`1234`**.
2. Tap **Receive a patient** and scan the patient's code, then **Add to clinic queue**.
3. Open the patient: correct the visit note if needed, enter vital signs, choose a priority, and tap **Confirm and save triage report**.
4. The triage report, the confirmed note and the WHO guidance reminders are now on that patient's page. The **Guidance** tab lists all guidance by condition.

**Offline:** turn on airplane mode after the app has opened and repeat the patient steps. Everything still works. (In Expo Go, do not reload while offline: Expo Go itself needs the computer to load the app. The installed Android app has no such limit.)

## Where the AI is, and its limits

| Step | How it works | Offline |
|---|---|---|
| Typed text → symptoms, danger signs, duration | A small text model on the backend (TF-IDF + logistic regression, about 100 KB) combined with keyword rules on the phone | Rules only |
| Urgency (go now / within 24 hours / home care / ask a health worker) | Fixed rules from WHO community danger signs | Yes |
| Services needed and recommended clinics | Rules and distance over real Kilifi facility records | Yes |
| Guidance reminders for clinicians | A registry of WHO guidance matched by fixed rules; nothing is generated | Yes |

- Accuracy on the team's 1,200 labelled statements, and what that does not show: [`docs/EVIDENCE.md`](docs/EVIDENCE.md).
- The app says "not sure, ask a health worker" when it cannot rule out danger signs, and a person confirms every step: the patient checks the summary, the nurse confirms the note, the doctor decides.
- **Drafts needing review:** the guidance reminders and vital-sign thresholds have not been checked by a clinician, and much of the Swahili was not written by a native speaker. The app labels the clinical drafts as such.
- **Not production security:** the clinic PIN is a demo gate, there are no accounts, data on the phone is not encrypted, and the demo backend has no access control. Do not enter real patient data.

## Data and sources

- **Health facilities:** 209 Kilifi County facilities from a public ArcGIS layer, 12 with services verified against public sources. No phone numbers or opening hours. Details: [`ml/data/facilities/README.md`](ml/data/facilities/README.md).
- **County boundaries:** geoBoundaries (public domain). Details: [`ml/data/boundaries/README.md`](ml/data/boundaries/README.md).
- **Training and evaluation text:** 1,200 synthetic, team-generated statements in English and Swahili. Details: [`ml/README.md`](ml/README.md).
- **Guidance:** WHO IMCI (2014), WHO guidelines for malaria, WHO pregnancy and antenatal care guidance (2015, 2016), WHO TB screening guideline (2021); sources are cited in the app.

## For developers

- **App:** Expo (React Native) with Expo Router, in `src/`. Stores data in SQLite on the phone.
- **Backend:** FastAPI, in [`backend/`](backend), deployed at `https://njia-ya-afya-nus-rangers.onrender.com`. Deploy guide: [`docs/BACKEND_DEPLOY.md`](docs/BACKEND_DEPLOY.md). API: [`docs/api.md`](docs/api.md). The free tier sleeps when idle; open `/health` to wake it.
- **Models and data:** [`ml/`](ml).
- **Demo script:** [`HACKATHON.md`](HACKATHON.md).

```bash
npm run typecheck && npm run lint
npm run check:intake    # scripted patients through the offline pipeline
npm run check:typed     # messy typed input
npm run evaluate        # extraction accuracy on the labelled statements
cd backend && pytest
```
