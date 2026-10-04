# Dataset findings and implementation checkpoint

Analysis date: 2026-10-04. Stop here before implementing/training the extractor.
Counts are reproducible with `python3 ml/src/analyze_data.py`; complete distributions,
including per-language and per-split counts, are in [data_audit.json](data_audit.json).

## 1. What data exists

The CSV (251,863 bytes) and JSONL (456,502 bytes) encode the same 1,200 examples,
in the same order after parsing CSV arrays, booleans and nullable fields. Do not
concatenate them into 2,400 examples. Both are raw *inputs to this project*, although
they were synthetically generated upstream. No upstream generator or separate dataset
documentation was supplied. Preserve both unchanged; provenance manifest is in `../data/raw/`.

JSONL keys: `id`, `language`, `text`, `labels`, `split`, `data_source`.
CSV columns: `id,language,text,patient_type,symptoms,duration_days,hydration_issue,danger_signs,notes,data_source,split`.
Labels: patient_type (string), symptoms (string array), duration_days (integer),
hydration_issue (boolean), danger_signs (string array), notes (nullable string).
Every row declares `synthetic_team_generated`. IDs are unique; all rows parse.

| Split | Total | English | Swahili |
|---|---:|---:|---:|
| train | 840 | 550 | 290 |
| validation | 180 | 112 | 68 |
| test | 180 | 112 | 68 |
| total | 1200 | 774 | 426 |

Language fields are supplied annotations, not independently verified language detection.
104 Swahili-tagged records contain an English note verbatim (e.g. `vomiting repeatedly`).
This is artificial mixing, not evidence of representative natural code switching.

No top-level missing values; no null core labels. Notes are null in 897 (74.75%)
records. Symptoms are never empty; danger_signs is empty in 644. Every record has
a patient category and duration, so there is no training coverage of unknown values
for those fields. Texts contain 44–218 characters (mean 102.16).

Patient groups: child 464 (38.7%), adult 426 (35.5%), pregnant 310 (25.8%).
Duration: 1 day 457, 2 days 326, 3 days 178, 4 days 120, 5 days 119.
Hydration: true 337 (28.1%), false 863 (71.9%). The latter is commonly not mentioned,
not an explicit assertion of normal drinking.

### `symptoms` distribution

| Label | Examples |
|---|---:|
| fever | 469 |
| cough | 211 |
| vomiting | 185 |
| weakness | 183 |
| diarrhoea | 163 |
| abdominal_pain | 119 |
| headache | 118 |
| breathing_difficulty | 90 |
| blurred_vision | 84 |
| bleeding | 74 |
| fluid_loss | 39 |
| reduced_fetal_movement | 39 |
| fatigue | 38 |

### `danger_signs` distribution

| Label | Examples |
|---|---:|
| cannot_drink | 117 |
| breathing_difficulty | 90 |
| bleeding | 74 |
| fever | 49 |
| severe_headache | 45 |
| blurred_vision | 39 |
| reduced_fetal_movement | 39 |
| water_breaking_early | 39 |
| convulsions | 36 |
| severe_abdominal_pain | 28 |

### `notes` distribution

| Label | Examples |
|---|---:|
| None | 897 |
| loose stools | 86 |
| very weak | 74 |
| vomiting repeatedly | 43 |
| had a seizure | 36 |
| very sleepy | 36 |
| not drinking well | 28 |

Symptom/sign counts are multi-label occurrence counts, not mutually exclusive classes.
Only 21 distinct symptom sets occur. Fever has 469 positives versus fatigue's 38
(12.3:1); sign support ranges from 117 cannot_drink to 28 severe_abdominal_pain.
Language/rare-label intersections are smaller still. Review support before splitting;
report unsupported metrics explicitly instead of silently averaging them away.

## 2. Leakage and label limitations

There are 996 unique exact texts: 204 duplicate excess rows. 73 exact-text groups
span splits (198 rows involved). Validation has 45/180 (25%) texts also in training;
test has 42/180 (23.3%). Sorting lowercase sentence fragments gives only 646 groups;
107 validation and 103 test examples then overlap training (59.4% and 57.2%). These
are heuristic near-duplicate groups, not recovered generator template identifiers.
No conflicting labels were found within exact-text or sentence-bag groups after
normalizing array order.

There are only 184 distinct lowercase sentence fragments. All fragments in 179/180
validation and 178/180 test records already appear in training. A random split can
mostly reward recognizing or recombining memorized phrases. Even grouped deduplication
cannot establish generalization beyond these templates.

Examples inspected:
- `health_ie_0636`: “There is fever in my child. My child has a cough. This has been
  going on for about four days.” Labels say child, fever/cough, duration 4, hydration
  false. The text establishes neither under-five age nor normal hydration, and duration is approximate.
- `health_ie_0958`: “This has been going on for two days. I have a fever.” Label adult
  is unsupported by explicit age. This same text appears in test as `health_ie_0030`.
- `health_ie_1091`: says both “for the last three days” and “hot since yesterday”.
  Label duration is 3; these may be distinct symptom/illness onsets and must not be collapsed blindly.
- `health_ie_0574` (Swahili): contains `Hawezi kunywa vizuri`, `Ana shida ya kunywa`,
  and the English phrase `vomiting repeatedly`; label cannot_drink needs bilingual
  review to distinguish degree of difficulty from absolute inability.
- `health_ie_0505`: “The water may have broken early…” is labeled as a positive sign,
  despite expressed uncertainty. That is not an established clinical finding.

74 texts mention “since yesterday” or “tangu jana”; their duration labels are
1:8, 2:30, 3:25, 4:11. Flag these for onset-scope review, not automatic relabeling.
“Today” becomes 1 day in supplied labels; that is not a measured 24-hour duration.
Pronoun changes (e.g. “I” followed by “They”) and repeated equivalent symptom/sign
sentences are additional generation artifacts.

`danger_signs` mixes text findings with context-specific interpretation: fever is a
symptom elsewhere but also a danger label for pregnancy examples. This extraction
project should not learn that as an autonomous urgency rule. `notes` is six fixed
English phrases, not a general summary target. No spans, negation labels, certainty
labels, age measurements, temperature measurements, or annotation guidelines exist.
No explicit symptom-denial patterns were found in the inspected sentence inventory.
Do not treat these labels as clinician-reviewed ground truth.

Coverage: short English/Swahili templated affirmative symptom descriptions, three
patient categories, durations 1–5 days and a narrow finding vocabulary. Not established:
natural ASR noise, dialect coverage, other languages, unknown fields, ordinary symptom
negation, multiple people, complex timing, measured vitals, open-ended medical histories,
real prevalence, real patients, diagnosis, or outcomes.

## 3. Proposed smallest useful contract (not implemented)

Keep camelCase to match the backend/mobile wire convention. Example request:

```json
{"text":"My child has had a fever for three days and has not been drinking much.","language":"en"}
```

`text`: required nonblank string, initial maximum 4,000 characters.
`language`: optional `en | sw | null`; caller-provided language hint, not a prediction.
Unsupported-language handling should explicitly reject unsupported supplied codes;
missing hint does not license guessing a patient's language or unsupported extraction.

Example response:

```json
{
  "extraction": {
    "patientType": "child",
    "symptoms": ["fever"],
    "durationDays": 3,
    "hydrationIssue": true,
    "reportedSigns": []
  },
  "sourceText": "My child has had a fever for three days and has not been drinking much.",
  "evidence": {
    "patientType": ["My child"],
    "symptoms.fever": ["a fever"],
    "durationDays": ["for three days"],
    "hydrationIssue": ["has not been drinking much"]
  },
  "modelVersion": "health-ie-v1",
  "requiresVerification": true
}
```

This is a proposed shape, not a model output produced during this work.

| Field | Allowed values and missing semantics |
|---|---|
| patientType | `child | pregnant | adult | null`; only supported subject evidence; “I” alone yields null. Pregnancy is not an age claim. |
| symptoms | Array of unique affirmed findings from the 13 symptom labels above. `[]` means no supported finding extracted, not symptom-free. |
| durationDays | Finite positive number or null, only explicit unambiguous day duration. Approximate, relative, competing or differently scoped durations stay null initially, with source retained for review. Do not fabricate 1 from “today”. |
| hydrationIssue | `true | false | null`; true for explicit reduced/difficult drinking, false only for explicit normal drinking/denial of difficulty, null if not stated or unclear. Not a dehydration diagnosis. |
| reportedSigns | Unique array from `cannot_drink | convulsions | bleeding`, representing literal affirmed mentions only. `[]` is not clearance. Do not infer inability from reduced drinking or vomiting. |
| sourceText | Original input, unchanged; used as proposed report notes. Never generate clinical notes or discard unsupported information. |
| evidence | Dictionary from populated field path (e.g. `reportedSigns.bleeding`) to nonempty arrays of exact input substrings. Omit absent paths; evidence verifies a mention, not clinical truth. |
| modelVersion | Required nonblank artifact/rules version. |
| requiresVerification | Always true for these extraction results; does not record completed verification. |

No diagnosis, risk, urgency, referral, confidence or temperature field. Unsupported,
negated, uncertain or historical descriptions stay in sourceText for review rather
than being asserted as current positives. Future richer certainty/span annotations
can extend this contract when there is reviewed data; no general NER model is
justified by the current sentence-level labels.

### Form compatibility

`src/packs/health.ts` currently expects `patient`, a SINGLE `dangerSign`, `days`,
`notes`, and separately acquired `location`. `capture.tsx` submits to `/analyze` or
local assessment on user submission; it has no text-prefill or verification step yet.

- patientType is a suggestion for `patient`. The form's `child` option means under 5;
  the dataset's child does not. Require human age confirmation before selecting it.
  Explicit pregnancy can suggest pregnant; ambiguous adult/child stays unselected.
- durationDays can suggest `days` only when unambiguous. Keep source timing visible.
- reportedSigns offers candidates for `dangerSign`, without choosing priority. Multiple
  signs need human resolution/current-form redesign; never silently choose the first.
  Empty extraction must not set `none`. Ordinary vomiting must not select the combined
  “Cannot drink / vomits everything” form option.
- sourceText proposes `notes`; symptoms and hydrationIssue can be shown for verification
  alongside it. Preserve findings not representable in the narrow sign select.
- Never infer location from these data.

Existing form validation only checks undefined/empty string for required values.
A future mapper must omit unknown fields rather than pass null through as a valid
selection, and enforce verification before the existing submit/assessment flow.
Do not call downstream triage automatically from extraction.

## 4. Task formulation and baseline recommendation

First build a bilingual deterministic baseline: literal phrase matching plus
negation, experiencer and uncertainty handling, numeric/number-word day parsing,
verbatim evidence, and abstention. This is a future task, not implemented here.

| Field | First method | ML comparison |
|---|---|---|
| patientType | Explicit subject/pregnancy/age rules; abstain on first-person-only text | Defer forced multiclass model: current labels teach unsupported adult guesses |
| symptoms | Bilingual phrase rules with local context checks | Shared TF-IDF features + one-vs-rest logistic regression for the 13 labels |
| durationDays | Number/day-unit rules with scope/ambiguity checks | No regression model: extract what is stated |
| hydrationIssue | Explicit mention/denial rules, otherwise null | Defer classifier until reviewed true/false/unknown annotations exist |
| reportedSigns | Three explicit finding detectors; negation/uncertainty gates | Consider separate binary heads only after label review; do not train clinical danger assignment |
| sourceText/evidence | Copy text and exact matched substrings | No generative notes model |

Train the first *learned* baseline as TF-IDF word unigrams/bigrams plus character
3–5-grams with linear one-vs-rest logistic regression, comparing against rules on
the same partitions. Fit vectorizers only on training text; cap vocabulary and
measure size. Start with one bilingual feature pipeline and separate binary symptom
heads; inspect errors by language before splitting models. Validation selects
thresholds and whether class weighting helps; do not assume it always helps.
Classifier candidates without defensible affirmative evidence should abstain in the
prefill service. Whole-document classification alone cannot establish subject,
negation, certainty or evidence; report the effect of these checks separately.

This is small CPU-friendly machinery appropriate for a first comparison, not a
promise of accuracy. No encoder/LLM escalation until independently authored examples
show a material limitation that justifies it. Reference: [scikit-learn text feature
extraction](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction).

## 5. Evaluation and label preparation before training

Preserve supplied raw splits for provenance, not headline performance. Create a
reviewed derived label set: unknown hydration instead of silent false; unknown
patient age/category where unsupported; unambiguous-only durations; affirmed current
mentions rather than assigned danger. Record every change with ID, original value,
new value, reason, reviewer and guideline version. Do not auto-overwrite raw labels.

Create fixed-seed grouped train/validation/test manifests after exact deduplication,
keeping sentence-order variants and related template/paraphrase families together.
Obtain generator family IDs if possible; otherwise annotate families and document
heuristic limits. Inspect language and rare-label coverage after grouping. Sentence
bags alone do not remove shared phrase-template leakage. Keep vocabularies, scaling,
threshold tuning and all other fitting inside training/validation boundaries.
Reference: [scikit-learn grouped validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).

Any synthetic test already inspected during this audit is a development benchmark,
not a pristine independent final test. Add a separately authored acceptance suite;
see [evaluation protocol](../data/evaluation/README.md). It specifies authorship,
partitions, paired hard cases, per-field metrics and error review. Use consented,
reviewed real-world data later before claims about real-world performance.

Report per-label precision/recall/F1, macro/micro F1 and symptom set exact match;
patientType precision and abstention coverage; duration exact value and missing-value
accuracy; hydration true/false/null confusion; evidence correctness; hallucinated
field rate. Break down by language and group. Inspect false negatives AND false
positives for cannot_drink, convulsions, bleeding, and symptoms. Do not hide errors
behind a single accuracy value. Measure artifact size, cold load, warmed CPU p50/p95
latency and memory. No model metrics, speed or size have been measured yet.

## 6. Eventual backend integration

Reuse the current lifespan, app.state, dependency injection, synchronous `/predict`
route and exception handling. `ml.py` already encapsulates model loading and
`ML_MODEL_PATH`; training stays under `ml/`, outside production request handling.

The current numeric-vector/scalar `PredictRequest`/`PredictResponse` and
`JoblibPredictor` are NOT drop-in-compatible with text → structured output.
After approval, replace the provisional schemas with the text extraction contract
and implement a text adapter behind `Predictor`. Mirror types in `src/api/types.ts`,
update the explicit frontend API mock and contract tests. `api.predict()` transport
can stay the same. A versioned artifact should contain vectorizer, learned heads,
label vocabularies, tuned thresholds, rules/schema version and training manifest hash.
Versioned runtime code handles deterministic parsing and output assembly; include
those versions in the bundle metadata. Make any serialized custom classes importable
in the deployed backend; do not depend on a training script's `__main__` classes.
Mount trusted artifacts read-only and pin the eventual sklearn/runtime versions.

No changes are needed to `llm.py`, `AiRouter.ts`, chatbot context, speech recognition
or routing. A later UI change calls `/predict`, displays editable suggestions and
source evidence, and only passes human-confirmed fields to the existing report
submission. Backend-local inference still requires phone-to-backend connectivity;
this is not an on-device implementation.

## 7. Prioritized next work after this checkpoint

1. Agree the proposed schema and annotation semantics, especially unknowns, child age,
   duration scope, explicit absence and uncertainty. Confirm generator/license provenance.
2. Review/transform derived labels with audit trail, deduplicate, group and freeze manifests.
   Have an independent bilingual author begin the held-out suite in parallel with this work.
3. Implement/test rules baseline and evidence/abstention behavior; score per field on development.
4. Train/evaluate TF-IDF symptom heads as a comparison; retain only improvements supported
   by validation. Inspect rare-sign false positives/negatives before any demo claim.
5. Export a versioned artifact; adapt the existing text contract/service and backend tests.
6. Add editable form suggestions and explicit human verification; never automatically
   submit, assign urgency, diagnose or route a patient.
7. Run frozen acceptance evaluation and CPU benchmarks; document failures and limits.

For the hackathon, a reliable rule-based extraction demo is preferable to adding an
unvalidated neural model. Synthetic/template scores support only a prototype extraction
claim; neither they nor a small authored suite establish clinical validity.
