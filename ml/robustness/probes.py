"""
Hand-labelled probes for input quirks the labelled sets never exercise.

The authored and synthetic cases contain no straight apostrophes, so the apostrophe perturbations in backtest.py
never applied. These probes test them directly: each one gives the SAME sentence in three spellings (straight
apostrophe, apostrophe dropped, curly U+2019) and states the one correct answer for all three.

Usage:  python ml/robustness/probes.py --artifact ml/artifacts/experimental_health_ie_final.joblib
"""

import argparse
import sys
from pathlib import Path

import joblib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from extraction_pipeline import ExtractionPipeline  # noqa: E402

# (label, sentence with straight apostrophes, expected symptoms, expected signs, expected hydrationIssue)
PROBES = [
    ("denied fever (don't)", "I don't have fever", [], [], None),
    ("denied cough (doesn't)", "my child doesn't have a cough", [], [], None),
    ("denied fever (haven't)", "I haven't had fever", [], [], None),
    ("denied sign (doesn't have convulsions)", "my child doesn't have convulsions", [], [], None),
    ("sign: can't drink", "my child can't drink", [], ["cannot_drink"], True),
    ("not drinking (isn't)", "my child isn't drinking", [], [], True),
    ("fever (affirmed, control)", "I have fever", ["fever"], [], None),
]


def variants(sentence: str) -> dict[str, str]:
    return {
        "straight": sentence,
        "dropped": sentence.replace("'", ""),
        "curly": sentence.replace("'", "’"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", type=Path, required=True)
    args = ap.parse_args()
    pipe = ExtractionPipeline(joblib.load(args.artifact))

    wrong = 0
    print(f"{'probe':58} {'variant':9} {'symptoms':12} {'signs':16} {'hydration':9} ok")
    for label, sentence, exp_sym, exp_sign, exp_hyd in PROBES:
        for kind, text in variants(sentence).items():
            r = pipe.extract(text)
            ok = set(r["symptoms"]) == set(exp_sym) and set(r["reportedSigns"]) == set(exp_sign) and r["hydrationIssue"] == exp_hyd
            wrong += not ok
            print(f"{label[:58]:58} {kind:9} {str(r['symptoms']):12} {str(r['reportedSigns']):16} {str(r['hydrationIssue']):9} {'ok' if ok else 'WRONG'}")
    print(f"\n{wrong} wrong of {len(PROBES) * 3}")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
