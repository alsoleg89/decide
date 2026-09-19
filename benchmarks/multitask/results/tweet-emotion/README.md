# Tweet emotions: 500 evaluated records

Jev accuracy: **83.6%**; macro-F1: **79.8%**. Naive Bayes accuracy: **65.0%**; training-majority accuracy: **36.8%**.

At threshold 0.8: **32/384 accepted errors**, 116 records for review, 1 failed provider responses. Known-usage inference cost: **≥$0.00934**. Batch processing: **41.5 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 499 | 1 | 81 | 16.2% (13.3%–19.7%) | 98.0% |
| 0.5 | 458 | 42 | 59 | 12.9% (10.1%–16.3%) | 89.8% |
| 0.8 | 384 | 116 | 32 | 8.3% (6.0%–11.5%) | 74.8% |
| 0.9 | 345 | 155 | 24 | 7.0% (4.7%–10.1%) | 67.6% |
| 0.95 | 309 | 191 | 15 | 4.9% (3.0%–7.9%) | 60.4% |
| 0.99 | 249 | 251 | 6 | 2.4% (1.1%–5.2%) | 48.4% |
| 1 | 199 | 301 | 2 | 1.0% (0.3%–3.6%) | 38.5% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **32.1%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **74.8%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 41 | 22 | 53.7% |
| [0.5, 0.8) | 74 | 27 | 36.5% |
| [0.8, 0.9) | 39 | 8 | 20.5% |
| [0.9, 0.95) | 36 | 9 | 25.0% |
| [0.95, 0.99) | 60 | 9 | 15.0% |
| [0.99, 1) | 50 | 4 | 8.0% |
| Exactly 1 | 199 | 2 | 1.0% |

## Reproduction and provenance

The baseline used **3,257** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
