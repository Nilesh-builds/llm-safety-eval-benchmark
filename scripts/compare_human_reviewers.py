"""Compare two independent human review CSV files."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

from src.agreement import quadratic_weighted_kappa


def compare(first_path: str, second_path: str, out_path: str) -> dict:
    def load(path):
        with open(path, encoding="utf-8-sig", newline="") as f:
            return {row["sample_id"]: row for row in csv.DictReader(f)}

    first, second = load(first_path), load(second_path)
    if set(first) != set(second):
        raise ValueError("Reviewer files must contain the same sample IDs")
    ids = sorted(first, key=lambda value: int(value))
    a = np.array([int(first[i]["human_score"]) for i in ids])
    b = np.array([int(second[i]["human_score"]) for i in ids])
    result = {
        "n": len(ids),
        "pearson_r": float(pearsonr(a, b).statistic),
        "spearman_rho": float(spearmanr(a, b).statistic),
        "mean_absolute_error": float(np.mean(np.abs(a - b))),
        "exact_match": float(np.mean(a == b)),
        "within_1": float(np.mean(np.abs(a - b) <= 1)),
        "quadratic_weighted_kappa": float(quadratic_weighted_kappa(a, b)),
    }
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote reviewer agreement to {output}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", required=True)
    parser.add_argument("--second", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    compare(args.first, args.second, args.out)
