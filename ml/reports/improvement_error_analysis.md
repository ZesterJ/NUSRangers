# Improvement error review

Synthetic-data benchmark results and authored development diagnostics only.

No training labels or original expectations were changed. All paired field mismatches are in improvement_errors.json.

## synthetic_validation

- improved: health_ie_0014 / sw / synthetic_template: 'Hanywi vizuri. Mtoto wangu ana homa. Mtoto anaonekana mchovu na dhaifu. Hali hii imeendelea kwa siku tatu. very weak. Hawezi kunywa. Mtoto wangu amekuwa akitapika.'. Expected ['fever', 'vomiting', 'weakness']; OLD ['diarrhoea', 'fever', 'weakness']; NEW ['fever', 'weakness'].
- improved: health_ie_0019 / en / synthetic_template: 'This has been going on for the last three days. There is difficulty drinking. very weak. My child has been sick and vomiting. They cannot drink. My child seems very weak. My child has been hot since yesterday.'. Expected ['fever', 'vomiting', 'weakness']; OLD ['diarrhoea', 'fever', 'weakness']; NEW ['fever', 'weakness'].
- remaining: health_ie_0069 / en / synthetic_template: 'This has been going on for one day. My head hurts. My vision is blurred. My vision is blurred.'. Expected ['headache', 'blurred_vision']; OLD ['headache']; NEW ['headache'].
- remaining: health_ie_0537 / sw / synthetic_template: 'Ninatapika. Hali hii imeendelea leo. Amekuwa hanywi maji vizuri. Ninaendesha.'. Expected ['vomiting', 'diarrhoea']; OLD ['vomiting']; NEW ['vomiting'].

Rule-field mismatches (all authored cases; first five raw cases):

- health_ie_0008: 'I have a fever during pregnancy. There is fever. This has been going on since two days ago. I am pregnant and have stomach pain.': `{'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
- health_ie_0011: 'Kichwa changu kinauma. Naona ukungu. Hali hii imeendelea tangu leo. Macho yangu hayaoni vizuri naona ukungu.': `{'patientType': {'expected': 'adult', 'old': None, 'new': None}, 'durationDays': {'expected': 1, 'old': None, 'new': None}, 'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
- health_ie_0016: 'I feel hot and have a fever. I keep coughing. This has been going on for about four days.': `{'patientType': {'expected': 'adult', 'old': None, 'new': None}, 'durationDays': {'expected': 4, 'old': None, 'new': None}, 'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
- health_ie_0019: 'This has been going on for the last three days. There is difficulty drinking. very weak. My child has been sick and vomiting. They cannot drink. My child seems very weak. My child has been hot since yesterday.': `{'durationDays': {'expected': 3, 'old': None, 'new': None}}`
## synthetic_test

- improved: health_ie_0029 / en / synthetic_template: 'This has been going on for three days. My belly hurts.'. Expected ['abdominal_pain']; OLD ['fever', 'headache']; NEW [].
- improved: health_ie_0053 / sw / synthetic_template: 'Tumbo langu linauma. Hali hii imeendelea tangu siku tatu zilizopita.'. Expected ['abdominal_pain']; OLD ['abdominal_pain', 'fever']; NEW ['abdominal_pain'].
- remaining: health_ie_0084 / en / synthetic_template: 'I feel tired and weak. They are not drinking well. I am vomiting. This has been going on for two days.'. Expected ['vomiting', 'weakness']; OLD ['vomiting']; NEW ['vomiting'].
- remaining: health_ie_0511 / sw / synthetic_template: 'Ninaumwa tumbo. Hali hii imeendelea kwa siku tatu.'. Expected ['abdominal_pain']; OLD []; NEW [].

Rule-field mismatches (all authored cases; first five raw cases):

- health_ie_0018: 'This has been going on for three days. I have abdominal pain.': `{'patientType': {'expected': 'adult', 'old': None, 'new': None}, 'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
- health_ie_0020: 'This has been going on today. There is bleeding. I am bleeding.': `{'patientType': {'expected': 'adult', 'old': None, 'new': None}, 'durationDays': {'expected': 1, 'old': None, 'new': None}, 'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
- health_ie_0029: 'This has been going on for three days. My belly hurts.': `{'patientType': {'expected': 'adult', 'old': None, 'new': None}, 'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
- health_ie_0036: 'I feel tired and weak. I have a fever. This has been going on for three days.': `{'patientType': {'expected': 'adult', 'old': None, 'new': None}, 'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
- health_ie_0042: 'I feel very weak. I have been feeling feverish. This has been going on for three days.': `{'patientType': {'expected': 'adult', 'old': None, 'new': None}, 'hydrationIssue': {'expected': False, 'old': None, 'new': None}}`
## original_diagnostics

- improved: diagnostic_003 / en / duration: 'Fever for three days.'. Expected ['fever']; OLD ['fever', 'weakness']; NEW ['fever'].
- improved: diagnostic_005 / en / hydration: 'The child is not drinking.'. Expected []; OLD ['diarrhoea', 'fever']; NEW [].
- improved: diagnostic_006 / en / hydration_negative: 'The child is drinking normally.'. Expected []; OLD ['diarrhoea', 'fever']; NEW [].
- improved: diagnostic_007 / en / sign: 'My child cannot drink.'. Expected []; OLD ['diarrhoea']; NEW [].
- improved: diagnostic_008 / en / reduced_vs_unable: 'My child is not drinking much.'. Expected []; OLD ['diarrhoea', 'fever']; NEW [].
- improved: diagnostic_010 / en / negation: 'I am not bleeding.'. Expected []; OLD ['bleeding']; NEW [].
- improved: diagnostic_012 / en / uncertainty: 'Maybe I am pregnant and bleeding.'. Expected []; OLD ['bleeding']; NEW [].
- improved: diagnostic_015 / en / duration_approximate: 'My child has fever for about three days.'. Expected ['fever']; OLD ['cough', 'fever']; NEW ['fever'].
- regressed: diagnostic_017 / en / multiple_subjects: 'I have a fever and my child is coughing.'. Expected ['fever', 'cough']; OLD ['cough', 'fever']; NEW [].
- improved: diagnostic_019 / en / explicit_adult: 'An adult has a cough.'. Expected ['cough']; OLD ['breathing_difficulty', 'cough']; NEW ['cough'].
- remaining: diagnostic_022 / en / negation: 'No fever, only a cough.'. Expected ['cough']; OLD ['cough', 'fever']; NEW [].
- improved: diagnostic_023 / en / short: 'Cough.'. Expected ['cough']; OLD ['breathing_difficulty', 'cough']; NEW ['cough'].
- remaining: diagnostic_024 / en / spelling: 'I have fevr and a caugh.'. Expected ['fever', 'cough']; OLD []; NEW [].
- remaining: diagnostic_025 / en / phrasing: 'My belly aches and I keep throwing up.'. Expected ['abdominal_pain', 'vomiting']; OLD []; NEW [].
- remaining: diagnostic_026 / en / multi_symptom: 'I have fever, cough and diarrhoea.'. Expected ['fever', 'cough', 'diarrhoea']; OLD ['diarrhoea', 'fever']; NEW ['diarrhoea', 'fever'].
- improved: diagnostic_027 / en / historical: 'I used to have a fever. Now I have a cough.'. Expected ['cough']; OLD ['cough', 'fever']; NEW ['cough'].
- improved: diagnostic_030 / sw / explicit_child: 'Mtoto wangu ana homa.'. Expected ['fever']; OLD ['cough', 'fever']; NEW ['fever'].
- improved: diagnostic_033 / sw / hydration: 'Mtoto wangu hanywi maji vizuri.'. Expected []; OLD ['diarrhoea', 'fever']; NEW [].
- improved: diagnostic_034 / sw / hydration_negative: 'Mtoto wangu anakunywa maji vizuri.'. Expected []; OLD ['diarrhoea', 'fever']; NEW [].
- improved: diagnostic_035 / sw / sign: 'Mtoto wangu hawezi kunywa.'. Expected []; OLD ['diarrhoea']; NEW [].
- improved: diagnostic_036 / sw / reduced_vs_unable: 'Mtoto wangu hawezi kunywa vizuri.'. Expected []; OLD ['diarrhoea']; NEW [].
- improved: diagnostic_038 / sw / negation: 'Sina homa lakini ninakohoa.'. Expected ['cough']; OLD ['cough', 'fever']; NEW ['cough'].
- improved: diagnostic_039 / sw / pregnancy: 'Mimi ni mjamzito na ninatapika.'. Expected ['vomiting']; OLD ['bleeding', 'vomiting']; NEW ['vomiting'].
- improved: diagnostic_040 / sw / uncertainty: 'Labda nina homa.'. Expected []; OLD ['fever']; NEW [].
- regressed: diagnostic_043 / sw / spelling: 'Nina hma na kikohzi.'. Expected ['fever', 'cough']; OLD ['cough']; NEW [].
- improved: diagnostic_047 / en / historical_scope_challenge: 'The bleeding stopped last year.'. Expected []; OLD ['bleeding']; NEW [].

Rule-field mismatches (all authored cases; first five raw cases):

- diagnostic_046: 'My child has fever for three days and is not drinking.': `{'durationDays': {'expected': 3, 'old': None, 'new': 3}}`
## expanded_diagnostics

- improved: expanded_001 / en / negation: 'No fever, not vomiting, without bleeding.'. Expected []; OLD ['bleeding', 'vomiting']; NEW [].
- improved: expanded_002 / sw / negation: 'Sina homa. Sitapiki. Hakuna damu inayotoka.'. Expected []; OLD ['fever']; NEW [].
- improved: expanded_005 / en / explicit_negative: 'The child is drinking well.'. Expected []; OLD ['diarrhoea', 'fever']; NEW [].
- improved: expanded_006 / sw / explicit_negative: 'Mtoto wangu anakunywa vizuri.'. Expected []; OLD ['diarrhoea', 'fever']; NEW [].
- improved: expanded_007 / en / multiple_subjects: 'My husband has fever but I feel fine.'. Expected []; OLD ['fever']; NEW [].
- improved: expanded_009 / sw / multiple_subjects: 'Mume wangu ana homa lakini mimi sina homa.'. Expected []; OLD ['fever']; NEW [].
- improved: expanded_012 / en / duration: 'Cough three days.'. Expected ['cough']; OLD ['cough', 'fever', 'weakness']; NEW ['cough'].
- improved: expanded_013 / en / relative_duration: 'I have been vomiting since yesterday.'. Expected ['vomiting']; OLD ['fever', 'vomiting']; NEW ['vomiting'].
- improved: expanded_015 / sw / weekday_duration: 'Mtoto wangu ana homa tangu Jumatatu.'. Expected ['fever']; OLD ['cough', 'fever']; NEW ['fever'].
- improved: expanded_017 / sw / approximate_duration: 'Nina homa kwa siku chache.'. Expected ['fever']; OLD ['fever', 'headache']; NEW ['fever'].
- remaining: expanded_019 / en / multiple_symptoms: 'Fever and cough and vomiting.'. Expected ['fever', 'cough', 'vomiting']; OLD ['cough', 'vomiting']; NEW ['cough', 'vomiting'].
- remaining: expanded_020 / sw / multiple_symptoms: 'Nina homa na kikohozi na ninatapika.'. Expected ['fever', 'cough', 'vomiting']; OLD ['cough', 'vomiting']; NEW ['cough', 'vomiting'].
- improved: expanded_021 / mixed / multiple_symptoms: 'Nina homa and a cough for three days.'. Expected ['fever', 'cough']; OLD ['cough', 'fever', 'weakness']; NEW ['cough', 'fever'].
- regressed: expanded_025 / en / spelling: 'fevr and vomitting for 2 days'. Expected ['fever', 'vomiting']; OLD ['fever', 'vomiting']; NEW [].
- regressed: expanded_026 / sw / spelling: 'nina hma na kikohzi'. Expected ['fever', 'cough']; OLD ['cough']; NEW [].
- improved: expanded_027 / en / asr: 'um no fever but cough cough for three days'. Expected ['cough']; OLD ['cough', 'fever']; NEW ['cough'].
- improved: expanded_028 / sw / asr: 'mtoto wangu hana homa lakini kikohozi siku tatu'. Expected ['cough']; OLD ['cough', 'fever']; NEW ['cough'].
- improved: expanded_029 / mixed / asr: 'no homa lakini vomiting for two days'. Expected ['vomiting']; OLD ['fever', 'vomiting']; NEW ['vomiting'].
- improved: expanded_030 / en / reduced_drinking: 'My child is drinking less.'. Expected []; OLD ['fever', 'reduced_fetal_movement']; NEW [].
- improved: expanded_031 / en / sign_affirmed: 'The child cannot drink.'. Expected []; OLD ['diarrhoea']; NEW [].
- improved: expanded_032 / en / sign_negated: 'The child has no convulsions.'. Expected []; OLD ['fever']; NEW [].
- improved: expanded_033 / sw / sign_negated: 'Mtoto wangu hana degedege.'. Expected []; OLD ['fever']; NEW [].
- improved: expanded_034 / en / sign_uncertain: 'The child may have had a seizure.'. Expected []; OLD ['fever']; NEW [].
- improved: expanded_040 / en / context: 'No fever but I feel very weak.'. Expected ['weakness']; OLD ['fever', 'weakness']; NEW ['weakness'].

Rule-field mismatches (all authored cases; first five raw cases):

- expanded_011: 'Fever for three days and not drinking much.': `{'durationDays': {'expected': 3, 'old': None, 'new': 3}}`
- expanded_027: 'um no fever but cough cough for three days': `{'durationDays': {'expected': 3, 'old': None, 'new': 3}}`
- expanded_028: 'mtoto wangu hana homa lakini kikohozi siku tatu': `{'durationDays': {'expected': 3, 'old': None, 'new': 3}}`
- expanded_029: 'no homa lakini vomiting for two days': `{'durationDays': {'expected': 2, 'old': None, 'new': 2}}`
- expanded_034: 'The child may have had a seizure.': `{'patientType': {'expected': 'child', 'old': None, 'new': 'child'}}`
