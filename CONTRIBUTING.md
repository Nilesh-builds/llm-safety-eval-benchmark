# Contributing

Thanks for helping make this benchmark better. The most valuable
contributions are **new test cases** and **new dimensions**.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
python -m src.runner --data data/test_cases_v2.json --dataset-version v2.0.0 --label mock --case-limit 4 --out results/smoke
```

> [!NOTE]
> `--case-limit` is for quick iteration only. `src/report.py` needs
> every dimension scored, so run the full dataset (drop `--case-limit`)
> before building charts.

No API keys are needed for setup: providers without a key fall back to
mock responses, so the pipeline runs end to end offline.

## Adding a test case

1. Append an entry to `data/test_cases_v2.json` matching the existing
   shape (`id`, `dimension`, `prompt`, `scoring_method`, plus `check`
   for rule-based cases).
2. Tag it with one of the 9 dimensions in `src/rubric.py`.
3. If rule-based, make the check **precise** — it must not
   false-positive on a good response.
4. Run the smoke command above and confirm the case scores sensibly.

To propose a case without writing code, open a
[Test case proposal](.github/ISSUE_TEMPLATE/new_test_case.md) issue.

## Adding a dimension

1. Add it to `DIMENSIONS` in `src/rubric.py` with a weight
   (weights must sum to 1.0 — there is an assert for this).
2. Add a branch in `src/scorers.py` if it needs a rule-based check.
3. Add at least two test cases and one calibration case in
   `data/judge_calibration_cases.json` with known-correct scores.

## Pull requests

- Keep PRs focused on one change.
- Describe what changed and why, and paste a before/after of any
  score changes (re-run `python scripts/build_metrics.py` if headline
  numbers move).
- Never commit API keys or `.env` contents. `.env` is gitignored —
  use `.env.example` for new variables.
- CI runs the full test suite (`tests.yml`) plus an offline mock
  pipeline (`smoke.yml`). Both must pass.
