"""
Runs every configured model against every test case, scores each response,
and writes results/raw_responses.json and results/scores.csv.

Usage:
    python -m src.runner
    python -m src.runner --config configs/models.json --data data/test_cases.json
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

from src.models import load_models_from_config
from src.scorers import score_test_case
from src.rubric import composite_score
from src.run_metadata import build_manifest, write_manifest
from src.schemas import load_json, validate_provider_configs, validate_test_cases

DIM_ALIAS = {"prompt_injection": "prompt_injection_resistance"}


def run(
    config_path: str,
    data_path: str,
    out_dir: str,
    judges_config_path: str,
    run_label: str = "development",
    dataset_version: str = "v1",
    rubric_version: str = "v1",
    attempts: int = 1,
    case_offset: int = 0,
    case_limit: int | None = None,
    case_ids: list[str] | None = None,
):
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    os.makedirs(out_dir, exist_ok=True)

    model_configs = validate_provider_configs(load_json(config_path), "model")
    test_cases = validate_test_cases(load_json(data_path))
    if case_offset < 0 or case_offset >= len(test_cases):
        raise ValueError("case_offset must be within the dataset")
    selected_cases = test_cases[case_offset:]
    if case_limit is not None:
        if case_limit < 1:
            raise ValueError("case_limit must be at least 1")
        selected_cases = selected_cases[:case_limit]
    if case_ids:
        requested_ids = set(case_ids)
        selected_cases = [tc for tc in test_cases if tc["id"] in requested_ids]
        missing_ids = requested_ids - {tc["id"] for tc in selected_cases}
        if missing_ids:
            raise ValueError(f"Unknown case IDs: {sorted(missing_ids)}")
        if not selected_cases:
            raise ValueError("case_ids must contain at least one known case ID")

    models = load_models_from_config(model_configs)

    from src.models import ModelClient
    if os.path.exists(judges_config_path):
        judge_configs = validate_provider_configs(load_json(judges_config_path), "judge")
        judge_clients = [ModelClient(**c) for c in judge_configs]
    else:
        judge_clients = [ModelClient(provider="groq", model="llama-3.3-70b-versatile", label="judge", temperature=0.0)]

    raw_responses = []
    score_rows = []

    run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    write_manifest(
        build_manifest(
            input_files=[data_path],
            config_files=[path for path in [config_path, judges_config_path] if os.path.exists(path)],
            run_id=run_id,
            metadata={
                "run_label": run_label,
                "dataset_version": dataset_version,
                "rubric_version": rubric_version,
                "attempts_per_case": attempts,
                "model_count": len(models),
                "case_count": len(selected_cases),
                "case_offset": case_offset,
                "total_dataset_cases": len(test_cases),
                "judge_count": len(judge_clients),
            },
        ),
        os.path.join(out_dir, "run_manifest.json"),
    )

    for model in models:
        print(f"\n=== Running model: {model.label} ===")
        dim_scores_for_composite = {}
        for attempt in range(1, attempts + 1):
            for tc in selected_cases:
                started = time.perf_counter()
                response = model.generate(tc["prompt"])
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                response_status = (
                    "error" if response.startswith("[ERROR after")
                    else "mock" if response.startswith("[MOCK RESPONSE")
                    else "ok"
                )
                if response_status == "error":
                    scoring = {"final_score": None, "llm_judge": {"invalid_judges": 0}}
                else:
                    scoring = score_test_case(tc, response, judge_clients=judge_clients)

                raw_responses.append({
                    "model": model.label,
                    "test_id": tc["id"],
                    "attempt": attempt,
                    "dimension": tc["dimension"],
                    "prompt": tc["prompt"],
                    "response": response,
                    "latency_ms": latency_ms,
                    "response_status": response_status,
                    "scoring": scoring,
                })

                dim_key = DIM_ALIAS.get(tc["dimension"], tc["dimension"])
                if scoring["final_score"] is not None:
                    dim_scores_for_composite.setdefault(dim_key, []).append(scoring["final_score"])

                score_rows.append({
                    "model": model.label,
                    "test_id": tc["id"],
                    "attempt": attempt,
                    "dimension": tc["dimension"],
                    "final_score": scoring["final_score"],
                    "valid_score": scoring["final_score"] is not None,
                    "invalid_judges": scoring.get("llm_judge", {}).get("invalid_judges", 0),
                    "latency_ms": latency_ms,
                    "response_status": response_status,
                })
                print(
                    f"  {tc['id']:10s} attempt={attempt} "
                    f"[{tc['dimension']:22s}] score={scoring['final_score']}"
                )

        # per-model composite (average each dimension first, then weight)
        avg_by_dim = {d: sum(s) / len(s) for d, s in dim_scores_for_composite.items()}
        comp = composite_score(avg_by_dim) if avg_by_dim else None
        print(f"  --> {model.label} composite score: {comp}/5")

    with open(os.path.join(out_dir, "raw_responses.json"), "w", encoding="utf-8") as f:
        json.dump(raw_responses, f, indent=2)

    with open(os.path.join(out_dir, "scores.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model", "test_id", "dimension", "final_score", "valid_score",
                "attempt", "invalid_judges", "latency_ms", "response_status",
            ],
        )
        writer.writeheader()
        writer.writerows(score_rows)

    print(f"\nSaved {len(raw_responses)} scored responses to {out_dir}/raw_responses.json and {out_dir}/scores.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/models.json")
    parser.add_argument("--data", default="data/test_cases.json")
    parser.add_argument("--out", default=None)
    parser.add_argument("--judges", default="configs/judges.json")
    parser.add_argument("--label", choices=["mock", "development", "real"], default="development")
    parser.add_argument("--dataset-version", default="v1")
    parser.add_argument("--rubric-version", default="v1")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--case-offset", type=int, default=0)
    parser.add_argument("--case-limit", type=int, default=None)
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        default=None,
        help="Run a specific test case ID; repeat for targeted retries",
    )
    args = parser.parse_args()
    output = args.out
    if output is None:
        stamp = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
        output = os.path.join("results", "runs", stamp)
    run(
        args.config,
        args.data,
        output,
        args.judges,
        run_label=args.label,
        dataset_version=args.dataset_version,
        rubric_version=args.rubric_version,
        attempts=args.attempts,
        case_offset=args.case_offset,
        case_limit=args.case_limit,
        case_ids=args.case_ids,
    )
