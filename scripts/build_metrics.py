"""Build results/metrics.json from committed evidence (no API calls)."""
import datetime
import json
from pathlib import Path

import pandas as pd

from src.rubric import composite_score
from src.statistics import bootstrap_mean_ci

ROOT = Path(__file__).resolve().parent.parent

summary = pd.read_csv(ROOT / "results" / "merged" / "summary.csv", index_col=0)
reviewer = json.loads((ROOT / "results" / "merged" / "reviewer_agreement.json").read_text())
calib_cases = json.loads((ROOT / "data" / "judge_calibration_cases.json").read_text())

# Composite bootstrap CIs by resampling scored responses (seed 42, 2000 resamples).
import numpy as np

df = pd.read_csv(ROOT / "results" / "merged" / "merged_scores.csv")
df["dimension"] = df["dimension"].replace({"prompt_injection": "prompt_injection_resistance"})
v = df[df["valid_score"] != False].copy()
rng = np.random.default_rng(42)
comp_ci = {}
for model in ["Groq-GPT-OSS-120B", "Groq-GPT-OSS-20B"]:
    sub = v[v["model"] == model]
    idx = sub.index.to_numpy()
    vals = []
    for _ in range(2000):
        s = v.loc[rng.choice(idx, size=len(idx), replace=True)]
        p = s.groupby("dimension")["final_score"].mean().round(2)
        vals.append(composite_score(p.to_dict()))
    comp_ci[model] = {
        "mean": float(summary.loc[model, "COMPOSITE"]),
        "ci_lower": round(float(np.quantile(vals, 0.025)), 3),
        "ci_upper": round(float(np.quantile(vals, 0.975)), 3),
        "n_scored_responses": int(len(sub)),
    }

row120 = summary.loc["Groq-GPT-OSS-120B"]
row20 = summary.loc["Groq-GPT-OSS-20B"]

out = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "provenance": "Offline verification from committed files (no API calls). Raw scores collected 2026-09-18 via Groq free tier; math recomputed locally.",
    "dataset": {"version": "v2.0.0", "cases_per_model": 200, "models": 2, "total_responses": 800},
    "models": {
        "Groq-GPT-OSS-120B": {
            "composite": float(row120["COMPOSITE"]),
            "safety": float(row120["CAT_SAFETY"]),
            "quality": float(row120["CAT_QUALITY"]),
            "robustness": float(row120["CAT_ROBUSTNESS"]),
            "composite_ci95": comp_ci["Groq-GPT-OSS-120B"],
        },
        "Groq-GPT-OSS-20B": {
            "composite": float(row20["COMPOSITE"]),
            "safety": float(row20["CAT_SAFETY"]),
            "quality": float(row20["CAT_QUALITY"]),
            "robustness": float(row20["CAT_ROBUSTNESS"]),
            "composite_ci95": comp_ci["Groq-GPT-OSS-20B"],
        },
    },
    "gap": {
        "diff": round(float(row120["COMPOSITE"] - row20["COMPOSITE"]), 3),
        "interpretation": "CIs overlap substantially; gap is consistent with noise at this sample size, not a proven superiority.",
    },
    "human_agreement": {
        "n": reviewer["n"],
        "quadratic_weighted_kappa": round(reviewer["quadratic_weighted_kappa"], 3),
        "exact_match": round(reviewer["exact_match"], 3),
        "within_1": reviewer["within_1"],
        "note": "Human-human agreement; source label CSVs are gitignored (results/human_review/) so this cannot be re-run from a clean clone.",
    },
    "calibration": {
        "n_cases": len(calib_cases),
        "status": "UNVERIFIED - requires live Groq judge API key; no result file committed",
    },
}

path = ROOT / "results" / "metrics.json"
path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(path.read_text())
