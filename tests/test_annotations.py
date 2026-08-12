import csv

import pytest

from src.annotations import load_annotation_rows


def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["model", "test_id", "dimension", "judge_score", "human_score"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_annotation_loader_skips_blank_human_scores(tmp_path):
    path = tmp_path / "labels.csv"
    write_rows(path, [{"model": "m", "test_id": "1", "dimension": "bias", "judge_score": "4", "human_score": ""}])

    assert load_annotation_rows(path) == []


def test_annotation_loader_rejects_duplicate_samples(tmp_path):
    path = tmp_path / "labels.csv"
    row = {"model": "m", "test_id": "1", "dimension": "bias", "judge_score": "4", "human_score": "4"}
    write_rows(path, [row, row])

    with pytest.raises(ValueError, match="Duplicate"):
        load_annotation_rows(path, allow_blank=False)
