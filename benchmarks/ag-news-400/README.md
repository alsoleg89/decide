# AG News: 400 real articles, 74.8% less JSON including review

One live run on 2026-09-19 using the actual MCP stdio subprocess and Jev 1.13.0.
The [rubric](rubric.json), default confidence threshold (0.8) and sample were fixed
before inference. No prompt revisions or retry-until-correct runs were performed.

| Measurement | Result |
| --- | ---: |
| Items | 400 |
| Accepted / review | 348 / 52 |
| Wrong labels among accepted | 31 / 348 (8.9%) |
| All labels agreeing with reference | 343 / 400 (85.8%) |
| Processing time | 31.166 seconds |
| Failed requests / retries | 0 / 0 |
| Provider input / output tokens | 205,683 / 19,431 |
| Estimated Jev inference cost | $0.008639 |
| Inline rubric + all inputs | 121,140 bytes |
| Path-based call + summary | 1,257 bytes |
| All full review records | 29,236 bytes |
| Initial JSON reduction | 98.96% |
| JSON reduction including all review records | **74.83%** |

Cost uses [published Jev pricing](https://docs.typesafe.ai/models): $0.042 per
million input tokens and free output. It excludes the agent's processing and
review. Byte measurements exclude MCP framing, host output duplication and agent
reasoning; they are not billed-token or total-dollar savings. This run uses
`review_limit: 0`, so the initial summary has no content previews.

## Thresholds change both savings and errors

The offline sweep reuses the same model predictions. The final column measures
**input JSONL kept out of review**, not end-to-end savings: it excludes the rubric,
summary and decision metadata. The full accounting above applies to the actual
0.8 run only.

| Threshold | Accepted | Review | Wrong among accepted | Input bytes kept out of review |
| --- | ---: | ---: | ---: | ---: |
| 0 | 400 | 0 | 57 (14.3%) | 100.0% |
| 0.5 | 380 | 20 | 47 (12.4%) | 95.1% |
| 0.8 | 348 | 52 | 31 (8.9%) | 87.1% |
| 0.9 | 332 | 68 | 25 (7.5%) | 83.0% |
| 0.95 | 318 | 82 | 22 (6.9%) | 79.7% |
| 0.99 | 298 | 102 | 18 (6.0%) | 74.6% |
| 1 | 280 | 120 | 15 (5.4%) | 70.6% |

Confidence 1 still accepts incorrect labels. No threshold in this sweep achieves
an accepted error rate below 5%. Choose a task-specific error tolerance on
calibration data and verify it separately; do not lower the threshold just to
make the context-savings figure larger.

## Reproduce

The sample has 100 randomly selected examples per class from the AG News test
split. [Dataset provenance](dataset.json) records the pinned CSV source, SHA-256,
seed and sampling procedure. IDs are one-based source CSV row numbers.
AG News is a public academic classification benchmark; it may have been used in
Jev training. This sample is new to this project, not proven unseen by the model.
The four classes can overlap, and no independent adjudication or measurement of
the agent's review quality was performed.

From the repository root:

```sh
mkdir -p /tmp/decide-ag-news
curl -fsSL https://raw.githubusercontent.com/mhjabreel/CharCnn_Keras/555590db4219b1243abb1918effd6a7425a2d75f/data/ag_news_csv/test.csv -o /tmp/decide-ag-news/test.csv
uv run --locked python benchmarks/ag-news-400/prepare.py /tmp/decide-ag-news/test.csv /tmp/decide-ag-news

# Free: recompute quality and input-byte sweep from recorded predictions.
uv run --locked python evaluate.py \
  --labels benchmarks/ag-news-400/labels.jsonl \
  --results benchmarks/ag-news-400/predictions.jsonl \
  --inputs /tmp/decide-ag-news/items.jsonl

# Paid: run the fixed rubric through Jev again. Prompts for a key if needed.
DECIDE_MODEL=jev-1.13.0 uv run --locked python benchmark_real.py \
  --root /tmp/decide-ag-news --rubric benchmarks/ag-news-400/rubric.json \
  --labels benchmarks/ag-news-400/labels.jsonl --output /tmp/decide-ag-news/report.json
```

Raw news text is not republished in this repository. The original dataset
[description](https://github.com/mhjabreel/CharCnn_Keras/blob/555590db4219b1243abb1918effd6a7425a2d75f/data/ag_news_csv/readme.txt)
credits Xiang Zhang, Junbo Zhao and Yann LeCun, *Character-level Convolutional
Networks for Text Classification*, NIPS 2015, using the AG corpus. Consult the
source's use terms before reusing its text.
