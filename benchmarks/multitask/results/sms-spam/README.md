# SMS spam: 500 evaluated records

Jev accuracy: **98.0%**; macro-F1: **95.7%**. Naive Bayes accuracy: **98.4%**; training-majority accuracy: **87.0%**.

At threshold 0.8: **2/461 accepted errors**, 39 records for review, 0 failed provider responses. Known-usage inference cost: **$0.00862**. Batch processing: **41.1 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 500 | 0 | 10 | 2.0% (1.1%–3.6%) | 98.1% |
| 0.5 | 480 | 20 | 4 | 0.8% (0.3%–2.1%) | 92.6% |
| 0.8 | 461 | 39 | 2 | 0.4% (0.1%–1.6%) | 88.4% |
| 0.9 | 435 | 65 | 1 | 0.2% (0.0%–1.3%) | 82.9% |
| 0.95 | 421 | 79 | 1 | 0.2% (0.0%–1.3%) | 79.6% |
| 0.99 | 378 | 122 | 1 | 0.3% (0.0%–1.5%) | 70.5% |
| 1 | 335 | 165 | 1 | 0.3% (0.1%–1.7%) | 62.6% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **73.3%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **88.4%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 20 | 6 | 30.0% |
| [0.5, 0.8) | 19 | 2 | 10.5% |
| [0.8, 0.9) | 26 | 1 | 3.8% |
| [0.9, 0.95) | 14 | 0 | 0.0% |
| [0.95, 0.99) | 43 | 0 | 0.0% |
| [0.99, 1) | 43 | 0 | 0.0% |
| Exactly 1 | 335 | 1 | 0.3% |

## Reproduction and provenance

The baseline used **4,954** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
