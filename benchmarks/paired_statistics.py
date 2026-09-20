"""Post-hoc paired uncertainty; never changes a frozen benchmark gate."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import unique_rows


def mcnemar(baseline_only, candidate_only):
    n = baseline_only + candidate_only
    return min(1., 2 * sum(math.comb(n, k) for k in range(min(baseline_only, candidate_only) + 1)) / 2**n)


def metrics(counts, labels, prediction):
    n = sum(counts.values())
    result = {'accuracy': sum(v for row, v in counts.items() if row[0] == row[prediction]) / n}
    f1 = []
    for label in labels:
        tp = sum(v for row, v in counts.items() if row[0] == label == row[prediction])
        fp = sum(v for row, v in counts.items() if row[0] != label == row[prediction])
        fn = sum(v for row, v in counts.items() if row[0] == label != row[prediction])
        result[label + '_precision'] = tp / (tp + fp) if tp + fp else 0
        result[label + '_recall'] = tp / (tp + fn) if tp + fn else 0
        f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0)
    result['macro_f1'] = sum(f1) / len(f1)
    return result


def percentile(values, fraction):
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def analyze(directory, repetitions=10000, seed=20260920):
    paths = [directory / 'labels.jsonl', directory / 'baseline/decisions.jsonl', directory / 'decide/decisions.jsonl']
    gold, baseline, candidate = map(unique_rows, paths)
    if not gold or gold.keys() != baseline.keys() or gold.keys() != candidate.keys():
        raise ValueError('Statistics require complete same-ID paired outputs')
    labels = sorted({row['expected'] for row in gold.values()})
    if any(row.get('choice') not in labels for outputs in [baseline, candidate] for row in outputs.values()):
        raise ValueError('Invalid predicted class')
    if repetitions < 2:
        raise ValueError('Need at least two bootstrap repetitions')
    pairs = Counter((gold[k]['expected'], baseline[k]['choice'], candidate[k]['choice']) for k in sorted(gold))
    b = sum(v for (g, a, c), v in pairs.items() if a == g and c != g)
    c = sum(v for (g, a, c), v in pairs.items() if a != g and c == g)
    before, after = metrics(pairs, labels, 1), metrics(pairs, labels, 2)
    samples = {key: [] for key in before}
    rng = random.Random(seed)
    population, weights = list(pairs), list(pairs.values())
    for _ in range(repetitions):
        counts = Counter(rng.choices(population, weights=weights, k=len(gold)))
        a, z = metrics(counts, labels, 1), metrics(counts, labels, 2)
        for key in samples:
            samples[key].append(z[key] - a[key])
    return {'items': len(gold), 'method': 'Paired record bootstrap, percentile 95% intervals; exact two-sided McNemar for accuracy.',
            'scope': 'Post-hoc sample uncertainty conditional on these labels and runs. No multiple-testing adjustment, no model-run or dataset-shift uncertainty. A CI spanning zero proves neither equivalence nor noninferiority. Frozen point-estimate gates remain unchanged.',
            'repetitions': repetitions, 'seed': seed,
            'input_sha256': {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'mcnemar': {'baseline_only_correct': b, 'candidate_only_correct': c, 'exact_two_sided_p': mcnemar(b, c)},
            'deltas': {key: {'estimate': after[key] - before[key],
                             'ci95': [percentile(sorted(values), .025), percentile(sorted(values), .975)]}
                       for key, values in samples.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze(args.directory)
    (args.directory / 'statistics.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
