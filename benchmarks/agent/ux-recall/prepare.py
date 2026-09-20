"""Select a label cutoff on old responses, then freeze exact-disjoint UX records. No API calls."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import benchmark_agent as agent
from benchmark_cascade import classification, parse
from evaluate import unique_rows

SEED = 20260925
CUTOFFS = [0, .8, .9, .95, .99, 1]


def metrics(gold, guesses):
    measured = classification([gold[key]['expected'] for key in gold], [guesses[key] for key in gold], ['yes', 'no'])
    positive = measured['per_class']['yes']
    return {'accuracy': measured['accuracy'], 'macro_f1': measured['macro_f1'],
            'feature_precision': positive['precision'], 'feature_recall': positive['recall']}


def select():
    result = {}
    sources = [
        ('original-500', 'benchmarks/workflows/results/ux-feature_request',
         'benchmarks/cascade/gpt-4.1-mini/results/ux-feature_request'),
        ('previous-1000', 'benchmarks/cascade/gpt-4.1-mini/followup/jev/ux-feature_request',
         'benchmarks/cascade/gpt-4.1-mini/followup/results/ux-feature_request')]
    eligible = set(CUTOFFS)
    for name, jev_path, api_path in sources:
        jdir, adir = REPO / jev_path, REPO / api_path
        labels, jev = unique_rows(jdir / 'labels.jsonl'), unique_rows(jdir / 'predictions.jsonl')
        plan = json.loads((adir / 'plan.json').read_text())
        mini = {}
        for line in (adir / 'responses.jsonl').read_text().split('\n'):
            if not line:
                continue
            response = json.loads(line)
            call = plan['calls'][response['index']]
            if call['arm'] == 'baseline':
                mini.update(parse(response['body'], call['ids'], ['yes', 'no']))
        baseline = metrics(labels, mini)
        candidates = []
        for cutoff in CUTOFFS:
            review = {key for key, row in jev.items() if row.get('error') or
                      row['choice'] == 'no' and row['confidence'] < cutoff}
            guessed = {key: mini[key] if key in review else row['choice'] for key, row in jev.items()}
            measured = metrics(labels, guessed)
            passed = all(measured[key] >= baseline[key] for key in baseline)
            if not passed:
                eligible.discard(cutoff)
            candidates.append({'no_cutoff': cutoff, 'review_items': len(review), 'metrics': measured, 'all_four_not_worse': passed})
        result[name] = {'baseline': baseline, 'candidates': candidates,
                        'source_sha256': {str(p.relative_to(REPO)): agent.sha(p) for p in
                           [jdir / 'labels.jsonl', jdir / 'predictions.jsonl', adir / 'plan.json', adir / 'responses.jsonl']}}
    if not eligible:
        raise ValueError('No candidate passes on both calibration sets')
    return {'selected_no_cutoff': min(eligible), 'cohorts': result,
            'selection': 'Smallest cutoff passing accuracy, macro-F1, feature precision AND recall on both old cohorts. '
                         'Nested review sets minimize review count among this grid, not a global cost proof. '
                         'Mini baseline outputs proxy review here; only the new live loop measures actual review behavior/cost.'}


def prepare(root, ux_source, previous, followup):
    selection = select()
    if root.exists():
        raise ValueError('Use a new root')
    source_manifest = json.loads((REPO / 'benchmarks/workflows/protocol.json').read_text())['sources']
    for key, value in source_manifest.items():
        if key.startswith('ux/'):
            assert agent.sha(ux_source / 'data' / key.split('/', 1)[1]) == value['sha256']
    prior_paths = [previous / 'ux-feature_request/items.jsonl', followup / 'ux-feature_request/items.jsonl']
    old_rows = [row for path in prior_paths for row in unique_rows(path).values()]
    old_ids, old_text = {r['id'] for r in old_rows}, {r['content'] for r in old_rows}
    seen, pool = set(), []
    for path in sorted((ux_source / 'data').glob('*.csv')):
        with path.open(encoding='utf-8-sig', newline='') as file:
            for i, row in enumerate(csv.DictReader(file), 1):
                text = row['data'].strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                key = f'{path.stem}:{i}'
                if key not in old_ids and text not in old_text:
                    pool.append({'id': key, 'content': text, 'expected': 'yes' if row['feature_request'] == '1' else 'no'})
    chosen = random.Random(SEED).sample(pool, 1000)
    inputs = root / 'inputs'
    inputs.mkdir(parents=True)
    for filename, fields in [('items.jsonl', ['id', 'content']), ('labels.jsonl', ['id', 'expected'])]:
        (inputs / filename).write_text(''.join(agent.encode({key: row[key] for key in fields}) + '\n' for row in chosen))
    rubric = json.loads((followup / 'ux-feature_request/rubric.json').read_text())
    rubric.update(confidence_threshold=0, confidence_thresholds={'no': selection['selected_no_cutoff']})
    agent.save(inputs / 'rubric.json', rubric)
    directory = root / 'run'
    protocol = agent.prepare(inputs, directory)
    protocol.update(scope='Guided real-MCP tool loop on 1000 exact-disjoint UX records; same public corpus, not native Codex/Claude.',
                    criterion='Complete artifacts; accuracy, macro-F1, feature precision AND feature recall at least mini; lower complete cost.',
                    sample={'seed': SEED, 'remaining_pool': len(pool), 'items': len(chosen), 'prior_records': len(old_rows),
                            'exact_id_overlap': 0, 'exact_content_overlap': 0,
                            'prior_inputs_sha256': {name: agent.sha(p) for name, p in zip(['original-500', 'previous-1000'], prior_paths)},
                            'sources': {key: value for key, value in source_manifest.items() if key.startswith('ux/')}},
                    policy_selection=selection, preparer_sha256=agent.sha(Path(__file__)))
    agent.save(directory / 'protocol.json', protocol)
    print('Frozen', len(chosen), 'new records; no cutoff', selection['selected_no_cutoff'], 'from pool', len(pool))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--ux-source', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--followup', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.root, args.ux_source, args.previous, args.followup)
