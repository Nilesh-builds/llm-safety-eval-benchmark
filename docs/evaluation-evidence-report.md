# Evaluation Evidence Report

## Run identity

- Run label: `real`
- Dataset version: `v2.0.0`
- Rubric version: `v1.0.0`
- Providers: Groq
- Models: Groq GPT-OSS-20B and Groq GPT-OSS-120B
- Attempts per case: 2 (80.5% of attempt-2 pairs recovered; 78 pairs rate-limited on Groq free tier)
- Source runs represented after deduplication: 9
- Collection date: 2026-09-18

## Coverage

- Total model responses: 800 (400 attempt-1 + 400 attempt-2)
- Cases: 200 per model
- Cases per dimension: 22 for most dimensions; 23 for prompt injection and refusal quality
- Judge calls: 1600 (two judge models per response)
- Failed responses: 78 attempt-2 pairs rate-limited (120B model hit free-tier quota ceiling)
- Invalid judge outputs: 0

## Results

| Model | Composite | Key strengths | Weakest dimensions |
|---|---:|---|---|
| Groq GPT-OSS-120B | 4.280 | factuality 4.82, relevance 4.84, bias 4.66 | hallucination 3.12, refusal quality 3.35 |
| Groq GPT-OSS-20B | 4.183 | factuality 4.64, relevance 4.77, instruction following 4.55 | hallucination 3.32, refusal quality 3.36 |

The complete per-dimension means and 95% bootstrap intervals are in
`results/merged/uncertainty.csv`. The comparison charts are
`results/merged/composite_scores.png` and
`results/merged/dimension_heatmap.png`.

## Human review

- Reviewers: two independent reviewers
- Blind sample: 60 responses, 10 each across six judge-scored dimensions
- Human-vs-human quadratic weighted kappa: 0.902
- Human-vs-human within-1 agreement: 100.0%
- Reviewer 1 vs. judge quadratic weighted kappa: 0.625; within-1: 88.3%
- Reviewer 2 vs. judge quadratic weighted kappa: 0.616; within-1: 80.0%
- Adjudicated disagreements: not yet recorded

The blind file is generated locally at
`results/human_review/human_labels_blind.csv`. Reviewers score the same rows
independently without seeing automated judge scores. The reviewer agreement
result indicates that the two reviewers applied the rubric consistently. The
judge comparison is substantial but weaker, especially for hallucination, so
the automated scores should be treated as a useful signal rather than a final
authority.

## Interpretation

In this sample, GPT-OSS-120B has the higher overall composite and is stronger
on most dimensions, while both models show the clearest weakness on
hallucination and refusal quality. These results support a comparative
benchmark finding for this dataset and rubric. They do not establish general
model safety, production reliability, or superiority outside this test set.

The evaluation used up to 2 attempts per case and free-tier API access.
78 of 400 attempt-2 pairs were rate-limited by Groq's free-tier quota ceiling,
all on the 120B model. The human sample covers six semantic dimensions and is
not a full review of all 800 model responses. Results may also reflect shared
judge-model blind spots.
