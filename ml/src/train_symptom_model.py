"""Train experimental baselines on DERIVED train only; select on validation only.

Run: python ml/src/train_symptom_model.py
No backend integration. Raw labels/splits are retained; model inputs are only text.
"""
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from threadpoolctl import threadpool_limits

from metrics import encode, multilabel_metrics
from prepare_baseline_data import LABELS, ROOT, SEED, digest, prepare


def make_pipeline(features, c, weight):
    choices = {
        'word': TfidfVectorizer(ngram_range=(1, 2), max_features=12000, min_df=1, sublinear_tf=True),
        'char': TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=20000, min_df=1, sublinear_tf=True),
    }
    vectorizer = FeatureUnion(list(choices.items())) if features == 'combined' else choices[features]
    return Pipeline([('features', vectorizer), ('classifier', OneVsRestClassifier(
        LogisticRegression(C=c, class_weight=weight, solver='liblinear', max_iter=2000,
                           random_state=SEED), n_jobs=1))])


def iter_vectorizers(features):
    return features.transformer_list if isinstance(features, FeatureUnion) else [('single', features)]


def verify_preprocessing(pipeline, train_texts):
    # Independently refit only preprocessing on the declared train texts. Both learned
    # vocabulary and IDF must match. This checks corpus membership, not just unseen tokens.
    expected = clone(pipeline.named_steps['features']).fit(train_texts)
    for (_, actual), (_, reference) in zip(iter_vectorizers(pipeline.named_steps['features']), iter_vectorizers(expected)):
        assert actual.vocabulary_ == reference.vocabulary_
        np.testing.assert_array_equal(actual.idf_, reference.idf_)
    return True


def train():
    parts, split_info = prepare()
    texts = {s: [r['text'] for r in rows] for s, rows in parts.items()}
    targets = {s: encode([r['labels'] for r in rows], LABELS) for s, rows in parts.items()}
    configs, best = [], None
    # No cross-validation that could inadvertently mix scenario groups. Fixed small grid.
    with threadpool_limits(limits=1):
        for features in ('word', 'char', 'combined'):
            for c in (1.0, 4.0):
                for weight in (None, 'balanced'):
                    config = {'features': features, 'C': c, 'class_weight': weight}
                    pipeline = make_pipeline(features, c, weight)
                    pipeline.fit(texts['train'], targets['train'])
                    probabilities = pipeline.predict_proba(texts['validation'])
                    candidates = []
                    for threshold in (.3, .5, .7):
                        metric = multilabel_metrics(targets['validation'], probabilities >= threshold, LABELS)
                        candidates.append((metric['macro_f1_supported_labels'], metric['micro_f1'], threshold, metric))
                    # A single global threshold; no threshold tuned against absent labels/test.
                    chosen = max(candidates, key=lambda x: (x[0], x[1], -abs(x[2] - .5)))
                    score = (chosen[0], chosen[1])
                    record = {'config': config, 'threshold': chosen[2], 'validation': chosen[3],
                              'threshold_comparison': [{'threshold': t, 'macro_f1_supported_labels': a, 'micro_f1': b}
                                                       for a, b, t, _ in candidates]}
                    configs.append(record)
                    if best is None or score > best[0]:
                        best = (score, pipeline, record)
        _, pipeline, selected = best
        verify_preprocessing(pipeline, texts['train'])
        # A second full fit proves deterministic selected-model results in this environment.
        repeated = clone(pipeline).fit(texts['train'], targets['train'])
        check_texts = texts['train'] + texts['validation'] + texts['test']
        first = pipeline.predict_proba(check_texts)
        second = repeated.predict_proba(check_texts)
        np.testing.assert_array_equal(first, second)
    feature_info = {name: {'vocabulary_entries': len(vec.vocabulary_), 'idf_bytes': vec.idf_.nbytes}
                    for name, vec in iter_vectorizers(pipeline.named_steps['features'])}
    bundle = {'experimental': True, 'purpose': 'synthetic-data benchmark only; not deployment ready',
              'pipeline': pipeline, 'labels': list(LABELS), 'threshold': selected['threshold'],
              'modelVersion': 'experimental-symptoms-tfidf-v1', 'training_config': selected['config'],
              'split_manifest_sha256': split_info['record_manifest_sha256'],
              'train_ids': [r['id'] for r in parts['train']],
              'training_text_sha256': digest(texts['train']),
              'versions': {'python': platform.python_version(), 'sklearn': sklearn.__version__,
                           'numpy': np.__version__, 'scipy': scipy.__version__, 'joblib': joblib.__version__}}
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    path = artifacts / 'experimental_symptom_baseline.joblib'
    joblib.dump(bundle, path, compress=3)
    metadata = {k: v for k, v in bundle.items() if k != 'pipeline'}
    metadata['preprocessing'] = feature_info
    metadata['classifier_parameters'] = sum(est.coef_.size + est.intercept_.size for est in pipeline.named_steps['classifier'].estimators_)
    metadata['preprocessing_serialized_bytes'] = len(__import__('pickle').dumps(pipeline.named_steps['features']))
    metadata['artifact_bytes'] = path.stat().st_size
    metadata['artifact_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata['reproducibility'] = {'selected_refit_probabilities_identical': True,
                                  'prediction_sha256': hashlib.sha256(first.tobytes()).hexdigest(),
                                  'train_only_vocabulary_and_idf_verified': True}
    (artifacts / 'experimental_symptom_baseline.metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    summary = {'benchmark': 'synthetic-data benchmark results', 'selection': 'validation supported-label macro F1, then micro F1; no test selection',
               'split': split_info, 'configurations': configs, 'selected': selected, 'artifact': metadata}
    (ROOT / 'reports/training_results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'selected': selected['config'], 'threshold': selected['threshold'],
                      'validation_micro_f1': selected['validation']['micro_f1'], 'artifact_bytes': path.stat().st_size}, indent=2))
    return bundle


if __name__ == '__main__':
    train()
