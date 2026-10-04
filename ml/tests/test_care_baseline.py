"""Dataset separation, missingness, policy abstention and metric contracts."""
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from care_policy import SERVICES, annotate, features, gate
from prepare_care_data import ROOT, generate
from train_care_baseline import metrics


def test_dataset_reproducibility_and_group_separation():
    rows = generate()
    assert rows == json.loads((ROOT/'cases.json').read_text())
    assert len(rows) == 400
    families, patients = {}, {}
    for row in rows:
        assert row['id'].startswith('care_')
        family = row['scenarioFamily']
        assert family not in families or families[family] == row['split']
        families[family] = row['split']
        signature = json.dumps(row['patient'], sort_keys=True)
        assert signature not in patients or patients[signature] == row['split']
        patients[signature] = row['split']
        assert row['annotation'] == annotate(row['patient'])
        assert 'painLocations' not in row['patient']
    assert {s: sum(r['split'] == s for r in rows) for s in ('train','validation','test')} == {'train':240,'validation':80,'test':80}


def test_features_no_label_or_metadata_leakage():
    row = generate()[0]
    before = features(row['patient'])
    row['patient'].update(sourceText='DO NOT USE', evidence={'fake':'text'}, modelVersion='fake')
    assert features(row['patient']) == before
    assert not any('care_' in str(v) or 'family_' in str(v) for v in before.values())
    p = row['patient']
    encoded = []
    for value in (True, False, None):
        p['hydrationIssue'] = value
        encoded.append(features(p)['hydration'])
    assert len(set(encoded)) == 3


def test_unknown_labels_not_negative_and_missing_not_no_care():
    rows = generate()
    for row in rows:
        a = row['annotation']
        if a['annotationStatus'] == 'unknown':
            assert set(a['serviceStates'].values()) == {'unknown'}
            assert not a['requiredServices']
        if row['scenarioKind'] in ('missing','negative_hydration','negative_signs','ambiguous_duration_only'):
            assert a['reason'] == 'no_supported_finding'
        if row['scenarioKind'] == 'contradictory_sign':
            assert gate(row['patient']) == ('unknown','contradictory_sign_projection')


def test_unknown_predictions_count_unsupported():
    row = next(r for r in generate() if r['annotation']['annotationStatus'] == 'unknown')
    m = metrics([row], np.array([[1,0,0]]))
    assert m['unsupportedAssertions'] == 1 and m['unsupportedServiceAssertionRate'] == 1
    assert metrics([row], np.zeros((1,3),dtype=int))['unsupportedServiceAssertionRate'] is None


def test_report_support_and_no_test_threshold_selection():
    report = json.loads((ROOT.parents[1]/'reports/care_baseline_results.json').read_text())
    assert len(report['validationTrials']) == 5
    assert report['test']['logisticGated']['allCases']['cases'] == 80
    assert report['supervisedTrainCases'] == 184
    assert report['distribution']['train']['annotationStatus']['unknown'] == 56
    assert set(report['test']['rules']['allCases']['perService']) == set(SERVICES)
