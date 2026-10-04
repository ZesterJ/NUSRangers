"""
What the user sees: run hand-written inputs through the real backend adapter (backend/app/extract.py), which turns
the pipeline output into the app's Extraction (value + confidence). The pipeline-level numbers in backtest.py say
what is detected; this shows whether a miss is flagged (low confidence / raw text in notes) or silent (high).

Needs pydantic (the backend's schema module). Usage:
  python ml/robustness/adapter_probes.py --artifact ml/artifacts/experimental_health_ie_final.joblib
"""

import argparse
import sys
import warnings
from pathlib import Path

import joblib

HERE = Path(__file__).resolve().parent
ML = HERE.parent
warnings.filterwarnings("ignore")

# (field the text goes in, text, what a correct, safe answer looks like)
PROBES = [
    # --- lost negation: the dangerous direction (a denied symptom asserted) ---
    ("complaint", "I don't have fever", "no symptoms"),
    ("complaint", "I dont have fever", "no symptoms; a high-confidence 'fever' is WRONG and silent"),
    ("complaint", "I don’t have fever", "no symptoms; a high-confidence 'fever' is WRONG and silent"),
    # --- danger signs: lost sign should at least be flagged ---
    ("danger", "my child can't drink", "unable_to_drink"),
    ("danger", "my child cant drink", "unable_to_drink, or low confidence"),
    ("danger", "my child can’t drink", "unable_to_drink, or low confidence"),
    ("danger", "cannot  drink", "unable_to_drink (double space), or low confidence"),
    # --- typos in a symptom or sign word ---
    ("complaint", "fevr and vomitting", "fever + vomiting (known misspellings in the phrase table)"),
    ("complaint", "homa na kikohoz", "fever + cough, or low confidence"),
    ("complaint", "fever and cough", "control: cough + fever"),
    ("complaint", "fever and cogh", "cough + fever, or low confidence: dropping cough at HIGH confidence is silent"),
    ("complaint", "fever and cough and diarhea", "3 symptoms, or low confidence"),
    # --- model gaps that are NOT typos (spelled correctly), for contrast ---
    ("complaint", "headache and fatigue", "headache + weakness (fatigue)"),
    ("complaint", "fever, vomiting and headache", "all three"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", type=Path, required=True)
    ap.add_argument("--backend", type=Path, default=ML.parent / "backend", help="path to the backend/ folder")
    args = ap.parse_args()

    sys.path.insert(0, str(args.backend))
    sys.path.insert(0, str(ML / "src"))
    from app.extract import IntakeExtractor
    from app.schemas import ExtractRequest
    from extraction_pipeline import ExtractionPipeline

    extractor = IntakeExtractor(ExtractionPipeline(joblib.load(args.artifact)))
    for field, text, ideal in PROBES:
        answers = {"who": "my child", "complaint": "", "duration": "", "danger": ""}
        answers[field] = text
        r = extractor.extract(ExtractRequest(locale="en", answers=answers))
        got = r.symptoms if field == "complaint" else r.dangerSigns
        print(f"[{field:9}] {text!r:34} -> {got.value} / {got.confidence:4}  notes={r.unmapped}")
        print(f"{'':12} want: {ideal}")


if __name__ == "__main__":
    main()
