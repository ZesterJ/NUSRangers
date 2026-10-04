"""Evidence, scope and abstention regression tests (classifier frozen)."""
import sys
from pathlib import Path

import joblib
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from extraction_pipeline import Config, ExtractionPipeline, extract_rules
from prepare_baseline_data import ROOT


@pytest.fixture(scope='module')
def pipeline():
    return ExtractionPipeline(joblib.load(ROOT / 'artifacts/experimental_symptom_baseline.joblib'))


@pytest.mark.parametrize('text,label', [
    ('No fever', 'fever'), ('not vomiting', 'vomiting'), ('without bleeding', 'bleeding'),
    ('Sina homa', 'fever'), ('Hana kikohozi', 'cough'), ('Sitapiki', 'vomiting'),
    ('Hakuna damu inayotoka', 'bleeding'), ('Sikohoi', 'cough'),
    ('No fever or cough', 'cough'), ('Maybe there is bleeding', 'bleeding'),
])
def test_scope_gates_even_high_score(pipeline, text, label):
    result = pipeline.extract(text, scores=[.99]*13)
    assert label not in result['symptoms']


def test_no_associated_symptoms(pipeline):
    result = pipeline.extract('My child is drinking less.', scores=[.99]*13)
    assert result['symptoms'] == []
    assert result['hydrationIssue'] is True
    assert result['reportedSigns'] == []


@pytest.mark.parametrize('text,value', [('The child has fever', None), ('The child is drinking normally', False),
    ('The child is not drinking', True), ('Mtoto wangu anakunywa vizuri', False), ('No trouble drinking', False)])
def test_hydration(text, value):
    assert extract_rules(text)['hydrationIssue'] is value


@pytest.mark.parametrize('text,value', [('for three days', 3), ('three days', 3), ('siku tatu', 3),
    ('since yesterday', None), ('since Monday', None), ('a few days', None),
    ('Fever for three days and not drinking', 3), ('two days but cough for four days', None),
    ('about three days', None)])
def test_duration(text, value):
    assert extract_rules(text)['durationDays'] == value


def test_subject(pipeline):
    text = 'My husband has fever but I feel fine.'
    assert pipeline.extract(text, scores=[.99]*13)['symptoms'] == []
    result = pipeline.extract(text, target_subject='husband', scores=[.99]*13)
    assert result['subject']['value'] == 'husband'
    assert result['symptoms'] == ['fever']
    assert pipeline.extract(text, target_subject='speaker', scores=[.99]*13)['symptoms'] == []


@pytest.mark.parametrize('text,state', [('There is bleeding', 'affirmed'), ('No bleeding', 'negated'),
                                      ('Maybe bleeding', 'uncertain'), ('There is cough', 'not_mentioned')])
def test_sign_states(text, state):
    result = extract_rules(text)
    assert result['reportedSignStates']['bleeding']['state'] == state
    assert ('bleeding' in result['reportedSigns']) == (state == 'affirmed')


def test_threshold(pipeline):
    result = pipeline.extract('Fever', scores=[.01]*13)
    assert result['symptoms'] == []
    with pytest.raises(ValueError):
        Config(float('nan'))
    with pytest.raises(ValueError):
        Config(1.1)


def test_all_populated_fields_have_exact_evidence(pipeline):
    import json
    for file in ('baseline_diagnostics.json', 'expanded_diagnostics.json'):
        for row in json.loads((ROOT / 'data/evaluation' / file).read_text())['cases']:
            text = row['text']
            result = pipeline.extract(text, row.get('target_subject'))
            required = [f for f in ('patientType', 'durationDays', 'hydrationIssue') if result[f] is not None]
            required += [f'symptoms.{x}' for x in result['symptoms']]
            required += [f'reportedSigns.{x}' for x in result['reportedSigns']]
            for field in required:
                assert result['evidence'][field]
            for spans in result['evidence'].values():
                for evidence in spans:
                    assert text[evidence['start']:evidence['end']] == evidence['text']
                    assert evidence['text'].strip()


def test_uncertain_symptom_does_not_erase_explicit_child():
    result = extract_rules('The child may have had a seizure.')
    assert result['patientType'] == 'child'
    assert result['reportedSignStates']['convulsions']['state'] == 'uncertain'
    assert result['reportedSigns'] == []


def test_ambiguous_pronouns(pipeline):
    result = pipeline.extract('She has fever but he is vomiting.', scores=[.99]*13)
    assert result['symptoms'] == []
    assert result['subject']['status'] == 'ambiguous'


def test_configurable_threshold(pipeline):
    stricter = ExtractionPipeline(pipeline.bundle, Config(threshold=.8))
    assert pipeline.extract('Fever', scores=[.6]*13)['symptoms'] == ['fever']
    assert stricter.extract('Fever', scores=[.6]*13)['symptoms'] == []


@pytest.mark.parametrize('scores', [[.5], [float('nan')]*13, [1.1]*13])
def test_invalid_scores_rejected(pipeline, scores):
    with pytest.raises(ValueError):
        pipeline.extract('Fever', scores=scores)
