"""Verify and summarize the frozen follow-up. Reads local artifacts; never calls Jev."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from analyze import classification, error_interval, read_rows


def size(value):
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode())


def verify(root):
    protocol = json.loads((HERE/'protocol.json').read_text())
    summaries = {}
    for name, plan in protocol['tasks'].items():
        folder = HERE/'results'/name
        report = json.loads((folder/'report.json').read_text())
        inputs = read_rows(root/name/'items.jsonl')
        labels = {r['id']: r['expected'] for r in read_rows(folder/'labels.jsonl')}
        predictions = {r['id']: r for r in read_rows(folder/'predictions.jsonl')}
        assert len(inputs) == len(predictions) == len(labels) == plan['items']
        assert set(plan['sample_ids']) == labels.keys() == predictions.keys() == {r['id'] for r in inputs}
        for filename, digest in plan['dataset']['files_sha256'].items():
            assert hashlib.sha256((root/name/filename).read_bytes()).hexdigest() == digest
        assert hashlib.sha256((folder/'rubric.json').read_bytes()).hexdigest() == report['rubric_sha256'] == plan['dataset']['files_sha256']['rubric.json']
        assert report['server_source_sha256'] == protocol['server_sha256']
        assert report['input_jsonl_sha256'] == plan['dataset']['files_sha256']['items.jsonl']
        assert json.loads((folder/'dataset.json').read_text()) == plan['dataset']
        assert report['rubric']['confidence_threshold'] == plan['threshold']
        assert set(report['models']) <= {protocol['model'], 'unavailable'}
        accepted = {key for key, r in predictions.items() if 'error' not in r and r['confidence'] >= plan['threshold']}
        assert accepted == {key for key, r in predictions.items() if r['status'] == 'accepted'}
        errors = sum(predictions[key]['choice'] != labels[key] for key in accepted)
        failed = sum('error' in r for r in predictions.values())
        assert (len(accepted), failed) == (report['accepted'], report['failed'])
        quality = classification(list(labels.values()), [predictions[key].get('choice') for key in labels], report['rubric']['criteria'])
        assert quality == report['quality']
        # Preserve the exact live summary used in the original byte calculation.
        saved_live = folder/'live-response.json'
        if saved_live.exists():
            live = json.loads(saved_live.read_text())
        else:
            raw = json.loads((root/name/'raw-report.json').read_text())
            live_path = Path(raw['results_path']).with_name('summary.json')
            live = json.loads(live_path.read_text())
            saved_live.write_text(json.dumps(live, ensure_ascii=False)+'\n', encoding='utf-8')
        assert (live['total'], live['accepted'], live['failed']) == (len(inputs), len(accepted), failed)
        input_tokens = sum(row.get('usage', {}).get('input_tokens', 0) for row in predictions.values())
        assert input_tokens == report['provider_usage']['input_tokens']
        assert math.isclose(input_tokens * .042 / 1_000_000, report['estimated_jev_cost_usd'])
        call = report['rubric']
        inline = {**call, 'items': inputs}
        del inline['source']
        review_bytes = sum(size(r)+1 for r in inputs if r['id'] not in accepted)
        assert review_bytes == report['all_review_records_bytes']
        assert size(inline) == report['inline_input_bytes']
        assert size(call)+size(live) == report['source_call_and_result_bytes']
        reduction = 1-(size(call)+size(live)+review_bytes)/size(inline)
        assert math.isclose(reduction, report['context_bytes_reduction_with_all_reviews'])
        interval = error_interval(errors, len(accepted))
        summaries[name] = {'items': plan['items'], 'threshold': plan['threshold'], 'error_budget': plan['accepted_error_budget'],
                           'accuracy': quality['accuracy'], 'macro_f1': quality['macro_f1'],
                           'accepted': len(accepted), 'accepted_errors': errors, 'accepted_error_rate': errors/len(accepted) if accepted else None,
                           'accepted_error_95ci': interval, 'review': len(inputs)-len(accepted), 'failed': failed,
                           'observed_budget_met': errors/len(accepted) <= plan['accepted_error_budget'] if accepted else None,
                           'wilson_upper_below_budget': interval[1] <= plan['accepted_error_budget'] if interval else None,
                           'full_review_json_reduction': reduction, 'known_jev_usd': report['estimated_jev_cost_usd'],
                           'cost_complete': report['cost_accounting_complete'], 'elapsed_seconds': report['elapsed_seconds'],
                           'nb_accuracy': report['baselines']['naive_bayes']['accuracy'],
                           'created_at': report['created_at'], 'accepted_error_ids': sorted(key for key in accepted if predictions[key]['choice'] != labels[key]),
                           'archive_sha256': {filename: hashlib.sha256((folder/filename).read_bytes()).hexdigest()
                                              for filename in ['predictions.jsonl', 'report.json', 'live-response.json']}}
    return {'protocol_commit': '651006b', 'protocol_sha256': hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),
            'tasks': summaries}


def render(result):
    pct = lambda x: '—' if x is None else f'{100*x:.1f}%'
    tasks = result['tasks']
    lines = ['# Frozen-threshold results on 2,770 new records', '',
             'All primary thresholds, record IDs and rubric hashes were '
             '[committed before inference](https://github.com/alsoleg89/decide/commit/651006b). '
             'These records have no ID or exact-content overlap with the earlier evaluations. '
             'The model and rubric wording are unchanged. No failed predictions were replaced.', '',
             '| Task | N | Threshold / error budget | Accuracy | Accepted errors | Error rate (95% Wilson interval) | Review | Full-review JSON saved |',
             '| --- | ---: | --- | ---: | ---: | --- | ---: | ---: |']
    for name, r in tasks.items():
        ci = r['accepted_error_95ci']
        interval = f'{pct(ci[0])}–{pct(ci[1])}' if ci else '—'
        lines.append(f'| [{name}](results/{name}/report.json) | {r["items"]} | {r["threshold"]:g} / {pct(r["error_budget"])} | '
                     f'{pct(r["accuracy"])} | {r["accepted_errors"]} / {r["accepted"]} | {pct(r["accepted_error_rate"])} ({interval}) | '
                     f'{r["review"]} ({pct(r["review"]/r["items"])}) | {pct(r["full_review_json_reduction"])} |')
    lines += ['', '## Quality, cost and failures', '',
              '| Task | Macro-F1 | Trained Naive Bayes accuracy | Observed error budget met | 95% Wilson upper ≤ budget | Provider failures | Known Jev cost | Batch time |',
              '| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |']
    for name, r in tasks.items():
        cost = ('' if r['cost_complete'] else '≥')+f'${r["known_jev_usd"]:.5f}'
        lines.append(f'| {name} | {pct(r["macro_f1"])} | {pct(r["nb_accuracy"])} | {r["observed_budget_met"]} | '
                     f'{r["wilson_upper_below_budget"]} | {r["failed"]} | {cost} | {r["elapsed_seconds"]:.1f}s |')
    total = sum(r['known_jev_usd'] for r in tasks.values())
    lines += ['', f'**Known Jev usage cost: ${total:.5f}**'+(' (lower bound).' if any(not r['cost_complete'] for r in tasks.values()) else '.'), '',
              'Accuracy counts provider failures as incorrect; all failures require review. Accepted errors '
              'are wrong source-label predictions among automatically accepted decisions. The intervals are '
              'descriptive per-task intervals, not simultaneous coverage across three tasks or guarantees '
              'about future deployment. JSON savings include the live call, summary and every full review '
              'record. They exclude MCP framing, host duplication, agent reasoning and billed-token differences.', '',
              'The three tasks were selected after promising results in the previous study. This follow-up '
              'tests those preselected thresholds on new records from the **same public corpora**, not arbitrary '
              'new domains or production data. Corpus contamination from model pretraining remains possible. '
              'The local Naive Bayes baseline uses labeled source training data; Jev receives no labeled examples.', '',
              'Each task folder contains the original predictions, labels, rubric, dataset hashes, live summary '
              'and complete report. The report also contains an exploratory threshold sweep, which did **not** '
              'select or change the primary threshold. [Machine-readable verified summary](summary.json).', '',
              '## Reproduce the verification', '',
              'Follow the [frozen protocol](README.md) to prepare inputs; the committed live summaries '
              'supply the response measurements, so rerunning paid inference is unnecessary:', '',
              '```sh', 'uv run --locked python benchmarks/multitask/followup/report.py --root /tmp/decide-followup', '```', '',
              'This command is offline: it verifies input hashes, server version, label agreement, routing '
              'and exact serialized-byte accounting before regenerating this summary. No model is called.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    summary = verify(args.root)
    (HERE/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    (HERE/'RESULTS.md').write_text(render(summary), encoding='utf-8')
    print('Verified and summarized 2,770 new decisions at frozen thresholds.')
