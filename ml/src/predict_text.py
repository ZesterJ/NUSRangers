"""Manual, local-only inference using the same frozen wrapper as evaluation.

python ml/src/predict_text.py "My child has a fever."
python ml/src/predict_text.py --interactive
Requires ml/requirements.txt and the existing trusted experimental artifact.
"""
import argparse
import json
from pathlib import Path
import sys

import joblib
from threadpoolctl import threadpool_limits

from extraction_pipeline import Config, ExtractionPipeline

ARTIFACT = Path(__file__).resolve().parents[1] / 'artifacts/experimental_symptom_baseline.joblib'
RULE_FIELDS = ('patientType', 'durationDays', 'hydrationIssue', 'reportedSigns')


def predict(pipeline, text):
    """Presentation only: all inference, evidence and abstention use the shared wrapper."""
    result = pipeline.extract(text)
    return {
        'extraction': {field: result[field] for field in (*RULE_FIELDS, 'symptoms')},
        'evidence': result['evidence'],
        'sourceText': result['sourceText'],
        'modelVersion': result['modelVersion'],
        'requiresVerification': result['requiresVerification'],
        'diagnostics': {
            'extractionVersion': result['extractionVersion'],
            'fieldSources': {**{field: 'deterministic rules' for field in RULE_FIELDS},
                            'symptoms': 'TF-IDF + one-vs-rest logistic regression, gated by evidence and subject rules'},
            'scoreMeaning': result['scoreMeaning'],
            'symptomDecisions': result['symptomDecisions'],
            'subject': result['subject'],
            'reportedSignStates': result['reportedSignStates'],
            'durationMentions': result['durationMentions'],
            'abstentions': result['abstentions'],
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('text', nargs='?', help='Patient text in English or Swahili (quote the whole input).')
    parser.add_argument('--interactive', action='store_true', help='Repeatedly prompt for patient text.')
    args = parser.parse_args(argv)
    if args.interactive and args.text is not None:
        parser.error('Use either text or --interactive, not both.')
    if not args.interactive and (args.text is None or not args.text.strip()):
        parser.error('Provide nonblank patient text or --interactive.')
    if not ARTIFACT.is_file():
        parser.exit(1, f'Model artifact not found: {ARTIFACT}\nRestore the existing experimental artifact before running inference.\n')
    try:
        # Exactly the evaluation loader: serialized preprocessing, classifiers, labels
        # and threshold come from the bundle. Never fit, retrain or call a remote API.
        bundle = joblib.load(ARTIFACT)
        pipeline = ExtractionPipeline(bundle, Config(threshold=bundle['threshold']))
    except Exception as exc:
        parser.exit(1, f'Unable to load the experimental artifact: {exc}\nUse the environment specified in ml/requirements.txt.\n')

    def output(text):
        print(json.dumps(predict(pipeline, text), indent=2, ensure_ascii=False, allow_nan=False))

    try:
        with threadpool_limits(limits=1):
            if not args.interactive:
                output(args.text)
                return 0
            while True:
                try:
                    text = input("Enter patient text (or 'quit'): ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    return 0
                if text.strip().lower() == 'quit':
                    return 0
                if not text.strip():
                    print('Please enter nonblank patient text.', file=sys.stderr)
                    continue
                output(text)
    except Exception as exc:
        parser.exit(1, f'Inference failed: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
