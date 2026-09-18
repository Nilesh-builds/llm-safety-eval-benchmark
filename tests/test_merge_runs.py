import csv
import json
import os

from scripts.merge_runs import load_runs, merge_rows


def make_run(runs_root, run_id, created_at, label, dataset_version, rows):
    run_dir = os.path.join(runs_root, run_id)
    os.makedirs(run_dir, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "created_at_utc": created_at,
        "run_label": label,
        "dataset_version": dataset_version,
        "rubric_version": "v1.0.0",
        "case_count": len(rows),
    }
    with open(os.path.join(run_dir, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with open(os.path.join(run_dir, "scores.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model", "test_id", "dimension", "final_score", "valid_score",
                "attempt", "invalid_judges", "latency_ms", "response_status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def row(model, test_id, final_score, valid, status="ok"):
    return {
        "model": model, "test_id": test_id, "dimension": "factuality",
        "final_score": final_score, "valid_score": valid, "attempt": "1",
        "invalid_judges": "0", "latency_ms": "100.0", "response_status": status,
    }


def test_rerun_replaces_error_rows(tmp_path):
    root = str(tmp_path / "runs")
    make_run(root, "run-20260918T010000Z", "2026-09-18T01:00:00+00:00", "real", "v2.0.0", [
        row("M1", "T1", "", "False", "error"),
        row("M1", "T2", "4.0", "True"),
    ])
    make_run(root, "run-20260918T020000Z", "2026-09-18T02:00:00+00:00", "real", "v2.0.0", [
        row("M1", "T1", "5.0", "True"),
    ])

    runs = load_runs(root, label="real", dataset_version=None)
    merged, warnings = merge_rows(runs)

    by_id = {r["test_id"]: r for r in merged}
    assert by_id["T1"]["run_id"] == "run-20260918T020000Z"
    assert by_id["T1"]["final_score"] == "5.0"
    assert by_id["T2"]["run_id"] == "run-20260918T010000Z"
    assert any("duplicate rows" in w for w in warnings)


def test_newer_error_row_does_not_replace_valid_score(tmp_path):
    root = str(tmp_path / "runs")
    make_run(root, "run-20260918T010000Z", "2026-09-18T01:00:00+00:00", "real", "v2.0.0", [
        row("M1", "T1", "4.0", "True"),
    ])
    make_run(root, "run-20260918T020000Z", "2026-09-18T02:00:00+00:00", "real", "v2.0.0", [
        row("M1", "T1", "", "False", "error"),
    ])

    runs = load_runs(root, label="real", dataset_version=None)
    merged, _ = merge_rows(runs)

    assert len(merged) == 1
    assert merged[0]["final_score"] == "4.0"
    assert merged[0]["run_id"] == "run-20260918T010000Z"


def test_label_filter_excludes_development_runs(tmp_path):
    root = str(tmp_path / "runs")
    make_run(root, "run-20260918T010000Z", "2026-09-18T01:00:00+00:00", "real", "v2.0.0", [
        row("M1", "T1", "4.0", "True"),
    ])
    make_run(root, "run-20260918T020000Z", "2026-09-18T02:00:00+00:00", "development", "v2.0.0", [
        row("M1", "T2", "1.0", "True"),
    ])

    runs = load_runs(root, label="real", dataset_version=None)
    merged, _ = merge_rows(runs)

    assert {r["test_id"] for r in merged} == {"T1"}


def test_mixed_dataset_versions_do_not_collide(tmp_path):
    root = str(tmp_path / "runs")
    make_run(root, "run-20260918T010000Z", "2026-09-18T01:00:00+00:00", "real", "v1.0.0", [
        row("M1", "IF-1", "3.0", "True"),
    ])
    make_run(root, "run-20260918T020000Z", "2026-09-18T02:00:00+00:00", "real", "v2.0.0", [
        row("M1", "IF-1", "5.0", "True"),
    ])

    runs = load_runs(root, label="real", dataset_version=None)
    merged, warnings = merge_rows(runs)

    assert len(merged) == 2
    assert any("mixed dataset versions" in w for w in warnings)
    assert {r["dataset_version"] for r in merged} == {"v1.0.0", "v2.0.0"}
