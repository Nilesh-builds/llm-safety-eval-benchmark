"""
Sanity-checks the LLM judge itself, independent of any model being benchmarked.

Runs the judge against a small set of hand-written reference responses with
known-correct scores (obviously good responses -> should score 5, obviously
bad ones -> should score 1). If the judge disagrees with these on cases this
clear-cut, it shouldn't be trusted on the harder, real model outputs either.

Usage:
    python -m src.calibration
"""
import argparse
import json

from src.models import ModelClient
from src.scorers import build_judge_prompt, score_llm_judge


def run_calibration(cases_path: str, judge_provider: str, judge_model: str):
    with open(cases_path) as f:
        cases = json.load(f)

    judge = ModelClient(provider=judge_provider, model=judge_model, label="calibration-judge", temperature=0.0)

    results = []
    for c in cases:
        # reuse the scorer with a fake test_case shape matching what score_llm_judge expects
        fake_test_case = {"dimension": c["dimension"], "prompt": c["prompt"], "check": {"calibration_label": c["label"]}}
        scoring = score_llm_judge(fake_test_case, c["response"], judge)
        match = scoring["score"] == c["expected_score"]
        close = abs(scoring["score"] - c["expected_score"]) <= 1
        results.append({
            "dimension": c["dimension"],
            "label": c["label"],
            "expected": c["expected_score"],
            "judge_gave": scoring["score"],
            "exact_match": match,
            "within_1": close,
            "judge_reasoning": scoring["reasoning"],
        })

    print(f"\n=== Judge Calibration Check ({judge.label}, n={len(results)}) ===\n")
    n_exact = sum(r["exact_match"] for r in results)
    n_close = sum(r["within_1"] for r in results)
    for r in results:
        flag = "OK  " if r["exact_match"] else ("~ok " if r["within_1"] else "FAIL")
        print(f"[{flag}] {r['dimension']:16s} | expected={r['expected']} judge={r['judge_gave']:<2d} | {r['label']}")
        if not r["exact_match"]:
            print(f"         judge reasoning: {r['judge_reasoning']}")

    print(f"\nExact match: {n_exact}/{len(results)} ({n_exact/len(results):.0%})")
    print(f"Within-1:    {n_close}/{len(results)} ({n_close/len(results):.0%})")
    if n_exact / len(results) < 0.7:
        print("\n⚠️  Judge is missing clear-cut cases — treat its scores on real model")
        print("   outputs with caution, and weight the human-agreement analysis more heavily.")
    else:
        print("\nJudge handles clear-cut cases reasonably well — a reasonable baseline")
        print("of trust, though the human-agreement analysis on real (harder) responses")
        print("is still the more meaningful check.")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="data/judge_calibration_cases.json")
    parser.add_argument("--judge-provider", default="groq")
    parser.add_argument("--judge-model", default="llama-3.3-70b-versatile")
    args = parser.parse_args()
    run_calibration(args.cases, args.judge_provider, args.judge_model)
