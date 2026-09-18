"""Read-only dashboard for benchmark results and evaluator reliability."""

from pathlib import Path
import json
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.statistics import bootstrap_mean_ci

st.set_page_config(page_title="LLM Evaluation Evidence", layout="wide")


@st.cache_data
def available_result_roots() -> dict[str, str]:
    roots = {"Committed results (legacy snapshot)": str(RESULTS)}
    merged = RESULTS / "merged"
    if (merged / "merged_scores.csv").exists():
        roots["Final merged evidence"] = str(merged)
    runs = RESULTS / "runs"
    if runs.exists():
        for path in sorted(runs.iterdir(), reverse=True):
            if path.is_dir() and (path / "scores.csv").exists():
                roots[f"Run: {path.name}"] = str(path)
    return roots


@st.cache_data
def load_scores(result_root: str) -> pd.DataFrame:
    root = Path(result_root)
    score_path = root / "scores.csv"
    if not score_path.exists():
        score_path = root / "merged_scores.csv"
    scores = pd.read_csv(score_path)
    if "valid_score" in scores.columns:
        scores = scores[scores["valid_score"] != False].copy()  # noqa: E712
    scores["final_score"] = pd.to_numeric(scores["final_score"], errors="coerce")
    return scores.dropna(subset=["final_score"])


@st.cache_data
def load_uncertainty(scores: pd.DataFrame, result_root: str) -> pd.DataFrame:
    path = Path(result_root) / "uncertainty.csv"
    if path.exists():
        return pd.read_csv(path)
    rows = []
    for (model, dimension), group in scores.groupby(["model", "dimension"]):
        rows.append(
            {
                "model": model,
                "dimension": dimension,
                **bootstrap_mean_ci(group["final_score"].tolist()),
            }
        )
    return pd.DataFrame(rows)


st.title("LLM Evaluation Evidence")
st.caption(
    "A read-only view of benchmark results. Scores are evidence with uncertainty, "
    "not a universal model ranking."
)

result_options = available_result_roots()
selected_result = st.sidebar.selectbox("Result set", list(result_options))
result_root = result_options[selected_result]
scores = load_scores(result_root)
uncertainty = load_uncertainty(scores, result_root)

manifest_path = Path(result_root) / "run_manifest.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    st.sidebar.caption(
        f"Label: {manifest.get('run_label', 'unknown')} | "
        f"Dataset: {manifest.get('dataset_version', 'unknown')} | "
        f"Rubric: {manifest.get('rubric_version', 'unknown')}"
    )
else:
    st.sidebar.caption("This is a legacy committed snapshot without run metadata.")

metric_one, metric_two, metric_three = st.columns(3)
metric_one.metric("Scored responses", f"{len(scores):,}")
metric_two.metric("Models", f"{scores['model'].nunique():,}")
metric_three.metric("Dimensions", f"{scores['dimension'].nunique():,}")

tab_models, tab_dimensions, tab_reliability = st.tabs(
    ["Model comparison", "Dimension detail", "Reliability"]
)

with tab_models:
    summary = scores.groupby("model", as_index=False).agg(
        mean_score=("final_score", "mean"),
        minimum_score=("final_score", "min"),
        maximum_score=("final_score", "max"),
    )
    summary = summary.sort_values("mean_score", ascending=False)
    st.subheader("Average score by model")
    st.bar_chart(summary.set_index("model")["mean_score"])
    st.dataframe(
        summary.style.format(
            {"mean_score": "{:.2f}", "minimum_score": "{:.2f}", "maximum_score": "{:.2f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )

with tab_dimensions:
    selected_model = st.selectbox("Model", sorted(scores["model"].unique()))
    model_scores = scores[scores["model"] == selected_model]
    detail = (
        uncertainty[uncertainty["model"] == selected_model]
        .sort_values("mean", ascending=False)
        .copy()
    )
    st.subheader("Score with bootstrap interval")
    st.bar_chart(detail.set_index("dimension")[["mean", "ci_lower", "ci_upper"]])
    st.dataframe(
        detail.style.format(
            {"mean": "{:.2f}", "ci_lower": "{:.2f}", "ci_upper": "{:.2f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"Rows used for this model: {len(model_scores):,}")

with tab_reliability:
    invalid = scores.get("invalid_judges", pd.Series(dtype=float))
    st.subheader("Run reliability signals")
    if len(invalid):
        st.metric("Rows with invalid judge calls", int((invalid > 0).sum()))
    else:
        st.info("This result file predates invalid-judge telemetry.")
    reviewer_agreement = RESULTS / "merged" / "reviewer_agreement.json"
    if not reviewer_agreement.exists():
        reviewer_agreement = RESULTS / "human_review" / "reviewer_agreement.json"
    if reviewer_agreement.exists():
        agreement = json.loads(reviewer_agreement.read_text(encoding="utf-8"))
        st.subheader("Human reviewer agreement")
        a, b, c = st.columns(3)
        a.metric("Quadratic weighted kappa", f"{agreement['quadratic_weighted_kappa']:.3f}")
        b.metric("Exact match", f"{agreement['exact_match']:.1%}")
        c.metric("Within 1 point", f"{agreement['within_1']:.1%}")
        st.caption(f"Two independent reviewers; n={agreement['n']}")
    else:
        st.write("Human agreement is kept separate from model performance.")
    st.code("streamlit run app/streamlit_app.py")
    st.warning(
        "The current benchmark is a methodology demonstration. Small test sets "
        "should not be used to make deployment decisions."
    )
