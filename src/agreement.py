"""
Computes how well the LLM judge agrees with human scores on the same responses.

Metrics reported (standard for validating an LLM-as-judge pipeline):
  - Pearson correlation   : linear relationship strength between judge & human scores
  - Spearman correlation  : rank-order agreement (robust to non-linearity)
  - Mean Absolute Error   : average |judge_score - human_score|
  - Exact match rate      : % of samples where judge_score == human_score
  - Within-1 agreement    : % of samples where |judge_score - human_score| <= 1
  - Quadratic weighted kappa : chance-corrected agreement for ordinal 1-5 ratings
                                (penalizes big misses more than small ones)

Usage:
    python -m src.agreement --labels results/human_label_template.csv
"""
import argparse
import os
import numpy as np
from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
from src.annotations import load_annotation_rows


def quadratic_weighted_kappa(y_true, y_pred, min_rating=1, max_rating=5):
    """Manual implementation (no sklearn dependency) of QWK for ordinal ratings."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    n_ratings = max_rating - min_rating + 1

    conf_mat = np.zeros((n_ratings, n_ratings))
    for t, p in zip(y_true, y_pred):
        conf_mat[t - min_rating][p - min_rating] += 1

    hist_true = np.sum(conf_mat, axis=1)
    hist_pred = np.sum(conf_mat, axis=0)
    n = len(y_true)

    weights = np.zeros((n_ratings, n_ratings))
    for i in range(n_ratings):
        for j in range(n_ratings):
            weights[i][j] = ((i - j) ** 2) / ((n_ratings - 1) ** 2)

    expected = np.outer(hist_true, hist_pred) / n
    num = np.sum(weights * conf_mat)
    den = np.sum(weights * expected)
    if den == 0:
        return 1.0
    return 1 - (num / den)


def load_labels(path: str):
    return load_annotation_rows(path, allow_blank=True)


def analyze(labels_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    rows = load_labels(labels_path)
    if len(rows) < 4:
        print(f"Only {len(rows)} labeled rows found — fill in more human_score values "
              f"in {labels_path} before running this (need at least a handful per dimension).")
        return

    judge = [r["judge_score"] for r in rows]
    human = [r["human_score"] for r in rows]

    pearson_r, pearson_p = pearsonr(judge, human)
    spearman_r, spearman_p = spearmanr(judge, human)
    mae = np.mean(np.abs(np.array(judge) - np.array(human)))
    judge_rounded = [int(round(s)) for s in judge]
    exact_match = np.mean(np.array(judge_rounded) == np.array(human))
    within_1 = np.mean(np.abs(np.array(judge) - np.array(human)) <= 1)
    qwk = quadratic_weighted_kappa(human, judge_rounded)

    print(f"\n=== Judge vs. Human Agreement (n={len(rows)}) ===")
    print(f"Pearson r          : {pearson_r:.3f}  (p={pearson_p:.4f})")
    print(f"Spearman rho       : {spearman_r:.3f}  (p={spearman_p:.4f})")
    print(f"Mean Absolute Error: {mae:.3f}")
    print(f"Exact match rate   : {exact_match:.1%}")
    print(f"Within-1 agreement : {within_1:.1%}")
    print(f"Quadratic weighted kappa: {qwk:.3f}")
    print(interpret_kappa(qwk))

    # per-dimension breakdown
    dims = sorted(set(r["dimension"] for r in rows))
    print("\n--- Per-dimension MAE (lower is better) ---")
    for d in dims:
        sub = [r for r in rows if r["dimension"] == d]
        if len(sub) < 2:
            print(f"  {d:20s} n={len(sub)} (too few to summarize)")
            continue
        sub_mae = np.mean([abs(r["judge_score"] - r["human_score"]) for r in sub])
        print(f"  {d:20s} n={len(sub):2d}  MAE={sub_mae:.2f}")

    # scatter plot with jitter so overlapping points are visible
    fig, ax = plt.subplots(figsize=(6, 6))
    jitter = lambda vals: np.array(vals) + np.random.uniform(-0.12, 0.12, size=len(vals))
    ax.scatter(jitter(judge), jitter(human), alpha=0.6, s=60)
    ax.plot([1, 5], [1, 5], "--", color="gray", label="perfect agreement")
    ax.set_xlabel("Judge score")
    ax.set_ylabel("Human score")
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_title(f"Judge vs. Human Scores (Pearson r={pearson_r:.2f})")
    ax.legend()
    plt.tight_layout()
    chart_path = f"{out_dir}/judge_vs_human_agreement.png"
    plt.savefig(chart_path, dpi=150)
    print(f"\nScatter plot saved to {chart_path}")

    return {
        "pearson_r": pearson_r, "spearman_r": spearman_r, "mae": mae,
        "exact_match": exact_match, "within_1": within_1, "qwk": qwk, "n": len(rows),
    }


def interpret_kappa(qwk: float) -> str:
    if qwk >= 0.8:
        band = "almost perfect agreement"
    elif qwk >= 0.6:
        band = "substantial agreement"
    elif qwk >= 0.4:
        band = "moderate agreement"
    elif qwk >= 0.2:
        band = "fair agreement"
    else:
        band = "slight/poor agreement — the judge should not be trusted without human spot-checks"
    return f"(Landis & Koch interpretation: {band})"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", default="results/human_label_template.csv")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    analyze(args.labels, args.out)
