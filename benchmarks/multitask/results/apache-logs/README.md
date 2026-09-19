# Apache severity: 300 evaluated records

Jev accuracy: **100.0%**; macro-F1: **100.0%**. Naive Bayes accuracy: **100.0%**; training-majority accuracy: **71.3%**.

At threshold 0.8: **0/300 accepted errors**, 0 records for review, 0 failed provider responses. Known-usage inference cost: **$0.00519**. Batch processing: **23.7 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 300 | 0 | 0 | 0.0% (0.0%–1.3%) | 97.2% |
| 0.5 | 300 | 0 | 0 | 0.0% (0.0%–1.3%) | 97.2% |
| 0.8 | 300 | 0 | 0 | 0.0% (0.0%–1.3%) | 97.2% |
| 0.9 | 300 | 0 | 0 | 0.0% (0.0%–1.3%) | 97.2% |
| 0.95 | 300 | 0 | 0 | 0.0% (0.0%–1.3%) | 97.2% |
| 0.99 | 300 | 0 | 0 | 0.0% (0.0%–1.3%) | 97.2% |
| 1 | 300 | 0 | 0 | 0.0% (0.0%–1.3%) | 97.2% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **97.4%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **97.2%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 0 | 0 | — |
| [0.5, 0.8) | 0 | 0 | — |
| [0.8, 0.9) | 0 | 0 | — |
| [0.9, 0.95) | 0 | 0 | — |
| [0.95, 0.99) | 0 | 0 | — |
| [0.99, 1) | 0 | 0 | — |
| Exactly 1 | 300 | 0 | 0.0% |

## Reproduction and provenance

The baseline used **1,495** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
