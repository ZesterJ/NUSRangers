# Evidence: how well the text extraction reads a statement

Reproduce with `npm run evaluate -- http://127.0.0.1:8000` (backend running; see `ml/README.md` for the model
file). Without the URL it reports the on-phone rules only. The table itself is regenerated into
`docs/evidence-extraction.md`.

**Data:** the team's 1,200 labelled statements in `ml/data/raw` (774 English, 426 Swahili). They are synthetic
and team-generated, so these numbers describe behaviour on that set and say nothing about real patients,
real accents or real spelling. "Held out" is the 190 statements the backend model was never fitted on.

**What is compared:** the on-phone rules alone (what runs with no signal) and the backend model combined
with those rules (what runs with signal). Run on 4 October 2026.

| Extractor, data | Statements | Patient type | Duration (exact days) | Symptom precision | Symptom recall | All symptoms right | Danger-sign precision | Danger-sign recall |
|---|---|---|---|---|---|---|---|---|
| Backend model + rules, all | 1200 | 62.8% | 69.9% | 97.2% | 100.0% | 96.2% | 64.9% | 100.0% |
| Backend model + rules, English | 774 | 61.8% | 71.7% | 97.4% | 100.0% | 96.5% | 72.3% | 100.0% |
| Backend model + rules, Swahili | 426 | 64.6% | 66.7% | 96.8% | 100.0% | 95.5% | 51.8% | 100.0% |
| Backend model + rules, held out | 190 | 22.6% | 82.1% | 100.0% | 100.0% | 100.0% | 81.4% | 100.0% |
| On-phone rules, all | 1200 | 59.5% | 67.1% | 97.0% | 95.5% | 90.8% | 60.1% | 81.6% |
| On-phone rules, English | 774 | 60.1% | 67.3% | 97.2% | 94.6% | 89.5% | 69.7% | 88.0% |
| On-phone rules, Swahili | 426 | 58.5% | 66.7% | 96.7% | 97.0% | 93.0% | 41.4% | 65.9% |
| On-phone rules, held out | 190 | 22.6% | 77.9% | 100.0% | 97.7% | 96.8% | 80.4% | 93.7% |

## Reading the numbers

- **Symptoms are the strong part.** Offline, the rules get every symptom in a statement right 90.8% of the
  time; with the model, 96.2%, and no mentioned symptom is missed (recall 100%).
- **Danger signs are never missed with the model (recall 100%), and are over-flagged.** Precision is 60–65%
  overall. Part of that is by design: the app keeps a danger sign found by either extractor, and part is a
  labelling difference (the app flags any blurred vision or bleeding as a danger sign; the dataset labels
  some of those mentions as a symptom only). An extra danger sign sends the patient to a clinic sooner and
  is corrected on the review screen; a missed one is not.
- **Offline, Swahili danger signs are the weak spot:** recall 65.9%, against 88.0% in English. This is the
  clearest gap the backend model closes, and the reason the danger-sign question is a tap checklist.
- **Patient type and duration are weak from free text** (about 60% and 70%). Free text rarely says "adult",
  and durations such as "about four days" are not exact. The app does not rely on text for either: both
  are tap options, and the summary flags a low-confidence value for the patient to check.
- **One artefact of the method:** the dataset has one statement per patient while the app asks four
  questions, so the whole statement was given as the answer to every question. Patient type suffers most
  from this, since the "who" answer is normally a short phrase such as "my child".

## What this does not cover

Real patient speech or typing, spelling outside the synthetic templates (see `npm run check:typed` for the
team's typed-input probes), code-switching, languages other than English and Swahili, and whether the
clinical labels themselves are right: they were written by the team, not by clinicians.
