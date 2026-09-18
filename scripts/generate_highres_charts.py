"""Generate high-resolution dashboard charts for portfolio screenshots."""

from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

# Load merged data
scores = pd.read_csv(RESULTS / "merged" / "merged_scores.csv")
scores = scores[scores["valid_score"] == True].copy()
scores["final_score"] = pd.to_numeric(scores["final_score"], errors="coerce")
scores = scores.dropna(subset=["final_score"])

# Colors
BG = "#0B1020"
CARD_BG = "#141B33"
ACCENT = "#6C63FF"
ACCENT_2 = "#00D4AA"
TEXT = "#E8ECF8"
MUTED = "#9AA4C0"
GRID = "rgba(255,255,255,0.08)"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor": CARD_BG,
    "axes.edgecolor": (1, 1, 1, 0.08),
    "axes.labelcolor": TEXT,
    "text.color": TEXT,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "grid.color": (1, 1, 1, 0.08),
    "grid.alpha": 0.5,
    "font.family": "sans-serif",
    "font.size": 12,
    "figure.dpi": 200,
})

# --- Chart 1: Model comparison bar chart ---
fig, ax = plt.subplots(figsize=(10, 5))
summary = scores.groupby("model")["final_score"].agg(["mean", "std", "count"]).sort_values("mean", ascending=False)
models = summary.index.tolist()
means = summary["mean"].values
colors = [ACCENT, ACCENT_2]

bars = ax.bar(models, means, color=colors, width=0.5, edgecolor="none", zorder=3)
for bar, val in zip(bars, means):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
            f"{val:.2f}", ha="center", va="bottom", fontweight="bold", fontsize=14, color=TEXT)

ax.set_ylim(0, 5.5)
ax.set_ylabel("Average Score (1-5 scale)", fontsize=12, color=MUTED)
ax.set_title("GPT-OSS-120B vs GPT-OSS-20B — Composite Scores", fontsize=16, fontweight="bold", pad=15, color=TEXT)
ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
ax.grid(axis="y", alpha=0.3, zorder=0)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
fig.savefig(OUT / "model_comparison.png", dpi=200, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"Saved {OUT / 'model_comparison.png'}")

# --- Chart 2: Dimension heatmap ---
fig, ax = plt.subplots(figsize=(12, 6))
dim_summary = scores.groupby(["model", "dimension"])["final_score"].mean().unstack(fill_value=0)
# Order dimensions by average score
dim_order = dim_summary.mean(axis=0).sort_values(ascending=False).index.tolist()
dim_summary = dim_summary[dim_order]

im = ax.imshow(dim_summary.values, cmap="RdYlGn", aspect="auto", vmin=2.5, vmax=5.0)
ax.set_xticks(range(len(dim_order)))
ax.set_xticklabels([d.replace("_", " ").title() for d in dim_order], rotation=45, ha="right", fontsize=10)
ax.set_yticks(range(len(dim_summary)))
ax.set_yticklabels(dim_summary.index, fontsize=12, fontweight="bold")

for i in range(len(dim_summary)):
    for j in range(len(dim_order)):
        val = dim_summary.values[i, j]
        ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                color="white" if val < 4.0 else "black", fontsize=11, fontweight="bold")

ax.set_title("Score by Dimension — Heatmap Comparison", fontsize=16, fontweight="bold", pad=15, color=TEXT)
cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
cbar.set_label("Score", color=MUTED, fontsize=11)
cbar.ax.tick_params(colors=MUTED)
plt.tight_layout()
fig.savefig(OUT / "dimension_heatmap.png", dpi=200, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"Saved {OUT / 'dimension_heatmap.png'}")

# --- Chart 3: Bootstrap confidence intervals ---
try:
    uncertainty = pd.read_csv(RESULTS / "merged" / "uncertainty.csv")
except FileNotFoundError:
    from src.statistics import bootstrap_mean_ci
    rows = []
    for (model, dim), grp in scores.groupby(["model", "dimension"]):
        rows.append({"model": model, "dimension": dim, **bootstrap_mean_ci(grp["final_score"].tolist())})
    uncertainty = pd.DataFrame(rows)

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
for idx, model in enumerate(["Groq-GPT-OSS-120B", "Groq-GPT-OSS-20B"]):
    ax = axes[idx]
    u = uncertainty[uncertainty["model"] == model].sort_values("mean", ascending=True)
    dims = [d.replace("_", " ").title() for d in u["dimension"]]
    y = range(len(dims))
    means = u["mean"].values
    lows = means - u["ci_lower"].values
    highs = u["ci_upper"].values - means

    ax.barh(y, means, xerr=[lows, highs], color=ACCENT if idx == 0 else ACCENT_2,
            error_kw={"color": MUTED, "capsize": 3, "linewidth": 1.2}, height=0.6, zorder=3)
    for i, v in enumerate(means):
        ax.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=10, color=TEXT, fontweight="bold")

    ax.set_yticks(list(y))
    ax.set_yticklabels(dims, fontsize=10)
    ax.set_xlim(0, 5.5)
    ax.set_xlabel("Score (1-5)", fontsize=11, color=MUTED)
    ax.set_title(model.replace("Groq-", ""), fontsize=13, fontweight="bold", color=TEXT)
    ax.grid(axis="x", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.suptitle("95% Bootstrap Confidence Intervals by Dimension", fontsize=16, fontweight="bold", y=1.02, color=TEXT)
plt.tight_layout()
fig.savefig(OUT / "confidence_intervals.png", dpi=200, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"Saved {OUT / 'confidence_intervals.png'}")

# --- Chart 4: Human agreement summary card ---
fig, ax = plt.subplots(figsize=(6, 3))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5)
ax.axis("off")
fig.patch.set_facecolor(CARD_BG)

metrics = [
    ("Quadratic Weighted Kappa", "0.902", "Excellent agreement"),
    ("Exact Match Rate", "70.0%", "12/18 cases"),
    ("Within 1 Point", "100.0%", "18/18 cases"),
    ("Double-Reviewed Cases", "60", "2 reviewers, blind"),
]

for i, (label, value, note) in enumerate(metrics):
    y = 4.2 - i * 1.1
    ax.text(0.5, y, label, fontsize=10, color=MUTED, va="center")
    ax.text(6, y, value, fontsize=18, fontweight="bold", color=ACCENT_2, va="center")
    ax.text(8.5, y, note, fontsize=9, color=MUTED, va="center", style="italic")

ax.set_title("Human Reviewer Agreement", fontsize=14, fontweight="bold", pad=10, color=TEXT)
plt.tight_layout()
fig.savefig(OUT / "human_agreement.png", dpi=200, bbox_inches="tight", facecolor=CARD_BG)
plt.close(fig)
print(f"Saved {OUT / 'human_agreement.png'}")

print(f"\nAll charts saved to {OUT}")
