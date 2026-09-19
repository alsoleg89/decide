# decide: 10-task evaluation

**5,570 real records, 10 tasks, 70 offline threshold evaluations.** Known successful-token usage corresponds to **at least $0.1489** of Jev inference. There were **35 rejected provider responses**; their missing usage makes the cost a lower bound. Jev 1.13.0, 2026-09-19, concurrency 4. Each task used one rubric fixed before inference; no prompt tuning, few-shot examples or model fine-tuning.

[Threshold-selection validation](threshold-validation/README.md) adds 60 retrospective checks using separate calibration and holdout partitions of these same decisions. It shows why selecting a threshold from observed errors alone can miss the chosen error budget.

## Decision quality

Accuracy counts failed provider responses as incorrect. Accepted errors are wrong labels among the decisions the tool would accept at confidence ≥0.8. The local Naive Bayes baseline uses the dataset training labels; Jev uses only the task description and label definitions.

| Task | Records | Jev accuracy | Jev macro-F1 | Naive Bayes accuracy | Accepted errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| [News topics](results/ag-news/README.md) | 1000 | 88.7% | 88.6% | 89.5% | 71/902 (7.9%) |
| [Apache severity](results/apache-logs/README.md) | 300 | 100.0% | 100.0% | 100.0% | 0/300 (0.0%) |
| [Banking support (77 intents)](results/banking77/README.md) | 770 | 77.1% | 77.6% | 79.0% | 69/596 (11.6%) |
| [Movie review sentiment](results/imdb/README.md) | 500 | 96.2% | 96.2% | 82.2% | 10/479 (2.1%) |
| [SMS spam](results/sms-spam/README.md) | 500 | 98.0% | 95.7% | 98.4% | 2/461 (0.4%) |
| [Tweet emotions](results/tweet-emotion/README.md) | 500 | 83.6% | 79.8% | 65.0% | 32/384 (8.3%) |
| [Tweet hate speech](results/tweet-hate/README.md) | 500 | 69.6% | 68.9% | 48.4% | 40/251 (15.9%) |
| [Tweet irony](results/tweet-irony/README.md) | 500 | 75.2% | 75.2% | 65.6% | 39/281 (13.9%) |
| [Tweet offensiveness](results/tweet-offensive/README.md) | 500 | 82.0% | 78.4% | 76.2% | 32/329 (9.7%) |
| [Tweet sentiment](results/tweet-sentiment/README.md) | 500 | 64.0% | 65.0% | 60.4% | 69/294 (23.5%) |

## Review workload, context and cost

The compact format was measured by replaying the recorded decisions through MCP after removing duplicated provider metadata from the review queue. All classifications and default routing were verified identical. Full probability vectors, reasons and usage remain in the audit results. Savings include reading every full review input, not just the initial tool response.

| Task | Needs review | Live format: JSON saved | Compact replay: JSON saved | Known Jev cost | Batch time |
| --- | ---: | ---: | ---: | ---: | ---: |
| News topics | 98 (9.8%) | 80.8% | 89.4% | $0.02159 | 78.7s |
| Apache severity | 0 (0.0%) | 97.4% | 97.2% | $0.00519 | 23.7s |
| Banking support (77 intents) | 174 (22.6%) | -353.0% | 70.0% | ≥$0.05403 | 62.6s |
| Movie review sentiment | 21 (4.2%) | 94.3% | 95.0% | $0.01418 | 39.4s |
| SMS spam | 39 (7.8%) | 73.3% | 88.4% | $0.00862 | 41.1s |
| Tweet emotions | 116 (23.2%) | 32.1% | 74.8% | ≥$0.00934 | 41.5s |
| Tweet hate speech | 249 (49.8%) | -10.2% | 53.0% | $0.00923 | 39.4s |
| Tweet irony | 219 (43.8%) | -21.4% | 55.6% | $0.00876 | 39.9s |
| Tweet offensiveness | 171 (34.2%) | 20.1% | 63.2% | $0.00918 | 39.7s |
| Tweet sentiment | 206 (41.2%) | -13.4% | 58.0% | ≥$0.00877 | 40.4s |

## What these results establish

- **The useful mechanism is selective reading.** Jev classifies the bulk; the agent receives counts and paths, and reads only the review inputs. Whether this helps depends on record sizes, routing and output overhead.
- **Long reviews are a strong observed use case.** On IMDb, Jev scored 96.2% versus 82.2% for the fixed trained baseline. At threshold 0.99, 430/500 decisions were accepted with 3 errors (0.7%), while the compact workflow kept 85.0% of JSON out of context. This is a sample result, not a promised production error rate.
- **A fixed review percentage is unnecessary.** On SMS at threshold 0.9, 435/500 decisions were accepted with 1 error; 13% review still saved 82.9% of JSON. At threshold 0.8, errors and review volume both differ.
- **Short ambiguous text remains hard.** Sentiment tweets had 23.5% errors among accepted decisions at 0.8. Lower API cost does not make these decisions reliable.
- **Use ordinary code when the label is explicit.** The Apache severity regex scored 100%, matching Jev without any inference charge. This is a deliberate negative control, not an argument to use a model.
- **Labeled training data can make a local classifier competitive.** This Naive Bayes baseline was similar or better on news, banking and SMS. Jev avoids collecting a training set for each new rubric; the benchmark does not establish that Jev is always the best classifier.

## Methods and limits

**Metrics.** Accuracy is reference-label agreement over all records. Macro-F1 gives each class equal weight. Accepted error rate excludes reviewed records; review includes failures. The 95% Wilson intervals in each task report describe sampling uncertainty and do not establish future calibration. Confidence is a model distribution statistic, not a guarantee of correctness. Each report includes confidence bins, per-class metrics and a confusion matrix.

**Context and cost.** Context is canonical UTF-8 JSON bytes: the full inline call versus the source call, compact summary and all review rows. It excludes host-specific output duplication, MCP framing and agent reasoning. These are not billed-token savings or total agent-dollar savings. [Jev pricing](https://docs.typesafe.ai/models) is $0.042/M input tokens with free output. Actual review quality by an expensive agent was not measured.

**Sampling.** Uniform seeded test samples, except Banking77 with 10 examples per intent. AG News excludes the earlier 400 evaluated IDs. SMS uses a seeded holdout because there is no official split. Apache labels are parsed severity fields, not human semantic annotations. IMDb IDs conceal the original positive/negative directory and rating. All sources are public and may occur in Jev pretraining; this is not contamination-free evidence. No results were filtered for good performance.

**Failures.** One response on sentiment, one on emotion, and 33 on Banking77 failed client response validation and remain failures in all headline metrics. Four separate diagnostic repeats returned valid responses; they did not replace failed predictions. The original raw rejected responses were not saved, so their precise cause is unproven. [Diagnostic records](diagnostics.json).

**Baseline.** Multinomial Naive Bayes implemented with Python standard-library counters, Laplace smoothing α=1, lowercase Unicode word tokens of length ≥2, raw counts, no hyperparameter search. Training sets and their hashes are recorded. This differs from Jev zero-shot inference and is not a state-of-the-art leaderboard comparison.

## Reproduce

Run from the repository root. Raw source data stays outside the repository; archived predictions, reference labels and rubrics are committed. Downloading/preparing and compact replay are free; `run.py` makes paid Jev calls unless completed raw reports already exist.

```sh
uv run --locked python benchmarks/multitask/prepare.py /tmp/decide-multitask
# Free: verify the archived measurements.
uv run --locked python benchmarks/multitask/verify.py --root /tmp/decide-multitask
# Free: replay recorded decisions through the current compact MCP format.
uv run --locked python benchmarks/multitask/replay.py --root /tmp/decide-multitask --results benchmarks/multitask/results
# Paid: produce a separate new evaluation (requires a TypeSafe key).
uv run --locked python benchmarks/multitask/run.py --root /tmp/decide-multitask --output /tmp/decide-eval-results
```

`run.py --tasks sms-spam imdb` limits a paid run. It stops on authentication/long-cooldown failures and refuses to silently repeat an interrupted, unreported run. Individual malformed responses stay in the metrics. Keep the original archived reports when comparing a new run.

## Sources

- [TweetEval](https://github.com/cardiffnlp/tweeteval): five official task splits; the common metrics here are not the full official TweetEval leaderboard score.
- [Banking77 / PolyAI](https://github.com/PolyAI-LDN/task-specific-datasets): fine-grained banking support intents.
- [AG News source description](https://github.com/mhjabreel/CharCnn_Keras/tree/master/data/ag_news_csv): Zhang, Zhao and LeCun (2015), using the AG news corpus.
- [SMS Spam Collection / UCI](https://archive.ics.uci.edu/dataset/228/sms%2Bspam%2Bcollection): Almeida and Hidalgo; CC BY 4.0.
- [Large Movie Review Dataset / Stanford](https://ai.stanford.edu/~amaas/data/sentiment/): Maas et al. (2011).
- [Loghub Apache logs](https://github.com/logpai/loghub): public server-log sample.

Source revisions, URLs, SHA-256 hashes, split sizes and exact sampled IDs are recorded in each `dataset.json`. Consult original use terms before redistributing raw text.
