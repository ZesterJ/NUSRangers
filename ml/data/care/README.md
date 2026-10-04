# Structured care-service experimental dataset

Read [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md) before interpreting the labels.
This is **assistant-authored synthetic data for the team prototype**, not human- or
clinician-reviewed annotation. It encodes a proposed service-selection policy.

400 cases: 288 positive, 32 negative-by-input, 80 unknown/abstention. The 32 negative
cases also abstain; they do not establish that no care is necessary. Service counts
are generalOutpatient 288, childHealth 72, maternal 72 (overlapping labels).
Splits are 240 train, 80 validation, 80 test, grouped by 50 scenario families.
Unknown targets are excluded from supervised fitting: 184 training cases remain.

Record contract:

```text
id, scenarioFamily, scenarioKind, split, source
patient:
  patientType, symptoms, durationDays, hydrationIssue, reportedSigns
  reportedSignStates: {cannot_drink: {state}, convulsions: {state}, bleeding: {state}}
  subject: {status}
  abstentions: array of structured extractor reason codes
annotation:
  annotationStatus: positive | negative | unknown
  requiredServices: array of the three service labels
  serviceStates: per-label positive | not_indicated_by_input | unknown
  reason, guideVersion, reviewStatus
```

The patient is a structured projection of the extractor contract. No source text or
span evidence is generated. Missing symptom entries are not explicit negatives.
Body-location fields are unavailable upstream and deliberately excluded. Contradictory
sign projections are malformed-input robustness probes; ambiguous subject/type fields
and uncertain signs are separate from explicit negative states.

Run from the repository root, using the existing ML environment:

```bash
python ml/src/prepare_care_data.py
python ml/src/train_care_baseline.py
python -m pytest ml/tests/test_care_baseline.py -q
```

Dependencies: existing `ml/requirements.txt`. No network or APIs required. The generator
reads neither extraction evaluation datasets nor facility data. `manifest.json` locks
the resulting dataset bytes; train/validation/test are set before model fitting.
The annotation guide/policy was written before generation and training. Model fitting
uses only determinate training cases. Threshold selection uses validation only.

Outputs: `ml/reports/care_baseline_results.{json,md}` and ignored local
`ml/artifacts/experimental_care_service_v1.joblib`. The artifact contains a structured
feature pipeline, services, selected threshold, policy version, training IDs and data
hash. It is not compatible with the existing numeric `/predict` contract. Inference
requires the `care_policy` feature projection and abstention gate, not the serialized
logistic estimator alone. Scores are uncalibrated. This is an experimental training
checkpoint, not a released serving adapter.

Rules reuse the explicit annotation policy, so perfect rules scores are tautological.
ML is measured on reproducing that policy; high performance does not validate its
clinical assumptions. The test set is family-disjoint but from the same generator.
No claim of independent clinical evaluation, bilingual generalization, ASR resilience
or real extraction-error coverage is supported. Obtain those evaluations separately.

The model misses three generalOutpatient labels on the test split, including a case
where a maternal label is emitted without the general label required by the authored
hierarchy. This inconsistency is recorded, not repaired by tuning on test data. Prefer
the transparent rules for a reviewed policy demonstration; the classifier adds no
measured benefit here. Even that demo is not ready for clinical deployment.

Do not connect outputs to automatic facility recommendations: the 209 real facility
records still have no verified capabilities. Router filtering must continue to abstain.
