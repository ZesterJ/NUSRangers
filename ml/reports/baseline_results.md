# First baseline: synthetic-data benchmark results

Experimental only. No clinical validity, real-world performance or deployment readiness is claimed.
Model selection used validation only. No production model decision has been made.

## Split and leakage controls

Derived rows: {'train': 805, 'validation': 205, 'test': 190}; families: {'train': 21, 'validation': 5, 'test': 5}.
Family = patient type + symptom set + danger-sign set + hydration + notes; excludes duration/language.
31 annotation-based scenario proxies; no recovered generator IDs. No family/exact-text/sentence-bag overlap.
Labels are grouping metadata, never features. Only derived-training text fits vocabulary, IDF and classifiers.
Original split labels remain in the ignored derived manifest. This is a new partition, not the original train split.
Single-family fatigue, fluid_loss, reduced_fetal_movement were reserved for training before fitting.
Test has positive support for only five labels; this benchmark cannot establish generalization for all 13.
Residual held-out sentence-fragment overlap: {'validation': 0.6923076923076923, 'test': 0.6764705882352942}.
Shared phrase leakage remains; results measure held-out scenario recombination, not unseen natural language.

## Configuration comparison (validation only)

| Features | C | Class weight | Threshold | Supported macro F1 | Micro F1 |
|---|---:|---|---:|---:|---:|
| word | 1.0 | None | 0.3 | 0.4241 | 0.6142 |
| word | 1.0 | balanced | 0.3 | 0.8078 | 0.8343 |
| word | 4.0 | None | 0.3 | 0.4902 | 0.6510 |
| word | 4.0 | balanced | 0.3 | 0.7940 | 0.8237 |
| char | 1.0 | None | 0.3 | 0.5441 | 0.6824 |
| char | 1.0 | balanced | 0.3 | 0.8626 | 0.8565 |
| char | 4.0 | None | 0.3 | 0.6474 | 0.7542 |
| char | 4.0 | balanced | 0.3 | 0.8611 | 0.8732 |
| combined | 1.0 | None | 0.3 | 0.5376 | 0.6939 |
| combined | 1.0 | balanced | 0.3 | 0.8431 | 0.8631 |
| combined | 4.0 | None | 0.3 | 0.5901 | 0.7255 |
| combined | 4.0 | balanced | 0.3 | 0.8453 | 0.8667 |

Selected experimental configuration: `{'features': 'char', 'C': 1.0, 'class_weight': 'balanced'}`, global threshold 0.3.
Selection maximizes validation supported-label macro F1, then micro F1. Tie retains the first configuration.

## Symptom results

| Set | N | Micro P | Micro R | Micro F1 | Supported macro F1 | Exact set |
|---|---:|---:|---:|---:|---:|---:|
| derived test | 190 | 0.7576 | 0.9106 | 0.8271 | 0.8937 | 0.5579 |
| authored diagnostics | 48 | 0.5312 | 0.8500 | 0.6538 | 0.5341 | 0.3958 |

Diagnostics are assistant-authored development cases, not blinded, independently authored or clinician/native-Swahili reviewed.
They were not used for vectorizer fitting, training, threshold selection or configuration selection.

### Derived-test per-label metrics

| Label | Support | Precision | Recall | F1 | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| abdominal_pain | 42 | 1.0000 | 0.6905 | 0.8169 | 0 | 13 |
| bleeding | 36 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |
| blurred_vision | 0 | N/A | N/A | N/A | 0 | 0 |
| breathing_difficulty | 0 | N/A | N/A | N/A | 0 | 0 |
| cough | 0 | N/A | N/A | N/A | 0 | 0 |
| diarrhoea | 0 | 0.0000 | N/A | 0.0000 | 30 | 0 |
| fatigue | 0 | N/A | N/A | N/A | 0 | 0 |
| fever | 79 | 0.6475 | 1.0000 | 0.7861 | 43 | 0 |
| fluid_loss | 0 | N/A | N/A | N/A | 0 | 0 |
| headache | 0 | 0.0000 | N/A | 0.0000 | 11 | 0 |
| reduced_fetal_movement | 0 | N/A | N/A | N/A | 0 | 0 |
| vomiting | 76 | 1.0000 | 0.9605 | 0.9799 | 0 | 3 |
| weakness | 69 | 0.9355 | 0.8406 | 0.8855 | 4 | 11 |

No-support recall is N/A; a false-positive-only label still gets F1=0. JSON also reports all-13 macro F1 with undefined values set to zero.

### Language breakdown

| Set | Language | N | Micro F1 | Supported macro F1 | Exact set |
|---|---|---:|---:|---:|---:|
| symptoms_test | en | 131 | 0.8307 | 0.8838 | 0.6336 |
| symptoms_test | sw | 59 | 0.8198 | 0.9088 | 0.3898 |
| symptoms_diagnostics | en | 33 | 0.6479 | 0.5317 | 0.3939 |
| symptoms_diagnostics | sw | 15 | 0.6667 | 0.8415 | 0.4000 |

## Rules

Raw-label agreement is not factual extraction accuracy: supplied adult/hydration/duration labels have known problems.
Unsupported-assertion metrics are only computed against explicit diagnostic expectations; raw labels cannot establish grounding.

| Field | Raw test agreement | Diagnostic accuracy | Unknown expected | Unknown accuracy | Unsupported/asserted |
|---|---:|---:|---:|---:|---|
| patientType | 0.2211 | 1.0000 | 28 | 1.0000 | 0/20 |
| durationDays | 0.6789 | 0.9792 | 44 | 1.0000 | 0/3 |
| hydrationIssue | 0.4000 | 1.0000 | 38 | 1.0000 | 0/10 |

Reported-sign diagnostic metrics:

| Sign | Support | P | R | F1 | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| cannot_drink | 3 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |
| convulsions | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |
| bleeding | 1 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |

All diagnostic rule-field assertions: {'count': 38, 'unsupported': 0, 'rate': 0.0}.
Full scalar confusion matrices, sign FP/FN counts, and original-label disagreements are in JSON.

## Size, speed and reproducibility

Compressed artifact: 94,552 bytes. Classifier coefficients + intercepts: 29,406.
Serialized preprocessing: 77,668 bytes; vocabulary/IDF details: `{'single': {'vocabulary_entries': 2261, 'idf_bytes': 18088}}`.
Rules source: 6552 bytes; no fitted parameters.
First artifact deserialization in evaluation process: 40.819 ms (OS cache state uncontrolled; not cold-machine startup).
Warm batch-size-one CPU benchmark, 1,000 iterations each, one numerical-library thread:

```json
{
  "hardware": "arm64",
  "platform": "macOS-27.0-arm64-arm-64bit-Mach-O",
  "python": "3.14.5",
  "threads": 1,
  "batch_size": 1,
  "iterations": 1000,
  "scope": "local Python preprocessing+inference; no HTTP, ASR or application overhead; not a production benchmark",
  "rules": {
    "p50_ms": 0.062313,
    "p95_ms": 0.1204601
  },
  "symptom_pipeline": {
    "p50_ms": 0.626771,
    "p95_ms": 0.7166475999999999
  },
  "process_peak_rss_bytes": 134250496,
  "rss_scope": "whole evaluation process including imports and metrics; not incremental model RAM"
}
```

Reproducibility checks: `{'selected_refit_probabilities_identical': True, 'prediction_sha256': '4a537bf8c9e5d344cf26d515e870497d319c2932e9dd0d9dc27070c4e07a036d', 'train_only_vocabulary_and_idf_verified': True}`.
Exact software versions and training configuration are in training_results.json and artifact metadata.
Numbers vary by hardware/cache/load; latency is not expected to reproduce bit-for-bit.

## Recommendation

Do not choose a production model or move directly to a transformer. First obtain reviewed unknown/negation/subject annotations and independently authored bilingual evaluation.
The linear baseline is a useful measurable reference; its shortcomings on natural-style diagnostics must not be disguised by synthetic scores.
A small multilingual encoder is only a justified next comparison if reviewed errors establish a semantic gap beyond data/label/scope defects.
No backend, /predict, frontend, speech, diagnosis or routing changes were made.
