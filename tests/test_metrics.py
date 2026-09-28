"""Regression tests locking README numbers to results/metrics.json."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _metrics():
    return json.loads((ROOT / "results" / "metrics.json").read_text())


def test_composite_scores_match_summary():
    import pandas as pd

    summary = pd.read_csv(ROOT / "results" / "merged" / "summary.csv", index_col=0)
    m = _metrics()
    assert m["models"]["Groq-GPT-OSS-120B"]["composite"] == round(float(summary.loc["Groq-GPT-OSS-120B", "COMPOSITE"]), 3)
    assert m["models"]["Groq-GPT-OSS-20B"]["composite"] == round(float(summary.loc["Groq-GPT-OSS-20B", "COMPOSITE"]), 3)


def test_gap_is_small_vs_uncertainty():
    m = _metrics()
    gap = m["gap"]["diff"]
    ci120 = m["models"]["Groq-GPT-OSS-120B"]["composite_ci95"]
    ci20 = m["models"]["Groq-GPT-OSS-20B"]["composite_ci95"]
    # CIs overlap -> gap not proven.
    assert ci120["ci_lower"] < ci20["ci_upper"]
    assert ci20["ci_lower"] < ci120["ci_upper"]
    assert gap == round(ci120["mean"] - ci20["mean"], 3)


def test_human_exact_match_is_63_not_70():
    m = _metrics()
    assert m["human_agreement"]["exact_match"] == 0.633
    assert m["human_agreement"]["quadratic_weighted_kappa"] == 0.902
    assert m["human_agreement"]["n"] == 60


def test_calibration_case_count():
    cases = json.loads((ROOT / "data" / "judge_calibration_cases.json").read_text())
    assert len(cases) == 11
    assert _metrics()["calibration"]["n_cases"] == 11


def test_composite_weighting_sanity():
    from src.rubric import composite_score

    # Safety-critical dims carry higher weight than consistency.
    from src.rubric import DIMENSIONS

    assert DIMENSIONS["refusal_quality"]["weight"] > DIMENSIONS["consistency"]["weight"]
    assert composite_score({"refusal_quality": 5, "consistency": 1}) > 3.0
