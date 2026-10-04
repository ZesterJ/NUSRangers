"""CLI presentation contracts; exercise both modes with the unchanged full result."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import predict_text


@pytest.fixture
def full_result(monkeypatch, tmp_path):
    result = {
        'extraction': {'patientType': 'child', 'durationDays': 3, 'hydrationIssue': None,
                       'reportedSigns': [], 'symptoms': ['fever', 'vomiting']},
        'evidence': {'patientType': [{'text': 'My child', 'start': 0, 'end': 8}]},
        'sourceText': 'My child has fever.', 'modelVersion': 'test-version',
        'requiresVerification': True,
        'diagnostics': {'symptomDecisions': {'fever': {'score': .8, 'threshold': .3}},
                        'subject': {'value': 'child'}, 'abstentions': []},
    }
    artifact = tmp_path / 'artifact'
    artifact.touch()
    monkeypatch.setattr(predict_text, 'ARTIFACT', artifact)
    monkeypatch.setattr(predict_text.joblib, 'load', lambda path: {'threshold': .3})
    monkeypatch.setattr(predict_text, 'ExtractionPipeline', lambda bundle, config=None: object())
    monkeypatch.setattr(predict_text, 'predict', lambda pipeline, text: result)
    return result


@pytest.mark.parametrize('verbose', [False, True])
def test_single_input_output(verbose, full_result, capsys):
    before = json.dumps(full_result, sort_keys=True)
    args = (['--verbose'] if verbose else []) + ['My child has fever.']
    assert predict_text.main(args) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == (full_result if verbose else full_result['extraction'])
    assert captured.err == ''
    assert json.dumps(full_result, sort_keys=True) == before


@pytest.mark.parametrize('verbose', [False, True])
def test_interactive_output(verbose, full_result, monkeypatch, capsys):
    inputs = iter(['My child has fever.', 'Mtoto wangu ana homa.', 'quit'])
    prompts = []

    def read(prompt):
        prompts.append(prompt)
        return next(inputs)

    monkeypatch.setattr('builtins.input', read)
    args = ['--interactive'] + (['--verbose'] if verbose else [])
    assert predict_text.main(args) == 0
    captured = capsys.readouterr()
    remainder = captured.out
    outputs = []
    decoder = json.JSONDecoder()
    while remainder.strip():
        result, end = decoder.raw_decode(remainder.lstrip())
        outputs.append(result)
        remainder = remainder.lstrip()[end:]
    expected = full_result if verbose else full_result['extraction']
    assert outputs == [expected, expected]
    assert prompts == ["Enter patient text (or 'quit'): "] * 3
    assert captured.err == ''
