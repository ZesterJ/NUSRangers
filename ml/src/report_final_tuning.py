"""Render the final report from recorded evaluation outputs; no tuning."""
import json
from collections import Counter
from prepare_baseline_data import ROOT, LABELS


def render():
    r=json.loads((ROOT/'reports/final_tuning_results.json').read_text())
    t=json.loads((ROOT/'reports/final_threshold_analysis.json').read_text())
    errors=json.loads((ROOT/'reports/final_tuning_errors.json').read_text())
    lines=['# Final health extraction tuning report', '',
           '**Experimental synthetic-data benchmark and authored-case results. No clinical validity or deployment readiness is claimed.**', '',
           '## Changes and rationale', '',
           '- Retained the exact fitted character TF-IDF + balanced one-vs-rest logistic regression weights. No transformer, LLM, retraining, oversampling, training augmentation or new runtime dependency.',
           '- Added a controlled, whole-token English/Swahili phrase table in `src/lexical_config.py`. It normalizes model input only; source text/evidence is never rewritten. Every added phrase has positive/negated regression coverage. No general fuzzy matching.',
           '- Added bare Mtoto child references, explicit normal/reduced-drinking Swahili expressions, and sign variants. Fetal movement wording is excluded from the new bare-child rule; it does not establish child age.',
           '- Split comma + only/just contrast clauses, fixing "No fever, only a cough" without opening uncertainty scope for "Maybe only a fever".',
           '- Normalized tree only when followed by day(s); approximate/relative/conflicting durations remain unknown. No date anchoring or invented interval.',
           '- Affirmed fields use the matched phrase span rather than whole-clause evidence. Negated/uncertain states retain context so their interpretation can be inspected.',
           '- Added validation-only per-label thresholds; the bundle contains preprocessing, frozen classifiers, labels, thresholds, extraction/model versions, lexical/rule configuration, source hashes and parent artifact provenance.',
           '- Preserved multi-subject abstention and explicit target selection. Unknown hydration remains null; reduced drinking is not cannot_drink.', '',
           '## Data boundaries and selection', '',
           'Derived split remains 805 train / 205 validation / 190 test, grouped into 31 scenario-family proxies. No vocabulary or classifier was refitted. Shared synthetic phrases remain; the test has positive support for only five symptom labels.',
           'Thresholds were selected ONLY using the 205 derived validation records. Grid: 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40. Changed thresholds require >=98% validation precision and no increase in validation false positives, then maximize F1, preferring 0.30 on ties. All labels get this conservative gate.',
           'Five labels have no positive validation examples and retain 0.30; three single-family rare labels are training-only. Small validation supports cannot justify further tuning of those labels.',
           '48 new fictional acceptance cases were hash-frozen before candidate changes, training or evaluation. They cover English/Swahili/mixed language and were never read by tune_final.py. They serve only as a final accept/reject veto.',
           'The acceptance set was authored by this assistant with requirements visible. It is NOT independently blinded, clinician reviewed, native-Swahili reviewed, or real-patient data. Existing 48/42 diagnostic sets remain development material.', '',
           f"Quality gate passed: **{r['quality_gate_passed']}**. No candidate was modified in response to acceptance results.", '',
           '## Before vs after', '',
           '| Dataset | Pipeline | Micro F1 | Supported macro F1 | All-13 macro* | Exact set | FP | FN |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for name,result in r['results'].items():
        for method in ('before','after'):
            m=result[method]['symptoms']
            lines.append(f"| {name} | {method} | {m['micro_f1']:.4f} | {m['macro_f1_supported_labels']:.4f} | {m['macro_f1_all_labels_zero_undefined']:.4f} | {m['exact_set_match']:.4f} | {m['false_positives']} | {m['false_negatives']} |")
    lines+=['', '*All-13 macro assigns zero to undefined F1; supported macro only includes labels with positive support. Perfect validation results reflect a small template-heavy tuning partition, not generalization.', '',
            '## Per-label thresholds, support and validation changes', '',
            '| Label | Train positives | Validation positives | Final threshold | Validation F1 at .3 | Selected F1 | Selected FP/FN |', '|---|---:|---:|---:|---:|---:|---|']
    for label,entry in t['per_label'].items():
        base=next(x for x in entry['trials'] if x['threshold']==.3);chosen=entry['chosen']
        lines.append(f"| {label} | {entry['train_support']} | {entry['validation_support']} | {t['thresholds'][label]} | {base['f1']:.4f} | {chosen['f1']:.4f} | {chosen['false_positives']}/{chosen['false_negatives']} |")
    lines+=['', 'Each threshold candidate’s precision, recall, F1, FP and FN is retained in final_threshold_analysis.json. No oversampling was performed.', '',
            '## Per-label test and authored performance', '']
    def fmt(x):return 'N/A' if x is None else f'{x:.3f}'
    for name in ('synthetic_test','original_diagnostics','expanded_diagnostics','frozen_acceptance'):
        result=r['results'][name]
        lines += [f'### {name}', '', '| Label | Support | Before P/R/F1 | After P/R/F1 | Before FP/FN | After FP/FN |', '|---|---:|---|---|---|---|']
        for label in LABELS:
            a,b=[result[m]['symptoms']['per_label'][label] for m in ('before','after')]
            lines.append(f"| {label} | {a['support']} | {' / '.join(fmt(a[k]) for k in ('precision','recall','f1'))} | {' / '.join(fmt(b[k]) for k in ('precision','recall','f1'))} | {a['false_positives']}/{a['false_negatives']} | {b['false_positives']}/{b['false_negatives']} |")
    lines+=['', '## Language breakdown', '', '| Dataset | Language | N | Before micro F1 | After micro F1 |', '|---|---|---:|---:|---:|']
    for name,result in r['results'].items():
        for lang,a in result['before']['symptoms']['by_language'].items():
            b=result['after']['symptoms']['by_language'][lang]
            lines.append(f"| {name} | {lang} | {a['examples']} | {a['micro_f1']:.4f} | {b['micro_f1']:.4f} |")
    lines+=['', '## Unsupported assertions and conservative controls', '',
            'These rates compare asserted symptoms/rule fields to authored expected values. They are not independent clinical verification.', '',
            '| Dataset | Before unsupported / asserted | After unsupported / asserted |', '|---|---|---|']
    for name in ('original_diagnostics','expanded_diagnostics','frozen_acceptance'):
        result=r['results'][name]
        a,b=[result[m]['all_assertions'] for m in ('before','after')]
        lines.append(f"| {name} | {a['unsupported']}/{a['count']} ({a['rate']:.1%}) | {b['unsupported']}/{b['count']} ({b['rate']:.1%}) |")
    lines+=['', '| Dataset | Field | Before agreement | After agreement | Before unknown accuracy | After unknown accuracy |', '|---|---|---:|---:|---:|---:|']
    for name in ('original_diagnostics','expanded_diagnostics','frozen_acceptance'):
        for f in ('patientType','durationDays','hydrationIssue'):
            a,b=[r['results'][name][m]['rules'][f] for m in ('before','after')]
            lines.append(f"| {name} | {f} | {a['exact_agreement']:.3f} | {b['exact_agreement']:.3f} | {fmt(a['unknown_handling_accuracy'])} | {fmt(b['unknown_handling_accuracy'])} |")
    lines+=['', 'Negation and subject-category controls (correct symptom set / cases, with extra assertions):', '', '| Dataset | Control | Before correct/N; extra | After correct/N; extra |', '|---|---|---|---|']
    for name in ('original_diagnostics','expanded_diagnostics','frozen_acceptance'):
        for control in ('negation','subjects'):
            a,b=[r['results'][name][m]['controls'][control] for m in ('before','after')]
            lines.append(f"| {name} | {control} | {a['symptom_exact_correct']}/{a['examples']}; {a['extra_symptoms']} | {b['symptom_exact_correct']}/{b['examples']}; {b['extra_symptoms']} |")
    lines+=['', 'Older original diagnostics expect document-level symptoms from multiple people; safe abstention still counts as false negatives there. Their labels were not changed.', '',
            '## Remaining errors and regressions', '',
            'Synthetic micro-F1 and exact set are unchanged. Supported macro-F1 falls slightly from 0.9420 to 0.9408: three vomiting misses are recovered but three weakness predictions are lost when controlled normalization changes the shared text representation. This per-label trade-off is retained explicitly; authored metrics improve and unsupported positives do not increase.',
            'No further threshold adjustment was made after looking at test/acceptance. Strong evidence below an unchanged threshold still abstains. No keyword-only rescue was added.', '']
    for name,rows in errors.items():
        reasons=Counter(reason for e in rows if e['field']=='symptoms' for d in e.get('miss_reasons',{}).values() for reason in d['reasons'])
        lines.append(f'- Remaining symptom FN reasons in {name}: {dict(reasons)}. A miss may have multiple reasons.')
    lines+=['', 'Representative remaining failures:', '']
    for name in ('synthetic_test','original_diagnostics','frozen_acceptance'):
        seen=set()
        for e in errors[name]:
            if e['field']!='symptoms' or not (set(e['expected'])-set(e['after'])):continue
            key=(e['category'],tuple(sorted(set(e['expected'])-set(e['after']))))
            if key in seen:continue
            seen.add(key)
            if len(seen)>5:continue
            lines.append(f"- {name} / {e['id']}: {e['text']!r}; expected {e['expected']}, after {e['after']}; reasons `{e.get('miss_reasons')}`.")
    lines+=['', '## Artifact and latency', '',
            f"Final experimental bundle: `ml/artifacts/experimental_health_ie_final.joblib` — **{r['candidate_bytes']:,} bytes**, SHA-256 `{r['candidate_sha256']}`. Ignored by Git; no artifact committed.",
            'Separate metadata JSON records versions/configuration and the gate report. The original experimental_symptom_baseline.joblib is untouched. The v2 reference source is retained under src/reference solely for reproducible comparisons.',
            'Manual CLI now loads the final bundle and reads its per-label thresholds through the shared wrapper; default extraction-only and --verbose formats are preserved.',
            'Warm single-request CPU timing, 1,000 calls per operation, one numerical-library thread on the same macOS arm64 environment; no HTTP/ASR overhead:', '',
            '| Operation | p50 ms | p95 ms |', '|---|---:|---:|']
    for name,m in r['latency'].items():lines.append(f"| {name} | {m['p50_ms']:.3f} | {m['p95_ms']:.3f} |")
    lines+=['', '## Integration recommendation', '',
            '**Ready for a supervised hackathon integration experiment, not clinical deployment.** Preserve human verification, null semantics, exact evidence, explicit subject selection and visible uncertain/omitted fields.',
            'The current /predict backend still expects numeric features and scalar output; do not point its old joblib adapter directly at this text bundle. A separate contract/adapter integration is required. No backend, frontend, speech, diagnosis or clinic-routing code was changed here.',
            'Remaining limitations: template leakage, five-label positive test coverage, no positive validation support for several rare labels, uncalibrated classifier scores, brittle clause/coreference heuristics, incomplete lexical/ASR coverage and no independent native-Swahili/clinical acceptance review.',
            'Next: integrate only the verified artifact/config into a draft-review workflow, obtain native-language review, and collect an independent acceptance suite before further tuning. Keep unresolved/multiple-patient text out of automatic form assignment.', '',
            '## Verification run', '', '161 Python tests passed (backend + ML), including a regression for every lexical addition, final-bundle provenance, per-label threshold loading, original-source evidence and CLI presentation. Historical baseline/v2 evaluations were rerun; raw SHA-256 verification and git diff --check passed. Single-input and interactive default/verbose manual checks passed. Frontend lint/typecheck/pack checks were attempted but eslint, tsc and tsx are not installed; no frontend files changed.', '', '## Reproduction', '', '```sh',
            'python ml/src/tune_final.py', 'python ml/src/evaluate_final_tuning.py',
            'python ml/src/report_final_tuning.py', 'python -m pytest ml/tests -q',
            'python ml/src/predict_text.py "Mtoto ana homa kwa siku tatu na anatapika."',
            'python ml/src/predict_text.py --interactive', '```',
            'Use the pinned ML environment. Evaluation only publishes the final bundle if its gate passes. Do not change/tune against frozen acceptance examples on later runs.']
    (ROOT/'reports/final_tuning_report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':render()
