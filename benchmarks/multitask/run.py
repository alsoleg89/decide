"""Run the fixed multi-task evaluation; reuses completed runs and never retries them implicitly."""
import argparse
import asyncio
import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import benchmark_real
from analyze import enrich

TASKS = ['tweet-sentiment', 'tweet-emotion', 'tweet-irony', 'tweet-offensive', 'tweet-hate',
         'banking77', 'ag-news', 'sms-spam', 'apache-logs', 'imdb']


async def run(root, output, selected):
    for name in selected:
        folder = root / name
        stored = folder / 'raw-report.json'
        if stored.exists():
            report = json.loads(stored.read_text())
            if (hashlib.sha256((folder/'items.jsonl').read_bytes()).hexdigest() != report['input_jsonl_sha256']
                or hashlib.sha256((folder/'rubric.json').read_bytes()).hexdigest() != report['rubric_sha256']):
                raise RuntimeError(f'{name}: inputs or rubric changed; use a new source directory for new inference')
            print('Reusing completed inference:', name, flush=True)
        else:
            # Require deliberate intervention after an interrupted paid batch.
            if (folder / '.decide').exists():
                raise RuntimeError(f'{name}: existing unfinished/unreported run; inspect artifacts before rerunning')
            print('Running:', name, flush=True)
            report = await benchmark_real.run(folder, folder / 'rubric.json', folder / 'labels.jsonl')
            stored.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        enriched = enrich(report, folder)
        target = output / name
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(report['results_path'], target / 'predictions.jsonl')
        for filename in ['labels.jsonl', 'rubric.json', 'dataset.json']:
            shutil.copyfile(folder / filename, target / filename)
        enriched.pop('results_path')
        enriched['predictions_file'] = 'predictions.jsonl'
        (target / 'report.json').write_text(json.dumps(enriched, indent=2) + '\n', encoding='utf-8')
        actual = next(row for row in enriched['threshold_sweep'] if row['threshold'] == .8)
        print(json.dumps({'task': name, 'items': enriched['items'], 'accuracy': enriched['quality']['accuracy'],
                          'macro_f1': enriched['quality']['macro_f1'], 'nb_accuracy': enriched['baselines']['naive_bayes']['accuracy'],
                          'review_fraction': actual['review_fraction'], 'accepted_error_rate': actual['accepted_error_rate'],
                          'full_review_json_reduction': enriched['context_bytes_reduction_with_all_reviews'],
                          'jev_usd': enriched['estimated_jev_cost_usd']}), flush=True)
        if enriched['failed']:
            failures = [json.loads(line) for line in (target / 'predictions.jsonl').read_text().split('\n') if line.strip()]
            fatal = {'provider_http_401', 'provider_http_403', 'provider_retry_later'}
            if any(row.get('error') in fatal for row in failures):
                raise RuntimeError(f'{name}: authentication or long cooldown; inspect before continuing')
            print(f'{name}: {enriched["failed"]} failed predictions retained in metrics; continuing other datasets', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tasks', nargs='+', choices=TASKS, default=TASKS)
    args = parser.parse_args()
    if not os.environ.get('TYPESAFE_API_KEY'):
        os.environ['TYPESAFE_API_KEY'] = getpass.getpass('TypeSafe API key: ')
    os.environ.setdefault('DECIDE_MODEL', 'jev-1.13.0')
    asyncio.run(run(args.root.resolve(), args.output.resolve(), args.tasks))
