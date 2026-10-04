"""Explicit, nonclinical synthetic annotation policy; no extraction modifications."""
SERVICES = ('generalOutpatient', 'childHealth', 'maternal')
SIGNS = ('cannot_drink', 'convulsions', 'bleeding')
OUTSIDE = {'bleeding', 'breathing_difficulty', 'blurred_vision', 'fluid_loss', 'reduced_fetal_movement'}


def gate(patient):
    if patient['subject']['status'] == 'ambiguous' or 'conflicting_patient_type' in patient['abstentions']:
        return 'unknown', 'ambiguous_or_conflicting_subject'
    states = {s: patient['reportedSignStates'][s]['state'] for s in SIGNS}
    if set(patient['reportedSigns']) != {s for s in SIGNS if states[s] == 'affirmed'}:
        return 'unknown', 'contradictory_sign_projection'
    if any(v in ('affirmed', 'uncertain') for v in states.values()) or set(patient['symptoms']) & OUTSIDE:
        return 'unknown', 'outside_prototype_policy'
    if not patient['symptoms'] and patient['hydrationIssue'] is not True:
        return 'negative', 'no_supported_finding'
    return 'positive', 'supported_prototype_finding'


def annotate(patient):
    status, reason = gate(patient)
    labels = []
    if status == 'positive':
        labels = ['generalOutpatient']
        if patient['patientType'] == 'child': labels.append('childHealth')
        if patient['patientType'] == 'pregnant': labels.append('maternal')
    return {'annotationStatus': status, 'requiredServices': labels,
            'serviceStates': {s: ('unknown' if status == 'unknown' else 'positive' if s in labels else 'not_indicated_by_input') for s in SERVICES},
            'reason': reason, 'guideVersion': 'care-policy-v1', 'reviewStatus': 'assistant_authored_not_human_reviewed'}


def rules_predict(patient):
    return annotate(patient)['requiredServices']


def features(patient):
    result = {'patientType': patient['patientType'] or 'unknown',
              'durationMissing': patient['durationDays'] is None,
              'durationDaysScaled': min(patient['durationDays'] or 0, 30) / 30,
              'hydration': 'unknown' if patient['hydrationIssue'] is None else str(patient['hydrationIssue']).lower(),
              'subjectStatus': patient['subject']['status']}
    for symptom in patient['symptoms']: result['symptom.' + symptom] = 1
    for sign in SIGNS: result['sign.' + sign] = patient['reportedSignStates'][sign]['state']
    for reason in patient['abstentions']: result['abstention.' + reason] = 1
    return result
