# Tweet sentiment: 500 evaluated records

Jev accuracy: **64.0%**; macro-F1: **65.0%**. Naive Bayes accuracy: **60.4%**; training-majority accuracy: **48.6%**.

At threshold 0.8: **69/294 accepted errors**, 206 records for review, 1 failed provider responses. Known-usage inference cost: **≥$0.00877**. Batch processing: **40.4 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 499 | 1 | 179 | 35.9% (31.8%–40.2%) | 98.2% |
| 0.5 | 413 | 87 | 132 | 32.0% (27.6%–36.6%) | 81.0% |
| 0.8 | 294 | 206 | 69 | 23.5% (19.0%–28.6%) | 58.0% |
| 0.9 | 248 | 252 | 53 | 21.4% (16.7%–26.9%) | 49.2% |
| 0.95 | 197 | 303 | 32 | 16.2% (11.7%–22.0%) | 39.4% |
| 0.99 | 132 | 368 | 18 | 13.6% (8.8%–20.5%) | 25.7% |
| 1 | 90 | 410 | 10 | 11.1% (6.1%–19.3%) | 17.4% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **-13.4%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **58.0%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 86 | 47 | 54.7% |
| [0.5, 0.8) | 119 | 63 | 52.9% |
| [0.8, 0.9) | 46 | 16 | 34.8% |
| [0.9, 0.95) | 51 | 21 | 41.2% |
| [0.95, 0.99) | 65 | 14 | 21.5% |
| [0.99, 1) | 42 | 8 | 19.0% |
| Exactly 1 | 90 | 10 | 11.1% |

## Reproduction and provenance

The baseline used **45,615** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
