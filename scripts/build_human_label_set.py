"""
Builds a CSV of judge-scored responses for you to hand-score, so we can measure
how well the LLM judge agrees with human judgment (this is the standard way
real eval teams validate an LLM-as-judge pipeline before trusting it).

Samples N responses per dimension (default 3), spread across different models
where possible, from dimensions that were actually judge-scored (relevance,
bias, toxicity, refusal_quality, prompt_injection, hallucination).

Usage:
    python -m scripts.build_human_label_set
    python -m scripts.build_human_label_set --n-per-dim 4 --seed 7
"""
import argparse
import csv
import json
import random

from src.rubric import DIMENSIONS

DIM_ALIAS = {"prompt_injection": "prompt_injection_resistance"}
JUDGED_DIMENSIONS = {"relevance", "bias", "toxicity", "refusal_quality", "prompt_injection", "hallucination"}


def build(raw_responses_path: str, out_path: str, n_per_dim: int, seed: int):
    random.seed(seed)
    with open(raw_responses_path) as f:
        raw = json.load(f)

    # only entries that actually had an llm_judge score
    judged = [r for r in raw if "llm_judge" in r["scoring"] and r["dimension"] in JUDGED_DIMENSIONS]

    by_dim = {}
    for r in judged:
        by_dim.setdefault(r["dimension"], []).append(r)

    rows = []
    sample_id = 1
    for dim, items in by_dim.items():
        # spread across different models: shuffle, then greedily pick distinct models first
        random.shuffle(items)
        items.sort(key=lambda r: r["model"])  # stable grouping helps dedupe pass below
        seen_models = set()
        chosen = []
        for r in items:
            if r["model"] not in seen_models:
                chosen.append(r)
                seen_models.add(r["model"])
            if len(chosen) >= n_per_dim:
                break
        # if not enough distinct models, top up with whatever's left
        if len(chosen) < n_per_dim:
            remaining = [r for r in items if r not in chosen]
            chosen += remaining[: n_per_dim - len(chosen)]

        dim_key = DIM_ALIAS.get(dim, dim)
        description = DIMENSIONS.get(dim_key, {}).get("description", "")

        for r in chosen:
            judge_block = r["scoring"]["llm_judge"]
            per_judge_str = "; ".join(f"{name}={v['score']}" for name, v in judge_block["judges"].items())
            rows.append({
                "sample_id": sample_id,
                "model": r["model"],
                "test_id": r["test_id"],
                "attempt": r.get("attempt", 1),
                "dimension": dim,
                "dimension_description": description,
                "prompt": r["prompt"],
                "response": r["response"],
                "judge_score": judge_block["mean_score"],
                "judge_spread": judge_block["spread"],
                "per_judge_scores": per_judge_str,
                "human_score": "",  # <-- fill this in, 1-5
                "human_notes": "",  # <-- optional
            })
            sample_id += 1

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        if not rows:
            raise ValueError("No judge-scored rows were available for annotation sampling")
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} samples across {len(by_dim)} dimensions to {out_path}")
    print("Open it in Excel/Google Sheets, read each prompt+response against the")
    print("dimension_description, and fill in human_score (1-5) for every row.")
    print("Do NOT look at judge_score while scoring — that defeats the point.")
    print("Consider hiding/deleting the judge_score column while you score, then")
    print("restoring it before running the agreement analysis.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="results/raw_responses.json")
    parser.add_argument("--out", default="results/human_label_template.csv")
    parser.add_argument("--n-per-dim", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    build(args.raw, args.out, args.n_per_dim, args.seed)
