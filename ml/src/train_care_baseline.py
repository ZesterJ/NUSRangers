"""Train/evaluate synthetic structured-service policy imitation, never clinical validity."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support, f1_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from care_policy import SERVICES, features, gate, rules_predict

ROOT = Path(__file__).resolve().parents[1]


def targets(rows):
    return np.array([[s in r['annotation']['requiredServices'] for s in SERVICES] for r in rows], dtype=int)


def predict(model, rows, threshold, gated=True):
    scores = model.predict_proba([features(r['patient']) for r in rows])
    result = (scores >= threshold).astype(int)
    if gated:
        for i, row in enumerate(rows):
            if gate(row['patient'])[0] != 'positive': result[i] = 0
    return result


def metrics(rows, predicted):
    y = targets(rows)
    p, r, f, support = precision_recall_fscore_support(y, predicted, zero_division=0)
    unsupported = int(((predicted == 1) & (y == 0)).sum())
    assertions = int(predicted.sum())
    positive = y.any(axis=1)
    return {'cases': len(rows), 'microF1': float(f1_score(y, predicted, average='micro', zero_division=0)),
            'macroF1': float(f1_score(y, predicted, average='macro', zero_division=0)),
            'exactServiceSetMatch': float((y == predicted).all(axis=1).mean()),
            'abstentionRate': float((~predicted.any(axis=1)).mean()),
            'positiveCaseCoverage': float(predicted[positive].any(axis=1).mean()) if positive.any() else None,
            'unsupportedAssertions': unsupported, 'totalAssertions': assertions,
            'unsupportedServiceAssertionRate': unsupported/assertions if assertions else None,
            'perService': {s: {'precision': float(p[i]), 'recall': float(r[i]), 'f1': float(f[i]), 'support': int(support[i])}
                           for i, s in enumerate(SERVICES)}}


def run():
    data_path = ROOT/'data/care/cases.json'
    manifest = json.loads((ROOT/'data/care/manifest.json').read_text())
    if hashlib.sha256(data_path.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('Dataset does not match manifest')
    rows = json.loads(data_path.read_text())
    parts = {s: [r for r in rows if r['split'] == s] for s in ('train', 'validation', 'test')}
    train = [r for r in parts['train'] if r['annotation']['annotationStatus'] != 'unknown']
    model = Pipeline([('features', DictVectorizer(sparse=False)), ('classifier', OneVsRestClassifier(
        LogisticRegression(C=1, class_weight='balanced', solver='liblinear', random_state=42, max_iter=1000)))])
    model.fit([features(r['patient']) for r in train], targets(train))
    trials = []
    for threshold in (.5, .6, .7, .8, .9):
        m = metrics(parts['validation'], predict(model, parts['validation'], threshold))
        trials.append({'threshold': threshold, **m})
    best = min(trials, key=lambda m: (m['unsupportedAssertions'], -m['microF1'], -m['threshold']))
    threshold = best['threshold']
    test = parts['test']
    rules = np.array([[s in rules_predict(r['patient']) for s in SERVICES] for r in test], dtype=int)
    output = {'dataSha256': manifest['sha256'], 'guideVersion': 'care-policy-v1',
              'limitations': ['Assistant-authored synthetic policy imitation; not clinical validation',
                             'Rules and annotations implement the same policy; perfect rules scores are expected',
                             'No real extractor-output or human-reviewed test set', 'Facility capabilities remain unknown'],
              'distribution': {s: {'cases': len(part), 'families': len({r['scenarioFamily'] for r in part}),
                   'annotationStatus': dict(Counter(r['annotation']['annotationStatus'] for r in part)),
                   'services': {service: sum(service in r['annotation']['requiredServices'] for r in part) for service in SERVICES}}
                   for s, part in parts.items()}, 'supervisedTrainCases': len(train),
              'threshold': threshold, 'thresholdSelection': 'validation only: minimum unsupported count, maximum micro-F1, highest threshold',
              'validationTrials': trials, 'test': {}, 'testErrors': []}
    for name, pred in [('rules', rules), ('logisticGated', predict(model, test, threshold)),
                       ('logisticRaw', predict(model, test, threshold, gated=False))]:
        determined = np.array([r['annotation']['annotationStatus'] != 'unknown' for r in test])
        output['test'][name] = {'allCases': metrics(test, pred),
             'determinateCases': metrics([r for r in test if r['annotation']['annotationStatus'] != 'unknown'], pred[determined])}
        for row, expected, actual in zip(test, targets(test), pred):
            if not np.array_equal(expected, actual):
                output['testErrors'].append({'method': name, 'id': row['id'], 'patient': row['patient'],
                     'expected': row['annotation']['requiredServices'], 'predicted': [s for s, value in zip(SERVICES, actual) if value]})
    artifact = ROOT/'artifacts/experimental_care_service_v1.joblib'
    joblib.dump({'model': model, 'services': SERVICES, 'threshold': threshold, 'policyVersion': 'care-policy-v1',
                 'modelVersion': 'experimental-care-service-v1', 'requiresVerification': True,
                 'scoreMeaning': 'uncalibrated synthetic-policy score', 'dataSha256': manifest['sha256'],
                 'trainingIds': [r['id'] for r in train]}, artifact)
    (ROOT/'reports/care_baseline_results.json').write_text(json.dumps(output, indent=2)+'\n')
    lines = ['# Structured care-service prototype results', '',
             'Assistant-authored synthetic policy imitation only. No clinical validity or human review.', '',
             f'400 cases; {len(train)} determinate cases used for supervised fitting. Threshold {threshold} selected on validation.', '',
             '| Split | Cases | Families | Positive / negative / unknown |', '| --- | ---: | ---: | --- |']
    for split, d in output['distribution'].items():
        counts = d['annotationStatus']
        lines.append(f"| {split} | {d['cases']} | {d['families']} | {counts.get('positive',0)} / {counts.get('negative',0)} / {counts.get('unknown',0)} |")
    lines += ['', '| Method (test) | Micro F1 | Macro F1 | Exact set | Abstention | Unsupported / assertions |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name, result in output['test'].items():
        m = result['allCases']
        lines.append(f"| {name} | {m['microF1']:.3f} | {m['macroF1']:.3f} | {m['exactServiceSetMatch']:.3f} | {m['abstentionRate']:.3f} | {m['unsupportedAssertions']} / {m['totalAssertions']} |")
    lines += ['', '| Method | Service | Precision | Recall | F1 | Support |', '| --- | --- | ---: | ---: | ---: | ---: |']
    for name, result in output['test'].items():
        for service, m in result['allCases']['perService'].items():
            lines.append(f"| {name} | {service} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['support']} |")
    lines += ['', '## Interpretation', '',
              'The rules baseline matches the annotation generator by construction. The ML model',
              'learns that same policy, principally patient-type associations; this does not establish',
              'medical service need. Raw ML results expose reliance on the abstention gate.',
              'Structured scenario families are disjoint, but all share the same authored policy.',
              'Complete determinate-only metrics, validation trials, distributions and error cases',
              'are in care_baseline_results.json. Unknown-target cases were excluded from model fitting.', '',
              'Not ready for automatic facility routing: all 209 facility capability records remain',
              'unknown. Do not relax mandatory filtering. Obtain independent human-reviewed labels,',
              'test real extraction outputs, and verify capability evidence before integration.', '',
              'No body-location field exists upstream; none was invented. No clinical labels,',
              'source text, facility identifiers or frozen extraction evaluation cases were used.',
              'Training labels here are synthetic service-policy labels, not diagnoses.']
    (ROOT/'reports/care_baseline_results.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'distribution': output['distribution'], 'threshold': threshold,
                      'test': {k: v['allCases'] for k,v in output['test'].items()}}, indent=2))


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        run()
