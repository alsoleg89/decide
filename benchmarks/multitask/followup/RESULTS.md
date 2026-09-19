# Frozen-threshold results on 2,770 new records

All primary thresholds, record IDs and rubric hashes were [committed before inference](https://github.com/alsoleg89/decide/commit/651006b). These records have no ID or exact-content overlap with the earlier evaluations. The model and rubric wording are unchanged. No failed predictions were replaced.

| Task | N | Threshold / error budget | Accuracy | Accepted errors | Error rate (95% Wilson interval) | Review | Full-review JSON saved |
| --- | ---: | --- | ---: | ---: | --- | ---: | ---: |
| [imdb](results/imdb/report.json) | 1000 | 0.95 / 5.0% | 96.7% | 10 / 902 | 1.1% (0.6%–2.0%) | 98 (9.8%) | 91.1% |
| [ag-news](results/ag-news/report.json) | 1000 | 0.99 / 10.0% | 86.5% | 53 / 728 | 7.3% (5.6%–9.4%) | 272 (27.2%) | 72.7% |
| [banking77](results/banking77/report.json) | 770 | 0.99 / 10.0% | 79.5% | 14 / 401 | 3.5% (2.1%–5.8%) | 369 (47.9%) | 45.5% |

## Quality, cost and failures

| Task | Macro-F1 | Trained Naive Bayes accuracy | Observed error budget met | 95% Wilson upper ≤ budget | Provider failures | Known Jev cost | Batch time |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| imdb | 96.7% | 81.5% | True | True | 0 | $0.02862 | 77.2s |
| ag-news | 86.6% | 89.4% | True | True | 1 | ≥$0.02158 | 76.3s |
| banking77 | 79.7% | 79.9% | True | True | 27 | ≥$0.05446 | 63.2s |

**Known Jev usage cost: $0.10466** (lower bound).

Accuracy counts provider failures as incorrect; all failures require review. Accepted errors are wrong source-label predictions among automatically accepted decisions. The intervals are descriptive per-task intervals, not simultaneous coverage across three tasks or guarantees about future deployment. JSON savings include the live call, summary and every full review record. They exclude MCP framing, host duplication, agent reasoning and billed-token differences.

The three tasks were selected after promising results in the previous study. This follow-up tests those preselected thresholds on new records from the **same public corpora**, not arbitrary new domains or production data. Corpus contamination from model pretraining remains possible. The local Naive Bayes baseline uses labeled source training data; Jev receives no labeled examples.

Each task folder contains the original predictions, labels, rubric, dataset hashes, live summary and complete report. The report also contains an exploratory threshold sweep, which did **not** select or change the primary threshold. [Machine-readable verified summary](summary.json).

## Reproduce the verification

Follow the [frozen protocol](README.md) to prepare inputs; the committed live summaries supply the response measurements, so rerunning paid inference is unnecessary:

```sh
uv run --locked python benchmarks/multitask/followup/report.py --root /tmp/decide-followup
```

This command is offline: it verifies input hashes, server version, label agreement, routing and exact serialized-byte accounting before regenerating this summary. No model is called.
