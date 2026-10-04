"""Validation-only threshold search; no acceptance/test reads and no model fitting.

Creates a CANDIDATE bundle. Final acceptance evaluation must pass before publishing
experimental_health_ie_final.joblib. The existing classifier weights remain frozen.
"""
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import precision_recall_fscore_support
from threadpoolctl import threadpool_limits

from extraction_pipeline import Config, ExtractionPipeline, VERSION, SYMPTOMS, SIGNS
from lexical_config import NORMALIZATION, RULE_ADDITIONS, normalize_model_text
from prepare_baseline_data import LABELS, ROOT, prepare
from metrics import encode

GRID = (.1,.15,.2,.25,.3,.35,.4)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rule_config():
    return {'normalization':NORMALIZATION,'rule_additions':RULE_ADDITIONS,
            'symptom_patterns':SYMPTOMS,'sign_patterns':SIGNS,
            'duration_normalization':'tree -> three only when directly followed by day(s)',
            'source_sha256':{name:file_sha(ROOT/'src'/name) for name in ('extraction_pipeline.py','lexical_config.py','baseline_rules.py')}}


def tune():
    bundle=joblib.load(ROOT/'artifacts/experimental_symptom_baseline.joblib')
    parts,info=prepare()
    assert bundle['split_manifest_sha256']==info['record_manifest_sha256']
    validation=parts['validation']
    texts=[r['text'] for r in validation]
    y=encode([r['labels'] for r in validation],LABELS)
    with threadpool_limits(limits=1):
        scores=bundle['pipeline'].predict_proba([normalize_model_text(t) for t in texts])
    wrapper=ExtractionPipeline(bundle)
    # Obtain evidence/subject eligibility without reducing candidates by a score gate.
    eligibility=np.array([[wrapper.extract(t,scores=[1.0]*len(LABELS))['symptomDecisions'][label]['accepted']
                           for label in LABELS] for t in texts])
    # No labels/text from test or authored acceptance are consulted by this function.
    thresholds,analysis={},{}
    for j,label in enumerate(LABELS):
        support=int(y[:,j].sum())
        trials=[]
        for threshold in GRID:
            p=(scores[:,j]>=threshold)&eligibility[:,j]
            precision,recall,f1,_=precision_recall_fscore_support(y[:,j],p,average='binary',zero_division=0)
            trials.append({'threshold':threshold,'precision':float(precision),'recall':float(recall),'f1':float(f1),
                           'false_positives':int(((y[:,j]==0)&p).sum()),'false_negatives':int(((y[:,j]==1)&~p).sum())})
        baseline=next(t for t in trials if t['threshold']==.3)
        # Safety gate applies to ALL labels: do not increase validation FP; require
        # >=98% precision for a changed threshold. Prefer .3 whenever F1 ties.
        eligible=[t for t in trials if t['false_positives']<=baseline['false_positives'] and t['precision']>=.98]
        chosen=max(eligible,key=lambda t:(t['f1'],-abs(t['threshold']-.3))) if support and eligible else baseline
        thresholds[label]=chosen['threshold'] if support else .3
        analysis[label]={'validation_support':support,'train_support':info['label_support']['train'][label],
                         'chosen':chosen if support else baseline,'trials':trials,
                         'reason':'validation F1 subject to no extra FP and >=98% precision' if support else 'no validation positives; retain 0.3'}
    candidate=dict(bundle,modelVersion='experimental-health-ie-v3',extractionVersion=VERSION,thresholds=thresholds,
                   inference_config=rule_config(),
                   threshold_selection={'data':'derived validation only','ids':[r['id'] for r in validation],
                                        'grid':GRID,'seed':42,'rule':'maximize per-label F1; no FP increase; changed threshold precision >=.98; prefer .3 on ties'},
                   parent_artifact_sha256=file_sha(ROOT/'artifacts/experimental_symptom_baseline.joblib'))
    candidate_path=ROOT/'artifacts/experimental_health_ie_candidate.joblib'
    joblib.dump(candidate,candidate_path,compress=3)
    result={'label':'synthetic-data validation tuning only','classifier_unchanged':True,'oversampling':False,
            'class_weight':'balanced (existing fitted weights)','thresholds':thresholds,'per_label':analysis,
            'selection_ids':candidate['threshold_selection']['ids'],'split_manifest_sha256':info['record_manifest_sha256'],
            'candidate_bytes':candidate_path.stat().st_size,'candidate_sha256':file_sha(candidate_path),
            'inference_config':candidate['inference_config']}
    (ROOT/'reports/final_threshold_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'thresholds':thresholds,'candidate_bytes':candidate_path.stat().st_size},indent=2))
    return candidate


if __name__=='__main__':
    tune()
