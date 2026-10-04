# Patient-text information extraction workspace

Status: first experimental rules and learned symptom baselines implemented and evaluated,
2026-10-04. No production model decision or backend/frontend integration.
Scope: raw patient text → proposed structured fields → human verification.
Speech recognition, diagnosis, triage decisions and facility routing are outside this workspace's remit.

## Layout

```text
ml/
  data/
    raw/          # unchanged supplied CSV + JSONL and SHA-256 manifest
    processed/    # generated grouped split manifest; ignored
    evaluation/   # protocol + authored DEVELOPMENT diagnostics, not acceptance data
  src/            # audit, grouped split, rules, training and evaluation code
  artifacts/      # experimental exports and metadata; ignored
  reports/        # small reviewable audit output and recommendations
```

Both root dataset files were moved into `data/raw/` without changing their bytes.
They are equivalent exports of the SAME 1,200 examples, not separate datasets.
Prefer JSONL as the future training reader; retain CSV for inspection. No dataset
README, data dictionary, generator, license, or separate metadata file was found
among the supplied root files. `HACKATHON.md` is project context and stays in place.
The raw record metadata declares `synthetic_team_generated` throughout; generator,
authorship details and redistribution rights have not independently been verified.
The manifest records original paths, sizes and hashes. No real-patient origin is claimed.

Run the standard-library audit from the repository root:

```sh
python3 ml/src/analyze_data.py
```

The script verifies hashes, compares every CSV and JSONL record, and regenerates
`reports/data_audit.json`. It makes no training changes and does not alter raw files.
The compact audit report is tracked deliberately; bulk processed data, evaluation
records and model binaries are ignored. Raw files are small (~0.7 MB combined),
retained for reproducibility; confirm provenance/license before redistributing.
Do not place identifiable patient information in Git.

Read [the analysis and proposal](reports/analysis.md) before implementing a model,
and [the evaluation protocol](data/evaluation/README.md) before authoring evaluation data.
The existing `/predict` contract still accepts numeric vectors and scalar results;
the proposed text/structured schema is not yet implemented.

## Reproduce the first baseline

Use a separate environment; no backend dependency or application changes are needed.
The exact tested environment was Python 3.14.5 on macOS arm64; package versions are
pinned in `requirements.txt`. Artifact portability to other runtimes is not guaranteed.

```sh
python3 -m venv ml/.venv
ml/.venv/bin/python -m pip install -r ml/requirements.txt
ml/.venv/bin/python ml/src/analyze_data.py
ml/.venv/bin/python ml/src/train_symptom_model.py
ml/.venv/bin/python ml/src/evaluate.py
ml/.venv/bin/python -m pytest ml/tests -q
```

Training regenerates the deterministic grouped split and compares 12 configurations:
word TF-IDF (1–2 grams), character-within-word TF-IDF (3–5 grams), or their union;
C=1/4; class weighting none/balanced. Other explicit preprocessing: lowercase,
L2-normalized TF-IDF, sublinear TF, min_df=1, no stopword removal, default Unicode
word tokenization, at most 12,000 word/20,000 character features. Each of 13 symptom
labels has a liblinear logistic regression head (max_iter=2000, seed=42).
A single threshold from 0.3/0.5/0.7 is selected using validation supported-label macro
F1, then micro F1; threshold ties prefer 0.5 and configuration ties retain grid order.
Models are never refit on validation/test. The best validation configuration alone
is evaluated on the derived test and authored diagnostics. Fitting uses only derived
training text, never IDs, language tags, family labels, duration, or other metadata.

The grouping proxy combines patient type, symptom set, sign set, hydration flag and
notes, excluding duration/language. It groups paraphrases and both languages within
31 broad scenarios. An initial 60/20/20 family shuffle with seed 42 reserves three
single-family labels for training to make all labels learnable: resulting rows are
805/205/190 across 21/5/5 families. Those rare labels have no positive held-out support.
Original splits stay in the raw files and `data/processed/baseline_split_manifest.json`.
The script asserts exact-text and sentence-order duplicate isolation. These groups
are proxies, not known generator IDs; shared phrases across scenarios remain.
There is no claim that all synthetic-template dependence has been eliminated.

Training verifies vocabulary and IDF against a fresh train-only preprocessing fit,
then independently refits the selected classifier and checks identical probabilities.
An additional full training rerun verified identical configuration, validation metrics,
and prediction fingerprints in the tested environment. Timing may vary between runs.

Read [baseline results](reports/baseline_results.md) and [error analysis](reports/error_analysis.md).
Complete metrics/configurations are in `reports/baseline_results.json` and
`reports/training_results.json`. `baseline_errors.json` preserves all inspected
mismatches. Reports are small text/JSON diagnostics tracked intentionally; the model
and derived manifests remain ignored. No raw labels were corrected or overwritten.

`data/evaluation/baseline_diagnostics.json` contains 48 assistant-authored fictional
DEVELOPMENT examples with explicit expectations. They are not independently authored,
clinician-reviewed, native-Swahili-reviewed, or clinical ground truth. Rules were
regression-corrected after inspecting them; the change and initial metrics are in
`reports/rule_revision_log.json`. Do not present post-fix scores as fresh acceptance
results. The independent evaluation protocol remains future work.

The symptom artifact is `artifacts/experimental_symptom_baseline.joblib`, accompanied
by configuration, versions, training IDs/hash, threshold, labels and size metadata.
It contains a text pipeline, not the numeric pipeline expected by the current backend.
For trusted local experiments only:

```python
import joblib
bundle = joblib.load("ml/artifacts/experimental_symptom_baseline.joblib")
probabilities = bundle["pipeline"].predict_proba(["My child has a fever"])[0]
candidates = [label for label, score in zip(bundle["labels"], probabilities)
              if score >= bundle["threshold"]]
```

These are unverified classifier candidates; it has no explicit negation, uncertainty
or subject resolution. Do not feed its outputs directly into triage. Only deserialize
trusted joblib files. No FastAPI, `/predict`, Expo, speech, diagnosis or routing code
was modified.

Implementation references: [TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html),
[one-vs-rest](https://scikit-learn.org/stable/modules/generated/sklearn.multiclass.OneVsRestClassifier.html),
[logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).

## Evidence-gated improvement (frozen classifier)

`src/extraction_pipeline.py` wraps the existing character TF-IDF + balanced logistic
regression artifact. It does not fit or replace a model. `baseline_rules.py` remains
unchanged as the reproducible OLD implementation; the new module exposes both
`extract_rules()` and `ExtractionPipeline.extract()`.

```sh
ml/.venv/bin/python ml/src/evaluate.py
ml/.venv/bin/python ml/src/evaluate_improvements.py
ml/.venv/bin/python -m pytest ml/tests -q
```

The paired evaluation reproduces the original metrics, verifies the artifact hash,
and compares the original validation/test split, unchanged 48 diagnostics and 42 new
fictional diagnostics. Reports: [comparison](reports/improvement_results.md) and
[error analysis](reports/improvement_error_analysis.md). Full metrics include every
label, language, scalar confusion matrix, report-sign errors, assertion counts and
same-process CPU timings. Generated predictions go to ignored `data/processed/`.
The new cases never enter training, vocabulary fitting or threshold selection.

```python
import sys
import joblib
sys.path.insert(0, "ml/src")
from extraction_pipeline import Config, ExtractionPipeline
bundle = joblib.load("ml/artifacts/experimental_symptom_baseline.joblib")
extractor = ExtractionPipeline(bundle, Config(threshold=0.3))
result = extractor.extract("My husband has fever but I feel fine.",
                           target_subject="husband")
```

Output includes `patientType`, `durationDays`, `hydrationIssue`, `reportedSigns`,
`symptoms`, `subject`, `evidence`, `reportedSignStates`, `durationMentions`, and
`symptomDecisions`, plus source/version/verification metadata. Every asserted clinical
field has a supporting exact substring with Python Unicode code-point start/end
offsets (end exclusive). These are not JavaScript UTF-16 offsets. Classifier scores
are uncalibrated model scores, not clinical confidence. Each symptom must pass BOTH
the configurable threshold and an affirmed literal-mention/subject check. Rejected
candidates retain reasons in `symptomDecisions`; no keyword-only positive rescue is
used. Confidence thresholds were not retuned against this evaluation.

Unknown hydration remains null. False requires explicit normal drinking/denial of
difficulty. Reduced drinking is not inability to drink. Report signs expose four
states: affirmed, negated, uncertain, not_mentioned; only affirmed signs populate the
positive array. Historical, conflicting or unresolved-subject mentions abstain.

Subject scope defaults to abstention when multiple explicit people are present.
Supported explicit targets are speaker, child, husband, wife, mother, father, sister,
brother. In multi-person text, only clauses explicitly naming the target are used;
pronoun/coreference resolution is not guessed. Subject-free short statements retain
an unspecified subject rather than silently being assigned to the speaker.

Exact explicit day counts can populate durationDays. Approximate expressions,
relative yesterday/weekday onsets and conflicting durations remain null with the
source retained in durationMentions. There is no reference timestamp or elapsed-day
convention, so “since Monday” is not converted into an invented interval. Negation
in a later hydration clause no longer erases an earlier explicit duration.

The phrase lexicon and clause rules are deliberately inspectable but incomplete.
Negation lists, reported speech, complex temporal scope, misspellings and ASR errors
can cause errors. Conservative evidence filtering can lose correct classifier
predictions. A native Swahili reviewer and independently authored acceptance set are
still needed. No diagnosis/urgency/treatment/referral fields are emitted, and no
backend, /predict, frontend or speech implementation was changed.

Development note: after inspecting the expanded case “The child may have had a
seizure”, subject extraction was scoped to uncertainty BEFORE the subject, rather
than uncertainty about a later symptom. A regression test records this correction;
no expected label changed. These suites remain development data, not fresh validation.
