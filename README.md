# LLM Safety & Response Evaluation Benchmark

A controlled benchmark for evaluating AI model responses across 9 dimensions:
**instruction following, factuality, relevance, bias, toxicity, refusal quality,
prompt injection resistance, hallucination, and consistency.**

Built to run entirely on **free-tier APIs** (Groq, with OpenRouter free
models optional) — no paid usage required.

The default configuration uses Groq. A small Gemini pilot validated the
harness across providers, but Gemini was dropped from the main benchmark
after its free tier was reduced to 20 requests/day, which is too small for
comparable coverage.

The benchmark is designed as a reproducible evaluation harness rather than a
single leaderboard number. Each run validates its inputs, records the source
and configuration hashes, preserves invalid judge outputs for review, and
reports limitations alongside the scores.

## Why this exists

Most "prompt engineering" portfolio projects show a model doing a task well.
This one asks a harder question: **can we systematically measure whether a
model's responses are safe, faithful, and controllable** — using the same
fixed dataset and rubric across multiple models, so results are comparable?

## How it works

```
data/test_cases.json   20 hand-written test cases, ~2 per dimension, each
                        tagged with how it should be scored
data/test_cases_v2.json 200 deterministic development cases, 22 per dimension
data/benchmark_manifest.json  dataset version, coverage, and generation notes
src/rubric.py           the 1-5 scoring rubric, dimension weights, and the
                        LLM-judge prompt template
src/models.py           unified client for Groq / Gemini / OpenRouter free
                        tiers (falls back to a mock response if a key is
                        missing, so the pipeline is always runnable)
src/scorers.py          rule-based scorers (regex/keyword checks — free,
                        deterministic) + an ENSEMBLE LLM-as-judge scorer
                        (2 judge models) for dimensions needing semantic
                        judgment, with per-judge scores and inter-judge
                        spread reported
src/runner.py           runs every configured model against every test case,
                        scores each response, saves results/raw_responses.json
                        and results/scores.csv
src/report.py           aggregates scores.csv into a per-model/per-dimension
                        summary table, a composite-score bar chart, and a
                        heatmap
scripts/build_human_label_set.py   samples judge-scored responses into a CSV
                        for you to hand-score blind, so judge quality can be
                        checked against real human judgment
src/agreement.py        compares your human scores to the judge's: Pearson/
                        Spearman correlation, MAE, exact-match rate, and
                        quadratic weighted kappa, plus a scatter plot
src/calibration.py      runs the judge against hand-written reference
                        responses with known-correct scores (obviously
                        good/bad), independent of any live model, to sanity-
                        check the judge itself
data/judge_calibration_cases.json   the reference good/bad responses used above
notebooks/01_exploration.ipynb   walk-through notebook: explains each
                        dimension, runs a single live example, loads the
                        full results, and covers judge reliability
src/schemas.py          validates test cases and provider configuration before
                        any model calls are made
src/run_metadata.py     writes run IDs, Git revision, environment details, and
                        SHA-256 hashes for inputs and configuration
src/statistics.py       estimates bootstrap confidence intervals for score
                        summaries
src/annotations.py      validates human-label files before agreement analysis
tests/                  contract, scoring-failure, and metadata tests
```

## Scoring approach

Two scoring methods, chosen per test case:

1. **Rule-based** — fast and free. Used where correctness is checkable by
   pattern (e.g. "does the response contain '1969'", "did it refuse", "did it
   leak the injected instruction", "did it hedge on a fictitious entity").
2. **LLM-as-judge (ensemble)** — used where judgment is inherently semantic
   (bias, toxicity, relevance, refusal *tone*, hallucination nuance). Two
   judge models score every response independently (`configs/judges.json`);
   the final score is their mean, and the spread between them is recorded as
   a cheap inter-judge agreement signal. The judges are free-tier models
   too, so this adds zero cost beyond the calls already being made.

Every dimension is scored 1-5. A weighted **composite score** combines all
dimensions a model was actually tested on (weights live in `src/rubric.py` —
refusal quality and prompt-injection resistance are weighted highest, since
those are the safety-critical dimensions).

## Validating the judge itself

An LLM judge is only useful if it actually agrees with human judgment — so
this project includes two independent checks on judge quality, rather than
just trusting it:

1. **Calibration against known-correct answers** — `src/calibration.py` runs
   the judge on a small set of hand-written responses with obvious, expert-
   assigned scores (clearly good vs. clearly bad, per dimension). If the
   judge misses these clear-cut cases, its scores on harder real outputs
   shouldn't be trusted either.

   ```bash
   python -m src.calibration
   ```

2. **Agreement with real human labels** — a stratified sample of actual
   judge-scored model responses gets hand-scored by you (blind to the
   judge's score), then compared statistically:

   ```bash
    python -m scripts.build_human_label_set --raw results/merged/merged_raw_responses.json --out results/human_review/human_labels_blind.csv --n-per-dim 10 --blind
    python -m scripts.build_human_review_xlsx --csv results/human_review/human_labels_blind.csv --out results/human_review/human_labels_blind.xlsx
    # reviewers fill in `human_score` (1-5) independently, then prepare analysis CSVs
    python -m scripts.prepare_human_labels --blind results/human_review/human_labels_analysis_template.csv --workbook results/human_review/human_labels_reviewer1.xlsx --out results/human_review/human_labels_reviewer1.csv
    python -m src.agreement --labels results/human_review/human_labels_reviewer1.csv
   ```

This reports Pearson/Spearman correlation, mean absolute error, exact-match
rate, and quadratic weighted kappa (the standard chance-corrected metric
for ordinal rating agreement) — plus a judge-vs-human scatter plot.

Annotation files are checked for required columns, duplicate samples, valid
1-5 scores, and malformed judge values before any statistics are calculated.

## Setup (all free)

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in whichever free key(s) you have — Groq's free tier is the fastest to get:
# https://console.groq.com/keys
```

You don't need all three providers. Any provider without a key runs in mock
mode so the harness still executes end-to-end — useful for testing the
pipeline before you have keys.

## Run it

```bash
python -m src.runner --data data/test_cases_v2.json --dataset-version v2.0.0 --label mock
python -m src.report      # builds results/summary.csv + charts
jupyter notebook notebooks/01_exploration.ipynb   # walk-through + interpretation
```

## Review the results

### Streamlit dashboard

Dashboard source: [`app/streamlit_app.py`](app/streamlit_app.py)

Run it locally from the repository root:

```bash
streamlit run app/streamlit_app.py
```

To publish it with Streamlit Community Cloud, create a new app from this
repository, select branch `main`, and set the main file to
`app/streamlit_app.py`. The dashboard is read-only and uses the committed
aggregate results, so no API key or paid service is required.

After a benchmark run, start the read-only dashboard:

```bash
streamlit run app/streamlit_app.py
```

It shows model comparisons, per-dimension bootstrap intervals, invalid-output
signals, and the human-agreement workflow without making live API calls. When
versioned run directories exist, the sidebar lets you choose a run and shows
its label, dataset version, and rubric version.

The real-run procedure is documented in [`docs/real-evaluation-protocol.md`](docs/real-evaluation-protocol.md),
with reviewer guidance in [`docs/annotation-guidelines.md`](docs/annotation-guidelines.md).

The current Groq-only real evaluation evidence is documented in
[`docs/evaluation-evidence-report.md`](docs/evaluation-evidence-report.md).
Aggregate results and charts are stored under `results/merged/`; raw API
responses and human-review files remain local.

Edit `configs/models.json` to change which models/providers are benchmarked.
Free-tier model IDs change over time — check the current list on each
provider's docs (Groq's models page, OpenRouter's `:free` model list, Gemini's
model list) before running, and swap in whatever's current.

Every run also writes `results/run_manifest.json`. The manifest records the
run ID, Git revision when available, Python environment, and SHA-256 hashes for
the dataset and configuration files. Offline runs remain deterministic because
mock responses use a stable digest rather than Python's process-randomized
`hash()` function.

By default, new runs are written to a unique directory under
`results/runs/` rather than overwriting an earlier run. Use `--label mock`,
`--label development`, or `--label real` and keep the dataset and rubric
versions in the manifest.

Per-case outputs also record latency and response status (`ok`, `mock`, or
`error`). Reports exclude invalid scores rather than treating them as a
neutral result and write `uncertainty.csv` with bootstrap intervals for each
model and dimension.

## Extending it

- Add test cases to `data/test_cases.json` — just follow the existing shape.
- Add a dimension by adding it to `DIMENSIONS` in `src/rubric.py` and writing
  a matching branch in `src/scorers.py` if it needs a rule-based check.
- Add a model/provider by adding an entry to `configs/models.json` (and, for
  a brand-new provider, a `_call_<provider>` method in `src/models.py`).

## Known limitations (worth stating in interviews)

- The original v1 contains 20 cases. The deterministic v2 development set has
  200 cases, 22 per dimension plus two additional safety cases, but it still needs domain-specific review and
  repeated real-model runs before rankings can be treated as stable.
- Mock runs validate the harness, not model behavior. Real API runs must be
  labeled separately and should include multiple attempts per case because
  LLMs are non-deterministic even at temperature 0 in practice.
- The human-agreement check only covers the ~18 samples you hand-score — a
  small sample size for a statistic like kappa. It's evidence the judge is
  reasonable, not proof, and the confidence interval on kappa with n≈18 is
  wide. State this precisely rather than overclaiming "validated."
- The judge ensemble is only 2 models, both free-tier and both from the
  Llama/Gemma family lineage — they may share correlated blind spots that a
  more diverse judge panel (or a stronger frontier model as judge) wouldn't.
- Rule-based checks (keyword/regex matching) are precision-optimized, not
  recall-optimized — a model can dodge a keyword check with different phrasing.
- This benchmark is an evaluation prototype, not a production safety
  certification or a substitute for human governance and domain review.
