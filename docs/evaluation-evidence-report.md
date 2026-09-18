# Evaluation Evidence Report

## Run identity

- Run label: `real`
- Dataset version: `v2.0.0`
- Rubric version: `v1.0.0`
- Providers: Groq
- Models: Groq GPT-OSS-20B and Groq GPT-OSS-120B
- Attempts per case: 1
- Source runs represented after deduplication: 9
- Collection date: 2026-09-18

## Coverage

- Total model responses: 400
- Cases: 200 per model
- Cases per dimension: 22 for most dimensions; 23 for prompt injection and refusal quality
- Judge calls: 800 (two judge models per response)
- Failed responses: 0
- Invalid judge outputs: 0

## Results

| Model | Composite | Key strengths | Weakest dimensions |
|---|---:|---|---|
| Groq GPT-OSS-120B | 4.334 | toxicity 5.00, relevance 4.86, factuality 4.82 | hallucination 3.00, refusal quality 3.57 |
| Groq GPT-OSS-20B | 4.182 | toxicity 5.00, relevance 4.82, factuality 4.64 | hallucination 3.00, refusal quality 3.52 |

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

The evaluation used one attempt per case and free-tier API access. The human
sample covers six semantic dimensions and is not a full review of all 400
model responses. Results may also reflect shared judge-model blind spots.
