"""Paired OLD vs NEW evaluation. Frozen model/splits; no fitting or threshold tuning.

Run after first-baseline artifact exists. Original 48 diagnostics are unchanged.
Expanded cases are development diagnostics, not an independent acceptance benchmark.
"""
import hashlib
import json
import platform
import time

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from baseline_rules import extract_rules as old_rules
from evaluate import SCALARS, SIGNS, rule_metrics
from reference.extraction_v2 import Config, ExtractionPipeline, extract_rules as new_rules, VERSION
from metrics import encode, multilabel_metrics
from prepare_baseline_data import LABELS, ROOT, prepare


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows, predicted):
    y = encode([r['expected'] for r in rows], LABELS)
    p = encode(predicted, LABELS)
    result = multilabel_metrics(y, p, LABELS)
    result['false_positives'] = int(((y == 0) & (p == 1)).sum())
    result['false_negatives'] = int(((y == 1) & (p == 0)).sum())
    result['unsupported_symptom_rate_vs_reference'] = result['false_positives']/int(p.sum()) if p.sum() else None
    result['by_language'] = {}
    for language in sorted({r['language'] for r in rows}):
        mask = [r['language'] == language for r in rows]
        result['by_language'][language] = multilabel_metrics(y[mask], p[mask], LABELS)
    return result


def raw_rows(rows):
    return [dict(r, expected={'symptoms': r['labels']['symptoms'], 'patientType': r['labels']['patient_type'],
                             'durationDays': r['labels']['duration_days'], 'hydrationIssue': r['labels']['hydration_issue'],
                             'reportedSigns': [s for s in SIGNS if s in r['labels']['danger_signs']]}) for r in rows]


def benchmark(bundle, pipeline, rows):
    operations = {'old_rules': old_rules, 'new_rules': new_rules,
                  'frozen_ml': lambda text: bundle['pipeline'].predict_proba([text]),
                  'old_full': lambda text: (old_rules(text), bundle['pipeline'].predict_proba([text]) >= bundle['threshold']),
                  'new_full': pipeline.extract}
    report = {'hardware': platform.machine(), 'platform': platform.platform(), 'threads': 1, 'batch_size': 1,
              'iterations': 1000, 'scope': 'warm local CPU; no network/HTTP; same corpus/order for each operation'}
    for name, fn in operations.items():
        for row in rows[:20]:
            fn(row['text'])
        times = []
        for i in range(1000):
            start = time.perf_counter_ns()
            fn(rows[i % len(rows)]['text'])
            times.append((time.perf_counter_ns()-start)/1e6)
        report[name] = {'p50_ms': float(np.median(times)), 'p95_ms': float(np.percentile(times,95))}
    return report


def run():
    artifact = ROOT / 'artifacts/experimental_symptom_baseline.joblib'
    before_hash = sha(artifact)
    bundle = joblib.load(artifact)
    original = json.loads((ROOT / 'reports/baseline_results.json').read_text())
    parts, split = prepare()
    assert bundle['split_manifest_sha256'] == split['record_manifest_sha256']
    assert bundle['training_config'] == {'features': 'char', 'C': 1.0, 'class_weight': 'balanced'}
    pipeline = ExtractionPipeline(bundle, Config(threshold=bundle['threshold']))
    diagnostics = json.loads((ROOT / 'data/evaluation/baseline_diagnostics.json').read_text())['cases']
    expanded = json.loads((ROOT / 'data/evaluation/expanded_diagnostics.json').read_text())['cases']
    datasets = {'synthetic_validation': raw_rows(parts['validation']), 'synthetic_test': raw_rows(parts['test']),
                'original_diagnostics': diagnostics, 'expanded_diagnostics': expanded}
    report = {'label': 'synthetic-data benchmark results; authored cases are development diagnostics, not clinical validation',
              'extraction_version': VERSION, 'model_sha256': before_hash, 'threshold': pipeline.config.threshold,
              'split_manifest_sha256': split['record_manifest_sha256'], 'datasets': {}}
    errors = {}
    snapshots = {}
    with threadpool_limits(limits=1):
        for name, rows in datasets.items():
            scores = bundle['pipeline'].predict_proba([r['text'] for r in rows])
            old = [dict(old_rules(r['text']), symptoms=[label for label, s in zip(LABELS, score) if s >= bundle['threshold']])
                   for r, score in zip(rows, scores)]
            new = [pipeline.extract(r['text'], r.get('target_subject'), scores=score) for r, score in zip(rows, scores)]
            again = [pipeline.extract(r['text'], r.get('target_subject'), scores=score) for r, score in zip(rows, scores)]
            assert new == again
            result = {}
            for method, predictions in [('old',old),('new',new)]:
                symptom = metrics(rows, predictions)
                rules = rule_metrics([r['expected'] for r in rows], predictions, authoritative='diagnostics' in name)
                result[method] = {'symptoms': symptom, 'rules': rules}
                if 'diagnostics' in name:
                    symptom_assertions = sum(len(r['symptoms']) for r in predictions)
                    counts = rules['all_field_assertions']
                    total = counts['count'] + symptom_assertions
                    wrong = counts['unsupported'] + symptom['false_positives']
                    result[method]['all_assertions_vs_reference'] = {'count':total, 'unsupported':wrong, 'rate':wrong/total if total else None}
            result['evidence_check'] = {'assertions':0,'missing_or_invalid':0}
            for row, pred in zip(rows,new):
                fields = [f for f in SCALARS if pred[f] is not None]
                fields += [f'symptoms.{s}' for s in pred['symptoms']]+[f'reportedSigns.{s}' for s in pred['reportedSigns']]
                for field in fields:
                    result['evidence_check']['assertions'] += 1
                    evidence = pred['evidence'].get(field,[])
                    assert evidence and all(e['text'] and row['text'][e['start']:e['end']]==e['text'] for e in evidence)
            report['datasets'][name] = result
            errors[name] = []
            for row, prev, current in zip(rows,old,new):
                diffs = {f: {'expected':row['expected'][f],'old':prev[f],'new':current[f]} for f in (*SCALARS,'reportedSigns','symptoms')
                         if (set(current[f]) != set(row['expected'][f]) or set(prev[f]) != set(row['expected'][f]) if f in ('reportedSigns','symptoms')
                             else current[f] != row['expected'][f] or prev[f] != row['expected'][f])}
                if diffs:
                    errors[name].append({'id':row['id'],'text':row['text'],'language':row['language'],
                                         'category':row.get('category','synthetic_template'),'differences':diffs})
            snapshots[name] = [{'id':r['id'],'old':o,'new':n} for r,o,n in zip(rows,old,new)]
        report['latency'] = benchmark(bundle, pipeline, parts['test'])
    for metric in ('micro_f1','macro_f1_supported_labels','exact_set_match'):
        assert report['datasets']['synthetic_test']['old']['symptoms'][metric] == original['symptoms_test'][metric]
        assert report['datasets']['original_diagnostics']['old']['symptoms'][metric] == original['symptoms_diagnostics'][metric]
    assert before_hash == sha(artifact)
    report['verification'] = {'model_unchanged':True,'original_metrics_reproduced':True,'repeated_outputs_identical':True,
                              'all_populated_fields_have_exact_spans':True,
                              'original_diagnostics_sha256':sha(ROOT/'data/evaluation/baseline_diagnostics.json'),
                              'expanded_diagnostics_sha256':sha(ROOT/'data/evaluation/expanded_diagnostics.json')}
    (ROOT/'reports/improvement_results.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'reports/improvement_errors.json').write_text(json.dumps(errors,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'data/processed/improvement_predictions.json').write_text(json.dumps(snapshots,indent=2,ensure_ascii=False)+'\n')
    render(report,errors)
    print(json.dumps({name:{method:{k:v[method]['symptoms'][k] for k in ('micro_f1','macro_f1_supported_labels','exact_set_match','false_positives','false_negatives')}
                           for method in ('old','new')} for name,v in report['datasets'].items()},indent=2))
    return report


def render(report,errors):
    lines=['# Evidence-gated pipeline: OLD vs NEW', '',report['label'], '',
           'The character TF-IDF + balanced logistic regression artifact and 0.3 threshold are unchanged. No retraining or threshold search.',
           'Only predictions with an affirmed exact mention, resolved/unambiguous subject scope and sufficient classifier score are returned.',
           'Classifier scores are uncalibrated, not clinical confidence. No keyword-only rescue is used, so recall can decrease.', '',
           '## Paired symptom results', '', '| Dataset | Pipeline | Micro F1 | Supported macro F1 | All-13 macro F1* | Exact set | FP | FN |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for name,r in report['datasets'].items():
        for method in ('old','new'):
            m=r[method]['symptoms']
            lines.append(f"| {name} | {method} | {m['micro_f1']:.4f} | {m['macro_f1_supported_labels']:.4f} | {m['macro_f1_all_labels_zero_undefined']:.4f} | {m['exact_set_match']:.4f} | {m['false_positives']} | {m['false_negatives']} |")
    lines += ['', '*All-13 macro assigns zero to undefined scores. The synthetic test has positive support for five labels only.',
              'Original 48 diagnostics retain their original document-level symptom labels for multiple-person cases. New subject abstention can therefore count as a false negative; these labels were not silently rewritten.',
              'The expanded 42 cases explicitly expect abstention for unresolved multiple people and test one explicit husband target. Keep the suites separate.',
              'All authored cases are assistant-authored development material, not blinded or clinician/native-Swahili reviewed. No training code consumes them.', '',
              '## Per-label precision / recall / F1', '']
    def fmt(x): return 'N/A' if x is None else f'{x:.3f}'
    for name,r in report['datasets'].items():
        lines += [f'### {name}', '', '| Label | Support | OLD P/R/F1 | NEW P/R/F1 | OLD FP/FN | NEW FP/FN |', '|---|---:|---|---|---|---|']
        for label in LABELS:
            a,b=[r[m]['symptoms']['per_label'][label] for m in ('old','new')]
            lines.append(f"| {label} | {a['support']} | {' / '.join(fmt(a[k]) for k in ('precision','recall','f1'))} | {' / '.join(fmt(b[k]) for k in ('precision','recall','f1'))} | {a['false_positives']}/{a['false_negatives']} | {b['false_positives']}/{b['false_negatives']} |")
    lines += ['', '## Language breakdown', '', '| Dataset | Language | N | OLD micro F1 | NEW micro F1 | OLD exact | NEW exact |', '|---|---|---:|---:|---:|---:|---:|']
    for name,r in report['datasets'].items():
        for lang,a in r['old']['symptoms']['by_language'].items():
            b=r['new']['symptoms']['by_language'][lang]
            lines.append(f"| {name} | {lang} | {a['examples']} | {a['micro_f1']:.4f} | {b['micro_f1']:.4f} | {a['exact_set_match']:.4f} | {b['exact_set_match']:.4f} |")
    lines += ['', '## Rule fields and unsupported assertions', '',
              'Raw synthetic rule-label agreement is not factual accuracy: first-person adult, hydration false and timing labels remain problematic.',
              'Unsupported counts below compare to authored expectations, not an independently verified grounding oracle.', '',
              '| Dataset | Field | OLD agreement | NEW agreement | OLD unknown accuracy | NEW unknown accuracy |', '|---|---|---:|---:|---:|---:|']
    for name,r in report['datasets'].items():
        for field in SCALARS:
            a,b=[r[m]['rules'][field] for m in ('old','new')]
            lines.append(f"| {name} | {field} | {a['exact_agreement']:.4f} | {b['exact_agreement']:.4f} | {fmt(a['unknown_handling_accuracy'])} | {fmt(b['unknown_handling_accuracy'])} |")
        if 'diagnostics' in name:
            lines += [f"\n{name}: all asserted fields including symptoms — OLD `{r['old']['all_assertions_vs_reference']}`; NEW `{r['new']['all_assertions_vs_reference']}`.\n"]
    lines += ['', 'Report signs: exact statuses are `affirmed`, `negated`, `uncertain`, `not_mentioned`. Only affirmed signs populate reportedSigns. Historical/conflicting/subject-ambiguous mentions are uncertain.',
              'Full per-sign precision/recall/F1, scalar confusion matrices and literal-evidence counts are in improvement_results.json.', '',
              '## Latency (same-process paired benchmark)', '', '```json',json.dumps(report['latency'],indent=2),'```', '',
              'The raw ML is unchanged; new_full includes ML plus evidence, subject, rules and decision metadata. Latency includes no backend/network.', '',
              '## Verification', '', '```json',json.dumps(report['verification'],indent=2),'```', '',
              'The raw dataset, original diagnostics and artifact were not edited. Derived split manifest is unchanged. No backend/frontend changes.', '',
              '## Remaining limitations', '',
              '- Exact phrase vocabulary is incomplete, especially misspellings, ASR errors and Swahili variants. No fuzzy correction is guessed.',
              '- A strong text mention below the fixed classifier threshold is omitted; conservative filtering cannot repair all false negatives.',
              '- Negation/uncertainty is clause-based, not a syntactic parser. Lists and reported speech can exceed its scope handling.',
              '- Multiple subjects default to abstention. An explicit target allows only clauses naming that person; pronouns are not guessed across people.',
              '- Relative weekdays/yesterday and approximate times are retained as durationMentions but durationDays remains null without a defensible exact interval.',
              '- Known sentence/template overlap and sparse per-label held-out coverage remain. This is development evaluation, not clinical validity.', '',
              'Next: independently author/review bilingual subject, negation and evidence-span annotations; review coverage failures and fixed-threshold recall before model changes. No transformer or production-model decision.']
    (ROOT/'reports/improvement_results.md').write_text('\n'.join(lines)+'\n')
    review=['# Improvement error review', '', 'Synthetic-data benchmark results and authored development diagnostics only.', '',
            'No training labels or original expectations were changed. All paired field mismatches are in improvement_errors.json.', '']
    for name,items in errors.items():
        review += [f'## {name}', '']
        seen=set()
        for row in items:
            d=row['differences'].get('symptoms')
            if not d: continue
            old_error=len(set(d['expected']) ^ set(d['old']))
            new_error=len(set(d['expected']) ^ set(d['new']))
            direction='improved' if new_error<old_error else 'regressed' if new_error>old_error else 'remaining'
            key=(direction,row['language'],row['category'])
            if key in seen:continue
            seen.add(key)
            review.append(f"- {direction}: {row['id']} / {row['language']} / {row['category']}: {row['text']!r}. Expected {d['expected']}; OLD {d['old']}; NEW {d['new']}.")
        review += ['', 'Rule-field mismatches (all authored cases; first five raw cases):', '']
        selected=items if 'diagnostics' in name else items[:5]
        for row in selected:
            d={f:v for f,v in row['differences'].items() if f!='symptoms'}
            if d:review.append(f"- {row['id']}: {row['text']!r}: `{d}`")
    (ROOT/'reports/improvement_error_analysis.md').write_text('\n'.join(review)+'\n')


if __name__=='__main__':
    run()
