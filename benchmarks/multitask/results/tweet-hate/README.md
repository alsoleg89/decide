# Tweet hate speech: 500 evaluated records

Jev accuracy: **69.6%**; macro-F1: **68.9%**. Naive Bayes accuracy: **48.4%**; training-majority accuracy: **57.0%**.

At threshold 0.8: **40/251 accepted errors**, 249 records for review, 0 failed provider responses. Known-usage inference cost: **$0.00923**. Batch processing: **39.4 seconds**.

## Threshold sweep

Every row below replays the same recorded model decisions through the MCP tool. There are no additional paid inference calls. JSON savings include the call, summary and every full `{id, content}` review record; classifications are identical to the live run.

| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 500 | 0 | 152 | 30.4% (26.5%–34.6%) | 98.7% |
| 0.5 | 354 | 146 | 89 | 25.1% (20.9%–29.9%) | 72.8% |
| 0.8 | 251 | 249 | 40 | 15.9% (11.9%–21.0%) | 53.0% |
| 0.9 | 198 | 302 | 26 | 13.1% (9.1%–18.5%) | 42.0% |
| 0.95 | 148 | 352 | 15 | 10.1% (6.2%–16.0%) | 31.2% |
| 0.99 | 85 | 415 | 6 | 7.1% (3.3%–14.6%) | 16.8% |
| 1 | 44 | 456 | 0 | 0.0% (0.0%–8.0%) | 7.9% |

These are observed errors against the source labels, not a future accuracy guarantee. The sweep is exploratory and must not be treated as a separately validated threshold selection.

## Context format comparison

The initial live run included full provider metadata in `review.jsonl`: **-10.2%** JSON reduction. The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: **53.0%** reduction. A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.

## Observed errors by confidence

| Jev confidence | Records | Errors | Error rate |
| --- | ---: | ---: | ---: |
| [0, 0.5) | 146 | 63 | 43.2% |
| [0.5, 0.8) | 103 | 49 | 47.6% |
| [0.8, 0.9) | 53 | 14 | 26.4% |
| [0.9, 0.95) | 50 | 11 | 22.0% |
| [0.95, 0.99) | 63 | 9 | 14.3% |
| [0.99, 1) | 41 | 6 | 14.6% |
| Exactly 1 | 44 | 0 | 0.0% |

## Reproduction and provenance

The baseline used **8,966** labeled training records; Jev received **zero** labeled examples. Exact duplicate evaluation texts were excluded from baseline training. A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.

[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · [Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)

[Shared methods and reproduction commands](../../README.md)
