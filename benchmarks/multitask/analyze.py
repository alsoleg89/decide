"""Classification, review-risk and inexpensive baseline metrics for recorded runs."""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import time


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').split('\n') if line.strip()]


def text_content(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def tokens(value):
    return re.findall(r'\b\w{2,}\b', text_content(value).lower())


def classification(expected, predicted, classes):
    assert len(expected) == len(predicted) and expected
    confusion = {label: Counter() for label in classes}
    for gold, guess in zip(expected, predicted):
        confusion[gold][guess or '__failed__'] += 1
    per_class = {}
    for label in classes:
        tp = confusion[label][label]
        support = sum(confusion[label].values())
        predicted_count = sum(row[label] for row in confusion.values())
        precision = tp / predicted_count if predicted_count else 0
        recall = tp / support if support else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        per_class[label] = {'support': support, 'precision': precision, 'recall': recall, 'f1': f1}
    return {'accuracy': sum(a == b for a, b in zip(expected, predicted)) / len(expected),
            'macro_f1': sum(row['f1'] for row in per_class.values()) / len(classes),
            'per_class': per_class, 'confusion': {key: dict(value) for key, value in confusion.items()}}


def error_interval(errors, count):
    """Two-sided 95% Wilson interval; descriptive, not a future-quality guarantee."""
    if not count:
        return None
    z = 1.959963984540054
    p, denominator = errors / count, 1 + z * z / count
    middle = (p + z * z / (2 * count)) / denominator
    spread = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [max(0, middle - spread), min(1, middle + spread)]


def baselines(train, inputs, expected, classes, name):
    """Multinomial NB, alpha=1, word counts; trained only on the source train split."""
    started = time.monotonic()
    documents = Counter(row['expected'] for row in train)
    majority = max(sorted(classes), key=lambda label: documents[label])
    counts = {label: Counter() for label in classes}
    for row in train:
        counts[row['expected']].update(tokens(row['content']))
    vocabulary = set().union(*(set(counter) for counter in counts.values()))
    totals = {label: sum(counter.values()) + len(vocabulary) for label, counter in counts.items()}
    priors = {label: math.log((documents[label] + 1) / (len(train) + len(classes))) for label in classes}
    trained = time.monotonic()
    predictions = []
    for row in inputs:
        bag = Counter(token for token in tokens(row['content']) if token in vocabulary)
        scores = {label: priors[label] + sum(amount * math.log((counts[label][token] + 1) / totals[label])
                                           for token, amount in bag.items()) for label in classes}
        predictions.append(max(sorted(classes), key=lambda label: scores[label]))
    result = {'majority_label': majority, 'majority': classification(expected, [majority] * len(inputs), classes),
              'naive_bayes': classification(expected, predictions, classes),
              'train_items': len(train), 'vocabulary_size': len(vocabulary),
              'train_seconds': round(trained - started, 3),
              'predict_seconds': round(time.monotonic() - trained, 3),
              'definition': 'Multinomial Naive Bayes; Laplace alpha=1; lowercase Unicode word tokens of length >=2; raw counts, no tuning. Training examples are never sent to Jev.'}
    if name == 'apache-logs':
        regex = [re.search(r'\[(notice|error|warn|info|debug|crit|alert|emerg)\]', row['content']).group(1) for row in inputs]
        result['regex'] = classification(expected, regex, classes)
    return result


def enrich(report, folder):
    inputs = read_rows(folder / 'items.jsonl')
    labels = {row['id']: row['expected'] for row in read_rows(folder / 'labels.jsonl')}
    records = {row['id']: row for row in read_rows(Path(report['results_path']))}
    assert records.keys() == labels.keys() == {row['id'] for row in inputs}
    expected = [labels[row['id']] for row in inputs]
    classes = list(report['rubric']['criteria'])
    report['quality'] = classification(expected, [records[row['id']].get('choice') for row in inputs], classes)
    report['baselines'] = baselines(read_rows(folder / 'train.jsonl'), inputs, expected, classes, folder.name)
    for row in report['threshold_sweep']:
        row['accepted_error_95ci'] = error_interval(row['accepted_errors'], row['accepted'])
    bins = []
    for low, high in [(0, .5), (.5, .8), (.8, .9), (.9, .95), (.95, .99), (.99, 1.0), (1.0, 1.0)]:
        members = [row for row in records.values() if 'confidence' in row and
                   (row['confidence'] == 1 if low == high == 1 else low <= row['confidence'] < high)]
        wrong = sum(row.get('choice') != labels[row['id']] for row in members)
        bins.append({'low': low, 'high_exclusive': high, 'exact_one': low == high == 1,
                     'items': len(members), 'errors': wrong, 'error_rate': wrong / len(members) if members else None})
    report['observed_error_by_confidence_bin'] = bins
    report['estimated_jev_cost_usd'] = report['provider_usage']['input_tokens'] * .042 / 1_000_000
    report['cost_accounting_complete'] = report['provider_usage']['complete']
    report['pricing_source'] = 'https://docs.typesafe.ai/models'
    report['pricing_note'] = 'Jev 1.13.0: $0.042/M input tokens, free output. Estimate excludes agent review and reasoning. When cost_accounting_complete is false, known successful usage is only a lower bound.'
    report['dataset'] = json.loads((folder / 'dataset.json').read_text())
    return report
