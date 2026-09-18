# Real Evaluation Protocol

This protocol separates harness verification from evidence about real model
behavior.

The project is designed to run without purchasing credits. Free-provider rate
limits may require multiple smaller runs across different days. That is
acceptable; do not bypass limits or add paid credits just to finish a run.

## Before the run

1. Copy `.env.example` to `.env`.
2. Add provider keys locally. Never commit `.env` or paste keys into issues.
3. Confirm the dataset version and rubric version.
4. Start with a small pilot before using the full 200-case target.

Recommended pilot:

- 50 cases
- 2 or 3 models
- 2 attempts per case
- 2 judge models

The default configuration uses Groq and Gemini. OpenRouter is optional and is
not required for the benchmark.

Review rate limits, failures, latency, and estimated cost before expanding.

## Full run

From PowerShell:

```powershell
.\scripts\run_real_benchmark.ps1 -Attempts 2
```

If a provider reaches its free quota, run the same dataset in a later batch or
use a provider-specific configuration. Keep each result directory and compare
them only after recording the provider, date, and quota state.

Example 50-case Groq batch:

```powershell
.\scripts\run_real_benchmark.ps1 `
  -Config configs/models_groq.json `
  -CaseOffset 0 `
  -CaseLimit 50 `
  -Attempts 1
```

The next batches use offsets `50`, `100`, and `150`. Gemini can be run in the
same way with `-Config configs/models_gemini.json`. Preserve each run directory
and compare them using their manifests.

The run creates a new directory under `results/runs/` and records:

- `run_manifest.json`
- `raw_responses.json`
- `scores.csv`

The manifest contains the run label, dataset version, rubric version, model
and judge counts, Git revision, environment, and input hashes.

## Human review

Sample responses from the run for blind review:

```powershell
python -m scripts.build_human_label_set `
  --raw results/runs/<run-id>/raw_responses.json `
  --out results/runs/<run-id>/human_labels.csv `
  --n-per-dim 10 `
  --seed 42
```

Use `docs/annotation-guidelines.md`. Reviewers should not see judge scores
while assigning labels. Run agreement after all labels are complete:

```powershell
python -m src.agreement `
  --labels results/runs/<run-id>/human_labels.csv `
  --out results/runs/<run-id>/agreement
```

## Reporting rules

- Mock results validate code paths, not model quality.
- Development results are for rubric and dataset iteration.
- Real results must include provider, model, timestamp, attempt count, and versions.
- Rankings should include uncertainty intervals and failure rates.
- Human agreement should be reported with sample size and reviewer count.
- Small or ambiguous samples must be described as evidence, not proof.
