"""Restore analysis-only judge columns onto completed blind review workbooks."""
import argparse
import csv
from pathlib import Path

from openpyxl import load_workbook


def read_workbook(path: str) -> list[dict]:
    sheet = load_workbook(path, data_only=True).active
    headers = [cell.value for cell in sheet[1]]
    return [dict(zip(headers, row)) for row in sheet.iter_rows(min_row=2, values_only=True)]


def prepare(blind_csv: str, workbook_path: str, output_csv: str) -> None:
    with open(blind_csv, encoding="utf-8-sig", newline="") as f:
        blind_rows = list(csv.DictReader(f))
    reviewed_rows = read_workbook(workbook_path)
    blind_by_id = {str(row["sample_id"]): row for row in blind_rows}
    reviewed_by_id = {str(int(row["sample_id"])): row for row in reviewed_rows}
    if set(reviewed_by_id) != set(blind_by_id):
        raise ValueError(f"{workbook_path} does not contain exactly the blind sample set")

    output_rows = []
    for sample_id, reviewed in reviewed_by_id.items():
        score = reviewed.get("human_score")
        if score in (None, "") or int(score) not in range(1, 6):
            raise ValueError(f"Invalid human_score for sample {reviewed.get('sample_id')}: {score}")
        original = blind_by_id[sample_id]
        row = dict(original)
        row["human_score"] = str(int(score))
        row["human_notes"] = reviewed.get("human_notes") or ""
        output_rows.append(row)

    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Wrote {len(output_rows)} labels to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--blind", required=True)
    parser.add_argument("--workbook", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    prepare(args.blind, args.workbook, args.out)
