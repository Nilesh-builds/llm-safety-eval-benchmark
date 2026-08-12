"""Contracts and loading helpers for human annotation files."""

from __future__ import annotations

import csv
from pathlib import Path


REQUIRED_COLUMNS = {
    "model",
    "test_id",
    "dimension",
    "judge_score",
    "human_score",
}


def load_annotation_rows(path: str | Path, allow_blank: bool = True) -> list[dict]:
    """Load labels and reject malformed or duplicated annotation records."""
    source = Path(path)
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Annotation file is missing columns: {sorted(missing)}")

        rows = []
        seen = set()
        for line_number, row in enumerate(reader, start=2):
            key = (row["model"], row["test_id"])
            if key in seen:
                raise ValueError(f"Duplicate annotation sample at line {line_number}: {key}")
            seen.add(key)
            try:
                judge_score = float(row["judge_score"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid judge_score at line {line_number}") from error
            if not 1 <= judge_score <= 5:
                raise ValueError(f"judge_score must be between 1 and 5 at line {line_number}")

            human_value = row["human_score"].strip()
            if not human_value and allow_blank:
                continue
            try:
                human_score = int(human_value)
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid human_score at line {line_number}") from error
            if human_score not in range(1, 6):
                raise ValueError(f"human_score must be an integer from 1 to 5 at line {line_number}")
            rows.append(
                {
                    "dimension": row["dimension"],
                    "judge_score": judge_score,
                    "human_score": human_score,
                    "model": row["model"],
                    "test_id": row["test_id"],
                }
            )
    return rows
