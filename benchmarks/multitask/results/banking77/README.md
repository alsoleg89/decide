# Banking support (77 intents): 770 evaluated records

Jev accuracy: **77.1%**; macro-F1: **77.6%**. Naive Bayes accuracy: **79.0%**; training-majority accuracy: **1.3%**.

At threshold 0.8: **69/596 accepted errors**, 174 records for review, 33 failed provider responses. Known-usage inference cost: **≥$0.05403**. Batch processing: **62.6 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 737 | 33 | 143 | 19.4% (16.7%–22.4%) | 87.7% |
| 0.5 | 708 | 62 | 121 | 17.1% (14.5%–20.0%) | 84.0% |
| 0.8 | 596 | 174 | 69 | 11.6% (9.3%–14.4%) | 70.0% |
| 0.9 | 548 | 222 | 54 | 9.9% (7.6%–12.6%) | 64.7% |
| 0.95 | 498 | 272 | 38 | 7.6% (5.6%–10.3%) | 58.3% |
| 0.99 | 383 | 387 | 18 | 4.7% (3.0%–7.3%) | 43.3% |
| 1 | 308 | 462 | 12 | 3.9% (2.2%–6.7%) | 33.7% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **-353.0%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **70.0%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 29 | 22 | 75.9% |
| [0.5, 0.8) | 112 | 52 | 46.4% |
| [0.8, 0.9) | 48 | 15 | 31.2% |
| [0.9, 0.95) | 50 | 16 | 32.0% |
| [0.95, 0.99) | 115 | 20 | 17.4% |
| [0.99, 1) | 75 | 6 | 8.0% |
| Exactly 1 | 308 | 12 | 3.9% |

## Reproduction and provenance

The baseline used **10,003** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
