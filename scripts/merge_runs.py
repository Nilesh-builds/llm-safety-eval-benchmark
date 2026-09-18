"""
Merges multiple run directories into a single deduplicated scores table so the
existing report pipeline (src.report) can aggregate across batches and re-runs.

Every merged row keeps its source run_id and run timestamp for auditability.
Duplicates (same model, test_id, attempt, dataset version) are resolved by
keeping the newest run's row, preferring rows with a valid score, so a re-run
of a failed batch replaces the error rows it supersedes.

Usage:
    python -m scripts.merge_runs
    python -m scripts.merge_runs --runs-root results/runs --out results/merged --label real
    python -m scripts.merge_runs --dataset-version v2.0.0
"""
import argparse
import csv
import json
import os
from datetime import datetime

SCORE_FIELDS = [
    "model", "test_id", "dimension", "final_score", "valid_score",
    "attempt", "invalid_judges", "latency_ms", "response_status",
]
MERGE_KEY_FIELDS = ["model", "test_id", "attempt", "dataset_version"]
PROVENANCE_FIELDS = ["run_id", "run_created_at", "dataset_version"]


def _parse_created_at(manifest: dict, run_id: str) -> datetime:
    raw = manifest.get("created_at_utc")
    if raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    try:
        return datetime.strptime(run_id, "run-%Y%m%dT%H%M%SZ").replace(tzinfo=None)
    except ValueError:
        return datetime.min


def load_runs(runs_root: str, label: str | None, dataset_version: str | None) -> list[dict]:
    """Returns one dict per usable run directory, oldest first."""
    runs = []
    for name in sorted(os.listdir(runs_root)):
        run_dir = os.path.join(runs_root, name)
        manifest_path = os.path.join(run_dir, "run_manifest.json")
        scores_path = os.path.join(run_dir, "scores.csv")
        if not (os.path.isfile(manifest_path) and os.path.isfile(scores_path)):
            continue
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        if label is not None and manifest.get("run_label") != label:
            continue
        if dataset_version is not None and manifest.get("dataset_version") != dataset_version:
            continue
        with open(scores_path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        run_id = manifest.get("run_id", name)
        runs.append({
            "run_id": run_id,
            "created_at": _parse_created_at(manifest, run_id),
            "manifest": manifest,
            "rows": rows,
        })
    runs.sort(key=lambda r: r["created_at"])
    return runs


def merge_rows(runs: list[dict]) -> tuple[list[dict], list[str]]:
    """Deduplicates rows across runs (oldest to newest). Returns (rows, warnings)."""
    warnings = []
    versions = {r["manifest"].get("dataset_version") for r in runs}
    if len(versions) > 1:
        warnings.append(f"mixed dataset versions merged: {sorted(v for v in versions if v)}")
    rubrics = {r["manifest"].get("rubric_version") for r in runs}
    if len(rubrics) > 1:
        warnings.append(f"mixed rubric versions merged: {sorted(v for v in rubrics if v)}")

    best: dict[tuple, dict] = {}
    superseded = 0
    for run in runs:
        for row in run["rows"]:
            candidate = dict(row)
            candidate["run_id"] = run["run_id"]
            candidate["run_created_at"] = run["created_at"].isoformat()
            candidate["dataset_version"] = run["manifest"].get("dataset_version", "")
            key = tuple(candidate.get(f, "") for f in MERGE_KEY_FIELDS)
            if key in best:
                superseded += 1
                new_valid = candidate.get("valid_score") == "True"
                old_valid = best[key].get("valid_score") == "True"
                if not new_valid and old_valid:
                    continue
            best[key] = candidate

    if superseded:
        warnings.append(f"{superseded} duplicate rows resolved (newest valid run kept)")
    merged = sorted(
        best.values(),
        key=lambda r: (r["model"], r["test_id"], r.get("attempt", "")),
    )
    return merged, warnings


def coverage_report(merged: list[dict]) -> str:
    lines = []
    for model in sorted({r["model"] for r in merged}):
        mr = [r for r in merged if r["model"] == model]
        valid = sum(1 for r in mr if r.get("valid_score") == "True")
        errors = sum(1 for r in mr if r.get("response_status") == "error")
        cases = len({r["test_id"] for r in mr})
        lines.append(
            f"  {model:22s} cases={cases:4d} rows={len(mr):4d} "
            f"valid_scores={valid:4d} errors={errors:3d}"
        )
    return "\n".join(lines)


def merge_runs(runs_root: str, out_dir: str, label: str | None, dataset_version: str | None) -> list[dict]:
    runs = load_runs(runs_root, label, dataset_version)
    if not runs:
        raise SystemExit(f"No runs with run_manifest.json + scores.csv found under {runs_root}")
    print(f"Merging {len(runs)} run(s):")
    for r in runs:
        print(f"  {r['run_id']}  {r['manifest'].get('run_label', '?'):11s} "
              f"dataset={r['manifest'].get('dataset_version', '?')} cases={r['manifest'].get('case_count', '?')}")

    merged, warnings = merge_rows(runs)
    for w in warnings:
        print(f"WARNING: {w}")

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "merged_scores.csv")
    fieldnames = SCORE_FIELDS + [f for f in PROVENANCE_FIELDS if f not in SCORE_FIELDS]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)
    print(f"\n{coverage_report(merged)}")
    print(f"\nWrote {len(merged)} merged rows to {out_path}")
    print(f"Build the report with: python -m src.report --scores {out_path} --out {out_dir}")
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", default="results/runs")
    parser.add_argument("--out", default="results/merged")
    parser.add_argument("--label", default=None, help="Filter by run_label, e.g. real")
    parser.add_argument("--dataset-version", default=None, help="Filter by dataset version")
    args = parser.parse_args()
    merge_runs(args.runs_root, args.out, args.label, args.dataset_version)
