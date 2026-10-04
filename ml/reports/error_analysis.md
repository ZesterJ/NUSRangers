# First-baseline error analysis

Synthetic-data benchmark results; experimental, not clinical validation.

All mismatches are preserved in baseline_errors.json. No raw labels were modified and no model was tuned against test/diagnostics.

## Learned symptoms

Held-out scenario changes can break associations learned from templated co-occurrence (e.g. symptom ↔ patient group).
The classifier has no explicit negation, uncertainty, temporal or subject mechanism. Document-level presence is not a verified patient finding.
Diagnostic targets omit negated/historical/uncertain mentions; multi-subject symptom targets retain document mentions only, demonstrating why subject assignment is a separate task.
Inspect language breakdowns with their denominators: Swahili diagnostics are unreviewed fictional examples, not a language-competence estimate.

Representative errors (first example of each error direction/category/language):

- derived_test / health_ie_0029 / en / synthetic_template: 'This has been going on for three days. My belly hurts.'. false_positives: ['fever', 'headache']; expected ['abdominal_pain']; predicted ['fever', 'headache'].
- derived_test / health_ie_0029 / en / synthetic_template: 'This has been going on for three days. My belly hurts.'. false_negatives: ['abdominal_pain']; expected ['abdominal_pain']; predicted ['fever', 'headache'].
- derived_test / health_ie_0053 / sw / synthetic_template: 'Tumbo langu linauma. Hali hii imeendelea tangu siku tatu zilizopita.'. false_positives: ['fever']; expected ['abdominal_pain']; predicted ['abdominal_pain', 'fever'].
- derived_test / health_ie_0511 / sw / synthetic_template: 'Ninaumwa tumbo. Hali hii imeendelea kwa siku tatu.'. false_negatives: ['abdominal_pain']; expected ['abdominal_pain']; predicted [].
- diagnostics / diagnostic_003 / en / duration: 'Fever for three days.'. false_positives: ['weakness']; expected ['fever']; predicted ['fever', 'weakness'].
- diagnostics / diagnostic_005 / en / hydration: 'The child is not drinking.'. false_positives: ['diarrhoea', 'fever']; expected []; predicted ['diarrhoea', 'fever'].
- diagnostics / diagnostic_006 / en / hydration_negative: 'The child is drinking normally.'. false_positives: ['diarrhoea', 'fever']; expected []; predicted ['diarrhoea', 'fever'].
- diagnostics / diagnostic_007 / en / sign: 'My child cannot drink.'. false_positives: ['diarrhoea']; expected []; predicted ['diarrhoea'].
- diagnostics / diagnostic_008 / en / reduced_vs_unable: 'My child is not drinking much.'. false_positives: ['diarrhoea', 'fever']; expected []; predicted ['diarrhoea', 'fever'].
- diagnostics / diagnostic_010 / en / negation: 'I am not bleeding.'. false_positives: ['bleeding']; expected []; predicted ['bleeding'].
- diagnostics / diagnostic_012 / en / uncertainty: 'Maybe I am pregnant and bleeding.'. false_positives: ['bleeding']; expected []; predicted ['bleeding'].
- diagnostics / diagnostic_015 / en / duration_approximate: 'My child has fever for about three days.'. false_positives: ['cough']; expected ['fever']; predicted ['cough', 'fever'].
- diagnostics / diagnostic_019 / en / explicit_adult: 'An adult has a cough.'. false_positives: ['breathing_difficulty']; expected ['cough']; predicted ['breathing_difficulty', 'cough'].
- diagnostics / diagnostic_023 / en / short: 'Cough.'. false_positives: ['breathing_difficulty']; expected ['cough']; predicted ['breathing_difficulty', 'cough'].
- diagnostics / diagnostic_024 / en / spelling: 'I have fevr and a caugh.'. false_negatives: ['cough', 'fever']; expected ['fever', 'cough']; predicted [].
- diagnostics / diagnostic_025 / en / phrasing: 'My belly aches and I keep throwing up.'. false_negatives: ['abdominal_pain', 'vomiting']; expected ['abdominal_pain', 'vomiting']; predicted [].
- diagnostics / diagnostic_026 / en / multi_symptom: 'I have fever, cough and diarrhoea.'. false_negatives: ['cough']; expected ['fever', 'cough', 'diarrhoea']; predicted ['diarrhoea', 'fever'].
- diagnostics / diagnostic_027 / en / historical: 'I used to have a fever. Now I have a cough.'. false_positives: ['fever']; expected ['cough']; predicted ['cough', 'fever'].
- diagnostics / diagnostic_030 / sw / explicit_child: 'Mtoto wangu ana homa.'. false_positives: ['cough']; expected ['fever']; predicted ['cough', 'fever'].
- diagnostics / diagnostic_033 / sw / hydration: 'Mtoto wangu hanywi maji vizuri.'. false_positives: ['diarrhoea', 'fever']; expected []; predicted ['diarrhoea', 'fever'].
- diagnostics / diagnostic_034 / sw / hydration_negative: 'Mtoto wangu anakunywa maji vizuri.'. false_positives: ['diarrhoea', 'fever']; expected []; predicted ['diarrhoea', 'fever'].
- diagnostics / diagnostic_035 / sw / sign: 'Mtoto wangu hawezi kunywa.'. false_positives: ['diarrhoea']; expected []; predicted ['diarrhoea'].
- diagnostics / diagnostic_036 / sw / reduced_vs_unable: 'Mtoto wangu hawezi kunywa vizuri.'. false_positives: ['diarrhoea']; expected []; predicted ['diarrhoea'].
- diagnostics / diagnostic_038 / sw / negation: 'Sina homa lakini ninakohoa.'. false_positives: ['fever']; expected ['cough']; predicted ['cough', 'fever'].
- diagnostics / diagnostic_039 / sw / pregnancy: 'Mimi ni mjamzito na ninatapika.'. false_positives: ['bleeding']; expected ['vomiting']; predicted ['bleeding', 'vomiting'].
- diagnostics / diagnostic_040 / sw / uncertainty: 'Labda nina homa.'. false_positives: ['fever']; expected []; predicted ['fever'].
- diagnostics / diagnostic_043 / sw / spelling: 'Nina hma na kikohzi.'. false_negatives: ['fever']; expected ['fever', 'cough']; predicted ['cough'].
- diagnostics / diagnostic_047 / en / historical_scope_challenge: 'The bleeding stopped last year.'. false_positives: ['bleeding']; expected []; predicted ['bleeding'].

## Rule fields

The raw data are a comparison reference only. First-person-only adult labels and hydration false without a drinking statement are not evidence of rule failure.
Approximation, yesterday/today, conflicting durations, and broad negation scope cause deliberate abstention. Some conservatism loses explicitly stated information.
English/Swahili phrase coverage is narrow. Cannot-drink gold labels include reduced-drinking variants; review bilingual semantics before calling all such abstentions false negatives.
The rules do not resolve arbitrary experiencers, pronouns, uncertainty or historical scope. Review the diagnostic counterexamples below.

### Diagnostic rule mismatches (all)

- diagnostic_046 (duration_scope_challenge): 'My child has fever for three days and is not drinking.'; differences: `{'durationDays': {'expected': 3, 'predicted': None}}`.

### Raw-test reported-sign false negatives (first example per sign)

- health_ie_0250: 'Hali hii imeendelea tangu siku mbili zilizopita. Mtoto wangu amekuwa akitapika. vomiting repeatedly. Mtoto wangu ana homa tangu jana. Hawezi kunywa vizuri. Amekuwa hanywi maji vizuri.'; supplied sign cannot_drink; extracted []. Review scope/degree of inability before changing rules or labels.

## Coverage limits and next data work

Short utterances, misspellings, phrasing variation, missing values, multiple symptoms, explicit denials, ambiguity and multiple subjects are tagged in diagnostics; per-category symptom metrics are in JSON.
The derived test covers only five positive symptom labels and few scenario families. Three single-family labels cannot be both learned and evaluated independently with this corpus.
No independent acceptance set exists. Commission separate English/Swahili descriptions and dual-reviewed evidence/subject/negation/unknown labels before comparing an encoder.
Do not relabel raw data to improve scores. Future corrections require ID, original/new labels, reason and reviewer; keep corrected evaluation separate.
One development fix is recorded in rule_revision_log.json: and/na clause splitting lost uncertainty scope and broke Swahili bleeding phrases. No gold labels changed.
Rule scope/code fixes should be regression-tested and versioned; changing a rule after inspecting a diagnostic makes that case development data, not fresh evaluation.
