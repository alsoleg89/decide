"""Freeze the two reused datasets before any paid Luna calls."""
import argparse
import json
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
import benchmark_agent as agent


def prepare(destination, ux_source, dev_source):
    destination.mkdir(parents=True, exist_ok=False)
    prices = json.loads((Path(__file__).parent / 'prices.json').read_text())
    for name, source, count in [('ux-feature_request', ux_source, 1000), ('dev-opencv', dev_source, 300)]:
        root = destination / name / 'inputs'
        root.mkdir(parents=True)
        for filename in ['items.jsonl', 'labels.jsonl', 'rubric.json']:
            shutil.copyfile(source / filename, root / filename)
        rows = agent.unique_rows(root / 'items.jsonl')
        assert len(rows) == count
        rubric = json.loads((root / 'rubric.json').read_text())
        assert rubric['confidence_threshold'] == 0
        assert rubric.get('confidence_thresholds', {}) == ({'no': .9} if name.startswith('ux') else {})
        directory = root.parent / 'run'
        protocol = agent.prepare(root, directory, model='gpt-5.6-luna', reasoning_effort='none', prices=prices)
        protocol.update(
            scope='Guided API tool loop on reused published evaluation records; not a new holdout or a native Codex session.',
            task=name,
            arm_order=['baseline', 'decide'] if name.startswith('ux') else ['decide', 'baseline'],
            quality_labels=['yes'] if name.startswith('ux') else list(rubric['criteria']),
            criterion='Both same-ID artifacts complete; accuracy, macro-F1 and precision/recall for each quality_label no worse than Luna alone; complete total inference cost lower.',
            policy_selection='Routing reused unchanged from mini studies; no threshold or reasoning search against Luna outcomes.',
            repetitions=1,
            model_reference='https://developers.openai.com/api/docs/models/gpt-5.6-luna',
        )
        agent.save(directory / 'protocol.json', protocol)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--ux-source', type=Path, required=True)
    parser.add_argument('--dev-source', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.destination, args.ux_source, args.dev_source)
