"""Render readable evaluation tables from the committed reports."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = {'ag-news':'News topics', 'apache-logs':'Apache severity', 'banking77':'Banking support (77 intents)',
         'imdb':'Movie review sentiment', 'sms-spam':'SMS spam', 'tweet-emotion':'Tweet emotions',
         'tweet-hate':'Tweet hate speech', 'tweet-irony':'Tweet irony', 'tweet-offensive':'Tweet offensiveness',
         'tweet-sentiment':'Tweet sentiment'}


def pct(value):
    return '—' if value is None else f'{value*100:.1f}%'


def cost(report):
    return ('' if report['provider_usage']['complete'] else '≥') + f"${report['estimated_jev_cost_usd']:.5f}"


reports=[]
for name,title in NAMES.items():
    folder=ROOT/'results'/name
    report=json.loads((folder/'report.json').read_text())
    reports.append((name,title,report))
    actual=next(row for row in report['threshold_sweep'] if row['threshold']==.8)
    report['quality_on_valid_responses']=report['correct_labeled_items']/(report['items']-report['failed'])
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lines=[f'# {title}: {report["items"]} evaluated records', '',
           f'Jev accuracy: **{pct(report["quality"]["accuracy"])}**; macro-F1: **{pct(report["quality"]["macro_f1"])}**. '
           f'Naive Bayes accuracy: **{pct(report["baselines"]["naive_bayes"]["accuracy"])}**; '
           f'training-majority accuracy: **{pct(report["baselines"]["majority"]["accuracy"])}**.', '',
           f'At threshold 0.8: **{actual["accepted_errors"]}/{actual["accepted"]} accepted errors**, '
           f'{actual["review"]} records for review, {report["failed"]} failed provider responses. '
           f'Known-usage inference cost: **{cost(report)}**. Batch processing: **{report["elapsed_seconds"]:.1f} seconds**.', '',
           '## Threshold sweep', '',
           'Every row below replays the same recorded model decisions through the MCP tool. '
           'There are no additional paid inference calls. JSON savings include the call, summary and every '
           'full `{id, content}` review record; classifications are identical to the live run.', '',
           '| Threshold | Accepted | Review | Accepted errors | Error rate (95% Wilson interval) | Full-review JSON saved |',
           '| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in report['compact_review_replay']['thresholds']:
        original=next(item for item in report['threshold_sweep'] if item['threshold']==row['threshold'])
        interval=original['accepted_error_95ci']
        interval_text=f'{pct(interval[0])}–{pct(interval[1])}' if interval else '—'
        lines.append(f'| {row["threshold"]:g} | {row["accepted"]} | {row["review"]} | {row["accepted_errors"]} | {pct(row["accepted_error_rate"])} ({interval_text}) | {pct(row["context_bytes_reduction_with_all_reviews"])} |')
    lines+=['', 'These are observed errors against the source labels, not a future accuracy guarantee. '
            'The sweep is exploratory and must not be treated as a separately validated threshold selection.', '',
            '## Context format comparison', '',
            f'The initial live run included full provider metadata in `review.jsonl`: '
            f'**{pct(report["context_bytes_reduction_with_all_reviews"])}** JSON reduction. '
            f'The compact replay keeps that metadata in `results.jsonl` and sends only original inputs for review: '
            f'**{pct(report["compact_review_replay"]["context_bytes_reduction_with_all_reviews"])}** reduction. '
            'A negative reduction means the workflow grew the context. This is serialized JSON, not billed model tokens.', '',
            '## Observed errors by confidence', '',
            '| Jev confidence | Records | Errors | Error rate |', '| --- | ---: | ---: | ---: |']
    for row in report['observed_error_by_confidence_bin']:
        band='Exactly 1' if row['exact_one'] else f'[{row["low"]:g}, {row["high_exclusive"]:g})'
        lines.append(f'| {band} | {row["items"]} | {row["errors"]} | {pct(row["error_rate"])} |')
    lines+=['', '## Reproduction and provenance', '',
            f'The baseline used **{report["baselines"]["train_items"]:,}** labeled training records; Jev received **zero** labeled examples. '
            'Exact duplicate evaluation texts were excluded from baseline training. '
            'A fixed baseline is useful for comparison, not a claim about the best possible trained classifier.', '',
            '[Dataset and input hashes](dataset.json) · [Rubric](rubric.json) · [Predictions](predictions.jsonl) · '
            '[Reference labels](labels.jsonl) · [Complete report, including per-class metrics and confusion matrix](report.json)', '',
            '[Shared methods and reproduction commands](../../README.md)', '']
    (folder/'README.md').write_text('\n'.join(lines),encoding='utf-8')

items=sum(r['items'] for _,_,r in reports)
known_cost=sum(r['estimated_jev_cost_usd'] for _,_,r in reports)
failed=sum(r['failed'] for _,_,r in reports)
text=['# decide: 10-task evaluation', '',
      f'**{items:,} real records, 10 tasks, 70 offline threshold evaluations.** '
      f'Known successful-token usage corresponds to **at least ${known_cost:.4f}** of Jev inference. '
      f'There were **{failed} rejected provider responses**; their missing usage makes the cost a lower bound. '
      'Jev 1.13.0, 2026-09-19, concurrency 4. Each task used one rubric fixed before inference; '
      'no prompt tuning, few-shot examples or model fine-tuning.', '',
      '## Decision quality', '',
      'Accuracy counts failed provider responses as incorrect. Accepted errors are wrong labels among '
      'the decisions the tool would accept at confidence ≥0.8. The local Naive Bayes baseline uses '
      'the dataset training labels; Jev uses only the task description and label definitions.', '',
      '| Task | Records | Jev accuracy | Jev macro-F1 | Naive Bayes accuracy | Accepted errors |',
      '| --- | ---: | ---: | ---: | ---: | ---: |']
for name,title,r in reports:
    s=next(row for row in r['threshold_sweep'] if row['threshold']==.8)
    text.append(f'| [{title}](results/{name}/README.md) | {r["items"]} | {pct(r["quality"]["accuracy"])} | {pct(r["quality"]["macro_f1"])} | {pct(r["baselines"]["naive_bayes"]["accuracy"])} | {s["accepted_errors"]}/{s["accepted"]} ({pct(s["accepted_error_rate"])}) |')
text+=['', '## Review workload, context and cost', '',
       'The compact format was measured by replaying the recorded decisions through MCP after removing '
       'duplicated provider metadata from the review queue. All classifications and default routing were verified '
       'identical. Full probability vectors, reasons and usage remain in the audit results. '
       'Savings include reading every full review input, not just the initial tool response.', '',
       '| Task | Needs review | Live format: JSON saved | Compact replay: JSON saved | Known Jev cost | Batch time |',
       '| --- | ---: | ---: | ---: | ---: | ---: |']
for name,title,r in reports:
    text.append(f'| {title} | {r["review_count"]} ({pct(r["review_fraction"])}) | {pct(r["context_bytes_reduction_with_all_reviews"])} | {pct(r["compact_review_replay"]["context_bytes_reduction_with_all_reviews"])} | {cost(r)} | {r["elapsed_seconds"]:.1f}s |')
text+=['', '## What these results establish', '',
       '- **The useful mechanism is selective reading.** Jev classifies the bulk; the agent receives counts '
       'and paths, and reads only the review inputs. Whether this helps depends on record sizes, routing and output overhead.',
       '- **Long reviews are a strong observed use case.** On IMDb, Jev scored 96.2% versus 82.2% for the fixed '
       'trained baseline. At threshold 0.99, 430/500 decisions were accepted with 3 errors (0.7%), while the compact '
       'workflow kept 85.0% of JSON out of context. This is a sample result, not a promised production error rate.',
       '- **A fixed review percentage is unnecessary.** On SMS at threshold 0.9, 435/500 decisions were accepted '
       'with 1 error; 13% review still saved 82.9% of JSON. At threshold 0.8, errors and review volume both differ.',
       '- **Short ambiguous text remains hard.** Sentiment tweets had 23.5% errors among accepted decisions '
       'at 0.8. Lower API cost does not make these decisions reliable.',
       '- **Use ordinary code when the label is explicit.** The Apache severity regex scored 100%, matching '
       'Jev without any inference charge. This is a deliberate negative control, not an argument to use a model.',
       '- **Labeled training data can make a local classifier competitive.** This Naive Bayes baseline was '
       'similar or better on news, banking and SMS. Jev avoids collecting a training set for each new rubric; '
       'the benchmark does not establish that Jev is always the best classifier.', '',
       '## Methods and limits', '',
       '**Metrics.** Accuracy is reference-label agreement over all records. Macro-F1 gives each class equal '
       'weight. Accepted error rate excludes reviewed records; review includes failures. The 95% Wilson '
       'intervals in each task report describe sampling uncertainty and do not establish future calibration. '
       'Confidence is a model distribution statistic, not a guarantee of correctness. Each report includes '
       'confidence bins, per-class metrics and a confusion matrix.', '',
       '**Context and cost.** Context is canonical UTF-8 JSON bytes: the full inline call versus the source '
       'call, compact summary and all review rows. It excludes host-specific output duplication, MCP framing '
       'and agent reasoning. These are not billed-token savings or total agent-dollar savings. '
       '[Jev pricing](https://docs.typesafe.ai/models) is $0.042/M input tokens with free output. '
       'Actual review quality by an expensive agent was not measured.', '',
       '**Sampling.** Uniform seeded test samples, except Banking77 with 10 examples per intent. '
       'AG News excludes the earlier 400 evaluated IDs. SMS uses a seeded holdout because there is no official '
       'split. Apache labels are parsed severity fields, not human semantic annotations. IMDb IDs conceal '
       'the original positive/negative directory and rating. All sources are public and may occur in Jev '
       'pretraining; this is not contamination-free evidence. No results were filtered for good performance.', '',
       '**Failures.** One response on sentiment, one on emotion, and 33 on Banking77 failed client response '
       'validation and remain failures in all headline metrics. Four separate diagnostic repeats returned '
       'valid responses; they did not replace failed predictions. The original raw rejected responses were '
       'not saved, so their precise cause is unproven. [Diagnostic records](diagnostics.json).', '',
       '**Baseline.** Multinomial Naive Bayes implemented with Python standard-library counters, Laplace '
       'smoothing α=1, lowercase Unicode word tokens of length ≥2, raw counts, no hyperparameter search. '
       'Training sets and their hashes are recorded. This differs from Jev zero-shot inference and is not a '
       'state-of-the-art leaderboard comparison.', '',
       '## Reproduce', '',
       'Run from the repository root. Raw source data stays outside the repository; archived predictions, '
       'reference labels and rubrics are committed. Downloading/preparing and compact replay are free; '
       '`run.py` makes paid Jev calls unless completed raw reports already exist.', '',
       '```sh', 'uv run --locked python benchmarks/multitask/prepare.py /tmp/decide-multitask',
       '# Free: verify the archived measurements.',
       'uv run --locked python benchmarks/multitask/verify.py --root /tmp/decide-multitask',
       '# Free: replay recorded decisions through the current compact MCP format.',
       'uv run --locked python benchmarks/multitask/replay.py --root /tmp/decide-multitask --results benchmarks/multitask/results',
       '# Paid: produce a separate new evaluation (requires a TypeSafe key).',
       'uv run --locked python benchmarks/multitask/run.py --root /tmp/decide-multitask --output /tmp/decide-eval-results', '```', '',
       '`run.py --tasks sms-spam imdb` limits a paid run. It stops on authentication/long-cooldown failures '
       'and refuses to silently repeat an interrupted, unreported run. Individual malformed responses stay '
       'in the metrics. Keep the original archived reports when comparing a new run.', '',
       '## Sources', '',
       '- [TweetEval](https://github.com/cardiffnlp/tweeteval): five official task splits; the common metrics '
       'here are not the full official TweetEval leaderboard score.',
       '- [Banking77 / PolyAI](https://github.com/PolyAI-LDN/task-specific-datasets): fine-grained banking support intents.',
       '- [AG News source description](https://github.com/mhjabreel/CharCnn_Keras/tree/master/data/ag_news_csv): '
       'Zhang, Zhao and LeCun (2015), using the AG news corpus.',
       '- [SMS Spam Collection / UCI](https://archive.ics.uci.edu/dataset/228/sms%2Bspam%2Bcollection): Almeida '
       'and Hidalgo; CC BY 4.0.',
       '- [Large Movie Review Dataset / Stanford](https://ai.stanford.edu/~amaas/data/sentiment/): Maas et al. (2011).',
       '- [Loghub Apache logs](https://github.com/logpai/loghub): public server-log sample.', '',
       'Source revisions, URLs, SHA-256 hashes, split sizes and exact sampled IDs are recorded in each '
       '`dataset.json`. Consult original use terms before redistributing raw text.', '']
(ROOT/'README.md').write_text('\n'.join(text),encoding='utf-8')
print(f'Rendered {len(reports)} task reports, {items} evaluated records.')
