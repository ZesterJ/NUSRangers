"""Final paired evaluation and explicit accept/reject gate; never tunes or fits.

Loads the frozen v2 reference and validation-selected v3 candidate. Acceptance data
is opened only here. Passing publishes a separate final experimental bundle.
"""
import json
import shutil
import time

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from reference.extraction_v2 import ExtractionPipeline as PreviousPipeline
from reference.extraction_v2 import extract_rules as previous_rules
from extraction_pipeline import ExtractionPipeline, extract_rules, VERSION
from evaluate import rule_metrics, SCALARS
from evaluate_improvements import metrics, raw_rows
from prepare_baseline_data import ROOT, LABELS, prepare
from tune_final import file_sha, rule_config


def benchmark(before,after,rows):
    report={}
    operations={'before_rules':previous_rules,'after_rules':extract_rules,
                'before_full':before.extract,'after_full':after.extract}
    for name,fn in operations.items():
        for row in rows[:20]:fn(row['text'])
        times=[]
        for i in range(1000):
            start=time.perf_counter_ns();fn(rows[i%len(rows)]['text'])
            times.append((time.perf_counter_ns()-start)/1e6)
        report[name]={'p50_ms':float(np.median(times)),'p95_ms':float(np.percentile(times,95))}
    return report


def run():
    manifest=json.loads((ROOT/'data/evaluation/frozen_acceptance_v1.manifest.json').read_text())
    acceptance_path=ROOT/'data/evaluation/frozen_acceptance_v1.json'
    assert file_sha(acceptance_path)==manifest['acceptance_sha256']
    assert file_sha(ROOT/'src/reference/extraction_v2.py')==manifest['reference_source_sha256']
    base_path=ROOT/'artifacts/experimental_symptom_baseline.joblib'
    candidate_path=ROOT/'artifacts/experimental_health_ie_candidate.joblib'
    base=joblib.load(base_path);candidate=joblib.load(candidate_path)
    assert candidate['parent_artifact_sha256']==file_sha(base_path)
    assert joblib.hash(base['pipeline'])==joblib.hash(candidate['pipeline'])
    assert candidate['inference_config']==rule_config()
    parts,split=prepare()
    assert candidate['split_manifest_sha256']==split['record_manifest_sha256']
    assert candidate['threshold_selection']['ids']==[r['id'] for r in parts['validation']]
    before,after=PreviousPipeline(base),ExtractionPipeline(candidate)
    datasets={'synthetic_validation':raw_rows(parts['validation']),'synthetic_test':raw_rows(parts['test'])}
    for name,file in [('original_diagnostics','baseline_diagnostics.json'),('expanded_diagnostics','expanded_diagnostics.json'),('frozen_acceptance','frozen_acceptance_v1.json')]:
        datasets[name]=json.loads((ROOT/'data/evaluation'/file).read_text())['cases']
    results,errors,predictions={},{},{}
    with threadpool_limits(limits=1):
        for name,rows in datasets.items():
            authored=not name.startswith('synthetic')
            methods={}
            for method,pipeline in [('before',before),('after',after)]:
                methods[method]=[pipeline.extract(r['text'],r.get('target_subject')) for r in rows]
            results[name]={}
            for method,pred in methods.items():
                m=metrics(rows,pred)
                rules=rule_metrics([r['expected'] for r in rows],pred,authoritative=authored)
                result={'symptoms':m,'rules':rules}
                if authored:
                    count=rules['all_field_assertions']['count']+sum(len(p['symptoms']) for p in pred)
                    wrong=rules['all_field_assertions']['unsupported']+m['false_positives']
                    result['all_assertions']={'count':count,'unsupported':wrong,'rate':wrong/count if count else None}
                    result['controls']={}
                    for control,condition in [('negation',lambda r:'negat' in r.get('category','')),
                                              ('subjects',lambda r:'subject' in r.get('category',''))]:
                        selected=[(r,p) for r,p in zip(rows,pred) if condition(r)]
                        result['controls'][control]={'examples':len(selected),'symptom_exact_correct':sum(set(r['expected']['symptoms'])==set(p['symptoms']) for r,p in selected),
                                                     'extra_symptoms':sum(len(set(p['symptoms'])-set(r['expected']['symptoms'])) for r,p in selected)}
                results[name][method]=result
            errors[name]=[]
            for row,a,b in zip(rows,methods['before'],methods['after']):
                for field in (*SCALARS,'reportedSigns','symptoms'):
                    expected=row['expected'][field]
                    def eq(x,y):return set(x)==set(y) if isinstance(x,list) else x==y
                    if not eq(a[field],expected) or not eq(b[field],expected):
                        record={'id':row['id'],'text':row['text'],'language':row['language'],'category':row.get('category','synthetic_template'),
                                'field':field,'expected':expected,'before':a[field],'after':b[field]}
                        if field=='symptoms':
                            record['miss_reasons']={label:b['symptomDecisions'][label] for label in expected if label not in b['symptoms']}
                        errors[name].append(record)
                fields=[f for f in SCALARS if b[f] is not None]+['symptoms.'+s for s in b['symptoms']]+['reportedSigns.'+s for s in b['reportedSigns']]
                assert all(b['evidence'].get(f) for f in fields)
                for spans in b['evidence'].values():
                    assert all(row['text'][s['start']:s['end']]==s['text'] and s['text'] for s in spans)
            predictions[name]=[{'id':r['id'],'before':a,'after':b} for r,a,b in zip(rows,methods['before'],methods['after'])]
        latency=benchmark(before,after,parts['test'])
    checks={}
    for name in ('original_diagnostics','expanded_diagnostics','frozen_acceptance'):
        a,b=results[name]['before'],results[name]['after']
        checks[name]={
            'micro_f1_non_decreasing':b['symptoms']['micro_f1']>=a['symptoms']['micro_f1'],
            'exact_set_non_decreasing':b['symptoms']['exact_set_match']>=a['symptoms']['exact_set_match'],
            'unsupported_count_non_increasing':b['all_assertions']['unsupported']<=a['all_assertions']['unsupported'],
            'unknown_handling_non_decreasing':all(b['rules'][f]['unknown_handling_accuracy'] is None or b['rules'][f]['unknown_handling_accuracy']>=a['rules'][f]['unknown_handling_accuracy'] for f in SCALARS),
            'no_extra_negation_or_subject_assertions':all(b['controls'][f]['extra_symptoms']<=a['controls'][f]['extra_symptoms'] for f in ('negation','subjects'))}
    passed=all(all(c.values()) for c in checks.values())
    output={'label':'synthetic-data and authored experimental evaluation; not clinical validation',
            'quality_gate_passed':passed,'gate_checks':checks,'results':results,'latency':latency,
            'thresholds':candidate['thresholds'],'candidate_bytes':candidate_path.stat().st_size,
            'candidate_sha256':file_sha(candidate_path),'base_artifact_sha256':file_sha(base_path),
            'acceptance_sha256':manifest['acceptance_sha256'],'reference_source_sha256':manifest['reference_source_sha256'],
            'classifier_weights_unchanged':True,'code_config_verified':True,'split_manifest_sha256':split['record_manifest_sha256']}
    report_dir=ROOT/'reports'
    (report_dir/'final_tuning_results.json').write_text(json.dumps(output,indent=2)+'\n')
    (report_dir/'final_tuning_errors.json').write_text(json.dumps(errors,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'data/processed/final_tuning_predictions.json').write_text(json.dumps(predictions,indent=2,ensure_ascii=False)+'\n')
    if passed:
        final=ROOT/'artifacts/experimental_health_ie_final.joblib'
        shutil.copyfile(candidate_path,final)
        metadata={k:v for k,v in candidate.items() if k!='pipeline'}
        metadata.update({'artifact_sha256':file_sha(final),'artifact_bytes':final.stat().st_size,'quality_gate_report':'ml/reports/final_tuning_results.json','quality_gate_passed':True})
        (ROOT/'artifacts/experimental_health_ie_final.metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'quality_gate_passed':passed,'checks':checks,'metrics':{n:{method:{k:r[method]['symptoms'][k] for k in ('micro_f1','macro_f1_supported_labels','exact_set_match','false_positives','false_negatives')} for method in ('before','after')} for n,r in results.items()}},indent=2))
    return output


if __name__=='__main__':
    run()
