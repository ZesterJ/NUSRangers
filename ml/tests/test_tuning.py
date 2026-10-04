"""One regression per controlled mapping plus conservative scope invariants."""
import sys
from pathlib import Path
import re

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from extraction_pipeline import SYMPTOMS, SIGNS, Config, extract_rules, finding, scoped_clauses
from lexical_config import PHRASES, RULE_ADDITIONS, normalize_model_text


@pytest.mark.parametrize('phrase', list(PHRASES))
def test_every_lexical_addition(phrase):
    label, canonical = PHRASES[phrase]
    assert normalize_model_text(phrase) == canonical
    text = 'I have ' + phrase
    eligible,_,_ = scoped_clauses(text)
    result = finding(text, SYMPTOMS[label], eligible)
    assert result['state'] == 'affirmed'
    assert any(e['text'] and e['text'].lower() in phrase for e in result['evidence'])
    denied = 'No ' + phrase
    eligible,_,_ = scoped_clauses(denied)
    assert finding(denied,SYMPTOMS[label],eligible)['state'] == 'negated'


@pytest.mark.parametrize('field,phrase', [(f,p) for f,ps in RULE_ADDITIONS.items() for p in ps])
def test_every_deterministic_addition(field,phrase):
    result = extract_rules('Mtoto '+phrase)
    if field == 'hydration_true': assert result['hydrationIssue'] is True
    elif field == 'hydration_false': assert result['hydrationIssue'] is False
    elif field == 'negation':
        eligible,_,_ = scoped_clauses(phrase)
        assert not any(finding(phrase,p,eligible)['state']=='affirmed' for p in SYMPTOMS.values())
    else: assert field in result['reportedSigns']


@pytest.mark.parametrize('text', ['Mtoto ana homa kwa siku tatu na anatapika.', 'Mtoto hana homa lakini anakohoa.'])
def test_bare_mtoto(text):
    assert extract_rules(text)['patientType']=='child'


def test_negative_scope():
    text='No fever, only a cough.'
    eligible,_,_=scoped_clauses(text)
    assert finding(text,SYMPTOMS['fever'],eligible)['state']=='negated'
    assert finding(text,SYMPTOMS['cough'],eligible)['state']=='affirmed'
    text='Maybe only a fever.'
    eligible,_,_=scoped_clauses(text)
    assert finding(text,SYMPTOMS['fever'],eligible)['state']=='uncertain'


def test_tree_context():
    assert normalize_model_text('tree days')=='three days'
    assert normalize_model_text('a tree outside')=='a tree outside'
    result=extract_rules('cough for tree days')
    assert result['durationDays']==3
    assert result['evidence']['durationDays'][0]['text']=='for tree days'


def test_fetal_context_not_child():
    assert extract_rules('Mtoto tumboni anacheza kidogo.')['patientType'] is None


def test_threshold_map_validation():
    assert Config(thresholds={'fever':.2}).for_label('fever')==.2
    assert Config(thresholds={'fever':.2}).for_label('cough')==.3
    with pytest.raises(ValueError): Config(thresholds={'fever':float('nan')})
    with pytest.raises(ValueError): Config(thresholds={'diagnosis':.2})


def test_final_bundle_and_acceptance_provenance():
    import json
    import joblib
    from prepare_baseline_data import ROOT, prepare
    from tune_final import file_sha, rule_config
    from extraction_pipeline import ExtractionPipeline
    path=ROOT/'artifacts/experimental_health_ie_final.joblib'
    if not path.exists():pytest.skip('Run validation tuning and the acceptance gate first')
    bundle=joblib.load(path)
    base=joblib.load(ROOT/'artifacts/experimental_symptom_baseline.joblib')
    assert joblib.hash(bundle['pipeline'])==joblib.hash(base['pipeline'])
    assert bundle['inference_config']==rule_config()
    parts,_=prepare()
    assert bundle['threshold_selection']['ids']==[r['id'] for r in parts['validation']]
    assert set(bundle['threshold_selection']['ids']).isdisjoint(r['id'] for r in parts['test'])
    manifest=json.loads((ROOT/'data/evaluation/frozen_acceptance_v1.manifest.json').read_text())
    assert file_sha(ROOT/'data/evaluation/frozen_acceptance_v1.json')==manifest['acceptance_sha256']
    pipeline=ExtractionPipeline(bundle)
    assert pipeline.config.for_label('vomiting')==bundle['thresholds']['vomiting']
    result=pipeline.extract('Mtoto ana homa kwa siku tatu na anatapika.')
    assert result['patientType']=='child'
    assert result['durationDays']==3
    assert result['hydrationIssue'] is None
    assert set(result['symptoms'])=={'fever','vomiting'}
    assert result['evidence']['symptoms.fever'][0]['text']=='homa'
