# Tweet offensiveness: 500 evaluated records

Jev accuracy: **82.0%**; macro-F1: **78.4%**. Naive Bayes accuracy: **76.2%**; training-majority accuracy: **73.4%**.

At threshold 0.8: **32/329 accepted errors**, 171 records for review, 0 failed provider responses. Known-usage inference cost: **$0.00918**. Batch processing: **39.7 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 500 | 0 | 90 | 18.0% (14.9%–21.6%) | 98.9% |
| 0.5 | 418 | 82 | 61 | 14.6% (11.5%–18.3%) | 81.4% |
| 0.8 | 329 | 171 | 32 | 9.7% (7.0%–13.4%) | 63.2% |
| 0.9 | 272 | 228 | 21 | 7.7% (5.1%–11.5%) | 52.1% |
| 0.95 | 235 | 265 | 16 | 6.8% (4.2%–10.8%) | 44.8% |
| 0.99 | 163 | 337 | 9 | 5.5% (2.9%–10.2%) | 31.8% |
| 1 | 93 | 407 | 3 | 3.2% (1.1%–9.1%) | 17.4% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **20.1%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **63.2%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 82 | 29 | 35.4% |
| [0.5, 0.8) | 89 | 29 | 32.6% |
| [0.8, 0.9) | 57 | 11 | 19.3% |
| [0.9, 0.95) | 37 | 5 | 13.5% |
| [0.95, 0.99) | 72 | 7 | 9.7% |
| [0.99, 1) | 70 | 6 | 8.6% |
| Exactly 1 | 93 | 3 | 3.2% |

## Reproduction and provenance

The baseline used **11,912** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
