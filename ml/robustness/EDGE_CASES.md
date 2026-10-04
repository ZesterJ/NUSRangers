# Typed-input edge cases: backtest, fixes and results

What happens when people type messily into the Intake text boxes, and what was changed about it. Everything here was
measured with the scripts in this folder; nothing is estimated. Scope: the free-text answers that feed `/extract` (the
backend adapter) and the on-phone rule extractor. Speech, the chatbot and triage are not covered.

## How each probe is judged

By what the **user sees**, not by raw detection:

| outcome | meaning |
|---|---|
| correct | the output matches the truth |
| flagged | wrong or incomplete, **but the app warns the user** (low confidence, or the patient's words are shown in notes) |
| **silent error** | wrong or incomplete at **high confidence**, with nothing flagged: the dangerous outcome |

Probes with no single right answer (`ambiguous`) are listed but not counted. The target is zero silent errors.

## The probe catalog (2,991 probes for the backend, 2,802 for the phone rules)

`edge_cases.py` (backend, through the real model) and `scripts/check-typed-input.ts` (phone rules, merge, taps):

- **control**: 32 correct sentences, English and Swahili, one per symptom and sign.
- **typo**: *every* single-character edit (delete, duplicate, swap neighbours, QWERTY-neighbour substitute) at *every*
  position of every key word of 32 sentences (34 for the phone rules): 1,959 probes.
- **negation**: 18 English and 8 Swahili denial cues x 4-5 symptoms x 9 apostrophe spellings (straight, dropped, curly
  U+2019, U+2018, backtick, acute, U+02BC, prime, space), plus negated danger signs and "can drink": 500 probes.
- **scope**: "no fever but cough", "fever and cough but no vomiting", semicolons, "without", Swahili "lakini"/"bila",
  "neither...nor", "not only...but also", all with apostrophe variants.
- **uncertainty**: hedged ("maybe", "labda") and past ("used to", "last year", "imeisha") statements.
- **group**: who is sick, ages in years and months, pregnancy and its denial ("sio mjamzito").
- **duration**: digits, words, Swahili, ranges, approximate, relative.
- **danger**: "none" in 14 spellings and 6 typos, "no, he cannot drink", "cannot even drink", reduced drinking.
- **format**: 39 transforms of 7 core sentences (case, tabs, NBSP, thin space, zero-width and soft-hyphen characters,
  bidi marks, full-width letters, newlines, emoji, HTML, markdown, JSON, 1,500 spaces of padding...).
- **garbage**: empty, spaces, emoji, SQL, script tags, null bytes, RTL and CJK text, 2,000-character limits, zalgo.
- **locale**: seven locale strings.

## Result: backend `/extract` (same 2,951 counted probes, original adapter vs fixed)

| | correct | flagged | **silent error** |
|---|---:|---:|---:|
| original adapter | 582 | 1,448 | **920** |
| fixed adapter | 2,665 | 285 | **0** |

By category, silent errors before -> after: typo 515 -> 0, negation 375 -> 0, scope 21 -> 0, format 3 -> 0, duration 4 -> 0,
danger 1 -> 0, group 1 -> 0. The 285 that remain flagged are by design: 278 typos the app flags for the patient to check
(not auto-corrected), 4 patient-group answers the model cannot map (ages of 5+, "nina mimba"), and 3 duration typos.

## Result: on-phone rules, merge and taps (`npm run check:typed`)

| | correct | flagged | **silent error** |
|---|---:|---:|---:|
| original rules | 600 | 1,132 | **1,056** |
| fixed rules | 2,758 | 30 | **0** |

The original rules had **no concept of a denial**: "I don't have fever", "no fever" and "sina homa" all returned fever at
high confidence (442 of 442 negation probes silent), nor of hedged or past statements (17 of 17 silent).

## What was wrong and what changed

Root causes, found by the catalog and confirmed against the code:

1. **Denials.** The model's cue list has no `didn't`, `hadn't`, `neither`, `nor`, `none of`, or the Swahili `hamna`, `haina`,
   `bila`, `sio`; and every contraction without its straight apostrophe (`dont`, `don’t`, `don´t`, ...) is missed, so a
   denied symptom or danger sign was asserted at high confidence. `normalize_text` (new `backend/app/typed_input.py`) maps
   these onto cues the model knows. `ml/src` is hash-frozen, so nothing there changed.
2. **Invisible and odd characters.** NBSP, tabs, thin spaces, zero-width and soft-hyphen characters, and full-width letters
   split words and phrases ("cannot  drink"). They are cleaned; newlines are kept because the model treats them as
   sentence breaks.
3. **Typos silently dropping a symptom.** A symptom needs an exact-wording match, so one wrong letter lost it, and with other
   symptoms present the answer still read "high confidence". A word one edit from a symptom word is now **suggested at low
   confidence with a note** (`Unclear word: "cogh"`). It is never asserted as sure.
4. **The classifier vetoing matched wording.** On clean text such as "I have fever, cough and diarrhoea." the original adapter
   returned only fever and diarrhoea at high confidence. When the wording matched and only the classifier vetoed it, the
   symptom is now suggested at low confidence.
5. **`no, he cannot drink`** was read as a sure "no danger signs" (high confidence, sign lost): the sign is judged on the part
   after the leading "no". `cannot even drink` and typos in `cannot drink` are caught, but "cannot drink *well*" stays
   reduced drinking, as the model intends.
6. **Short keywords inside other words (phone rules).** `koo` (throat) fired inside the typo `kikoohozi`, `hot` inside
   "photo", `son` inside "person" and "poisoning": 10 of 12 such probes were silent. Keywords of four letters or fewer are
   now whole words. This was already in the code, not caused by typing.
7. **Duration ranges** ("2-3 days", "siku mbili au tatu") silently picked one number; they are now unknown, like "about 3 days".
8. **Contradictory taps.** "None of these" tapped while the text names a danger sign read as a sure "none". The sign stays
   and confidence drops to low (`src/intake/choices.ts`).

## What was tried and rejected, with the measurement

- **Rescue any symptom whose classifier score clears its threshold.** On typo probes it produced 482 wrong labels against
  1,127 right ones, and on clean text it added *fever* to "my child has a cough" and *cough* and *diarrhoea* to "I came to ask
  about my appointment": 88 false positives and 0 correct on the team's 138 authored cases. The exact-wording gate is
  doing real work; only a *matched* wording with a classifier veto is rescued (item 4).
- **Fuzzy correction of the text itself.** The model's authors rejected it, and it is not done: a flagged suggestion needs
  the patient to confirm it; a silently corrected word could turn a denial into a symptom.

## Regression check on clean text

The original and fixed adapters, on the team's 1,338 labelled clean texts (138 authored, 1,200 synthetic):

- 1,283 identical; 55 changed. **0 correct symptoms removed; 0 danger-sign changes; 0 duration changes.**
- 37 changes added a correct symptom at low confidence. All 41 answers that moved from high to low confidence did so because a
  symptom the original had silently lost on clean text is now present and flagged (checked: in every one of the 41 the new
  symptom set strictly adds to the old one).
- 19 additions counted "wrong" against the labels: all are the literal words "very weak" in synthetic text whose label list
  has no weakness, at low confidence.
- The team's own tests pass: `backend/tests` (173 passed with the model, 118 passed and 56 skipped without), `npm run check:intake`,
  `check:packs`, `typecheck` and `lint`. `ml/` is untouched; its 116 tests pass on the committed bytes, but one fails on a Windows
  checkout with `core.autocrlf=true` because the raw-data SHA-256 check sees CRLF line endings. That failure exists without these
  changes, and a `.gitattributes` entry such as `ml/data/raw/* -text` would fix it.

## Known limits (deliberate or unresolved)

- **A typo that is itself a real word is not flagged:** deleting the `f` of `fever` leaves `ever`. Flagging it would raise
  false alarms on "has he ever had fever". Two probes; excluded from the counts.
- **Tokens under 4 letters** are only checked against `homa` (`hoa`, `oma`, `hom`).
- **Typos in non-symptom words** (`maumivu`, `kinauma`, `shida`) are not flagged; those phrases are not suggestible.
- **A newline between every word** ("I\ndon't\nhave\nfever") is read as separate sentences; the model deliberately treats a
  newline as a break ("no fever\ncough"). Four probes, excluded as artificial.
- **Weeks, months and relative durations** are unknown by the team's design, not a bug. Typos in a duration unit
  ("3 dys") stay unknown and flagged.
- **Model gaps unrelated to typing**, not addressed: older children and "nina mimba" map to no group, and `fatigue` has no
  positive support in the team's held-out data.
- **Danger signs are still over-asserted by the phone rules** ("hakuna degedege" yields convulsions): the team's policy.
- Findings are on simulated typing, the team's authored cases and synthetic data. They show what breaks and how badly,
  not real-world error rates; real phone autocorrect fixes many typos. The frozen acceptance set was used read-only.

## Reproduce

```sh
# backend (needs the extraction artifact, see ml/README.md, and backend deps)
python ml/robustness/edge_cases.py --artifact ml/artifacts/experimental_health_ie_final.joblib --out /tmp/edge
EXTRACT_MODEL_PATH=ml/artifacts/experimental_health_ie_final.joblib pytest backend/tests/test_typed_input.py
# phone rules, merge, taps
npm run check:typed
```
To reproduce the "before" column, run `edge_cases.py` against a checkout of the original `backend/app` with `--backend` and
`--code`. The probe catalog is deterministic.

## Merge policy, unchanged

`mergeExtractions` trusts a confident backend model over the phone rules for anything the model can judge (it understands
negation; the rules over-assert danger signs), and keeps signs only the rules know. That is the team's design and was left as
is; `check:typed` tests it so it cannot drift silently.
