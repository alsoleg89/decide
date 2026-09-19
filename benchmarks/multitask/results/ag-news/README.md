# News topics: 1000 evaluated records

Jev accuracy: **88.7%**; macro-F1: **88.6%**. Naive Bayes accuracy: **89.5%**; training-majority accuracy: **26.0%**.

At threshold 0.8: **71/902 accepted errors**, 98 records for review, 0 failed provider responses. Known-usage inference cost: **$0.02159**. Batch processing: **78.7 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 1000 | 0 | 113 | 11.3% (9.5%–13.4%) | 99.6% |
| 0.5 | 966 | 34 | 92 | 9.5% (7.8%–11.5%) | 96.0% |
| 0.8 | 902 | 98 | 71 | 7.9% (6.3%–9.8%) | 89.4% |
| 0.9 | 861 | 139 | 65 | 7.5% (6.0%–9.5%) | 85.4% |
| 0.95 | 824 | 176 | 59 | 7.2% (5.6%–9.1%) | 81.5% |
| 0.99 | 758 | 242 | 41 | 5.4% (4.0%–7.3%) | 75.1% |
| 1 | 700 | 300 | 38 | 5.4% (4.0%–7.4%) | 69.4% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **80.8%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **89.4%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 34 | 21 | 61.8% |
| [0.5, 0.8) | 64 | 21 | 32.8% |
| [0.8, 0.9) | 41 | 6 | 14.6% |
| [0.9, 0.95) | 37 | 6 | 16.2% |
| [0.95, 0.99) | 66 | 18 | 27.3% |
| [0.99, 1) | 58 | 3 | 5.2% |
| Exactly 1 | 700 | 38 | 5.4% |

## Reproduction and provenance

The baseline used **120,000** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
