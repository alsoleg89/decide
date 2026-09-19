# Can a selected confidence threshold generalize?

A retrospective split-validation experiment using the same 5,570 archived decisions: **10 tasks × 3 error budgets × 2 selection rules**, with no new paid calls. This tests threshold selection, not a new model or new unseen corpus.

## Findings

| Error budget | Empirical: tasks accepting / exceeding budget | Bounded: tasks accepting / exceeding budget |
| --- | ---: | ---: |
| 1.0% | 4 / 1 | 0 / 0 |
| 5.0% | 9 / 4 | 3 / 0 |
| 10.0% | 9 / 2 | 6 / 0 |

These are counts of tasks out of ten, not independent repeated trials. Review-all outcomes do not count as successful quality validation.

- At a **5%** budget, empirical selection exceeded the budget on news, banking, emotion and hate speech. Bounded selection retained only Apache, IMDb and SMS; their holdout error rates were below 5%. Apache remains a negative control: a regex already achieves the same labels.
- On **IMDb at 5%**, bounded selection chose 0.95 using calibration data: holdout had **2 errors among 231 accepted**, 28/259 records for review and **88.4% of input bytes** withheld. The holdout Wilson interval is 0.2%–3.1%.
- At a **1%** budget, no task qualified under the bounded rule. Even with zero errors, this seven-candidate procedure needs at least **492 accepted calibration examples**. A few hundred examples cannot establish a very low error rate with this confidence requirement.

## Protocol

Exact duplicate content is reduced to the lexicographically first ID before splitting. A SHA-256 split with seed `decide-threshold-validation-v1` assigns approximately half of the distinct texts to calibration and half to holdout. IDs and exclusions are archived in [report.json](report.json). Only calibration labels enter threshold selection; holdout labels score the chosen threshold afterward. The full original dataset results were already known, so this is not a prospective blind study.

For each 1%, 5% or 10% accepted-error budget, select from `[0, .5, .8, .9, .95, .99, 1]` to keep the most calibration input bytes out of review. Ties prefer the lower threshold. **Empirical** selection checks the observed error rate. **Bounded** selection checks a one-sided exact binomial upper bound with Bonferroni α=0.05/7 for the seven candidates. If no candidate qualifies, all holdout inputs need review; a zero-accept policy has undefined error rate.

`review all` is an offline policy fallback, not the server argument `confidence_threshold=1`: the server still accepts confidence exactly 1. This experiment does not change runtime defaults.

The bounds assume independent, identically distributed error observations and a stable deployment distribution. Deduplication helps avoid exact-copy leakage but does not establish these assumptions. Correction covers the seven thresholds within one task, not a joint claim over all tasks. Holdout 95% Wilson intervals are descriptive and unadjusted. An observed budget pass is not a guarantee.

Distinct texts: **5,536**; exact duplicate rows excluded: **34**; duplicate groups with conflicting labels: **0**.

## Accepted-error budget: 1.0%

| Task | Rule | Cal / holdout | Threshold | Accepted errors / accepted | Holdout error (95% interval) | Review | Input bytes withheld* |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| ag-news | empirical | 487 / 513 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| ag-news | bounded | 487 / 513 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| apache-logs | empirical | 132 / 143 | 0 | 0 / 143 | 0.0% (0.0%–2.6%) | 0.0% | 100.0% |
| apache-logs | bounded | 132 / 143 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| banking77 | empirical | 383 / 387 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| banking77 | bounded | 383 / 387 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| imdb | empirical | 241 / 259 | 0.99 | 1 / 215 | 0.5% (0.1%–2.6%) | 17.0% | 81.9% |
| imdb | bounded | 241 / 259 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| sms-spam | empirical | 242 / 253 | 0.5 | 3 / 242 | 1.2% (0.4%–3.6%) | 4.3% | 95.4% |
| sms-spam | bounded | 242 / 253 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-emotion | empirical | 261 / 239 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-emotion | bounded | 261 / 239 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-hate | empirical | 256 / 244 | 1 | 0 / 21 | 0.0% (0.0%–15.5%) | 91.4% | 8.3% |
| tweet-hate | bounded | 256 / 244 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-irony | empirical | 257 / 243 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-irony | bounded | 257 / 243 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-offensive | empirical | 236 / 260 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-offensive | bounded | 236 / 260 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-sentiment | empirical | 239 / 261 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-sentiment | bounded | 239 / 261 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |

## Accepted-error budget: 5.0%

| Task | Rule | Cal / holdout | Threshold | Accepted errors / accepted | Holdout error (95% interval) | Review | Input bytes withheld* |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| ag-news | empirical | 487 / 513 | 1 | 21 / 357 | 5.9% (3.9%–8.8%) | 30.4% | 69.6% |
| ag-news | bounded | 487 / 513 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| apache-logs | empirical | 132 / 143 | 0 | 0 / 143 | 0.0% (0.0%–2.6%) | 0.0% | 100.0% |
| apache-logs | bounded | 132 / 143 | 0 | 0 / 143 | 0.0% (0.0%–2.6%) | 0.0% | 100.0% |
| banking77 | empirical | 383 / 387 | 0.99 | 11 / 195 | 5.6% (3.2%–9.8%) | 49.6% | 49.3% |
| banking77 | bounded | 383 / 387 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| imdb | empirical | 241 / 259 | 0 | 10 / 259 | 3.9% (2.1%–7.0%) | 0.0% | 100.0% |
| imdb | bounded | 241 / 259 | 0.95 | 2 / 231 | 0.9% (0.2%–3.1%) | 10.8% | 88.4% |
| sms-spam | empirical | 242 / 253 | 0 | 7 / 253 | 2.8% (1.3%–5.6%) | 0.0% | 100.0% |
| sms-spam | bounded | 242 / 253 | 0 | 7 / 253 | 2.8% (1.3%–5.6%) | 0.0% | 100.0% |
| tweet-emotion | empirical | 261 / 239 | 0.95 | 8 / 149 | 5.4% (2.7%–10.2%) | 37.7% | 62.3% |
| tweet-emotion | bounded | 261 / 239 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-hate | empirical | 256 / 244 | 0.99 | 4 / 43 | 9.3% (3.7%–21.6%) | 82.4% | 18.2% |
| tweet-hate | bounded | 256 / 244 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-irony | empirical | 257 / 243 | 1 | 0 / 32 | 0.0% (0.0%–10.7%) | 86.8% | 12.8% |
| tweet-irony | bounded | 257 / 243 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-offensive | empirical | 236 / 260 | 1 | 1 / 50 | 2.0% (0.4%–10.5%) | 80.8% | 17.3% |
| tweet-offensive | bounded | 236 / 260 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-sentiment | empirical | 239 / 261 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-sentiment | bounded | 239 / 261 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |

## Accepted-error budget: 10.0%

| Task | Rule | Cal / holdout | Threshold | Accepted errors / accepted | Holdout error (95% interval) | Review | Input bytes withheld* |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| ag-news | empirical | 487 / 513 | 0.8 | 34 / 463 | 7.3% (5.3%–10.1%) | 9.7% | 89.9% |
| ag-news | bounded | 487 / 513 | 0.99 | 21 / 386 | 5.4% (3.6%–8.2%) | 24.8% | 74.9% |
| apache-logs | empirical | 132 / 143 | 0 | 0 / 143 | 0.0% (0.0%–2.6%) | 0.0% | 100.0% |
| apache-logs | bounded | 132 / 143 | 0 | 0 / 143 | 0.0% (0.0%–2.6%) | 0.0% | 100.0% |
| banking77 | empirical | 383 / 387 | 0.9 | 29 / 283 | 10.2% (7.2%–14.3%) | 26.9% | 73.2% |
| banking77 | bounded | 383 / 387 | 0.99 | 11 / 195 | 5.6% (3.2%–9.8%) | 49.6% | 49.3% |
| imdb | empirical | 241 / 259 | 0 | 10 / 259 | 3.9% (2.1%–7.0%) | 0.0% | 100.0% |
| imdb | bounded | 241 / 259 | 0 | 10 / 259 | 3.9% (2.1%–7.0%) | 0.0% | 100.0% |
| sms-spam | empirical | 242 / 253 | 0 | 7 / 253 | 2.8% (1.3%–5.6%) | 0.0% | 100.0% |
| sms-spam | bounded | 242 / 253 | 0 | 7 / 253 | 2.8% (1.3%–5.6%) | 0.0% | 100.0% |
| tweet-emotion | empirical | 261 / 239 | 0.8 | 14 / 186 | 7.5% (4.5%–12.2%) | 22.2% | 77.8% |
| tweet-emotion | bounded | 261 / 239 | 0.99 | 3 / 123 | 2.4% (0.8%–6.9%) | 48.5% | 51.8% |
| tweet-hate | empirical | 256 / 244 | 0.95 | 8 / 71 | 11.3% (5.8%–20.7%) | 70.9% | 31.5% |
| tweet-hate | bounded | 256 / 244 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-irony | empirical | 257 / 243 | 0.95 | 6 / 85 | 7.1% (3.3%–14.6%) | 65.0% | 34.2% |
| tweet-irony | bounded | 257 / 243 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-offensive | empirical | 236 / 260 | 0.99 | 2 / 86 | 2.3% (0.6%–8.1%) | 66.9% | 31.5% |
| tweet-offensive | bounded | 236 / 260 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-sentiment | empirical | 239 / 261 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |
| tweet-sentiment | bounded | 239 / 261 | review all | 0 / 0 | — (—) | 100.0% | 0.0% |

*Input-only canonical JSONL bytes withheld from review. This excludes call/summary overhead, MCP framing, tokenizer differences and agent reasoning. It is neither the parent report’s full-review JSON metric nor billed-token savings.

## Reproduce

Prepare the sources using the [parent instructions](../README.md), then run:

```sh
uv run --locked python benchmarks/multitask/validate_thresholds.py --self-test
uv run --locked python benchmarks/multitask/validate_thresholds.py --root /tmp/decide-multitask --check
```

Omit `--check` to regenerate these artifacts. The check recomputes all splits, selections, errors, intervals and input byte counts and compares both artifacts exactly.

Methods: [R exact binomial intervals](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/binom.test.html) and [NIST Bonferroni inequality](https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm).
