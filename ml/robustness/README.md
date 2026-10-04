# Typing-error backtest of the text extraction

> **Start with [`EDGE_CASES.md`](EDGE_CASES.md)**: the systematic edge-case test (about 3,000 probes: every single-character typo
> at every position, every apostrophe spelling and denial cue, scope, hedging, formatting, Unicode and hostile input), what it
> found, what was fixed (`backend/app/typed_input.py`, `src/intake/extractRules.ts`), what was tried and rejected, and the
> known limits. `edge_cases.py` runs it; `npm run check:typed` runs the phone-side counterpart. The rest of this file is the
> earlier random-perturbation backtest of the model alone.

How the pipeline behind `/extract` (`ml/src/extraction_pipeline.py`) copes with messy typed input. This is a
sensitivity test, not a measured real-world error rate. Nothing in `ml/src` or `backend/` was changed.

## Run it
```sh
python ml/robustness/backtest.py --artifact ml/artifacts/experimental_health_ie_final.joblib --out ml/reports/robustness
python ml/robustness/probes.py --artifact ml/artifacts/experimental_health_ie_final.joblib
python ml/robustness/adapter_probes.py --artifact ml/artifacts/experimental_health_ie_final.joblib   # needs pydantic
```
- `perturb.py`: 13 corruptions (phone-keyboard typos, SMS vowel drops, apostrophes, caps, spacing, punctuation, number format).
- `backtest.py`: counts only regressions the corruption *caused* (right on clean text, wrong after). Full tables: `results_tables.md`.
- `probes.py`: hand-labelled apostrophe cases, because **no labelled case contains a straight apostrophe**, so the apostrophe perturbations never applied in the backtest.
- `adapter_probes.py`: what the app's `Extraction` (value + confidence) shows for hand-written inputs.

## Findings
The pipeline accepts a symptom only if the classifier score clears the threshold **and** an exact-wording regex
matches the raw text. Danger signs, negation and duration are regex only. So:

| Finding | Evidence |
|---|---|
| **Lost apostrophe turns a denial into an assertion, at high confidence.** | `I dont have fever` and `I don’t have fever` return `fever` / **high**, nothing in notes (adapter). Probes: with a straight apostrophe 7/7 correct; with it dropped or curly, **12 of 14 variants wrong**, e.g. `doesn’t have convulsions` returns the danger sign `convulsions`. |
| **A typo in a matched word usually drops the symptom.** | Typo inside a matched symptom/sign word: symptom lost 77% (dev, 90 cases), 71% (frozen, 48), 38% (synthetic, 190). One random typo anywhere: 36% / 39% / 8%. Cause is the regex gate in ~100% of cases. |
| **A typo inside a danger-sign phrase removes the sign.** | Signs have no classifier fallback, only the regex. In the dev and frozen cases the sign phrase was the only matched wording, so every targeted typo hit it: signs lost in 100% of trials (80/80 dev, 20/20 frozen). In the synthetic set typos more often hit other words, so only 12% of sign trials lost the sign (88 trials). One random typo lost the sign in 70% / 30% / 6% (dev / frozen / synthetic). The adapter then returns **low** confidence, so the app asks for a check; this safety net works. |
| **One lost symptom among several is silent.** | `fever and cogh` returns `['fever']` / **high**, `notes=[]`. The adapter only fills `notes` when no symptom was found. |
| **Double spaces break multi-word phrases.** | Danger signs lost 62% / 50% / 57% when every space is doubled (an upper bound; one double space inside "cannot drink" is enough). |
| **A typo in a negation cue flips a denial.** | Dev: 75 symptoms and 45 danger signs asserted that the text denied; frozen: 60 and 15. Synthetic data has no negation, so 0 there. |
| Robust: capitals, number format. | ALL CAPS / lowercase: 0 regressions; `2 days` vs `two days`: 0–1%. |
| Missing punctuation hurts a little. | 5–12% of symptoms lost; the classifier still scores most of them above threshold. |
| Partly mitigated by design. | The team's phrase table already includes some misspellings (`fevr and vomitting` works). Only unknown typos fail. |

"Rescuable": of the symptoms lost to a typo in a matched word, the classifier alone still scored above its
threshold for 76% (dev), 77% (frozen), 86% (synthetic). For vowel drops (`homa` → `hma`) only 45% (dev).
That means a typo-tolerant step could keep most of them, but its false-positive cost was **not** measured.

## Suggested fixes (proposals only; the pipeline belongs to its authors)
1. **Normalise the text before extraction:** curly → straight apostrophes (U+2018/2019/02BC), collapse whitespace, trim. Cheap; fixes the curly-quote and spacing failures.
2. **Add apostrophe-less negation and ability forms** (`dont`, `doesnt`, `isnt`, `wasnt`, `hasnt`, `havent`, `cant`) to `NEGATED` and the sign patterns, with the positive/negated regression cases the team already requires for new phrases. This closes the one silent, high-confidence error.
3. **Rescue as a suggestion, not an assertion:** when the classifier clears its threshold but the regex gate fails, return the symptom at *low* confidence for the patient to confirm. This keeps the team's rule of never asserting on fuzzy matches.
4. **Do not let a found symptom hide an unexplained one:** lower confidence (or show the raw answer) when the text has content words that matched nothing.

## Caveats
- Test sets are small. The 90 development and 48 "frozen" cases were authored by the team's assistant, not independently; synthetic cases are template-heavy. The frozen set was used read-only for measurement. Do not tune against it.
- The perturbations are my model of typing errors. `typo_in_evidence` always hits the key word, so it is a worst case by construction. Real phone autocorrect fixes many typos.
- The model was **rebuilt locally** from the team's scripts (Python 3.13, scikit-learn 1.9.1). Every published metric reproduced exactly (0 differences), but the file is not byte-identical to theirs, which was built on Python 3.14.5.
- Not tested: the on-phone fallback `src/intake/extractRules.ts`, Swahili-specific typo patterns beyond vowel drops, ASR-style text, or whether fixes cost accuracy.
- Two misses that are **not** typos showed up: `headache and fatigue` drops `fatigue`, and `fever, vomiting and headache` drops `fever`. Not investigated.
- On Windows the team's scripts need two workarounds: `ml/src/evaluate.py` imports the Unix-only `resource` module, and with `core.autocrlf=true` the raw data, acceptance set and reference source fail their SHA-256 checks. A `.gitattributes` entry such as `ml/data/raw/* -text` would help.
