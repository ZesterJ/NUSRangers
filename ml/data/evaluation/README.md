# Independent evaluation protocol (planned, not yet collected)

Create a small human-authored suite, not variations produced from the supplied
sentence templates. Target 120 examples: 50 English, 50 Swahili, 20 mixed-language.
Use 40 as a separate development challenge set and freeze the remaining 80 as
acceptance evaluation before selecting thresholds. Keep each author/scenario family
entirely within one partition; report language and label support for each partition.
These are pragmatic hackathon targets, not a statistically powered clinical study.

A bilingual reviewer should author or review Swahili examples. Two annotators mark
literal evidence and proposed values independently, then adjudicate disagreements.
Use fictional, natural descriptions; collecting real patient records is not required.
Record author, language, scenario family, annotation guideline version, and split.
Store records as ignored JSONL in this folder, with IDs distinct from training IDs.
Neither acceptance examples nor their paraphrases enter training, vocabulary fitting,
rule development, threshold selection, or prompt/model selection. Any examples already
used to design rules belong to development, not the frozen acceptance suite.

Cover omitted fields; explicit denials; uncertainty; historical/resolved symptoms;
multiple people; caregiver vs patient; older children; ambiguous first person;
pregnancy without age; reduced drinking vs inability; ordinary vomiting vs vomiting
everything; multiple durations and symptom-specific onset; hours/weeks and approximation;
misspellings; punctuation-free speech transcripts; repetitions; code switching;
unsupported symptoms and unrelated text. Inspect extraction of cannot_drink,
convulsions and bleeding with paired positive, negated and uncertain descriptions.
Keep the task factual: no diagnosis, urgency or referral labels.

Report precision/recall/F1 per finding, macro/micro F1 and set exact match;
patient-type precision/coverage with abstention; duration value accuracy plus
missing/ambiguous accuracy; hydration true/false/null confusion matrix; evidence-span
accuracy; unsupported-assertion rate. Break down by language, patient group and challenge
category. Inspect every false positive/negative for the three form sign candidates.
Report denominators and uncertainty, including labels with no positive support.
Do not report all-null or all-negative accuracy as evidence of useful performance.

Measure artifact bytes, cold load time, warm end-to-end CPU inference p50/p95,
peak memory and test hardware. Use a fixed warmed benchmark with at least 1,000
requests spanning input lengths; time API overhead separately. No measurements exist yet.

Synthetic benchmark scores and this small authored suite describe prototype behavior
only. Neither establishes clinical validity, robustness to actual ASR output, or
real-world patient performance. Obtain separate consented, reviewed validation before
making such claims.

## Current development diagnostics

`baseline_diagnostics.json` is a deliberately tracked, small set of 48 fictional
assistant-authored development cases used by the first baseline. It is separate from
the independently authored acceptance suite described above, which does not exist yet.
Do not put these cases into a future acceptance set. Rules were corrected after
inspecting these cases; see `../../reports/rule_revision_log.json`. No classifier
fit, vocabulary fit, threshold selection or model selection used them.

`expanded_diagnostics.json` adds 42 fictional development cases for the evidence-gated
wrapper: English, Swahili, mixed-language, explicit denials, subject ambiguity, unknown
fields, ambiguous duration, multiple symptoms, short text, misspellings and ASR-like
repetition/punctuation loss. Its multi-person expectations require abstention unless
a target subject is explicit. The original 48-case file is unchanged and retains its
older document-level symptom targets, so subject abstention can score as a regression
there. Both OLD and NEW are evaluated against the SAME expectations within each suite.
Neither suite is used for classifier fitting or threshold selection. The new rules
were developed with these cases visible; do not describe the results as independent
acceptance performance or evidence of clinical validity.
