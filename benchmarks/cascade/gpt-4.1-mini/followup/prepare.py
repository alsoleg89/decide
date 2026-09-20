"""Freeze new records for the selected no-confidence-review policy; no API calls."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import random
import sys

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'benchmarks/multitask'))
from analyze import read_rows
from prepare import encode, write_rows

SEED = 20260924


def prepare(root, previous, ux_source, dev_source):
    if root.exists():
        raise ValueError('Use a new output directory; do not overwrite frozen or paid inputs')
    old_protocol = json.loads((REPO / 'benchmarks/workflows/protocol.json').read_text())
    for key, source in old_protocol['sources'].items():
        kind, name = key.split('/', 1)
        path = (ux_source if kind == 'ux' else dev_source) / 'data' / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
    root.mkdir(parents=True)
    protocol = {'seed': SEED, 'jev_model': 'jev-1.13.0', 'comparison_model': 'gpt-4.1-mini-2025-04-14',
                'server_sha256': hashlib.sha256((REPO / 'decide.py').read_bytes()).hexdigest(),
                'criterion': 'Final accuracy AND macro-F1 at least the full mini baseline, and lower complete classification cost.',
                'policy': 'Threshold 0: accept every valid Jev decision. Only invalid/oversized/provider-error records go to mini. '
                          'No confidence-based review. Same unchanged rubrics and required-ID output schema in both mini arms; batch size 25.',
                'selection': 'These two tasks were chosen after earlier results. New exact-disjoint records, same public corpora; '
                             'not a distribution-shift or pretraining-contamination-free test. No tuning after these results.',
                'sources': old_protocol['sources'], 'tasks': {}}

    def save(name, rows, groups, pool_count):
        old = previous / name
        old_inputs = read_rows(old / 'items.jsonl')
        old_gold = {r['id']: r['expected'] for r in read_rows(old / 'labels.jsonl')}
        old_contents = {encode(r['content']) for r in old_inputs}
        assert not old_contents & {encode(r['content']) for r in rows}
        assert not {r['id'] for r in old_inputs} & {r['id'] for r in rows}
        folder = root / name
        folder.mkdir()
        write_rows(folder / 'items.jsonl', [{'id': r['id'], 'content': r['content']} for r in rows])
        write_rows(folder / 'labels.jsonl', [{'id': r['id'], 'expected': r['expected']} for r in rows])
        # The old evaluation becomes training data for a supplementary local baseline only.
        write_rows(folder / 'train.jsonl', [{**r, 'expected': old_gold[r['id']]} for r in old_inputs])
        rubric = json.loads((old / 'rubric.json').read_text())
        rubric['confidence_threshold'] = 0
        (folder / 'rubric.json').write_text(json.dumps(rubric, indent=2) + '\n')
        dataset = {'sample_items': len(rows), 'pool_items': pool_count,
                   'class_counts': dict(Counter(r['expected'] for r in rows)), 'seed': SEED,
                   'groups': groups, 'baseline_train_items': len(old_inputs),
                   'baseline_note': 'Old evaluation records train the local NB only; neither Jev nor mini receives them.',
                   'previous_input_sha256': hashlib.sha256((old / 'items.jsonl').read_bytes()).hexdigest(),
                   'previous_exact_content_overlap': 0,
                   'files_sha256': {f: hashlib.sha256((folder / f).read_bytes()).hexdigest()
                                    for f in ['items.jsonl', 'labels.jsonl', 'train.jsonl', 'rubric.json']}}
        (folder / 'dataset.json').write_text(json.dumps(dataset, indent=2) + '\n')
        protocol['tasks'][name] = dataset

    previous_reviews = {r['content'] for r in read_rows(previous / 'ux-feature_request/items.jsonl')}
    pool, seen, groups = [], set(previous_reviews), {}
    for path in sorted((ux_source / 'data').glob('*.csv')):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for i, row in enumerate(csv.DictReader(stream), 1):
                text = row['data'].strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                key = f'{path.stem}:{i}'
                groups[key] = path.stem
                pool.append({'id': key, 'content': text, 'expected': 'yes' if row['feature_request'] == '1' else 'no'})
    chosen = random.Random(SEED).sample(pool, 1000)
    save('ux-feature_request', chosen, {r['id']: groups[r['id']] for r in chosen}, len(pool))

    csv.field_size_limit(10_000_000)
    prior_issues = {encode(r['content']) for p in previous.glob('dev-*/items.jsonl') for r in read_rows(p)}
    pool, seen, count = [], set(prior_issues), 0
    with (dev_source / 'data/issues_train.csv').open(encoding='utf-8', newline='') as stream:
        for i, row in enumerate(csv.DictReader(stream), 1):
            if row['repo'] != 'opencv/opencv':
                continue
            count += 1
            content = {'title': row['title'], 'body': row['body']}
            if encode(content) in seen:
                continue
            seen.add(encode(content))
            pool.append({'id': f'nlbse24:train:{i}', 'content': content, 'expected': row['label']})
    assert not prior_issues & {encode(r['content']) for r in pool}
    save('dev-opencv', pool, {r['id']: 'opencv/opencv' for r in pool}, count)
    protocol['tasks']['dev-opencv']['removed_duplicate_contents'] = count - len(pool)
    return protocol


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--previous', type=Path, default=Path('/private/tmp/decide-workflows'))
    parser.add_argument('--ux-source', type=Path, default=Path('/private/tmp/decide-role-ux-source'))
    parser.add_argument('--dev-source', type=Path, default=Path('/private/tmp/decide-role-dev-source'))
    parser.add_argument('--protocol', type=Path, required=True)
    args = parser.parse_args()
    if args.protocol.exists():
        parser.error('Protocol already exists')
    result = prepare(args.root, args.previous, args.ux_source, args.dev_source)
    args.protocol.write_text(json.dumps(result, indent=2) + '\n')
    print({name: task['sample_items'] for name, task in result['tasks'].items()})
