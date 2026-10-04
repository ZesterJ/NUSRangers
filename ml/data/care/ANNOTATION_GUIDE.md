# Care-service prototype annotation guide v1

## Status and provenance

This is an assistant-authored synthetic policy proposed for the team's hackathon,
not clinician annotation or established clinical guidance. No human review is claimed.
Labels express services suggested for HUMAN REVIEW under this policy, not clinically
necessary services. No diagnosis, treatment, urgency, referral or facility capability
is inferred. Dataset and model are independent of the facility catalogue.

## Inspected input contract

The current extraction wrapper supplies patientType (adult/child/pregnant/null),
symptoms (13 fixed labels), durationDays (number/null), hydrationIssue (true/false/null),
reportedSigns, reportedSignStates (affirmed/negated/uncertain/not_mentioned), subject
(resolved/ambiguous/unspecified) and abstentions. The manual CLI displays only five
fields; integration must use the full structured wrapper result to retain uncertainty.
No painLocations or body-diagram field exists. Do not fabricate one or infer a body
location from a symptom. No exact child age is available; child is not under-five.

Only a projection of these structured fields is generated/used here. No sourceText,
evidence text, classifier score, ID, scenario tag, label, language, facility data or
annotation rationale is a model feature. These are constructed inputs, not outputs
measured from actual text inference. Evidence spans are not invented.

## Smallest provisional taxonomy

- generalOutpatient: general assessment, only when the prototype input has an affirmed
  finding and is within the accepted policy domain.
- childHealth: additional child-focused assessment context when patientType is child.
- maternal: additional maternal-focused assessment context when patientType is pregnant.

The latter two supplement general assessment; these labels do NOT establish a need
for separate appointments, specialists or a combined facility referral. This explicit
hierarchy explains why multi-label targets are used. Labels reuse router vocabulary
only; they do not fill any facility capability fields.

No laboratory, imaging, respiratory-specialty or emergency target: there is no reviewed
patient-to-service policy or facility evidence for those labels. No inference from
facility name, type, level or symptom associations is allowed.

## Annotation decision order (frozen before training)

1. Ambiguous subject, conflicting_patient_type or contradictory reportedSigns/state
   combinations: all service annotations unknown; abstain and seek clarification.
2. Any affirmed or uncertain reported sign (cannot_drink, convulsions, bleeding), or
   symptoms bleeding, breathing_difficulty, blurred_vision, fluid_loss,
   reduced_fetal_movement: outside this narrow prototype policy. All services unknown;
   abstain for human assessment. This is a coverage boundary, NOT an urgency rule.
3. No affirmed symptoms and hydrationIssue is not true: no supported finding.
   Service labels are not_indicated_by_input (negative learning targets); abstain.
   This never means no care is needed. Missing data and explicit negative findings
   remain distinct input states.
4. Otherwise: generalOutpatient positive, plus childHealth if child or maternal if
   pregnant. Other services not_indicated_by_input. A null patientType does not
   establish adult; only the general service can be proposed.

Duration alone never establishes need. Null duration or ambiguous_duration does not
negate otherwise usable findings. Subject unspecified can still carry a single-patient
structured report; only explicitly ambiguous subject blocks the prototype.
Unknown target entries are excluded from supervised fitting, never coerced to negative.
Each case records serviceStates, requiredServices, annotationStatus, reason and review
status. RequiredServices=[] on unknown cases means abstention, not negative clinical truth.

## Dataset design and separation

400 cases, 50 scenario families × 8 variations. 35 families cover distinct combinations
of ordinary findings; 15 cover empty/negative information, ambiguity, inconsistent
projections and excluded findings. Variations cover patient type, hydration tri-state,
duration missingness and multiple findings. Contradictory projections are labelled
robustness probes, not claims that the extractor normally emits invalid combinations.
Only state distinctions actually exposed by the extractor are represented; absent
symptoms are not described as explicit negatives. Negated reported signs and hydration
false are explicit negative examples. Unknowns include null fields and uncertain signs.

Family partition is fixed before fitting: 240 train / 80 validation / 80 test. All
variations of a family stay together; exact structured duplicates are prohibited across
splits. Scenario families share the same authored policy, so this is a weak synthetic
policy-imitation benchmark, NOT independent clinical validation. Existing extraction
raw data, development suites and frozen acceptance sets are not read or reused.

## Training and evaluation protocol

Rules implement this documented policy. Logistic regression is one-vs-rest with C=1,
balanced weights and structured DictVectorizer features. Fit vectorizer/model only
on determinate training annotations. Select one global threshold on validation from
0.5/0.6/0.7/0.8/0.9, minimizing unsupported assertions then maximizing micro-F1, with
higher threshold as final tie break. Scores are uncalibrated.

Both deployed-prototype candidates use the same conservative eligibility gate from
steps 1–3. Report raw ungated ML separately to expose what the gate is doing.
Service-set metrics treat abstentions as the empty desired output; also report metrics
on determinate cases to avoid hiding performance behind unknown cases. Unsupported
assertion rate = predicted services not positive in annotation / all predicted services;
unknown-case assertions count as unsupported, not proven clinically incorrect.
Report numerator/denominator. Zero predictions yields an undefined (null) rate.
Abstention rate = fraction returning no services. No-service prediction is never a
negative care recommendation. Also report coverage of cases with positive targets.

No automatic facility routing readiness: all 209 real facilities still have unknown
capabilities. Before integration, obtain human review, independent authored evaluation,
real extractor-output testing, capability evidence and approved clinical safety policy.
