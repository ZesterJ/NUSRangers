"""Regression and data-boundary tests; diagnostics remain scored, not forced to pass."""
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from baseline_rules import extract_rules
from prepare_baseline_data import LABELS, ROOT, prepare
from train_symptom_model import make_pipeline, verify_preprocessing


@pytest.mark.parametrize('text,field,expected', [
    ('I have a fever', 'patientType', None),
    ('My child has fever', 'patientType', 'child'),
    ('I am pregnant', 'patientType', 'pregnant'),
    ('I am 30 years old', 'patientType', 'adult'),
    ('The child is not drinking', 'hydrationIssue', True),
    ('The child is drinking normally', 'hydrationIssue', False),
    ('The child has fever', 'hydrationIssue', None),
    ('Fever for three days', 'durationDays', 3),
    ('Fever for about three days', 'durationDays', None),
    ('Fever for two days, cough for three days', 'durationDays', None),
    ('No bleeding', 'reportedSigns', []),
    ('Maybe I am pregnant and bleeding', 'reportedSigns', []),
    ('Ninatokwa na damu', 'reportedSigns', ['bleeding']),
    ('Mtoto wangu hawezi kunywa vizuri', 'reportedSigns', []),
    ('Mtoto wangu hawezi kunywa', 'reportedSigns', ['cannot_drink']),
    ('Hakuna degedege', 'reportedSigns', []),
    ('The child had a seizure', 'reportedSigns', ['convulsions']),
])
def test_rule_regressions(text, field, expected):
    assert extract_rules(text)[field] == expected


def test_multiple_subjects_abstain():
    result = extract_rules('I have fever and my child is bleeding')
    assert all(result[f] is None for f in ('patientType', 'durationDays', 'hydrationIssue'))
    assert result['reportedSigns'] == []


def test_evidence_is_literal():
    for text in ['I am 30 years old', 'Mtoto wangu hawezi kunywa', 'Fever for three days', 'No trouble drinking']:
        for spans in extract_rules(text)['evidence'].values():
            assert all(span in text for span in spans)


def test_split_is_deterministic_and_disjoint():
    a, info_a = prepare()
    b, info_b = prepare()
    assert a == b and info_a == info_b
    assert info_a['family_overlap'] == info_a['exact_and_sentence_bag_overlap'] == 0
    ids = {s: {r['id'] for r in rows} for s, rows in a.items()}
    assert not ids['train'] & (ids['validation'] | ids['test'])
    assert not ids['validation'] & ids['test']
    assert len(set.union(*ids.values())) == 1200


@pytest.mark.parametrize('features', ['word', 'char', 'combined'])
def test_fit_does_not_learn_evaluation_tokens(features):
    pipeline = make_pipeline(features, 1.0, None)
    train = ['cough fever', 'fever', 'weak cough', 'weak']
    target = np.array([[1, 1], [0, 1], [1, 0], [0, 0]])
    pipeline.fit(train, target)
    before = joblib.hash(pipeline.named_steps['features'])
    pipeline.predict_proba(['zzzzheldoutsentinel'])
    assert before == joblib.hash(pipeline.named_steps['features'])
    assert verify_preprocessing(pipeline, train)


def test_artifact_matches_training_partition():
    path = ROOT / 'artifacts/experimental_symptom_baseline.joblib'
    if not path.exists():
        pytest.skip('Run training first for the artifact integration check')
    bundle = joblib.load(path)
    parts, info = prepare()
    assert bundle['experimental'] is True
    assert bundle['labels'] == list(LABELS)
    assert bundle['train_ids'] == [r['id'] for r in parts['train']]
    assert bundle['split_manifest_sha256'] == info['record_manifest_sha256']
    assert verify_preprocessing(bundle['pipeline'], [r['text'] for r in parts['train']])
