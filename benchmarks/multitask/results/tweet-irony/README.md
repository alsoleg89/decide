# Tweet irony: 500 evaluated records

Jev accuracy: **75.2%**; macro-F1: **75.2%**. Naive Bayes accuracy: **65.6%**; training-majority accuracy: **40.4%**.

At threshold 0.8: **39/281 accepted errors**, 219 records for review, 0 failed provider responses. Known-usage inference cost: **$0.00876**. Batch processing: **39.9 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 500 | 0 | 124 | 24.8% (21.2%–28.8%) | 98.3% |
| 0.5 | 395 | 105 | 81 | 20.5% (16.8%–24.8%) | 78.3% |
| 0.8 | 281 | 219 | 39 | 13.9% (10.3%–18.4%) | 55.6% |
| 0.9 | 224 | 276 | 26 | 11.6% (8.0%–16.5%) | 43.9% |
| 0.95 | 178 | 322 | 14 | 7.9% (4.7%–12.8%) | 34.0% |
| 0.99 | 103 | 397 | 3 | 2.9% (1.0%–8.2%) | 18.9% |
| 1 | 63 | 437 | 1 | 1.6% (0.3%–8.5%) | 11.2% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **-21.4%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **55.6%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 105 | 43 | 41.0% |
| [0.5, 0.8) | 114 | 42 | 36.8% |
| [0.8, 0.9) | 57 | 13 | 22.8% |
| [0.9, 0.95) | 46 | 12 | 26.1% |
| [0.95, 0.99) | 75 | 11 | 14.7% |
| [0.99, 1) | 40 | 2 | 5.0% |
| Exactly 1 | 63 | 1 | 1.6% |

## Reproduction and provenance

The baseline used **2,862** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
