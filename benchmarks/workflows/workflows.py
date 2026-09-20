"""Role-based live evaluations. Reuses the existing MCP runner and quality metrics."""
import argparse
import asyncio
from collections import Counter
import csv
import getpass
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'benchmarks/multitask'))
sys.path.insert(0, str(REPO))
from analyze import classification, error_interval
from prepare import encode, write_rows
from run import run
from evaluate import risk_coverage, unique_rows

SEED = 20260922
THRESHOLD = .95
SOURCES = {
    'ux': ('Jl-wei/APIA2022-French-user-reviews-classification-dataset', 'c8fd015f526d9c93d4726122ae845296d46fb5a8'),
    'dev': ('nlbse2024/issue-report-classification', '2927bc67eb42db8affd16eaf3e5a6d74f3063961'),
}
UX = {
    'bug_report': ('Find reported product failures for the engineering backlog.',
                   'Reports an app malfunction experienced by the user: data loss, crash, connection error, or a feature not working.'),
    'feature_request': ('Find feature requests for product discovery.',
                        'Requests a new or changed function, content, interface, or capability in the app.'),
    'user_experience': ('Find concrete usage experiences for UX research synthesis.',
                        'Describes experience with a specific app function, including how a function is helpful or used.'),
    'rating': ('Separate general praise and criticism from detailed product feedback.',
               'Expresses an overall evaluation of the app, including praise, criticism, or dissuading others from using it.'),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(ux_source, dev_source, root, protocol_path):
    if protocol_path.exists() or root.exists():
        raise ValueError('Use a new root and protocol; never overwrite a frozen or paid run')
    csv.field_size_limit(10_000_000)
    source_files = {}
    for kind, directory in [('ux', ux_source), ('dev', dev_source)]:
        repo, commit = SOURCES[kind]
        actual = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != commit:
            raise ValueError(f'{kind}: checkout must be pinned to {commit}')
        for path in sorted((directory / 'data').glob('*.csv')):
            # Verify working files against the pinned commit, not just HEAD.
            original = subprocess.check_output(['git', '-C', str(directory), 'show', f'{commit}:data/{path.name}'])
            assert hashlib.sha256(original).hexdigest() == digest(path)
            source_files[f'{kind}/{path.name}'] = {'sha256': digest(path), 'repo': repo, 'commit': commit}
    root.mkdir(parents=True)
    protocol = {'seed': SEED, 'model': 'jev-1.13.0', 'threshold': THRESHOLD,
                'server_sha256': digest(REPO / 'decide.py'), 'sources': source_files,
                'rule': 'Fixed threshold 0.95 for every task, chosen before inference; no calibrated error guarantee. '
                        'No rubric tuning or retrying failed records after seeing results. Sweeps are exploratory. '
                        'Four binary UX decisions per review preserve multilabel annotations. Labels and star scores are never model inputs.',
                'tasks': {}}

    def save(name, rows, train, question, criteria, role, action):
        folder = root / name
        folder.mkdir()
        test_contents = {encode(row['content']) for row in rows}
        train = [row for row in train if encode(row['content']) not in test_contents]
        write_rows(folder / 'items.jsonl', [{'id': r['id'], 'content': r['content']} for r in rows])
        write_rows(folder / 'labels.jsonl', [{'id': r['id'], 'expected': r['expected']} for r in rows])
        write_rows(folder / 'train.jsonl', train)
        write_json(folder / 'rubric.json', {'question': question, 'criteria': criteria,
                   'source': {'kind': 'jsonl', 'paths': ['items.jsonl']},
                   'confidence_threshold': THRESHOLD, 'review_limit': 0, 'concurrency': 4})
        dataset = {'role': role, 'action': action, 'sample_items': len(rows), 'baseline_train_items': len(train),
                   'class_counts': dict(Counter(r['expected'] for r in rows)),
                   'groups': {r['id']: r['group'] for r in rows},
                   'sources': source_files, 'seed': SEED,
                   'files_sha256': {f: digest(folder / f) for f in ['items.jsonl', 'labels.jsonl', 'train.jsonl', 'rubric.json']}}
        write_json(folder / 'dataset.json', dataset)
        protocol['tasks'][name] = dataset

    pool, seen, duplicates = [], set(), 0
    for path in sorted((ux_source / 'data').glob('*.csv')):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for index, row in enumerate(csv.DictReader(stream), 1):
                text = row['data'].strip()
                if not text or text in seen:
                    duplicates += 1
                    continue
                seen.add(text)
                assert all(row[label] in {'0', '1'} for label in UX)
                pool.append({'id': f'{path.stem}:{index}', 'content': text, 'group': path.stem, 'labels': row})
    chosen = random.Random(SEED).sample(pool, 500)
    chosen_ids = {r['id'] for r in chosen}
    protocol['ux_selection'] = {'source_rows': 6000, 'eligible_unique_nonempty_texts': len(pool),
                                 'removed_empty_or_duplicate_texts': duplicates,
                                 'selection': 'Uniform 500 from globally deduplicated original French texts; same reviews for all four axes.'}
    for label, (action, definition) in UX.items():
        convert = lambda r: {k: r[k] for k in ['id', 'content', 'group']} | {'expected': 'yes' if r['labels'][label] == '1' else 'no'}
        save('ux-' + label, [convert(r) for r in chosen], [convert(r) for r in pool if r['id'] not in chosen_ids],
             f'Does this French app review contain the following type of feedback: {label.replace("_", " ")}? '
             'A review can contain several types; evaluate only this type, independently of the others.',
             {'yes': definition, 'no': 'Does not contain this type of feedback.'}, 'UX / product', action)

    splits = {}
    for split in ['test', 'train']:
        with (dev_source / f'data/issues_{split}.csv').open(encoding='utf-8', newline='') as stream:
            splits[split] = [{'id': f'nlbse24:{split}:{i}', 'group': r['repo'], 'expected': r['label'],
                              'content': {'title': r['title'], 'body': r['body']}}
                             for i, r in enumerate(csv.DictReader(stream), 1)]
    all_test_contents = {encode(r['content']) for r in splits['test']}
    train = [r for r in splits['train'] if encode(r['content']) not in all_test_contents]
    protocol['dev_selection'] = {'selection': 'Entire official 1500-record test split, unchanged; one task per repository.',
                                 'train_exact_test_duplicates_removed': len(splits['train']) - len(train),
                                 'test_duplicate_contents': len(splits['test']) - len(all_test_contents)}
    for project in sorted({r['group'] for r in splits['test']}):
        save('dev-' + project.split('/')[-1], [r for r in splits['test'] if r['group'] == project],
             [r for r in train if r['group'] == project],
             'Which issue type best fits the title and body of this GitHub issue?',
             {'bug': 'Reports existing software behaving incorrectly or failing.',
              'feature': 'Requests a new capability or improvement to existing behavior.',
              'question': 'Asks for explanation, usage help, or troubleshooting assistance.'},
             'Developer', f'Triage the {project} issue backlog into bugs, feature requests, and questions.')
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(protocol_path, protocol)
    print(json.dumps({'tasks': len(protocol['tasks']), 'decisions': sum(t['sample_items'] for t in protocol['tasks'].values())}))


async def live(root, output, protocol_path):
    protocol = json.loads(protocol_path.read_text())
    assert digest(REPO / 'decide.py') == protocol['server_sha256']
    for name, task in protocol['tasks'].items():
        for file, sha in task['files_sha256'].items():
            assert digest(root / name / file) == sha, (name, file)
    if not os.environ.get('TYPESAFE_API_KEY'):
        os.environ['TYPESAFE_API_KEY'] = getpass.getpass('TypeSafe API key: ')
    os.environ['DECIDE_MODEL'] = protocol['model']
    await run(root, output, list(protocol['tasks']))
    for name in protocol['tasks']:
        raw = json.loads((root / name / 'raw-report.json').read_text())
        write_json(output / name / 'live-response.json', json.loads((Path(raw['results_path']).parent / 'summary.json').read_text()))


def report(output, protocol_path, root=None):
    protocol = json.loads(protocol_path.read_text())
    tasks, ux_predictions, ux_labels = {}, {}, {}
    dev_records, dev_labels = {}, {}
    dev_inline_bytes = dev_pipeline_bytes = 0
    for name, task in protocol['tasks'].items():
        folder = output / name
        stored = json.loads((folder / 'report.json').read_text())
        records, labels = unique_rows(folder / 'predictions.jsonl'), unique_rows(folder / 'labels.jsonl')
        assert digest(folder / 'labels.jsonl') == task['files_sha256']['labels.jsonl']
        assert digest(folder / 'rubric.json') == task['files_sha256']['rubric.json']
        assert stored['server_source_sha256'] == protocol['server_sha256']
        assert stored['input_jsonl_sha256'] == task['files_sha256']['items.jsonl']
        assert stored['models'].keys() <= {protocol['model'], 'unavailable'}
        if root is not None:
            for file, sha in task['files_sha256'].items():
                assert digest(root / name / file) == sha, (name, file)
            inputs = list(unique_rows(root / name / 'items.jsonl').values())
            assert {r['id'] for r in inputs} == records.keys()
            inline = {**stored['rubric'], 'items': inputs}
            del inline['source']
            live_response = json.loads((folder / 'live-response.json').read_text())
            inline_bytes = len(encode(inline).encode())
            response_bytes = len(encode(stored['rubric']).encode()) + len(encode(live_response).encode())
            review_bytes = sum(len(encode(r).encode()) + 1 for r in inputs if records[r['id']]['status'] == 'review')
            assert inline_bytes == stored['inline_input_bytes']
            assert response_bytes == stored['source_call_and_result_bytes']
            assert review_bytes == stored['all_review_records_bytes']
            assert 1 - (response_bytes + review_bytes) / inline_bytes == stored['context_bytes_reduction_with_all_reviews']
        risk = risk_coverage(records, labels, THRESHOLD)
        accepted = {k: r for k, r in records.items() if r['status'] == 'accepted'}
        assert len(accepted) == risk['accepted'] == stored['accepted']
        assert all('error' not in r and r['confidence'] >= THRESHOLD for r in accepted.values())
        classes = list(stored['rubric']['criteria'])
        quality = classification([labels[k]['expected'] for k in records], [r.get('choice') for r in records.values()], classes)
        assert quality == stored['quality']
        primary = {'action': task['action'], 'quality': quality, **risk,
                   'accepted_error_95ci': error_interval(risk['accepted_errors'], risk['accepted']),
                   'full_review_json_saved': stored['context_bytes_reduction_with_all_reviews'],
                   'known_jev_usd': stored['estimated_jev_cost_usd'], 'cost_complete': stored['cost_accounting_complete'],
                   'elapsed_seconds': stored['elapsed_seconds'], 'nb_accuracy': stored['baselines']['naive_bayes']['accuracy']}
        primary['accepted_confusion'] = {label: dict(Counter(r['choice'] for k, r in accepted.items() if labels[k]['expected'] == label)) for label in classes}
        primary['groups'] = {}
        for group in sorted(set(task['groups'].values())):
            keys = [k for k in records if task['groups'][k] == group]
            primary['groups'][group] = risk_coverage({k: records[k] for k in keys}, {k: labels[k] for k in keys}, THRESHOLD)
        if name.startswith('ux-'):
            primary['accepted_false_negatives'] = sum(labels[k]['expected'] == 'yes' and r['choice'] == 'no' for k, r in accepted.items())
            primary['accepted_false_positives'] = sum(labels[k]['expected'] == 'no' and r['choice'] == 'yes' for k, r in accepted.items())
            ux_predictions[name], ux_labels[name] = records, labels
        else:
            assert not dev_records.keys() & records.keys()
            dev_records.update(records)
            dev_labels.update(labels)
            dev_inline_bytes += stored['inline_input_bytes']
            dev_pipeline_bytes += stored['source_call_and_result_bytes'] + stored['all_review_records_bytes']
        tasks[name] = primary
    keys = next(iter(ux_predictions.values())).keys()
    assert all(rows.keys() == keys for rows in ux_predictions.values())
    all_accepted = [k for k in keys if all(rows[k]['status'] == 'accepted' for rows in ux_predictions.values())]
    exact = lambda k: all(ux_predictions[n][k].get('choice') == ux_labels[n][k]['expected'] for n in ux_predictions)
    ux = {'unique_reviews': len(keys), 'binary_decisions': sum(len(v) for v in ux_predictions.values()),
          'four_label_exact_match_accuracy': sum(exact(k) for k in keys) / len(keys),
          'all_four_accepted_reviews': len(all_accepted), 'reviews_needing_at_least_one_check': len(keys) - len(all_accepted),
          'errors_among_all_four_accepted_reviews': sum(not exact(k) for k in all_accepted),
          'note': 'Four independent binary calls per review; costs include all four. Per-axis byte savings are not combined workflow savings.'}
    developer = {**risk_coverage(dev_records, dev_labels, THRESHOLD),
                 'quality': classification([dev_labels[k]['expected'] for k in dev_records],
                                            [r.get('choice') for r in dev_records.values()], ['bug', 'feature', 'question']),
                 'mean_repository_macro_f1': sum(t['quality']['macro_f1'] for n, t in tasks.items() if n.startswith('dev-')) / 5,
                 'full_review_json_saved': 1 - dev_pipeline_bytes / dev_inline_bytes,
                 'byte_definition': 'Ratio of summed measured bytes across the five per-repository calls; not an average of percentages.'}
    result = {'status': 'measured_live', 'threshold': THRESHOLD, 'tasks': tasks, 'ux_multilabel': ux, 'developer': developer,
              'known_jev_usd': sum(t['known_jev_usd'] for t in tasks.values()),
              'cost_complete': all(t['cost_complete'] for t in tasks.values())}
    write_json(output.parent / 'summary.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'run', 'report'])
    parser.add_argument('--root', type=Path, default=Path('/private/tmp/decide-workflows'))
    parser.add_argument('--ux-source', type=Path, default=Path('/private/tmp/decide-role-ux-source'))
    parser.add_argument('--dev-source', type=Path, default=Path('/private/tmp/decide-role-dev-source'))
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'results')
    parser.add_argument('--protocol', type=Path, default=Path(__file__).parent / 'protocol.json')
    parser.add_argument('--verify-inputs', action='store_true', help='Also verify source hashes and full JSON byte accounting using --root')
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.ux_source, args.dev_source, args.root, args.protocol)
    elif args.mode == 'run':
        asyncio.run(live(args.root.resolve(), args.output, args.protocol))
    else:
        report(args.output, args.protocol, args.root if args.verify_inputs else None)
