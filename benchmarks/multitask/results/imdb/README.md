# Movie review sentiment: 500 evaluated records

Jev accuracy: **96.2%**; macro-F1: **96.2%**. Naive Bayes accuracy: **82.2%**; training-majority accuracy: **54.0%**.

At threshold 0.8: **10/479 accepted errors**, 21 records for review, 0 failed provider responses. Known-usage inference cost: **$0.01418**. Batch processing: **39.4 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 500 | 0 | 19 | 3.8% (2.4%–5.9%) | 99.8% |
| 0.5 | 490 | 10 | 15 | 3.1% (1.9%–5.0%) | 97.3% |
| 0.8 | 479 | 21 | 10 | 2.1% (1.1%–3.8%) | 95.0% |
| 0.9 | 469 | 31 | 6 | 1.3% (0.6%–2.8%) | 93.3% |
| 0.95 | 455 | 45 | 5 | 1.1% (0.5%–2.5%) | 90.7% |
| 0.99 | 430 | 70 | 3 | 0.7% (0.2%–2.0%) | 85.0% |
| 1 | 407 | 93 | 3 | 0.7% (0.3%–2.1%) | 80.7% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **94.3%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **95.0%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 10 | 4 | 40.0% |
| [0.5, 0.8) | 11 | 5 | 45.5% |
| [0.8, 0.9) | 10 | 4 | 40.0% |
| [0.9, 0.95) | 14 | 1 | 7.1% |
| [0.95, 0.99) | 25 | 2 | 8.0% |
| [0.99, 1) | 23 | 0 | 0.0% |
| Exactly 1 | 407 | 3 | 0.7% |

## Reproduction and provenance

The baseline used **24,998** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
