"""Evaluate frozen experimental artifact; never fits or selects anything.

Synthetic held-out labels are scored as supplied. Explicit development diagnostics
have separately authored expectations; they are not independent acceptance data.
"""
import hashlib
import json
import platform
import resource
import statistics
import time

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from baseline_rules import VERSION, extract_rules
from metrics import encode, multilabel_metrics
from prepare_baseline_data import LABELS, ROOT, prepare

SIGNS = ('cannot_drink', 'convulsions', 'bleeding')
SCALARS = ('patientType', 'durationDays', 'hydrationIssue')


def rule_metrics(expected, predicted, authoritative=False):
    report = {}
    for field in SCALARS:
        truth, pred = [r[field] for r in expected], [r[field] for r in predicted]
        known = sum(x is not None for x in pred)
        missing = [i for i, x in enumerate(truth) if x is None]
        wrong = sum(p is not None and p != t for p, t in zip(pred, truth))
        report[field] = {'examples': len(truth), 'exact_agreement': sum(p == t for p, t in zip(pred, truth))/len(truth),
                         'non_null_predictions': known, 'coverage': known/len(truth),
                         'missing_expected': len(missing),
                         'unknown_handling_accuracy': sum(pred[i] is None for i in missing)/len(missing) if missing else None,
                         'confusion': {f'{t!r} -> {p!r}': sum(a == t and b == p for a, b in zip(truth, pred))
                                       for t, p in sorted(set(zip(truth, pred)), key=str)}}
        if authoritative:
            report[field]['unsupported_assertions_vs_diagnostic_expectation'] = wrong
            report[field]['unsupported_assertion_rate_among_assertions'] = wrong/known if known else None
    report['reportedSigns'] = multilabel_metrics(encode(expected, SIGNS, 'reportedSigns'), encode(predicted, SIGNS, 'reportedSigns'), SIGNS)
    assertions = sum(len(r['reportedSigns']) for r in predicted)
    wrong_signs = sum(len(set(p['reportedSigns']) - set(t['reportedSigns'])) for p, t in zip(predicted, expected))
    if authoritative:
        report['reportedSigns']['unsupported_assertion_rate_among_assertions'] = wrong_signs/assertions if assertions else None
        count = sum(report[f]['non_null_predictions'] for f in SCALARS) + assertions
        wrong = sum(report[f]['unsupported_assertions_vs_diagnostic_expectation'] for f in SCALARS) + wrong_signs
        report['all_field_assertions'] = {'count': count, 'unsupported': wrong, 'rate': wrong/count if count else None}
    return report


def evaluate_symptoms(bundle, rows, expected_key='labels'):
    targets = encode([r[expected_key] for r in rows], LABELS)
    probabilities = bundle['pipeline'].predict_proba([r['text'] for r in rows])
    predicted = probabilities >= bundle['threshold']
    result = multilabel_metrics(targets, predicted, LABELS)
    result['by_language'] = {lang: multilabel_metrics(targets[[r['language'] == lang for r in rows]],
                              predicted[[r['language'] == lang for r in rows]], LABELS)
                             for lang in sorted({r['language'] for r in rows})}
    errors = []
    for i, row in enumerate(rows):
        fp = [label for j, label in enumerate(LABELS) if predicted[i, j] and not targets[i, j]]
        fn = [label for j, label in enumerate(LABELS) if targets[i, j] and not predicted[i, j]]
        if fp or fn:
            errors.append({'id': row['id'], 'language': row['language'], 'text': row['text'],
                           'category': row.get('category', 'synthetic_template'),
                           'expected': row[expected_key]['symptoms'],
                           'predicted': [label for j, label in enumerate(LABELS) if predicted[i, j]],
                           'false_positives': fp, 'false_negatives': fn})
    return result, errors


def benchmark(bundle, rows):
    texts = [r['text'] for r in rows]
    operations = {
        'rules': lambda t: extract_rules(t),
        'symptom_pipeline': lambda t: bundle['pipeline'].predict_proba([t]) >= bundle['threshold'],
    }
    out = {'hardware': platform.machine(), 'platform': platform.platform(), 'python': platform.python_version(),
           'threads': 1, 'batch_size': 1, 'iterations': 1000,
           'scope': 'local Python preprocessing+inference; no HTTP, ASR or application overhead; not a production benchmark'}
    with threadpool_limits(limits=1):
        for name, fn in operations.items():
            for text in texts[:20]:
                fn(text)
            times = []
            for i in range(1000):
                start = time.perf_counter_ns()
                fn(texts[i % len(texts)])
                times.append((time.perf_counter_ns() - start)/1e6)
            out[name] = {'p50_ms': statistics.median(times), 'p95_ms': float(np.percentile(times, 95))}
    out['process_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system() == 'Darwin' else 1024)
    out['rss_scope'] = 'whole evaluation process including imports and metrics; not incremental model RAM'
    return out


def render(results, training, errors, rule_errors):
    lines = ['# First baseline: synthetic-data benchmark results', '',
             'Experimental only. No clinical validity, real-world performance or deployment readiness is claimed.',
             'Model selection used validation only. No production model decision has been made.', '',
             '## Split and leakage controls', '',
             f"Derived rows: {training['split']['rows_per_split']}; families: {training['split']['families_per_split']}.",
             'Family = patient type + symptom set + danger-sign set + hydration + notes; excludes duration/language.',
             '31 annotation-based scenario proxies; no recovered generator IDs. No family/exact-text/sentence-bag overlap.',
             'Labels are grouping metadata, never features. Only derived-training text fits vocabulary, IDF and classifiers.',
             'Original split labels remain in the ignored derived manifest. This is a new partition, not the original train split.',
             'Single-family fatigue, fluid_loss, reduced_fetal_movement were reserved for training before fitting.',
             'Test has positive support for only five labels; this benchmark cannot establish generalization for all 13.',
             f"Residual held-out sentence-fragment overlap: {training['split']['heldout_sentence_fragment_overlap_fraction']}.",
             'Shared phrase leakage remains; results measure held-out scenario recombination, not unseen natural language.', '',
             '## Configuration comparison (validation only)', '',
             '| Features | C | Class weight | Threshold | Supported macro F1 | Micro F1 |', '|---|---:|---|---:|---:|---:|']
    for r in training['configurations']:
        c = r['config']; m = r['validation']
        lines.append(f"| {c['features']} | {c['C']} | {c['class_weight']} | {r['threshold']} | {m['macro_f1_supported_labels']:.4f} | {m['micro_f1']:.4f} |")
    lines += ['', f"Selected experimental configuration: `{training['selected']['config']}`, global threshold {training['selected']['threshold']}.",
              'Selection maximizes validation supported-label macro F1, then micro F1. Tie retains the first configuration.', '',
              '## Symptom results', '', '| Set | N | Micro P | Micro R | Micro F1 | Supported macro F1 | Exact set |', '|---|---:|---:|---:|---:|---:|---:|']
    for name, m in [('derived test', results['symptoms_test']), ('authored diagnostics', results['symptoms_diagnostics'])]:
        lines.append(f"| {name} | {m['examples']} | {m['micro_precision']:.4f} | {m['micro_recall']:.4f} | {m['micro_f1']:.4f} | {m['macro_f1_supported_labels']:.4f} | {m['exact_set_match']:.4f} |")
    lines += ['', 'Diagnostics are assistant-authored development cases, not blinded, independently authored or clinician/native-Swahili reviewed.',
              'They were not used for vectorizer fitting, training, threshold selection or configuration selection.', '',
              '### Derived-test per-label metrics', '', '| Label | Support | Precision | Recall | F1 | FP | FN |', '|---|---:|---:|---:|---:|---:|---:|']
    def number(v):
        return 'N/A' if v is None else f'{v:.4f}'
    for label, m in results['symptoms_test']['per_label'].items():
        lines.append(f"| {label} | {m['support']} | {number(m['precision'])} | {number(m['recall'])} | {number(m['f1'])} | {m['false_positives']} | {m['false_negatives']} |")
    lines += ['', 'No-support recall is N/A; a false-positive-only label still gets F1=0. JSON also reports all-13 macro F1 with undefined values set to zero.', '',
              '### Language breakdown', '', '| Set | Language | N | Micro F1 | Supported macro F1 | Exact set |', '|---|---|---:|---:|---:|---:|']
    for set_name in ('symptoms_test', 'symptoms_diagnostics'):
        for lang, m in results[set_name]['by_language'].items():
            lines.append(f"| {set_name} | {lang} | {m['examples']} | {m['micro_f1']:.4f} | {m['macro_f1_supported_labels']:.4f} | {m['exact_set_match']:.4f} |")
    lines += ['', '## Rules', '', 'Raw-label agreement is not factual extraction accuracy: supplied adult/hydration/duration labels have known problems.',
              'Unsupported-assertion metrics are only computed against explicit diagnostic expectations; raw labels cannot establish grounding.', '',
              '| Field | Raw test agreement | Diagnostic accuracy | Unknown expected | Unknown accuracy | Unsupported/asserted |', '|---|---:|---:|---:|---:|---|']
    for f in SCALARS:
        raw, diag = results['rules_raw_test'][f], results['rules_diagnostics'][f]
        lines.append(f"| {f} | {raw['exact_agreement']:.4f} | {diag['exact_agreement']:.4f} | {diag['missing_expected']} | {number(diag['unknown_handling_accuracy'])} | {diag['unsupported_assertions_vs_diagnostic_expectation']}/{diag['non_null_predictions']} |")
    lines += ['', 'Reported-sign diagnostic metrics:', '', '| Sign | Support | P | R | F1 | FP | FN |', '|---|---:|---:|---:|---:|---:|---:|']
    for label, m in results['rules_diagnostics']['reportedSigns']['per_label'].items():
        lines.append(f"| {label} | {m['support']} | {number(m['precision'])} | {number(m['recall'])} | {number(m['f1'])} | {m['false_positives']} | {m['false_negatives']} |")
    lines += ['', f"All diagnostic rule-field assertions: {results['rules_diagnostics']['all_field_assertions']}.",
              'Full scalar confusion matrices, sign FP/FN counts, and original-label disagreements are in JSON.', '',
              '## Size, speed and reproducibility', '',
              f"Compressed artifact: {training['artifact']['artifact_bytes']:,} bytes. Classifier coefficients + intercepts: {training['artifact']['classifier_parameters']:,}.",
              f"Serialized preprocessing: {training['artifact']['preprocessing_serialized_bytes']:,} bytes; vocabulary/IDF details: `{training['artifact']['preprocessing']}`.",
              f"Rules source: {results['rules_source_bytes']} bytes; no fitted parameters.",
              f"First artifact deserialization in evaluation process: {results['artifact_load_ms']:.3f} ms (OS cache state uncontrolled; not cold-machine startup).",
              'Warm batch-size-one CPU benchmark, 1,000 iterations each, one numerical-library thread:', '',
              '```json', json.dumps(results['benchmark'], indent=2), '```', '',
              f"Reproducibility checks: `{training['artifact']['reproducibility']}`.",
              'Exact software versions and training configuration are in training_results.json and artifact metadata.',
              'Numbers vary by hardware/cache/load; latency is not expected to reproduce bit-for-bit.', '',
              '## Recommendation', '',
              'Do not choose a production model or move directly to a transformer. First obtain reviewed unknown/negation/subject annotations and independently authored bilingual evaluation.',
              'The linear baseline is a useful measurable reference; its shortcomings on natural-style diagnostics must not be disguised by synthetic scores.',
              'A small multilingual encoder is only a justified next comparison if reviewed errors establish a semantic gap beyond data/label/scope defects.',
              'No backend, /predict, frontend, speech, diagnosis or routing changes were made.']
    (ROOT / 'reports/baseline_results.md').write_text('\n'.join(lines) + '\n')
    review = ['# First-baseline error analysis', '', 'Synthetic-data benchmark results; experimental, not clinical validation.', '',
              'All mismatches are preserved in baseline_errors.json. No raw labels were modified and no model was tuned against test/diagnostics.', '',
              '## Learned symptoms', '',
              'Held-out scenario changes can break associations learned from templated co-occurrence (e.g. symptom ↔ patient group).',
              'The classifier has no explicit negation, uncertainty, temporal or subject mechanism. Document-level presence is not a verified patient finding.',
              'Diagnostic targets omit negated/historical/uncertain mentions; multi-subject symptom targets retain document mentions only, demonstrating why subject assignment is a separate task.',
              'Inspect language breakdowns with their denominators: Swahili diagnostics are unreviewed fictional examples, not a language-competence estimate.', '',
              'Representative errors (first example of each error direction/category/language):', '']
    seen = set()
    for source, items in errors.items():
        for e in items:
            for direction in ('false_positives', 'false_negatives'):
                key = (source, e['category'], e['language'], direction)
                if e[direction] and key not in seen:
                    seen.add(key)
                    review.append(f"- {source} / {e['id']} / {e['language']} / {e['category']}: {e['text']!r}. {direction}: {e[direction]}; expected {e['expected']}; predicted {e['predicted']}.")
    review += ['', '## Rule fields', '',
               'The raw data are a comparison reference only. First-person-only adult labels and hydration false without a drinking statement are not evidence of rule failure.',
               'Approximation, yesterday/today, conflicting durations, and broad negation scope cause deliberate abstention. Some conservatism loses explicitly stated information.',
               'English/Swahili phrase coverage is narrow. Cannot-drink gold labels include reduced-drinking variants; review bilingual semantics before calling all such abstentions false negatives.',
               'The rules do not resolve arbitrary experiencers, pronouns, uncertainty or historical scope. Review the diagnostic counterexamples below.', '',
               '### Diagnostic rule mismatches (all)', '']
    for e in rule_errors['diagnostics']:
        review.append(f"- {e['id']} ({e['category']}): {e['text']!r}; differences: `{e['differences']}`.")
    review += ['', '### Raw-test reported-sign false negatives (first example per sign)', '']
    seen = set()
    for e in rule_errors['raw_test']:
        for sign in e['false_negative_signs']:
            if sign not in seen:
                seen.add(sign)
                review.append(f"- {e['id']}: {e['text']!r}; supplied sign {sign}; extracted {e['predicted']['reportedSigns']}. Review scope/degree of inability before changing rules or labels.")
    if not seen:
        review.append('No reported-sign false negatives on this derived test partition; inspect label support before generalizing.')
    review += ['', '## Coverage limits and next data work', '',
               'Short utterances, misspellings, phrasing variation, missing values, multiple symptoms, explicit denials, ambiguity and multiple subjects are tagged in diagnostics; per-category symptom metrics are in JSON.',
               'The derived test covers only five positive symptom labels and few scenario families. Three single-family labels cannot be both learned and evaluated independently with this corpus.',
               'No independent acceptance set exists. Commission separate English/Swahili descriptions and dual-reviewed evidence/subject/negation/unknown labels before comparing an encoder.',
               'Do not relabel raw data to improve scores. Future corrections require ID, original/new labels, reason and reviewer; keep corrected evaluation separate.',
               'One development fix is recorded in rule_revision_log.json: and/na clause splitting lost uncertainty scope and broke Swahili bleeding phrases. No gold labels changed.',
               'Rule scope/code fixes should be regression-tested and versioned; changing a rule after inspecting a diagnostic makes that case development data, not fresh evaluation.']
    (ROOT / 'reports/error_analysis.md').write_text('\n'.join(review) + '\n')


def main():
    parts, info = prepare()
    start = time.perf_counter_ns()
    bundle = joblib.load(ROOT / 'artifacts/experimental_symptom_baseline.joblib')
    load_ms = (time.perf_counter_ns() - start)/1e6
    training = json.loads((ROOT / 'reports/training_results.json').read_text())
    assert bundle['split_manifest_sha256'] == info['record_manifest_sha256']
    assert bundle['train_ids'] == [r['id'] for r in parts['train']]
    cases = json.loads((ROOT / 'data/evaluation/baseline_diagnostics.json').read_text())['cases']
    with threadpool_limits(limits=1):
        symptom_test, errors_test = evaluate_symptoms(bundle, parts['test'])
        symptom_diag, errors_diag = evaluate_symptoms(bundle, cases, 'expected')
        symptom_diag['by_category'] = {}
        for tag in sorted({r['category'] for r in cases}):
            metrics, _ = evaluate_symptoms(bundle, [r for r in cases if r['category'] == tag], 'expected')
            metrics.pop('by_language')
            symptom_diag['by_category'][tag] = metrics
    raw_expected = [{'patientType': r['labels']['patient_type'], 'durationDays': r['labels']['duration_days'],
                     'hydrationIssue': r['labels']['hydration_issue'],
                     'reportedSigns': [s for s in SIGNS if s in r['labels']['danger_signs']]} for r in parts['test']]
    raw_pred = [extract_rules(r['text']) for r in parts['test']]
    diag_pred = [extract_rules(r['text']) for r in cases]
    rule_errors = {}
    for name, rows, expectations, predictions in [('raw_test', parts['test'], raw_expected, raw_pred),
                                                ('diagnostics', cases, [r['expected'] for r in cases], diag_pred)]:
        rule_errors[name] = []
        for row, expected, pred in zip(rows, expectations, predictions):
            differences = {f: {'expected': expected[f], 'predicted': pred[f]} for f in (*SCALARS, 'reportedSigns')
                           if (set(expected[f]) != set(pred[f]) if f == 'reportedSigns' else expected[f] != pred[f])}
            if differences:
                rule_errors[name].append({'id': row['id'], 'text': row['text'], 'category': row.get('category', 'synthetic'),
                                         'differences': differences, 'predicted': pred,
                                         'false_negative_signs': sorted(set(expected['reportedSigns']) - set(pred['reportedSigns']))})
    results = {'benchmark_label': 'synthetic-data benchmark results', 'rules_version': VERSION,
               'symptoms_test': symptom_test, 'symptoms_diagnostics': symptom_diag,
               'rules_raw_test': rule_metrics(raw_expected, raw_pred),
               'rules_diagnostics': rule_metrics([r['expected'] for r in cases], diag_pred, authoritative=True),
               'rules_source_bytes': (ROOT / 'src/baseline_rules.py').stat().st_size,
               'artifact_load_ms': load_ms, 'benchmark': benchmark(bundle, parts['test']),
               'diagnostic_cases_sha256': hashlib.sha256((ROOT / 'data/evaluation/baseline_diagnostics.json').read_bytes()).hexdigest()}
    (ROOT / 'reports/baseline_results.json').write_text(json.dumps(results, indent=2) + '\n')
    errors = {'derived_test': errors_test, 'diagnostics': errors_diag}
    (ROOT / 'reports/baseline_errors.json').write_text(json.dumps({'symptoms': errors, 'rules': rule_errors}, indent=2, ensure_ascii=False) + '\n')
    render(results, training, errors, rule_errors)
    print(json.dumps({'test_micro_f1': symptom_test['micro_f1'], 'test_macro_supported': symptom_test['macro_f1_supported_labels'],
                      'diagnostics_micro_f1': symptom_diag['micro_f1'], 'rules_diagnostic_assertions': results['rules_diagnostics']['all_field_assertions'],
                      'benchmark': results['benchmark']}, indent=2))


if __name__ == '__main__':
    main()
