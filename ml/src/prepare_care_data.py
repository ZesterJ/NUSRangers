"""Generate only fictional structured cases under the documented care-policy-v1."""
from itertools import combinations
import hashlib
import json
from pathlib import Path
import random

from care_policy import SIGNS, annotate

ROOT = Path(__file__).resolve().parents[1] / 'data/care'


def generate():
    rng = random.Random(20261004)
    ordinary = ['fever', 'cough', 'vomiting', 'diarrhoea', 'fatigue', 'weakness', 'headache', 'abdominal_pain']
    combinations_ = [list(c) for n in (1, 2, 3) for c in combinations(ordinary, n)]
    rng.shuffle(combinations_)
    families = [('ordinary', c) for c in combinations_[:35]]
    families += [(kind, []) for kind in ['missing', 'negative_hydration', 'negative_signs', 'uncertain_sign',
                 'affirmed_sign', 'contradictory_sign', 'ambiguous_subject', 'conflicting_type',
                 'bleeding', 'breathing_difficulty', 'blurred_vision', 'fluid_loss',
                 'reduced_fetal_movement', 'ambiguous_duration_only', 'hydration_only']]
    # Stratify ordinary/challenge families; no individual variation crosses split.
    assignment = {}
    for indexes, sizes in [(list(range(35)), (21, 7)), (list(range(35, 50)), (9, 3))]:
        rng.shuffle(indexes)
        for pos, index in enumerate(indexes):
            assignment[index] = 'train' if pos < sizes[0] else 'validation' if pos < sum(sizes) else 'test'
    rows = []
    for index, (kind, symptoms) in enumerate(families):
        for variant in range(8):
            p = {'patientType': ['adult', 'child', 'pregnant', None][variant % 4],
                 'symptoms': list(symptoms), 'durationDays': [None, 1, 2, 3, 5, 7, 10, 14][variant],
                 'hydrationIssue': [None, False, True][variant % 3], 'reportedSigns': [],
                 'reportedSignStates': {s: {'state': 'not_mentioned'} for s in SIGNS},
                 'subject': {'status': 'resolved' if variant % 2 else 'unspecified'}, 'abstentions': []}
            if kind != 'ordinary':
                p['hydrationIssue'] = None
                if kind == 'negative_hydration': p['hydrationIssue'] = False
                if kind == 'negative_signs':
                    for s in SIGNS: p['reportedSignStates'][s]['state'] = 'negated'
                if kind in ('uncertain_sign', 'affirmed_sign', 'contradictory_sign'):
                    p['reportedSignStates']['cannot_drink']['state'] = 'uncertain' if kind == 'uncertain_sign' else 'affirmed'
                    if kind == 'affirmed_sign': p['reportedSigns'] = ['cannot_drink']
                if kind in ('ambiguous_subject', 'conflicting_type'):
                    p['subject']['status'] = 'ambiguous' if kind == 'ambiguous_subject' else 'resolved'
                    p['abstentions'] = ['multiple_subjects' if kind == 'ambiguous_subject' else 'conflicting_patient_type']
                    p['patientType'] = None
                if kind in ('bleeding', 'breathing_difficulty', 'blurred_vision', 'fluid_loss', 'reduced_fetal_movement'):
                    p['symptoms'] = [kind, ordinary[variant]]
                if kind == 'ambiguous_duration_only':
                    p['abstentions'] = ['ambiguous_duration']
                if kind == 'hydration_only': p['hydrationIssue'] = True
            if kind == 'ambiguous_duration_only':
                # Different explicit negative sign states distinguish valid structured variations.
                p['durationDays'] = None
                for bit, sign in enumerate(SIGNS):
                    p['reportedSignStates'][sign]['state'] = 'negated' if variant & (1 << bit) else 'not_mentioned'
            rows.append({'id': f'care_{index:02d}_{variant}', 'scenarioFamily': f'family_{index:02d}',
                         'scenarioKind': kind, 'split': assignment[index],
                         'source': 'assistant_authored_synthetic_for_team_prototype',
                         'patient': p, 'annotation': annotate(p)})
    seen = {}
    for row in rows:
        key = json.dumps(row['patient'], sort_keys=True)
        if key in seen and seen[key] != row['split']: raise ValueError('Structured duplicate crosses split')
        seen[key] = row['split']
    return rows


if __name__ == '__main__':
    rows = generate()
    path = ROOT/'cases.json'
    path.write_text(json.dumps(rows, indent=2) + '\n')
    manifest = {'schemaVersion': 'care-policy-v1', 'count': len(rows), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'source': 'assistant-authored synthetic; not human-reviewed', 'seed': 20261004,
                'extractionEvaluationDataUsed': False, 'facilityDataUsed': False}
    (ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(manifest)
