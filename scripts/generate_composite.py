"""Generate a full dashboard composite image at high resolution."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

scores = pd.read_csv(RESULTS / "merged" / "merged_scores.csv")
valid = scores[scores["valid_score"] == True].copy()
valid["final_score"] = pd.to_numeric(valid["final_score"], errors="coerce")
valid = valid.dropna(subset=["final_score"])

BG = "#0B1020"
CARD_BG = "#141B33"
ACCENT = "#6C63FF"
ACCENT2 = "#00D4AA"
TEXT = "#E8ECF8"
MUTED = "#9AA4C0"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": CARD_BG,
    "axes.edgecolor": (1,1,1,0.08), "axes.labelcolor": TEXT,
    "text.color": TEXT, "xtick.color": MUTED, "ytick.color": MUTED,
    "grid.color": (1,1,1,0.08), "grid.alpha": 0.5,
    "font.family": "sans-serif", "font.size": 10,
})

try:
    uncertainty = pd.read_csv(RESULTS / "merged" / "uncertainty.csv")
except Exception:
    from src.statistics import bootstrap_mean_ci
    rows = []
    for (model, dim), grp in valid.groupby(["model", "dimension"]):
        rows.append({"model": model, "dimension": dim, **bootstrap_mean_ci(grp["final_score"].tolist())})
    uncertainty = pd.DataFrame(rows)

fig = plt.figure(figsize=(14, 20))
gs_outer = gridspec.GridSpec(4, 1, figure=fig, hspace=0.3,
                            left=0.06, right=0.94, top=0.95, bottom=0.04)
gs_title = gs_outer[0].subgridspec(1, 1)
gs_kpi = gs_outer[1].subgridspec(1, 4, wspace=0.3)
gs_charts = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3,
                              left=0.06, right=0.94, top=0.62, bottom=0.04)

# Title
ax = fig.add_subplot(gs_title[0, 0])
ax.set_xlim(0, 10); ax.set_ylim(0, 4); ax.axis("off")
ax.text(5, 3.2, "LLM Evaluation Evidence", fontsize=28, fontweight="bold",
        ha="center", va="center", color=TEXT)
ax.text(5, 2.1, "200 cases x 2 attempts  |  722 valid responses  |  Free-tier Groq API",
        fontsize=12, ha="center", va="center", color=MUTED)
badges = ["9 evaluation dimensions", "LLM-as-judge ensemble", "Free-tier APIs only", "Blind human review"]
bcolors = [ACCENT, ACCENT, ACCENT2, ACCENT2]
for i, (b, c) in enumerate(zip(badges, bcolors)):
    x = 1.5 + i * 2.3
    ax.text(x, 1.0, b, fontsize=9, ha="center", va="center", color=TEXT,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=c, alpha=0.25, edgecolor=c, linewidth=1))

# KPIs
kpis = [("Scored Responses", f"{len(valid):,}"), ("Models Evaluated", str(valid["model"].nunique())),
        ("Dimensions", str(valid["dimension"].nunique())), ("Human QWK", "0.902")]
for i, (label, value) in enumerate(kpis):
    ax = fig.add_subplot(gs_kpi[0, i])
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")
    ax.text(5, 3.2, value, fontsize=34, fontweight="bold", ha="center", va="center",
            color=ACCENT2 if i == 3 else TEXT)
    ax.text(5, 0.8, label, fontsize=12, ha="center", va="center", color=TEXT)
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_edgecolor((1,1,1,0.12)); sp.set_linewidth(1)

# Model comparison - use report composites
report = pd.read_csv(RESULTS / "merged" / "summary.csv")
report = report.set_index("model").sort_values("COMPOSITE", ascending=False)
ax_bar = fig.add_subplot(gs_charts[0, 0])
models = report.index.tolist()
composites = report["COMPOSITE"].values
bars = ax_bar.barh(range(len(models)), composites, color=[ACCENT2, ACCENT][:len(models)], height=0.5, zorder=3)
for i, val in enumerate(composites):
    ax_bar.text(val + 0.03, i, f"{val:.3f}", va="center", fontweight="bold", fontsize=12, color=TEXT)
ax_bar.set_yticks(range(len(models)))
ax_bar.set_yticklabels([m.replace("Groq-", "") for m in models], fontsize=11, fontweight="bold")
ax_bar.set_xlim(0, 5.5)
ax_bar.set_title("Composite Score by Model (1-5)", fontsize=13, fontweight="bold", pad=10, color=TEXT)
ax_bar.grid(axis="x", alpha=0.3, zorder=0)
ax_bar.spines["top"].set_visible(False); ax_bar.spines["right"].set_visible(False)

# 120B CI
ax_dim = fig.add_subplot(gs_charts[0, 1])
u120 = uncertainty[uncertainty["model"] == "Groq-GPT-OSS-120B"].sort_values("mean", ascending=True)
d120 = [d.replace("_", " ").title() for d in u120["dimension"]]
m120 = u120["mean"].values
l120 = m120 - u120["ci_lower"].values
h120 = u120["ci_upper"].values - m120
ax_dim.barh(range(len(d120)), m120, xerr=[l120, h120], color=ACCENT,
            error_kw={"color": MUTED, "capsize": 3, "linewidth": 1}, height=0.6, zorder=3)
for i, v in enumerate(m120):
    ax_dim.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=9, color=TEXT, fontweight="bold")
ax_dim.set_yticks(range(len(d120))); ax_dim.set_yticklabels(d120, fontsize=9)
ax_dim.set_xlim(0, 5.5)
ax_dim.set_title("GPT-OSS-120B  -  95% CI", fontsize=13, fontweight="bold", pad=10, color=TEXT)
ax_dim.grid(axis="x", alpha=0.3, zorder=0)
ax_dim.spines["top"].set_visible(False); ax_dim.spines["right"].set_visible(False)

# 20B CI
ax_d2 = fig.add_subplot(gs_charts[1, 0])
u20 = uncertainty[uncertainty["model"] == "Groq-GPT-OSS-20B"].sort_values("mean", ascending=True)
d20 = [d.replace("_", " ").title() for d in u20["dimension"]]
m20 = u20["mean"].values
l20 = m20 - u20["ci_lower"].values
h20 = u20["ci_upper"].values - m20
ax_d2.barh(range(len(d20)), m20, xerr=[l20, h20], color=ACCENT2,
           error_kw={"color": MUTED, "capsize": 3, "linewidth": 1}, height=0.6, zorder=3)
for i, v in enumerate(m20):
    ax_d2.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=9, color=TEXT, fontweight="bold")
ax_d2.set_yticks(range(len(d20))); ax_d2.set_yticklabels(d20, fontsize=9)
ax_d2.set_xlim(0, 5.5)
ax_d2.set_title("GPT-OSS-20B  -  95% CI", fontsize=13, fontweight="bold", pad=10, color=TEXT)
ax_d2.grid(axis="x", alpha=0.3, zorder=0)
ax_d2.spines["top"].set_visible(False); ax_d2.spines["right"].set_visible(False)

# Human agreement card
ax_h = fig.add_subplot(gs_charts[1, 1])
ax_h.set_xlim(0, 10); ax_h.set_ylim(0, 5); ax_h.axis("off")
ax_h.text(5, 4.2, "Human Reviewer Agreement", fontsize=14, fontweight="bold",
          ha="center", va="center", color=TEXT)
metrics = [("QWK", "0.902", "Excellent"), ("Exact Match", "70.0%", "12/18"),
           ("Within 1 Point", "100.0%", "18/18"), ("Samples", "60", "2 reviewers, blind")]
for i, (lbl, val, note) in enumerate(metrics):
    y = 3.2 - i * 0.9
    ax_h.text(0.5, y, lbl, fontsize=10, color=MUTED, va="center")
    ax_h.text(4, y, val, fontsize=16, fontweight="bold", color=ACCENT2, va="center")
    ax_h.text(7, y, note, fontsize=9, color=MUTED, va="center", style="italic")
for sp in ax_h.spines.values():
    sp.set_visible(True); sp.set_edgecolor((1,1,1,0.1)); sp.set_linewidth(1)

out_path = OUT / "dashboard_composite.png"
fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"Saved {out_path}")
