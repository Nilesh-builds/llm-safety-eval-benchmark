# Can We Trust the Judge? Auditing an LLM-as-Judge With Blind Human Review

Most teams that adopt LLM-as-judge ship the scores and stop there. The judge says 4.2, the dashboard says 4.2, everyone moves on. But an evaluator is itself a measurement instrument — and instruments that are never calibrated quietly make things up.

I built a [9-dimension LLM safety benchmark](https://github.com/Nilesh-builds/llm-safety-eval-benchmark) partly to answer a harder question than "which model scores higher": **can we trust the judge at all?**

Here's how the audit worked, what the numbers said, and what I'd change.

## The setup

- **200 fixed test cases** across 9 dimensions (instruction following, factuality, relevance, bias, toxicity, refusal quality, prompt-injection resistance, hallucination, consistency) — 22 cases per dimension.
- Every model response scored 1–5 by **rule-based checks plus a dual LLM-as-judge ensemble** (two judge models per response).
- All of it on free-tier APIs (Groq default): **800 model responses, 1,600 judge calls, 0 invalid judge outputs** after schema validation.
- Bootstrap confidence intervals on every composite score, plus judge-calibration tests on known-correct answers.

Two open-weight models went through the same gauntlet: Groq GPT-OSS-120B (composite **4.280**) and GPT-OSS-20B (**4.183**). Both looked solid on factuality and relevance, and both fell apart on the same two dimensions — hallucination (~3.1–3.3/5) and refusal quality (~3.35/5).

Fine. But those scores all came from the judge. So: is the judge measuring anything real?

## The blind audit

Scores can't validate themselves. So I ran a human study the way you're supposed to:

1. **60 responses sampled blind** — 10 per dimension across six judge-scored dimensions.
2. **Two independent reviewers** scored each response against the same rubric, *without seeing the judge's scores*.
3. Judge-vs-human and human-vs-human agreement computed with **quadratic weighted kappa (QWK)** — chance-corrected, ordinal-aware — plus within-1 agreement (how often the two raters land within one point on a 1–5 scale).

## What the numbers said

| Comparison | QWK | Within-1 |
|---|---:|---:|
| Human vs human | **0.902** | 100% |
| Reviewer 1 vs judge | 0.625 | 88.3% |
| Reviewer 2 vs judge | 0.616 | 80.0% |

Three findings, in order of how much they mattered:

**1. The rubric is real.** Human-vs-human QWK of 0.902 ("almost perfect" by convention) with every disagreement within one point means two people, scoring blind, independently apply the same standard. If humans couldn't agree, the whole benchmark would be noise — full stop.

**2. The judge is useful, not authoritative.** QWK around 0.62 lands in "substantial agreement" — clearly above chance, clearly below the humans' agreement with each other. The judge tracks human judgment well enough to *rank and compare*, but not well enough to *replace* review. Within-1 rates of 80–88% sound high until you remember humans hit 100% with each other on the same sample.

**3. The judge's errors aren't uniform.** The weakest judge-human agreement showed up on hallucination — the dimension where "is this claim actually supported?" requires grounding checks that a judge skimming fluent text is bad at. Fluency fools the judge the same way it fools people.

## What this changes in practice

- **Report agreement, not just scores.** A leaderboard number without a judge-validation number is an uncalibrated instrument reading.
- **Blind the human review.** Reviewers who see judge scores anchor on them; the blind step is what makes 0.902 mean something.
- **Weight the judge where it agrees, escalate where it doesn't.** Hallucination-type dimensions now route to human spot-checks in my pipeline; high-agreement dimensions can stay automated.
- **Free tier is fine, quotas are real.** 78 of 400 second-attempt pairs were rate-limited on Groq's free tier (all on the 120B model). The evidence report records it instead of hiding it — coverage gaps are part of the result.

## Limitations, stated plainly

60 samples is a small human study — it proves the rubric is scorable, not that the judge is perfect. Six of nine dimensions were human-reviewed. Two reviewers share blind spots. And judge-human agreement of 0.62 is on *this* rubric, *these* models — not a law of LLM-as-judge.

## The takeaway

LLM-as-judge is leverage: 1,600 evaluations that no team could do by hand. But leverage on an uncalibrated instrument just scales the error. One blind double-review of 60 samples cost an afternoon and told me exactly where the automated scores can be trusted — that trade should be the default, not the exception.

Full evidence report, rubric, and code: [github.com/Nilesh-builds/llm-safety-eval-benchmark](https://github.com/Nilesh-builds/llm-safety-eval-benchmark). Live read-only dashboard: [the Streamlit app](https://llm-safety-eval-benchmark-vrjugdrizxtaqt38s6mgep.streamlit.app/).

---

*Numbers in this post come from the project's evaluation evidence report (run `real`, dataset v2.0.0, rubric v1.0.0, collected 2026-09-18).*
