# Evidence-gated pipeline: OLD vs NEW

synthetic-data benchmark results; authored cases are development diagnostics, not clinical validation

The character TF-IDF + balanced logistic regression artifact and 0.3 threshold are unchanged. No retraining or threshold search.
Only predictions with an affirmed exact mention, resolved/unambiguous subject scope and sufficient classifier score are returned.
Classifier scores are uncalibrated, not clinical confidence. No keyword-only rescue is used, so recall can decrease.

## Paired symptom results

| Dataset | Pipeline | Micro F1 | Supported macro F1 | All-13 macro F1* | Exact set | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| synthetic_validation | old | 0.8565 | 0.8626 | 0.5308 | 0.5610 | 76 | 55 |
| synthetic_validation | new | 0.9343 | 0.9291 | 0.5718 | 0.7317 | 0 | 55 |
| synthetic_test | old | 0.8271 | 0.8937 | 0.3437 | 0.5579 | 88 | 27 |
| synthetic_test | new | 0.9532 | 0.9420 | 0.3623 | 0.8579 | 0 | 27 |
| original_diagnostics | old | 0.6538 | 0.5341 | 0.2876 | 0.3958 | 30 | 6 |
| original_diagnostics | new | 0.8235 | 0.6029 | 0.3246 | 0.8542 | 0 | 12 |
| expanded_diagnostics | old | 0.6598 | 0.7101 | 0.2731 | 0.3810 | 30 | 3 |
| expanded_diagnostics | new | 0.9062 | 0.9431 | 0.3627 | 0.9048 | 0 | 6 |

*All-13 macro assigns zero to undefined scores. The synthetic test has positive support for five labels only.
Original 48 diagnostics retain their original document-level symptom labels for multiple-person cases. New subject abstention can therefore count as a false negative; these labels were not silently rewritten.
The expanded 42 cases explicitly expect abstention for unresolved multiple people and test one explicit husband target. Keep the suites separate.
All authored cases are assistant-authored development material, not blinded or clinician/native-Swahili reviewed. No training code consumes them.

## Per-label precision / recall / F1

### synthetic_validation

| Label | Support | OLD P/R/F1 | NEW P/R/F1 | OLD FP/FN | NEW FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 49 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| bleeding | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| blurred_vision | 39 | 0.767 / 0.846 / 0.805 | 1.000 / 0.846 / 0.917 | 10/6 | 0/6 |
| breathing_difficulty | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| cough | 42 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| diarrhoea | 39 | 0.500 / 0.872 / 0.636 | 1.000 / 0.872 / 0.932 | 34/5 | 0/5 |
| fatigue | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 20/0 | 0/0 |
| fever | 127 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| fluid_loss | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| headache | 39 | 0.796 / 1.000 / 0.886 | 1.000 / 1.000 / 1.000 | 10/0 | 0/0 |
| reduced_fetal_movement | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| vomiting | 75 | 0.939 / 0.413 / 0.574 | 1.000 / 0.413 / 0.585 | 2/44 | 0/44 |
| weakness | 36 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
### synthetic_test

| Label | Support | OLD P/R/F1 | NEW P/R/F1 | OLD FP/FN | NEW FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 42 | 1.000 / 0.690 / 0.817 | 1.000 / 0.690 / 0.817 | 0/13 | 0/13 |
| bleeding | 36 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | 0/0 | 0/0 |
| blurred_vision | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| breathing_difficulty | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| cough | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| diarrhoea | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 30/0 | 0/0 |
| fatigue | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fever | 79 | 0.648 / 1.000 / 0.786 | 1.000 / 1.000 / 1.000 | 43/0 | 0/0 |
| fluid_loss | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| headache | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 11/0 | 0/0 |
| reduced_fetal_movement | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| vomiting | 76 | 1.000 / 0.961 / 0.980 | 1.000 / 0.961 / 0.980 | 0/3 | 0/3 |
| weakness | 69 | 0.935 / 0.841 / 0.885 | 1.000 / 0.841 / 0.913 | 4/11 | 0/11 |
### original_diagnostics

| Label | Support | OLD P/R/F1 | NEW P/R/F1 | OLD FP/FN | NEW FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 1 | N/A / 0.000 / 0.000 | N/A / 0.000 / 0.000 | 0/1 | 0/1 |
| bleeding | 2 | 0.333 / 1.000 / 0.500 | 1.000 / 0.500 / 0.667 | 4/0 | 0/1 |
| blurred_vision | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| breathing_difficulty | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 2/0 | 0/0 |
| cough | 15 | 0.867 / 0.867 / 0.867 | 1.000 / 0.667 / 0.800 | 2/2 | 0/5 |
| diarrhoea | 1 | 0.100 / 1.000 / 0.182 | 1.000 / 1.000 / 1.000 | 9/0 | 0/0 |
| fatigue | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fever | 16 | 0.538 / 0.875 / 0.667 | 1.000 / 0.812 / 0.897 | 12/2 | 0/3 |
| fluid_loss | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| headache | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| reduced_fetal_movement | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| vomiting | 4 | 1.000 / 0.750 / 0.857 | 1.000 / 0.750 / 0.857 | 0/1 | 0/1 |
| weakness | 1 | 0.500 / 1.000 / 0.667 | N/A / 0.000 / 0.000 | 1/0 | 0/1 |
### expanded_diagnostics

| Label | Support | OLD P/R/F1 | NEW P/R/F1 | OLD FP/FN | NEW FP/FN |
|---|---:|---|---|---|---|
| abdominal_pain | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| bleeding | 2 | 0.500 / 1.000 / 0.667 | 1.000 / 1.000 / 1.000 | 2/0 | 0/0 |
| blurred_vision | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 1/0 | 0/0 |
| breathing_difficulty | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| cough | 9 | 0.900 / 1.000 / 0.947 | 1.000 / 0.889 / 0.941 | 1/0 | 0/1 |
| diarrhoea | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 3/0 | 0/0 |
| fatigue | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| fever | 14 | 0.407 / 0.786 / 0.537 | 1.000 / 0.714 / 0.833 | 16/3 | 0/4 |
| fluid_loss | 0 | N/A / N/A / N/A | N/A / N/A / N/A | 0/0 | 0/0 |
| headache | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 2/0 | 0/0 |
| reduced_fetal_movement | 0 | 0.000 / N/A / 0.000 | N/A / N/A / N/A | 1/0 | 0/0 |
| vomiting | 9 | 0.818 / 1.000 / 0.900 | 1.000 / 0.889 / 0.941 | 2/0 | 0/1 |
| weakness | 1 | 0.333 / 1.000 / 0.500 | 1.000 / 1.000 / 1.000 | 2/0 | 0/0 |

## Language breakdown

| Dataset | Language | N | OLD micro F1 | NEW micro F1 | OLD exact | NEW exact |
|---|---|---:|---:|---:|---:|---:|
| synthetic_validation | en | 133 | 0.8581 | 0.9262 | 0.5338 | 0.6992 |
| synthetic_validation | sw | 72 | 0.8537 | 0.9492 | 0.6111 | 0.7917 |
| synthetic_test | en | 131 | 0.8307 | 0.9436 | 0.6336 | 0.8321 |
| synthetic_test | sw | 59 | 0.8198 | 0.9733 | 0.3898 | 0.9153 |
| original_diagnostics | en | 33 | 0.6479 | 0.7826 | 0.3939 | 0.8182 |
| original_diagnostics | sw | 15 | 0.6667 | 0.9091 | 0.4000 | 0.9333 |
| expanded_diagnostics | en | 26 | 0.6552 | 0.9189 | 0.4615 | 0.9231 |
| expanded_diagnostics | mixed | 3 | 0.8000 | 1.0000 | 0.3333 | 1.0000 |
| expanded_diagnostics | sw | 13 | 0.6207 | 0.8421 | 0.2308 | 0.8462 |

## Rule fields and unsupported assertions

Raw synthetic rule-label agreement is not factual accuracy: first-person adult, hydration false and timing labels remain problematic.
Unsupported counts below compare to authored expectations, not an independently verified grounding oracle.

| Dataset | Field | OLD agreement | NEW agreement | OLD unknown accuracy | NEW unknown accuracy |
|---|---|---:|---:|---:|---:|
| synthetic_validation | patientType | 0.4146 | 0.4146 | N/A | N/A |
| synthetic_validation | durationDays | 0.5122 | 0.6195 | N/A | N/A |
| synthetic_validation | hydrationIssue | 0.3659 | 0.3659 | N/A | N/A |
| synthetic_test | patientType | 0.2211 | 0.2211 | N/A | N/A |
| synthetic_test | durationDays | 0.6789 | 0.8211 | N/A | N/A |
| synthetic_test | hydrationIssue | 0.4000 | 0.4000 | N/A | N/A |
| original_diagnostics | patientType | 1.0000 | 1.0000 | 1.000 | 1.000 |
| original_diagnostics | durationDays | 0.9792 | 1.0000 | 1.000 | 1.000 |
| original_diagnostics | hydrationIssue | 1.0000 | 1.0000 | 1.000 | 1.000 |

original_diagnostics: all asserted fields including symptoms — OLD `{'count': 102, 'unsupported': 30, 'rate': 0.29411764705882354}`; NEW `{'count': 67, 'unsupported': 0, 'rate': 0.0}`.

| expanded_diagnostics | patientType | 0.9762 | 1.0000 | 1.000 | 1.000 |
| expanded_diagnostics | durationDays | 0.9048 | 1.0000 | 1.000 | 1.000 |
| expanded_diagnostics | hydrationIssue | 1.0000 | 1.0000 | 1.000 | 1.000 |

expanded_diagnostics: all asserted fields including symptoms — OLD `{'count': 86, 'unsupported': 30, 'rate': 0.3488372093023256}`; NEW `{'count': 58, 'unsupported': 0, 'rate': 0.0}`.


Report signs: exact statuses are `affirmed`, `negated`, `uncertain`, `not_mentioned`. Only affirmed signs populate reportedSigns. Historical/conflicting/subject-ambiguous mentions are uncertain.
Full per-sign precision/recall/F1, scalar confusion matrices and literal-evidence counts are in improvement_results.json.

## Latency (same-process paired benchmark)

```json
{
  "hardware": "arm64",
  "platform": "macOS-27.0-arm64-arm-64bit-Mach-O",
  "threads": 1,
  "batch_size": 1,
  "iterations": 1000,
  "scope": "warm local CPU; no network/HTTP; same corpus/order for each operation",
  "old_rules": {
    "p50_ms": 0.060812,
    "p95_ms": 0.11616815
  },
  "new_rules": {
    "p50_ms": 0.059187000000000003,
    "p95_ms": 0.1217101
  },
  "frozen_ml": {
    "p50_ms": 0.6162084999999999,
    "p95_ms": 0.66316665
  },
  "old_full": {
    "p50_ms": 0.689854,
    "p95_ms": 0.77898925
  },
  "new_full": {
    "p50_ms": 0.760458,
    "p95_ms": 0.9125166499999999
  }
}
```

The raw ML is unchanged; new_full includes ML plus evidence, subject, rules and decision metadata. Latency includes no backend/network.

## Verification

```json
{
  "model_unchanged": true,
  "original_metrics_reproduced": true,
  "repeated_outputs_identical": true,
  "all_populated_fields_have_exact_spans": true,
  "original_diagnostics_sha256": "29dc8ea3485f2dad0a37356d4e539a1a252bbf1d4ca8797e0f164d47c3f8f57b",
  "expanded_diagnostics_sha256": "8cdc2fe7294a3acc0cbeee04e8ca1d9abf20186d5ba2b8d3424af910cf56badc"
}
```

The raw dataset, original diagnostics and artifact were not edited. Derived split manifest is unchanged. No backend/frontend changes.

## Remaining limitations

- Exact phrase vocabulary is incomplete, especially misspellings, ASR errors and Swahili variants. No fuzzy correction is guessed.
- A strong text mention below the fixed classifier threshold is omitted; conservative filtering cannot repair all false negatives.
- Negation/uncertainty is clause-based, not a syntactic parser. Lists and reported speech can exceed its scope handling.
- Multiple subjects default to abstention. An explicit target allows only clauses naming that person; pronouns are not guessed across people.
- Relative weekdays/yesterday and approximate times are retained as durationMentions but durationDays remains null without a defensible exact interval.
- Known sentence/template overlap and sparse per-label held-out coverage remain. This is development evaluation, not clinical validity.

Next: independently author/review bilingual subject, negation and evidence-span annotations; review coverage failures and fixed-threshold recall before model changes. No transformer or production-model decision.
