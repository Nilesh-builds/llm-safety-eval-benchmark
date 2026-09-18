"""Read-only dashboard for benchmark results and evaluator reliability."""

from pathlib import Path
import json
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.statistics import bootstrap_mean_ci

ACCENT = "#6C63FF"
ACCENT_2 = "#00D4AA"
BG_TOP = "#0B1020"
BG_BOTTOM = "#141B33"
CARD_BG = "rgba(255, 255, 255, 0.045)"
CARD_BORDER = "rgba(255, 255, 255, 0.10)"
TEXT_MUTED = "#9AA4C0"

st.set_page_config(
    page_title="LLM Evaluation Evidence",
    page_icon="ðŸ“Š",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(160deg, {BG_TOP} 0%, {BG_BOTTOM} 55%, #0E1526 100%);
    }}
    .stApp > header {{ background: transparent; }}
    h1, h2, h3, h4, p, span, label, li {{ color: #E8ECF8 !important; }}
    .stCaption, .stMarkdown small {{ color: {TEXT_MUTED} !important; }}

    div[data-testid="stSidebar"] {{
        background: rgba(10, 14, 28, 0.92);
        border-right: 1px solid {CARD_BORDER};
    }}
    div[data-testid="stSidebar"] * {{ color: #D7DDF0 !important; }}

    div[data-testid="stMetric"] {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 14px;
        padding: 18px 20px;
        backdrop-filter: blur(8px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    }}
    div[data-testid="stMetric"] label {{ color: {TEXT_MUTED} !important; font-size: 0.8rem; }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: #FFFFFF !important;
        font-weight: 700;
    }}

    div[data-testid="stTabs"] button {{
        background: transparent;
        color: {TEXT_MUTED} !important;
        font-weight: 600;
    }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{
        color: #FFFFFF !important;
        border-bottom: 2px solid {ACCENT};
    }}

    div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
        border: 1px solid {CARD_BORDER};
        border-radius: 12px;
        overflow: hidden;
    }}

    .hero {{
        padding: 28px 32px;
        border-radius: 18px;
        background: linear-gradient(120deg, rgba(108,99,255,0.22), rgba(0,212,170,0.14));
        border: 1px solid {CARD_BORDER};
        margin-bottom: 8px;
    }}
    .hero h1 {{
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0 0 6px 0;
        background: linear-gradient(90deg, #FFFFFF, #B9B4FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .hero p {{ color: {TEXT_MUTED} !important; margin: 0; }}
    .badge {{
        display: inline-block;
        margin: 10px 8px 0 0;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #E8ECF8;
        background: rgba(108, 99, 255, 0.25);
        border: 1px solid rgba(108, 99, 255, 0.5);
    }}
    .badge.green {{
        background: rgba(0, 212, 170, 0.16);
        border-color: rgba(0, 212, 170, 0.45);
    }}
    .card {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 14px;
        padding: 18px 20px;
        margin-top: 14px;
    }}
    .footer {{
        margin-top: 28px;
        padding-top: 14px;
        border-top: 1px solid {CARD_BORDER};
        color: {TEXT_MUTED} !important;
        font-size: 0.78rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

PLOT_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#D7DDF0"),
    margin=dict(l=20, r=20, t=50, b=20),
)


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


result_options = available_result_roots()
selected_result = st.sidebar.selectbox("Result set", list(result_options))
result_root = result_options[selected_result]
scores = load_scores(result_root)
uncertainty = load_uncertainty(scores, result_root)

manifest_path = Path(result_root) / "run_manifest.json"
manifest = {}
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    st.sidebar.caption(
        f"Label: {manifest.get('run_label', 'unknown')} | "
        f"Dataset: {manifest.get('dataset_version', 'unknown')} | "
        f"Rubric: {manifest.get('rubric_version', 'unknown')}"
    )
else:
    st.sidebar.caption("This is a legacy committed snapshot without run metadata.")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Read-only evidence dashboard. No live API calls are made and no keys are required."
)

st.markdown(
    """
    <div class="hero">
        <h1>LLM Evaluation Evidence</h1>
        <p>A controlled, zero-cost benchmark for measuring how safe, faithful, and
        controllable model responses are â€” with uncertainty, not hype.</p>
        <span class="badge">9 evaluation dimensions</span>
        <span class="badge">LLM-as-judge ensemble</span>
        <span class="badge green">Free-tier APIs only</span>
        <span class="badge green">Blind human review</span>
    </div>
    """,
    unsafe_allow_html=True,
)

kpi_one, kpi_two, kpi_three, kpi_four = st.columns(4)
kpi_one.metric("Scored responses", f"{len(scores):,}")
kpi_two.metric("Models evaluated", f"{scores['model'].nunique():,}")
kpi_three.metric("Dimensions", f"{scores['dimension'].nunique():,}")
agreement_path = RESULTS / "merged" / "reviewer_agreement.json"
if not agreement_path.exists():
    agreement_path = RESULTS / "human_review" / "reviewer_agreement.json"
agreement = {}
if agreement_path.exists():
    agreement = json.loads(agreement_path.read_text(encoding="utf-8"))
    kpi_four.metric("Human agreement (QWK)", f"{agreement['quadratic_weighted_kappa']:.3f}")
else:
    kpi_four.metric("Human agreement (QWK)", "â€”")

tab_overview, tab_dimensions, tab_reliability = st.tabs(
    ["Model comparison", "Dimension detail", "Reliability & review"]
)

with tab_overview:
    summary = (
        scores.groupby("model", as_index=False)
        .agg(
            mean_score=("final_score", "mean"),
            minimum_score=("final_score", "min"),
            maximum_score=("final_score", "max"),
            responses=("final_score", "size"),
        )
        .sort_values("mean_score", ascending=False)
    )
    fig = go.Figure(
        go.Bar(
            x=summary["model"],
            y=summary["mean_score"],
            marker=dict(
                color=[ACCENT, ACCENT_2, "#FFB86B", "#FF6B9A"][: len(summary)],
                line=dict(width=0),
            ),
            text=summary["mean_score"].round(2),
            textposition="outside",
        )
    )
    fig.update_layout(
        **PLOT_LAYOUT,
        title="Average score by model (1â€“5 scale)",
        yaxis=dict(range=[0, 5.4], gridcolor="rgba(255,255,255,0.08)"),
    )
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        summary.style.format(
            {
                "mean_score": "{:.2f}",
                "minimum_score": "{:.2f}",
                "maximum_score": "{:.2f}",
            }
        ),
        width="stretch",
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
    detail["error_minus"] = detail["mean"] - detail["ci_lower"]
    detail["error_plus"] = detail["ci_upper"] - detail["mean"]
    fig = go.Figure(
        go.Bar(
            x=detail["dimension"],
            y=detail["mean"],
            error_y=dict(
                type="data",
                symmetric=False,
                array=detail["error_plus"],
                arrayminus=detail["error_minus"],
                color=ACCENT_2,
                thickness=1.6,
                width=7,
            ),
            marker=dict(color=ACCENT),
            text=detail["mean"].round(2),
            textposition="outside",
        )
    )
    fig.update_layout(
        **PLOT_LAYOUT,
        title=f"{selected_model}: score by dimension with 95% bootstrap interval",
        yaxis=dict(range=[0, 5.6], gridcolor="rgba(255,255,255,0.08)"),
    )
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        detail[["dimension", "n", "mean", "ci_lower", "ci_upper"]].style.format(
            {"mean": "{:.2f}", "ci_lower": "{:.2f}", "ci_upper": "{:.2f}"}
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(f"Rows used for this model: {len(model_scores):,}")

with tab_reliability:
    invalid = scores.get("invalid_judges", pd.Series(dtype=float))
    col_one, col_two = st.columns(2)
    with col_one:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Run reliability signals")
        if len(invalid):
            st.metric("Rows with invalid judge calls", int((invalid > 0).sum()))
        else:
            st.info("This result file predates invalid-judge telemetry.")
        errors = scores.get("response_status")
        if errors is not None:
            st.metric("Failed responses", int((errors == "error").sum()))
        st.markdown("</div>", unsafe_allow_html=True)
    with col_two:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Human reviewer agreement")
        if agreement:
            a, b, c = st.columns(3)
            a.metric("QWK", f"{agreement['quadratic_weighted_kappa']:.3f}")
            b.metric("Exact match", f"{agreement['exact_match']:.1%}")
            c.metric("Within 1 point", f"{agreement['within_1']:.1%}")
            st.caption(
                f"Two independent reviewers blind to judge scores; n={agreement['n']}. "
                "Human agreement validates the judge, it is not a model score."
            )
        else:
            st.write("Human agreement is kept separate from model performance.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.warning(
        "The current benchmark is a methodology demonstration. Small test sets "
        "should not be used to make deployment decisions."
    )

st.markdown(
    """
    <div class="footer">
        LLM Safety &amp; Response Evaluation Benchmark â€” evidence with uncertainty,
        never a universal ranking. Source: github.com/Nilesh-builds/llm-safety-eval-benchmark
    </div>
    """,
    unsafe_allow_html=True,
)

