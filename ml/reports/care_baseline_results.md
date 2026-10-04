# Structured care-service prototype results

Assistant-authored synthetic policy imitation only. No clinical validity or human review.

400 cases; 184 determinate cases used for supervised fitting. Threshold 0.5 selected on validation.

| Split | Cases | Families | Positive / negative / unknown |
| --- | ---: | ---: | --- |
| train | 240 | 30 | 168 / 16 / 56 |
| validation | 80 | 10 | 64 / 8 / 8 |
| test | 80 | 10 | 56 / 8 / 16 |

| Method (test) | Micro F1 | Macro F1 | Exact set | Abstention | Unsupported / assertions |
| --- | ---: | ---: | ---: | ---: | ---: |
| rules | 1.000 | 1.000 | 1.000 | 0.300 | 0 / 84 |
| logisticGated | 0.982 | 0.991 | 0.963 | 0.325 | 0 / 81 |
| logisticRaw | 0.876 | 0.851 | 0.762 | 0.125 | 20 / 101 |

| Method | Service | Precision | Recall | F1 | Support |
| --- | --- | ---: | ---: | ---: | ---: |
| rules | generalOutpatient | 1.000 | 1.000 | 1.000 | 56 |
| rules | childHealth | 1.000 | 1.000 | 1.000 | 14 |
| rules | maternal | 1.000 | 1.000 | 1.000 | 14 |
| logisticGated | generalOutpatient | 1.000 | 0.946 | 0.972 | 56 |
| logisticGated | childHealth | 1.000 | 1.000 | 1.000 | 14 |
| logisticGated | maternal | 1.000 | 1.000 | 1.000 | 14 |
| logisticRaw | generalOutpatient | 0.869 | 0.946 | 0.906 | 56 |
| logisticRaw | childHealth | 0.700 | 1.000 | 0.824 | 14 |
| logisticRaw | maternal | 0.700 | 1.000 | 0.824 | 14 |

## Interpretation

The rules baseline matches the annotation generator by construction. The ML model
learns that same policy, principally patient-type associations; this does not establish
medical service need. Raw ML results expose reliance on the abstention gate.
Structured scenario families are disjoint, but all share the same authored policy.
Complete determinate-only metrics, validation trials, distributions and error cases
are in care_baseline_results.json. Unknown-target cases were excluded from model fitting.

Not ready for automatic facility routing: all 209 facility capability records remain
unknown. Do not relax mandatory filtering. Obtain independent human-reviewed labels,
test real extraction outputs, and verify capability evidence before integration.

No body-location field exists upstream; none was invented. No clinical labels,
source text, facility identifiers or frozen extraction evaluation cases were used.
Training labels here are synthetic service-policy labels, not diagnoses.
