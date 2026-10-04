# Final health extraction tuning report

**Experimental synthetic-data benchmark and authored-case results. No clinical validity or deployment readiness is claimed.**

## Changes and rationale

- Retained the exact fitted character TF-IDF + balanced one-vs-rest logistic regression weights. No transformer, LLM, retraining, oversampling, training augmentation or new runtime dependency.
- Added a controlled, whole-token English/Swahili phrase table in `src/lexical_config.py`. It normalizes model input only; source text/evidence is never rewritten. Every added phrase has positive/negated regression coverage. No general fuzzy matching.
- Added bare Mtoto child references, explicit normal/reduced-drinking Swahili expressions, and sign variants. Fetal movement wording is excluded from the new bare-child rule; it does not establish child age.
- Split comma + only/just contrast clauses, fixing "No fever, only a cough" without opening uncertainty scope for "Maybe only a fever".
- Normalized tree only when followed by day(s); approximate/relative/conflicting durations remain unknown. No date anchoring or invented interval.
- Affirmed fields use the matched phrase span rather than whole-clause evidence. Negated/uncertain states retain context so their interpretation can be inspected.
- Added validation-only per-label thresholds; the bundle contains preprocessing, frozen classifiers, labels, thresholds, extraction/model versions, lexical/rule configuration, source hashes and parent artifact provenance.
- Preserved multi-subject abstention and explicit target selection. Unknown hydration remains null; reduced drinking is not cannot_drink.

## Data boundaries and selection

Derived split remains 805 train / 205 validation / 190 test, grouped into 31 scenario-family proxies. No vocabulary or classifier was refitted. Shared synthetic phrases remain; the test has positive support for only five symptom labels.
Thresholds were selected ONLY using the 205 derived validation records. Grid: 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40. Changed thresholds require >=98% validation precision and no increase in validation false positives, then maximize F1, preferring 0.30 on ties. All labels get this conservative gate.
Five labels have no positive validation examples and retain 0.30; three single-family rare labels are training-only. Small validation supports cannot justify further tuning of those labels.
48 new fictional acceptance cases were hash-frozen before candidate changes, training or evaluation. They cover English/Swahili/mixed language and were never read by tune_final.py. They serve only as a final accept/reject veto.
The acceptance set was authored by this assistant with requirements visible. It is NOT independently blinded, clinician reviewed, native-Swahili reviewed, or real-patient data. Existing 48/42 diagnostic sets remain development material.

Quality gate passed: **True**. No candidate was modified in response to acceptance results.

## Before vs after

| Dataset | Pipeline | Micro F1 | Supported macro F1 | All-13 macro* | Exact set | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| synthetic_validation | before | 0.9343 | 0.9291 | 0.5718 | 0.7317 | 0 | 55 |
| synthetic_validation | after | 1.0000 | 1.0000 | 0.6154 | 1.0000 | 0 | 0 |
| synthetic_test | before | 0.9532 | 0.9420 | 0.3623 | 0.8579 | 0 | 27 |
| synthetic_test | after | 0.9532 | 0.9408 | 0.3618 | 0.8579 | 0 | 27 |
| original_diagnostics | before | 0.8235 | 0.6029 | 0.3246 | 0.8542 | 0 | 12 |
| original_diagnostics | after | 0.9189 | 0.6519 | 0.3510 | 0.9167 | 0 | 6 |
| expanded_diagnostics | before | 0.9062 | 0.9431 | 0.3627 | 0.9048 | 0 | 6 |
| expanded_diagnostics | after | 0.9706 | 0.9846 | 0.3787 | 0.9524 | 0 | 2 |
| frozen_acceptance | before | 0.7222 | 0.7436 | 0.6864 | 0.6875 | 2 | 18 |
| frozen_acceptance | after | 0.9268 | 0.9365 | 0.8644 | 0.8958 | 0 | 6 |

*All-13 macro assigns zero to undefined F1; supported macro only includes labels with positive support. Perfect validation results reflect a small template-heavy tuning partition, not generalization.

## Per-label thresholds, support and validation changes

| Label | Train positives | Validation positives | Final threshold | Validation F1 at .3 | Selected F1 | Selected FP/FN |
|---|---:|---:|---:|---:|---:|---|
| abdominal_pain | 28 | 49 | 0.3 | 1.0000 | 1.0000 | 0/0 |
| bleeding | 38 | 0 | 0.3 | 0.0000 | 0.0000 | 0/0 |
| blurred_vision | 45 | 39 | 0.25 | 0.9167 | 1.0000 | 0/0 |
| breathing_difficulty | 90 | 0 | 0.3 | 0.0000 | 0.0000 | 0/0 |
| cough | 169 | 42 | 0.3 | 1.0000 | 1.0000 | 0/0 |
| diarrhoea | 124 | 39 | 0.15 | 0.9315 | 1.0000 | 0/0 |
| fatigue | 38 | 0 | 0.3 | 0.0000 | 0.0000 | 0/0 |
| fever | 263 | 127 | 0.3 | 1.0000 | 1.0000 | 0/0 |
| fluid_loss | 39 | 0 | 0.3 | 0.0000 | 0.0000 | 0/0 |
| headache | 79 | 39 | 0.3 | 1.0000 | 1.0000 | 0/0 |
| reduced_fetal_movement | 39 | 0 | 0.3 | 0.0000 | 0.0000 | 0/0 |
| vomiting | 34 | 75 | 0.1 | 0.7395 | 1.0000 | 0/0 |
| weakness | 78 | 36 | 0.3 | 1.0000 | 1.0000 | 0/0 |

Each threshold candidate’s precision, recall, F1, FP and FN is retained in final_threshold_analysis.json. No oversampling was performed.

## Per-label test and authored performance

### synthetic_test

| Label | Support | Before P/R/F1 | After P/R/F1 | Before FP/FN | After FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 42 | 1.000 / 0.690 / 0.817 | 1.000 / 0.690 / 0.817 | 0/13 | 0/13 |
| bleeding | 36 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| blurred_vision | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| breathing_difficulty | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| cough | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| diarrhoea | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fatigue | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fever | 79 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| fluid_loss | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| headache | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| reduced_fetal_movement | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| vomiting | 76 | 1.000 / 0.961 / 0.980 | 1.000 / 1.000 / 1.000 | 0/3 | 0/0 |
| weakness | 69 | 1.000 / 0.841 / 0.913 | 1.000 / 0.797 / 0.887 | 0/11 | 0/14 |
### original_diagnostics

| Label | Support | Before P/R/F1 | After P/R/F1 | Before FP/FN | After FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 1 | N/A / 0.000 / 0.000 | N/A / 0.000 / 0.000 | 0/1 | 0/1 |
| bleeding | 2 | 1.000 / 0.500 / 0.667 | 1.000 / 0.500 / 0.667 | 0/1 | 0/1 |
| blurred_vision | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| breathing_difficulty | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| cough | 15 | 1.000 / 0.667 / 0.800 | 1.000 / 0.867 / 0.929 | 0/5 | 0/2 |
| diarrhoea | 1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| fatigue | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fever | 16 | 1.000 / 0.812 / 0.897 | 1.000 / 0.938 / 0.968 | 0/3 | 0/1 |
| fluid_loss | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| headache | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| reduced_fetal_movement | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| vomiting | 4 | 1.000 / 0.750 / 0.857 | 1.000 / 1.000 / 1.000 | 0/1 | 0/0 |
| weakness | 1 | N/A / 0.000 / 0.000 | N/A / 0.000 / 0.000 | 0/1 | 0/1 |
### expanded_diagnostics

| Label | Support | Before P/R/F1 | After P/R/F1 | Before FP/FN | After FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| bleeding | 2 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| blurred_vision | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| breathing_difficulty | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| cough | 9 | 1.000 / 0.889 / 0.941 | 1.000 / 1.000 / 1.000 | 0/1 | 0/0 |
| diarrhoea | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fatigue | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fever | 14 | 1.000 / 0.714 / 0.833 | 1.000 / 0.857 / 0.923 | 0/4 | 0/2 |
| fluid_loss | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| headache | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| reduced_fetal_movement | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| vomiting | 9 | 1.000 / 0.889 / 0.941 | 1.000 / 1.000 / 1.000 | 0/1 | 0/0 |
| weakness | 1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
### frozen_acceptance

| Label | Support | Before P/R/F1 | After P/R/F1 | Before FP/FN | After FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 3 | 1.000 / 0.333 / 0.500 | 1.000 / 0.667 / 0.800 | 0/2 | 0/1 |
| bleeding | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| blurred_vision | 1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| breathing_difficulty | 2 | 1.000 / 0.500 / 0.667 | 1.000 / 1.000 / 1.000 | 0/1 | 0/0 |
| cough | 10 | 1.000 / 0.600 / 0.750 | 1.000 / 0.900 / 0.947 | 0/4 | 0/1 |
| diarrhoea | 2 | 1.000 / 0.500 / 0.667 | 1.000 / 1.000 / 1.000 | 0/1 | 0/0 |
| fatigue | 2 | N/A / 0.000 / 0.000 | 1.000 / 0.500 / 0.667 | 0/2 | 0/1 |
| fever | 10 | 0.833 / 0.500 / 0.625 | 1.000 / 0.700 / 0.824 | 1/5 | 0/3 |
| fluid_loss | 1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| headache | 3 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| reduced_fetal_movement | 1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| vomiting | 8 | 0.833 / 0.625 / 0.714 | 1.000 / 1.000 / 1.000 | 1/3 | 0/0 |
| weakness | 1 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |

## Language breakdown

| Dataset | Language | N | Before micro F1 | After micro F1 |
|---|---|---:|---:|---:|
| synthetic_validation | en | 133 | 0.9262 | 1.0000 |
| synthetic_validation | sw | 72 | 0.9492 | 1.0000 |
| synthetic_test | en | 131 | 0.9436 | 0.9436 |
| synthetic_test | sw | 59 | 0.9733 | 0.9733 |
| original_diagnostics | en | 33 | 0.7826 | 0.8800 |
| original_diagnostics | sw | 15 | 0.9091 | 1.0000 |
| expanded_diagnostics | en | 26 | 0.9189 | 0.9744 |
| expanded_diagnostics | mixed | 3 | 1.0000 | 1.0000 |
| expanded_diagnostics | sw | 13 | 0.8421 | 0.9524 |
| frozen_acceptance | en | 27 | 0.6667 | 0.9167 |
| frozen_acceptance | mixed | 3 | 0.5714 | 0.8889 |
| frozen_acceptance | sw | 18 | 0.8462 | 0.9600 |

## Unsupported assertions and conservative controls

These rates compare asserted symptoms/rule fields to authored expected values. They are not independent clinical verification.

| Dataset | Before unsupported / asserted | After unsupported / asserted |
|---|---|---|
| original_diagnostics | 0/67 (0.0%) | 0/73 (0.0%) |
| expanded_diagnostics | 0/58 (0.0%) | 0/62 (0.0%) |
| frozen_acceptance | 2/39 (5.1%) | 0/63 (0.0%) |

| Dataset | Field | Before agreement | After agreement | Before unknown accuracy | After unknown accuracy |
|---|---|---:|---:|---:|---:|
| original_diagnostics | patientType | 1.000 | 1.000 | 1.000 | 1.000 |
| original_diagnostics | durationDays | 1.000 | 1.000 | 1.000 | 1.000 |
| original_diagnostics | hydrationIssue | 1.000 | 1.000 | 1.000 | 1.000 |
| expanded_diagnostics | patientType | 1.000 | 1.000 | 1.000 | 1.000 |
| expanded_diagnostics | durationDays | 1.000 | 1.000 | 1.000 | 1.000 |
| expanded_diagnostics | hydrationIssue | 1.000 | 1.000 | 1.000 | 1.000 |
| frozen_acceptance | patientType | 0.771 | 1.000 | 1.000 | 1.000 |
| frozen_acceptance | durationDays | 0.979 | 1.000 | 1.000 | 1.000 |
| frozen_acceptance | hydrationIssue | 0.958 | 1.000 | 1.000 | 1.000 |

Negation and subject-category controls (correct symptom set / cases, with extra assertions):

| Dataset | Control | Before correct/N; extra | After correct/N; extra |
|---|---|---|---|
| original_diagnostics | negation | 6/7; 0 | 7/7; 0 |
| original_diagnostics | subjects | 0/2; 0 | 0/2; 0 |
| expanded_diagnostics | negation | 8/8; 0 | 8/8; 0 |
| expanded_diagnostics | subjects | 4/4; 0 | 4/4; 0 |
| frozen_acceptance | negation | 9/12; 0 | 12/12; 0 |
| frozen_acceptance | subjects | 1/2; 2 | 2/2; 0 |

Older original diagnostics expect document-level symptoms from multiple people; safe abstention still counts as false negatives there. Their labels were not changed.

## Remaining errors and regressions

Synthetic micro-F1 and exact set are unchanged. Supported macro-F1 falls slightly from 0.9420 to 0.9408: three vomiting misses are recovered but three weakness predictions are lost when controlled normalization changes the shared text representation. This per-label trade-off is retained explicitly; authored metrics improve and unsupported positives do not increase.
No further threshold adjustment was made after looking at test/acceptance. Strong evidence below an unchanged threshold still abstains. No keyword-only rescue was added.

- Remaining symptom FN reasons in synthetic_validation: {}. A miss may have multiple reasons.
- Remaining symptom FN reasons in synthetic_test: {'below_threshold': 27}. A miss may have multiple reasons.
- Remaining symptom FN reasons in original_diagnostics: {'unresolved_subject_or_empty_input': 4, 'not_mentioned': 4, 'below_threshold': 2}. A miss may have multiple reasons.
- Remaining symptom FN reasons in expanded_diagnostics: {'below_threshold': 2}. A miss may have multiple reasons.
- Remaining symptom FN reasons in frozen_acceptance: {'below_threshold': 6}. A miss may have multiple reasons.

Representative remaining failures:

- synthetic_test / health_ie_0029: 'This has been going on for three days. My belly hurts.'; expected ['abdominal_pain'], after []; reasons `{'abdominal_pain': {'score': 0.09295493916609412, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- synthetic_test / health_ie_0084: 'I feel tired and weak. They are not drinking well. I am vomiting. This has been going on for two days.'; expected ['vomiting', 'weakness'], after ['vomiting']; reasons `{'weakness': {'score': 0.2819242054358429, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- original_diagnostics / diagnostic_017: 'I have a fever and my child is coughing.'; expected ['fever', 'cough'], after []; reasons `{'fever': {'score': 0.6739572046603557, 'threshold': 0.3, 'accepted': False, 'state': 'not_mentioned', 'reasons': ['unresolved_subject_or_empty_input', 'not_mentioned']}, 'cough': {'score': 0.8993008352536784, 'threshold': 0.3, 'accepted': False, 'state': 'not_mentioned', 'reasons': ['unresolved_subject_or_empty_input', 'not_mentioned']}}`.
- original_diagnostics / diagnostic_018: 'My mother is bleeding and I feel weak.'; expected ['bleeding', 'weakness'], after []; reasons `{'bleeding': {'score': 0.8585192559850447, 'threshold': 0.3, 'accepted': False, 'state': 'not_mentioned', 'reasons': ['unresolved_subject_or_empty_input', 'not_mentioned']}, 'weakness': {'score': 0.6456707873426908, 'threshold': 0.3, 'accepted': False, 'state': 'not_mentioned', 'reasons': ['unresolved_subject_or_empty_input', 'not_mentioned']}}`.
- original_diagnostics / diagnostic_025: 'My belly aches and I keep throwing up.'; expected ['abdominal_pain', 'vomiting'], after ['vomiting']; reasons `{'abdominal_pain': {'score': 0.13741977348281745, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- original_diagnostics / diagnostic_026: 'I have fever, cough and diarrhoea.'; expected ['fever', 'cough', 'diarrhoea'], after ['diarrhoea', 'fever']; reasons `{'cough': {'score': 0.24340163090734412, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- frozen_acceptance / acceptance_v1_033: 'Fever, cough, headache and vomiting.'; expected ['fever', 'cough', 'headache', 'vomiting'], after ['headache', 'vomiting']; reasons `{'fever': {'score': 0.13331444631355885, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}, 'cough': {'score': 0.2799338416174629, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- frozen_acceptance / acceptance_v1_034: 'Nina homa, maumivu ya kichwa na ninatapika.'; expected ['fever', 'headache', 'vomiting'], after ['headache', 'vomiting']; reasons `{'fever': {'score': 0.11373919142476879, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- frozen_acceptance / acceptance_v1_035: 'Homa and vomiting.'; expected ['fever', 'vomiting'], after ['vomiting']; reasons `{'fever': {'score': 0.2636420480272762, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- frozen_acceptance / acceptance_v1_036: 'Loose stools and my stomach hurts.'; expected ['diarrhoea', 'abdominal_pain'], after ['diarrhoea']; reasons `{'abdominal_pain': {'score': 0.16502441363166234, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.
- frozen_acceptance / acceptance_v1_041: 'I feel exhausted.'; expected ['fatigue'], after []; reasons `{'fatigue': {'score': 0.2778508601676195, 'threshold': 0.3, 'accepted': False, 'state': 'affirmed', 'reasons': ['below_threshold']}}`.

## Artifact and latency

Final experimental bundle: `ml/artifacts/experimental_health_ie_final.joblib` — **97,783 bytes**, SHA-256 `c03967d0927d686eaddb09e8380994ec5eccd45a423bba94d31d8f0eb64c8e94`. Ignored by Git; no artifact committed.
Separate metadata JSON records versions/configuration and the gate report. The original experimental_symptom_baseline.joblib is untouched. The v2 reference source is retained under src/reference solely for reproducible comparisons.
Manual CLI now loads the final bundle and reads its per-label thresholds through the shared wrapper; default extraction-only and --verbose formats are preserved.
Warm single-request CPU timing, 1,000 calls per operation, one numerical-library thread on the same macOS arm64 environment; no HTTP/ASR overhead:

| Operation | p50 ms | p95 ms |
|---|---:|---:|
| before_rules | 0.058 | 0.122 |
| after_rules | 0.061 | 0.125 |
| before_full | 0.754 | 0.899 |
| after_full | 0.770 | 0.930 |

## Integration recommendation

**Ready for a supervised hackathon integration experiment, not clinical deployment.** Preserve human verification, null semantics, exact evidence, explicit subject selection and visible uncertain/omitted fields.
The current /predict backend still expects numeric features and scalar output; do not point its old joblib adapter directly at this text bundle. A separate contract/adapter integration is required. No backend, frontend, speech, diagnosis or clinic-routing code was changed here.
Remaining limitations: template leakage, five-label positive test coverage, no positive validation support for several rare labels, uncalibrated classifier scores, brittle clause/coreference heuristics, incomplete lexical/ASR coverage and no independent native-Swahili/clinical acceptance review.
Next: integrate only the verified artifact/config into a draft-review workflow, obtain native-language review, and collect an independent acceptance suite before further tuning. Keep unresolved/multiple-patient text out of automatic form assignment.

## Verification run

161 Python tests passed (backend + ML), including a regression for every lexical addition, final-bundle provenance, per-label threshold loading, original-source evidence and CLI presentation. Historical baseline/v2 evaluations were rerun; raw SHA-256 verification and git diff --check passed. Single-input and interactive default/verbose manual checks passed. Frontend lint/typecheck/pack checks were attempted but eslint, tsc and tsx are not installed; no frontend files changed.

## Reproduction

```sh
python ml/src/tune_final.py
python ml/src/evaluate_final_tuning.py
python ml/src/report_final_tuning.py
python -m pytest ml/tests -q
python ml/src/predict_text.py "Mtoto ana homa kwa siku tatu na anatapika."
python ml/src/predict_text.py --interactive
```
Use the pinned ML environment. Evaluation only publishes the final bundle if its gate passes. Do not change/tune against frozen acceptance examples on later runs.
