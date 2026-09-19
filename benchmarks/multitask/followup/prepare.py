"""Freeze disjoint follow-up samples from cached public sources; no network or inference."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import re
import sys
import tarfile

PARENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARENT))
from analyze import read_rows

SEED = 20260921
TASKS = {'imdb': (1000, .95, .05), 'ag-news': (1000, .99, .10), 'banking77': (770, .99, .10)}


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def write_rows(path, rows):
    path.write_text(''.join(encode(row) + '\n' for row in rows), encoding='utf-8')


def prepare(previous, root):
    root.mkdir(parents=True, exist_ok=True)
    protocol = {'seed': SEED, 'model': 'jev-1.13.0', 'server_sha256': hashlib.sha256((PARENT.parents[1]/'decide.py').read_bytes()).hexdigest(),
                'selection_report_sha256': hashlib.sha256((PARENT/'threshold-validation/report.json').read_bytes()).hexdigest(),
                'rule': 'Thresholds selected by the previous bounded calibration rule, before follow-up inference. '
                        'IMDb accepted-error budget 5%; AG News and Banking77 10%. No threshold/rubric changes after observing results. '
                        'No repeat of failed decisions. Failures remain in quality and review metrics.',
                'tasks': {}}
    for name, (count, threshold, budget) in TASKS.items():
        old = previous/name
        manifest = json.loads((old/'dataset.json').read_text())
        for filename, info in manifest['sources'].items():
            assert hashlib.sha256((previous/'sources'/filename).read_bytes()).hexdigest() == info['sha256']
        if name == 'imdb':
            extracted = {}
            with tarfile.open(previous/'sources/imdb.tar.gz', mode='r|gz') as archive:
                for member in archive:
                    if re.fullmatch(r'aclImdb/test/(pos|neg)/\d+_\d+\.txt', member.name):
                        extracted[member.name] = archive.extractfile(member).read().decode('utf-8')
            pool = [{'id': 'imdb:' + hashlib.sha256(f'test:{i+1}'.encode()).hexdigest()[:20],
                     'content': extracted[path], 'expected': 'positive' if '/pos/' in path else 'negative'}
                    for i, path in enumerate(sorted(extracted))]
        elif name == 'ag-news':
            mapping = {'1': 'world', '2': 'sports', '3': 'business', '4': 'science_technology'}
            pool = [{'id': f'ag-news-test:{i+1}', 'content': {'title': row[1], 'description': row[2]}, 'expected': mapping[row[0]]}
                    for i, row in enumerate(csv.reader(io.StringIO((previous/'sources/news-test.csv').read_text(encoding='utf-8'))))]
        else:
            pool = [{'id': f'banking77:test:{i+1}', 'content': row['text'], 'expected': row['category']}
                    for i, row in enumerate(csv.DictReader(io.StringIO((previous/'sources/bank-test.csv').read_text(encoding='utf-8'))))]
        old_ids = {row['id'] for row in read_rows(old/'items.jsonl')}
        if name == 'ag-news':
            old_ids.update(row['id'] for row in read_rows(PARENT.parent/'ag-news-400/labels.jsonl'))
        old_content = {encode(row['content']) for row in pool if row['id'] in old_ids}
        assert old_ids <= {row['id'] for row in pool}
        seen, eligible = set(old_content), []
        for row in pool:
            content = encode(row['content'])
            if row['id'] not in old_ids and content not in seen:
                eligible.append(row)
                seen.add(content)
        rng = random.Random(SEED)
        if name == 'banking77':
            selected = []
            for label in sorted({row['expected'] for row in eligible}):
                selected.extend(rng.sample([row for row in eligible if row['expected'] == label], 10))
            rng.shuffle(selected)
        else:
            selected = rng.sample(eligible, count)
        assert len(selected) == count and not old_ids & {row['id'] for row in selected}
        assert not old_content & {encode(row['content']) for row in selected}
        folder = root/name
        if (folder/'.decide').exists() or (folder/'raw-report.json').exists():
            raise RuntimeError('Refusing to overwrite inputs used by an existing paid run')
        folder.mkdir(exist_ok=True)
        write_rows(folder/'items.jsonl', [{'id': row['id'], 'content': row['content']} for row in selected])
        write_rows(folder/'labels.jsonl', [{'id': row['id'], 'expected': row['expected']} for row in selected])
        new_content = {encode(row['content']) for row in selected}
        train = [row for row in read_rows(old/'train.jsonl') if encode(row['content']) not in new_content]
        write_rows(folder/'train.jsonl', train)
        rubric = json.loads((old/'rubric.json').read_text())
        rubric['confidence_threshold'] = threshold
        (folder/'rubric.json').write_text(json.dumps(rubric, indent=2)+'\n', encoding='utf-8')
        dataset = {**manifest, 'seed': SEED, 'sample_items': count, 'test_pool_items': len(eligible),
                   'baseline_train_items': len(train), 'class_counts': dict(Counter(row['expected'] for row in selected)),
                   'selection': '10 per class, sorted labels, then shuffle' if name == 'banking77' else f'uniform {count} from eligible unique texts',
                   'previously_evaluated_ids_excluded': len(old_ids), 'previous_content_overlap': 0,
                   'notes': 'Follow-up on previously unqueried IDs and exact contents from the same public test corpus. '
                            'Not a distribution-shift test or evidence of absence from pretraining. '
                            'Baseline uses previous source training data with new evaluation duplicates removed.',
                   'files_sha256': {filename: hashlib.sha256((folder/filename).read_bytes()).hexdigest()
                                    for filename in ['items.jsonl', 'labels.jsonl', 'train.jsonl', 'rubric.json']}}
        (folder/'dataset.json').write_text(json.dumps(dataset, indent=2)+'\n', encoding='utf-8')
        protocol['tasks'][name] = {'items': count, 'threshold': threshold, 'accepted_error_budget': budget,
                                   'dataset': dataset, 'sample_ids': [row['id'] for row in selected]}
        print('Frozen', name, count, 'new records; threshold', threshold, 'error budget', budget, flush=True)
    return protocol


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', required=True, type=Path)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--protocol', required=True, type=Path)
    args = parser.parse_args()
    if args.protocol.exists():
        parser.error('Protocol already exists; preserve the pre-inference record')
    protocol = prepare(args.previous, args.root)
    args.protocol.write_text(json.dumps(protocol, indent=2)+'\n', encoding='utf-8')
