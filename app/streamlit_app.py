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

# ---- design tokens (match assets/banner.svg) --------------------------------
INK, INK_2 = "#080c18", "#0f1730"
LINE = "#22304f"
AMBER, TEAL = "#ffb547", "#3dd6c6"
TEXT, MUTED = "#e6ebfa", "#8fa2cf"
PALETTE = [AMBER, TEAL, "#8b7bff", "#ff6b8a", "#5db2ff", "#c6f36b"]
HEAT = [[0, "#141d36"], [0.5, "#1f6f7a"], [0.8, TEAL], [1, AMBER]]

st.set_page_config(
    page_title="LLM Safety Benchmark",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@500;700&display=swap');
    html, body, [class*="css"], .stApp {{ font-family: 'Inter', sans-serif; }}
    .stApp {{
        background:
          radial-gradient(900px 420px at 88% -8%, rgba(255,181,71,.13), transparent 60%),
          radial-gradient(700px 380px at 0% 0%, rgba(61,214,198,.09), transparent 55%),
          linear-gradient(160deg, {INK} 0%, {INK_2} 100%);
        color: {TEXT};
    }}
    .stApp > header {{ background: transparent; }}
    .block-container {{ padding-top: 1.6rem; max-width: 1280px; }}
    h1, h2, h3, h4 {{ color: {TEXT}; letter-spacing: -0.4px; }}
    [data-testid="stCaptionContainer"] {{ color: {MUTED}; }}

    section[data-testid="stSidebar"] {{
        background: rgba(8,12,24,.94); border-right: 1px solid {LINE};
    }}

    /* hero */
    .hero {{
        position: relative; overflow: hidden; padding: 26px 30px; border-radius: 18px;
        background: linear-gradient(120deg, rgba(15,23,48,.95), rgba(16,26,51,.85));
        border: 1px solid {LINE}; margin-bottom: 18px;
    }}
    .hero::after {{
        content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 3px;
        background: linear-gradient(90deg, {AMBER}, {TEAL});
    }}
    .live {{ font: 700 12px 'JetBrains Mono', monospace; color: {TEAL}; letter-spacing: .5px; }}
    .live i {{
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        background: {TEAL}; margin-right: 8px; animation: pulse 2s infinite;
    }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; box-shadow: 0 0 0 0 rgba(61,214,198,.5); }}
                        50% {{ opacity: .4; box-shadow: 0 0 0 8px rgba(61,214,198,0); }} }}
    .hero h1 {{
        font-size: 2.3rem; font-weight: 800; margin: 8px 0 6px;
        background: linear-gradient(90deg, #fff, #9fb4e6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}
    .hero p {{ color: {MUTED}; margin: 0 0 12px; font-size: 1.02rem; max-width: 760px; }}
    .chip {{
        display: inline-block; margin: 4px 8px 0 0; padding: 4px 12px; border-radius: 999px;
        font: 600 12px 'JetBrains Mono', monospace; color: #c9d6f5;
        background: #101a33; border: 1px solid {LINE};
    }}

    /* KPI metrics */
    div[data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
        border: 1px solid {LINE}; border-radius: 16px; padding: 14px 18px;
        box-shadow: 0 10px 30px rgba(0,0,0,.28);
    }}
    div[data-testid="stMetric"] label p {{ color: {MUTED}; font-size: .8rem; }}
    div[data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #fff;
    }}

    /* podium cards */
    .pod {{
        border: 1px solid {LINE}; border-radius: 16px; padding: 16px 18px;
        background: rgba(255,255,255,.035); height: 100%;
    }}
    .pod.first {{
        border-color: {AMBER};
        background: linear-gradient(160deg, rgba(255,181,71,.16), rgba(255,255,255,.03));
        box-shadow: 0 0 0 1px rgba(255,181,71,.25), 0 16px 40px rgba(255,181,71,.10);
    }}
    .pod .rk {{ font: 700 12px 'JetBrains Mono', monospace; color: {MUTED}; }}
    .pod .nm {{ font-weight: 800; font-size: 1.15rem; margin: 4px 0 2px; word-break: break-word; }}
    .pod .sc {{ font: 700 2rem 'JetBrains Mono', monospace; color: {AMBER}; }}
    .pod .sub {{ color: {MUTED}; font-size: .82rem; }}

    .insight {{
        border-left: 3px solid {TEAL}; background: rgba(61,214,198,.07);
        padding: 12px 16px; border-radius: 0 12px 12px 0; margin: 10px 0 4px; color: {TEXT};
    }}

    /* section nav buttons */
    div[data-testid="stButton"] button[kind="secondary"] {{
        color: {MUTED}; font-weight: 700; border: 1px solid {LINE};
        background: rgba(255,255,255,.02); border-radius: 999px;
    }}
    div[data-testid="stButton"] button[kind="secondary"]:hover {{
        color: #fff; border-color: {AMBER};
    }}
    div[data-testid="stButton"] button[kind="primary"] {{
        color: #0b0f1e; font-weight: 800; border: 1px solid {AMBER};
        background: {AMBER}; border-radius: 999px;
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid {LINE}; border-radius: 14px; overflow: hidden;
    }}
    .footer {{
        margin-top: 26px; padding-top: 12px; border-top: 1px solid {LINE};
        color: {MUTED}; font-size: .8rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def layout(**extra) -> dict:
    base = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TEXT),
        margin=dict(l=20, r=20, t=50, b=20),
        height=380,
        legend=dict(orientation="h", y=-0.15),
    )
    base.update(extra)
    return base


GRID = "rgba(255,255,255,0.07)"


# ---- data loading (unchanged contract) --------------------------------------
@st.cache_data
def available_result_roots() -> dict[str, str]:
    roots = {}
    merged = RESULTS / "merged"
    if (merged / "merged_scores.csv").exists():
        roots["Final merged evidence"] = str(merged)
    roots["Committed results (legacy snapshot)"] = str(RESULTS)
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
            {"model": model, "dimension": dimension, **bootstrap_mean_ci(group["final_score"].tolist())}
        )
    return pd.DataFrame(rows)


result_options = available_result_roots()
st.sidebar.markdown("### Controls")
selected_result = st.sidebar.selectbox("Result set", list(result_options))
result_root = result_options[selected_result]
scores = load_scores(result_root)
uncertainty = load_uncertainty(scores, result_root)

all_models = sorted(scores["model"].unique())
chosen = st.sidebar.multiselect("Models to compare", all_models, default=all_models)
if not chosen:
    st.warning("Select at least one model in the sidebar.")
    st.stop()
scores = scores[scores["model"].isin(chosen)]
uncertainty = uncertainty[uncertainty["model"].isin(chosen)]
color_of = {m: PALETTE[i % len(PALETTE)] for i, m in enumerate(all_models)}

manifest_path = Path(result_root) / "run_manifest.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    st.sidebar.caption(
        f"Label: {manifest.get('run_label', 'unknown')} | "
        f"Dataset: {manifest.get('dataset_version', 'unknown')} | "
        f"Rubric: {manifest.get('rubric_version', 'unknown')}"
    )
else:
    st.sidebar.caption("Legacy committed snapshot without run metadata.")
st.sidebar.markdown("---")
st.sidebar.caption("Read-only. No live API calls, no keys required.")

# ---- derived tables ---------------------------------------------------------
composite_path = RESULTS / "merged" / "summary.csv"
if composite_path.exists() and "COMPOSITE" in pd.read_csv(composite_path, nrows=1).columns:
    board = pd.read_csv(composite_path)[["model", "COMPOSITE"]].rename(columns={"COMPOSITE": "composite"})
    board = board[board["model"].isin(chosen)]
    composite_label = "Weighted composite"
else:
    board = scores.groupby("model", as_index=False).agg(composite=("final_score", "mean"))
    composite_label = "Mean score"
board["responses"] = board["model"].map(scores.groupby("model").size())
board = board.sort_values("composite", ascending=False).reset_index(drop=True)

matrix = scores.pivot_table(index="model", columns="dimension", values="final_score", aggfunc="mean")

agreement_path = RESULTS / "merged" / "reviewer_agreement.json"
if not agreement_path.exists():
    agreement_path = RESULTS / "human_review" / "reviewer_agreement.json"
agreement = json.loads(agreement_path.read_text(encoding="utf-8")) if agreement_path.exists() else {}

# ---- hero + KPIs ------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
      <span class="live"><i></i>EVIDENCE DASHBOARD</span>
      <h1>LLM Safety &amp; Response Benchmark</h1>
      <p>How safe, faithful and controllable are these models? Scored on the same
      rubric, reported with uncertainty instead of hype.</p>
      <span class="chip">9 dimensions</span><span class="chip">LLM-judge ensemble</span>
      <span class="chip">blind human review</span><span class="chip">$0 free-tier</span>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Scored responses", f"{len(scores):,}")
k2.metric("Models evaluated", f"{scores['model'].nunique():,}")
k3.metric("Dimensions", f"{scores['dimension'].nunique():,}")
k4.metric("Human agreement (QWK)", f"{agreement['quadratic_weighted_kappa']:.3f}" if agreement else "-")

PAGES = ["Leaderboard", "Dimension map", "Model deep-dive", "Reliability & review"]
if "page" not in st.session_state:
    st.session_state.page = PAGES[0]
nav = st.columns(4)
for i, name in enumerate(PAGES):
    with nav[i]:
        if st.button(
            name, key=f"nav_{i}", use_container_width=True,
            type="primary" if st.session_state.page == name else "secondary",
        ):
            st.session_state.page = name
            st.rerun()

# ---- section 1: leaderboard -------------------------------------------------
if st.session_state.page == "Leaderboard":
    medals = ["#1", "#2", "#3"]
    cols = st.columns(min(3, len(board)))
    for i, col in enumerate(cols):
        row = board.iloc[i]
        col.markdown(
            f"""<div class="pod {'first' if i == 0 else ''}">
                <div class="rk">{medals[i]}</div><div class="nm">{row['model']}</div>
                <div class="sc">{row['composite']:.2f}</div>
                <div class="sub">{composite_label} of 5 · {int(row['responses']):,} responses</div></div>""",
            unsafe_allow_html=True,
        )

    if matrix.shape[1] > 1:
        best_dim = matrix.loc[board.iloc[0]["model"]].idxmax()
        weak_dim = matrix.mean().idxmin()
        st.markdown(
            f"""<div class="insight"><b>{board.iloc[0]['model']}</b> leads on {composite_label.lower()}
            and is strongest at <b>{best_dim}</b>. Across models, the hardest dimension is
            <b>{weak_dim}</b> (mean {matrix.mean().min():.2f}).</div>""",
            unsafe_allow_html=True,
        )

    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure(
            go.Bar(
                y=board["model"][::-1],
                x=board["composite"][::-1],
                orientation="h",
                marker=dict(
                    color=[color_of[m] for m in board["model"][::-1]],
                    line=dict(width=0),
                ),
                text=board["composite"][::-1].round(2),
                textposition="outside",
                cliponaxis=False,
            )
        )
        fig.update_layout(**layout(title=f"{composite_label} (1-5)", showlegend=False),
                          xaxis=dict(range=[0, 5.4], gridcolor=GRID), yaxis=dict(automargin=True))
        st.plotly_chart(fig, width="stretch")
    with right:
        fig = go.Figure()
        for m in board["model"]:
            fig.add_trace(go.Box(
                y=scores.loc[scores["model"] == m, "final_score"], name=m,
                marker_color=color_of[m], line_color=color_of[m],
                fillcolor=rgba(color_of[m], 0.25), boxmean=True,
            ))
        fig.update_layout(**layout(title="Score spread", showlegend=False),
                          yaxis=dict(range=[0.8, 5.2], gridcolor=GRID))
        st.plotly_chart(fig, width="stretch")

    st.dataframe(
        board.rename(columns={"composite": composite_label}),
        column_config={
            composite_label: st.column_config.ProgressColumn(
                composite_label, min_value=0, max_value=5, format="%.2f"),
            "responses": st.column_config.NumberColumn("Responses", format="%d"),
        },
        width="stretch",
        hide_index=True,
    )

# ---- section 2: radar + heatmap ---------------------------------------------
if st.session_state.page == "Dimension map":
    left, right = st.columns(2)
    with left:
        dims = list(matrix.columns)
        fig = go.Figure()
        for m in matrix.index:
            vals = matrix.loc[m].tolist()
            fig.add_trace(go.Scatterpolar(
                r=vals + vals[:1], theta=dims + dims[:1], name=m,
                line=dict(color=color_of[m], width=2.5),
                fill="toself", fillcolor=rgba(color_of[m], 0.13),
            ))
        fig.update_layout(**layout(
            title="Capability radar", height=460,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(range=[0, 5], gridcolor=GRID, linecolor=LINE, tickfont=dict(color=MUTED)),
                angularaxis=dict(gridcolor=GRID, linecolor=LINE),
            ),
        ))
        st.plotly_chart(fig, width="stretch")
    with right:
        fig = go.Figure(go.Heatmap(
            z=matrix.values, x=dims, y=list(matrix.index), colorscale=HEAT, zmin=1, zmax=5,
            xgap=3, ygap=3, texttemplate="%{z:.2f}", textfont=dict(color="#fff", size=12),
            colorbar=dict(title="Score", thickness=10),
        ))
        fig.update_layout(**layout(title="Model × dimension heatmap", height=460),
                          xaxis=dict(tickangle=-35), yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, width="stretch")

# ---- section 3: per-model CI ------------------------------------------------
if st.session_state.page == "Model deep-dive":
    selected_model = st.selectbox("Model", sorted(scores["model"].unique()))
    model_scores = scores[scores["model"] == selected_model]
    detail = uncertainty[uncertainty["model"] == selected_model].sort_values("mean", ascending=False).copy()
    detail["error_minus"] = detail["mean"] - detail["ci_lower"]
    detail["error_plus"] = detail["ci_upper"] - detail["mean"]
    accent = color_of[selected_model]
    fig = go.Figure(go.Bar(
        x=detail["dimension"], y=detail["mean"],
        error_y=dict(type="data", symmetric=False, array=detail["error_plus"],
                     arrayminus=detail["error_minus"], color="#fff", thickness=1.5, width=6),
        marker=dict(color=detail["mean"], colorscale=HEAT, cmin=1, cmax=5, line=dict(width=0)),
        text=detail["mean"].round(2), textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(**layout(title=f"{selected_model}: score by dimension, 95% bootstrap interval",
                               showlegend=False, height=420),
                      yaxis=dict(range=[0, 5.7], gridcolor=GRID))
    st.plotly_chart(fig, width="stretch")

    dist = model_scores["final_score"].round().value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
    fig = go.Figure(go.Bar(x=[f"{s}" for s in dist.index], y=dist.values,
                           marker=dict(color=accent), text=dist.values, textposition="outside"))
    fig.update_layout(**layout(title="Score distribution (rounded)", showlegend=False, height=280),
                      xaxis=dict(title="Score"), yaxis=dict(gridcolor=GRID))
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Rows used for this model: {len(model_scores):,}. Wide intervals mean few samples, read them as uncertainty.")

# ---- section 4: reliability -------------------------------------------------
if st.session_state.page == "Reliability & review":
    left, right = st.columns(2)
    with left:
        st.subheader("Human reviewer agreement")
        if agreement:
            qwk = agreement["quadratic_weighted_kappa"]
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=qwk,
                number=dict(valueformat=".2f",
                            font=dict(family="JetBrains Mono", color="#fff", size=44)),
                gauge=dict(
                    axis=dict(range=[0, 1], tickcolor=MUTED),
                    bar=dict(color=AMBER, thickness=0.28),
                    bgcolor="rgba(0,0,0,0)", borderwidth=0,
                    steps=[dict(range=[0, .4], color="#2a1a2a"), dict(range=[.4, .6], color="#1d2a3a"),
                           dict(range=[.6, .8], color="#16404a"), dict(range=[.8, 1], color="#1b5a5a")],
                ),
                title=dict(text="Quadratic weighted kappa"),
                domain=dict(x=[0, 1], y=[0, 1]),
            ))
            fig.update_layout(**layout(height=260, margin=dict(l=30, r=30, t=60, b=10)))
            st.plotly_chart(fig, width="stretch")
            a, b = st.columns(2)
            a.metric("Exact match", f"{agreement['exact_match']:.1%}")
            b.metric("Within 1 point", f"{agreement['within_1']:.1%}")
            st.caption(f"n={agreement['n']} blind double-reviewed samples. Small n means a wide interval on kappa.")
        else:
            st.info("Human agreement is kept separate from model performance and is not available for this result set.")
    with right:
        st.subheader("Run reliability")
        status = scores.get("response_status")
        if status is not None:
            counts = status.value_counts()
            fig = go.Figure(go.Pie(
                labels=counts.index, values=counts.values, hole=0.65,
                marker=dict(colors=[TEAL, "#ff6b8a", AMBER, "#8b7bff"], line=dict(color=INK, width=3)),
                textinfo="label+percent",
            ))
            fig.update_layout(**layout(title="Response status", height=260, showlegend=False))
            st.plotly_chart(fig, width="stretch")
            st.metric("Failed responses", int((status == "error").sum()))
        invalid = scores.get("invalid_judges", pd.Series(dtype=float))
        if len(invalid):
            st.metric("Invalid judge calls", int((invalid > 0).sum()))

st.markdown(
    """
    <div class="footer">
      LLM Safety &amp; Response Evaluation Benchmark · evidence with uncertainty, never a universal ranking ·
      <a href="https://github.com/Nilesh-builds/llm-safety-eval-benchmark" style="color:#3dd6c6">source on GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
