"""
Builds a per-model x per-dimension summary table and a bar chart from results/scores.csv.

Usage:
    python -m src.report
"""
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt

from src.rubric import composite_score
from src.statistics import bootstrap_mean_ci

DIM_ALIAS = {"prompt_injection": "prompt_injection_resistance"}


def build_report(scores_csv: str, out_dir: str):
    df = pd.read_csv(scores_csv)
    df["dimension"] = df["dimension"].replace(DIM_ALIAS)
    if "valid_score" in df.columns:
        invalid_count = int((df["valid_score"] == False).sum())  # noqa: E712
        if invalid_count:
            print(f"Ignoring {invalid_count} invalid score rows in the report.")
        df = df[df["valid_score"] != False].copy()  # noqa: E712
    df["final_score"] = pd.to_numeric(df["final_score"], errors="coerce")
    df = df.dropna(subset=["final_score"])

    pivot = df.pivot_table(index="model", columns="dimension", values="final_score", aggfunc="mean").round(2)

    composites = {}
    for model, row in pivot.iterrows():
        composites[model] = composite_score(row.dropna().to_dict())
    pivot["COMPOSITE"] = pd.Series(composites)
    pivot = pivot.sort_values("COMPOSITE", ascending=False)

    os.makedirs(out_dir, exist_ok=True)
    summary_path = os.path.join(out_dir, "summary.csv")
    pivot.to_csv(summary_path)
    print(f"Summary table saved to {summary_path}\n")
    print(pivot.to_string())

    # Composite score bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    pivot["COMPOSITE"].plot(kind="barh", ax=ax, color="#4C72B0")
    ax.set_xlabel("Composite score (1-5)")
    ax.set_xlim(0, 5)
    ax.set_title("LLM Safety & Response Evaluation Benchmark — Composite Scores")
    ax.invert_yaxis()
    plt.tight_layout()
    chart_path = os.path.join(out_dir, "composite_scores.png")
    plt.savefig(chart_path, dpi=150)
    print(f"\nChart saved to {chart_path}")

    # Heatmap-style per-dimension chart
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    dim_cols = [c for c in pivot.columns if c != "COMPOSITE"]
    im = ax2.imshow(pivot[dim_cols].values, cmap="RdYlGn", vmin=1, vmax=5, aspect="auto")
    ax2.set_xticks(range(len(dim_cols)))
    ax2.set_xticklabels(dim_cols, rotation=45, ha="right")
    ax2.set_yticks(range(len(pivot.index)))
    ax2.set_yticklabels(pivot.index)
    for i in range(len(pivot.index)):
        for j in range(len(dim_cols)):
            val = pivot[dim_cols].values[i, j]
            ax2.text(j, i, f"{val:.1f}" if pd.notna(val) else "-", ha="center", va="center", fontsize=8)
    fig2.colorbar(im, ax=ax2, label="Score (1-5)")
    ax2.set_title("Per-Dimension Scores by Model")
    plt.tight_layout()
    heatmap_path = os.path.join(out_dir, "dimension_heatmap.png")
    plt.savefig(heatmap_path, dpi=150)
    print(f"Heatmap saved to {heatmap_path}")

    uncertainty_rows = []
    for (model, dimension), group in df.groupby(["model", "dimension"]):
        interval = bootstrap_mean_ci(group["final_score"].tolist())
        uncertainty_rows.append(
            {
                "model": model,
                "dimension": dimension,
                **interval,
            }
        )
    uncertainty_path = os.path.join(out_dir, "uncertainty.csv")
    pd.DataFrame(uncertainty_rows).to_csv(uncertainty_path, index=False)
    print(f"Uncertainty table saved to {uncertainty_path}")

    return pivot


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", default="results/scores.csv")
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    build_report(args.scores, args.out)
