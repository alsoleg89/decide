"""Retrospective split validation of archived decisions. No network or model calls."""
import argparse
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evaluate import risk_coverage, unique_rows
from analyze import error_interval

HERE = Path(__file__).resolve().parent
THRESHOLDS = (0, .5, .8, .9, .95, .99, 1)
BUDGETS = (.01, .05, .10)
SEED = 'decide-threshold-validation-v1'
ALPHA = .05 / len(THRESHOLDS)


@lru_cache(maxsize=None)
def upper_error(errors, count):
    """One-sided Clopper-Pearson upper bound, Bonferroni over seven candidates."""
    if not 0 <= errors <= count:
        raise ValueError('Expected 0 <= errors <= count')
    if not count:
        return None
    if errors == count:
        return 1.0
    if not errors:
        return -math.expm1(math.log(ALPHA) / count)
    coefficients = [math.lgamma(count + 1) - math.lgamma(k + 1) - math.lgamma(count - k + 1)
                    for k in range(errors + 1)]
    low, high = errors / count, 1.0
    for _ in range(60):
        p = (low + high) / 2
        terms = [c + k * math.log(p) + (count - k) * math.log1p(-p)
                 for k, c in enumerate(coefficients)]
        maximum = max(terms)
        log_cdf = maximum + math.log(sum(math.exp(t - maximum) for t in terms))
        if log_cdf > math.log(ALPHA):
            low = p
        else:
            high = p
    return high


def measure(records, labels, inputs, threshold):
    # A missing threshold means abstain on everything, including confidence=1.
    provider_failures = sum('error' in row for row in records.values())
    if threshold is None:
        records = {key: {'error': 'policy_abstained'} for key in records}
    result = risk_coverage(records, labels, threshold if threshold is not None else 0, inputs)
    result['threshold'] = threshold
    result['failed'] = provider_failures
    result['accepted_error_95ci'] = error_interval(result['accepted_errors'], result['accepted'])
    result['selection_upper_error_bound'] = upper_error(result['accepted_errors'], result['accepted'])
    return result


def choose(candidates, budget, method):
    key = 'accepted_error_rate' if method == 'empirical' else 'selection_upper_error_bound'
    eligible = [row for row in candidates if row[key] is not None and row[key] <= budget]
    # Lower thresholds include all higher-threshold accepted rows. Maximize input bytes withheld.
    return max(eligible, key=lambda row: (row['input_bytes_kept_out_of_review_fraction'],
                                         -row['threshold']))['threshold'] if eligible else None


def evaluate(root):
    reports = {}
    for folder in sorted((HERE / 'results').iterdir()):
        if not folder.is_dir():
            continue
        manifest = json.loads((folder / 'dataset.json').read_text())
        source = root / folder.name / 'items.jsonl'
        assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest['files_sha256']['items.jsonl']
        assert hashlib.sha256((folder/'labels.jsonl').read_bytes()).hexdigest() == manifest['files_sha256']['labels.jsonl']
        records, labels, inputs = (unique_rows(path) for path in
                                  (folder/'predictions.jsonl', folder/'labels.jsonl', source))
        assert records.keys() == labels.keys() == inputs.keys()
        # Deduplicate before splitting, using no labels/confidence; exact duplicate text is one unit.
        groups = {}
        for key in sorted(inputs):
            content = json.dumps(inputs[key]['content'], ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            digest = hashlib.sha256(content.encode()).hexdigest()
            groups.setdefault(digest, []).append(key)
        partitions = [[], []]
        for digest, keys in sorted(groups.items()):
            side = int(hashlib.sha256((SEED + ':' + digest).encode()).hexdigest(), 16) % 2
            partitions[side].append(keys[0])
        calibration, holdout = partitions
        assert calibration and holdout and not set(calibration) & set(holdout)
        def subset(ids, threshold):
            return measure(*({key: rows[key] for key in ids} for rows in (records, labels, inputs)), threshold)
        candidates = [subset(calibration, threshold) for threshold in THRESHOLDS]
        policies = []
        for budget in BUDGETS:
            for method in ('empirical', 'bounded'):
                selected = choose(candidates, budget, method)
                measured = subset(holdout, selected)
                observed = measured['accepted_error_rate']
                policies.append({'error_budget': budget, 'method': method, 'selected_threshold': selected,
                                 'calibration': subset(calibration, selected), 'holdout': measured,
                                 'holdout_observed_budget_met': observed <= budget if observed is not None else None})
        reports[folder.name] = {
            'original_records': len(inputs), 'unique_contents': len(groups),
            'duplicate_records_excluded': len(inputs) - len(groups),
            'conflicting_label_groups': sum(len({labels[key]['expected'] for key in keys}) > 1 for keys in groups.values()),
            'duplicate_groups': [keys for keys in groups.values() if len(keys) > 1],
            'calibration_ids': calibration, 'holdout_ids': holdout,
            'source_sha256': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in
                              (source, folder/'predictions.jsonl', folder/'labels.jsonl')},
            'calibration_candidates': candidates, 'policies': policies,
            'holdout_fixed_08': subset(holdout, .8)}
    assert len(reports) == 10
    return {'protocol': {'seed': SEED, 'thresholds': THRESHOLDS, 'error_budgets': BUDGETS,
                         'selection_alpha_per_threshold': ALPHA, 'paid_calls': 0,
                         'design': 'Retrospective deterministic content-deduplicated hash split; approximately half per side. '
                                   'No holdout labels passed to selection. Fixed thresholds and budgets; no seed search. '
                                   'Parent dataset results had already been inspected: not a prospective blind test.',
                         'objective': 'Maximize calibration input JSONL bytes withheld from review subject to the error budget. '
                                      'Input-only bytes exclude tool call, summary and agent reasoning.'}, 'tasks': reports}


def render(report):
    pct = lambda value: '—' if value is None else f'{100*value:.1f}%'
    tasks = report['tasks']
    lines = ['# Can a selected confidence threshold generalize?', '',
             'A retrospective split-validation experiment using the same 5,570 archived decisions: '
             '**10 tasks × 3 error budgets × 2 selection rules**, with no new paid calls. '
             'This tests threshold selection, not a new model or new unseen corpus.', '',
             '## Findings', '',
             '| Error budget | Empirical: tasks accepting / exceeding budget | Bounded: tasks accepting / exceeding budget |',
             '| --- | ---: | ---: |']
    for budget in BUDGETS:
        counts = []
        for method in ('empirical', 'bounded'):
            policies = [p for task in tasks.values() for p in task['policies']
                        if p['error_budget'] == budget and p['method'] == method]
            counts.append(f'{sum(p["holdout"]["accepted"] > 0 for p in policies)} / '
                          f'{sum(p["holdout_observed_budget_met"] is False for p in policies)}')
        lines.append(f'| {pct(budget)} | {counts[0]} | {counts[1]} |')
    lines += ['', 'These are counts of tasks out of ten, not independent repeated trials. '
              'Review-all outcomes do not count as successful quality validation.', '',
              '- At a **5%** budget, empirical selection exceeded the budget on news, banking, emotion and hate speech. '
              'Bounded selection retained only Apache, IMDb and SMS; their holdout error rates were below 5%. '
              'Apache remains a negative control: a regex already achieves the same labels.',
              '- On **IMDb at 5%**, bounded selection chose 0.95 using calibration data: holdout had '
              '**2 errors among 231 accepted**, 28/259 records for review and **88.4% of input bytes** withheld. '
              'The holdout Wilson interval is 0.2%–3.1%.',
              '- At a **1%** budget, no task qualified under the bounded rule. Even with zero errors, '
              'this seven-candidate procedure needs at least **492 accepted calibration examples**. '
              'A few hundred examples cannot establish a very low error rate with this confidence requirement.', '',
             '## Protocol', '',
             'Exact duplicate content is reduced to the lexicographically first ID before splitting. '
             f'A SHA-256 split with seed `{SEED}` assigns approximately half of the distinct texts to '
             'calibration and half to holdout. IDs and exclusions are archived in [report.json](report.json). '
             'Only calibration labels enter threshold selection; holdout labels score the chosen threshold afterward. '
             'The full original dataset results were already known, so this is not a prospective blind study.', '',
             'For each 1%, 5% or 10% accepted-error budget, select from `[0, .5, .8, .9, .95, .99, 1]` '
             'to keep the most calibration input bytes out of review. Ties prefer the lower threshold. '
             '**Empirical** selection checks the observed error rate. **Bounded** selection checks a '
             'one-sided exact binomial upper bound with Bonferroni α=0.05/7 for the seven candidates. '
             'If no candidate qualifies, all holdout inputs need review; a zero-accept policy has undefined error rate.', '',
             '`review all` is an offline policy fallback, not the server argument `confidence_threshold=1`: '
             'the server still accepts confidence exactly 1. This experiment does not change runtime defaults.', '',
             'The bounds assume independent, identically distributed error observations and a stable deployment distribution. '
             'Deduplication helps avoid exact-copy leakage but does not establish these assumptions. '
             'Correction covers the seven thresholds within one task, not a joint claim over all tasks. '
             'Holdout 95% Wilson intervals are descriptive and unadjusted. An observed budget pass is not a guarantee.', '',
             f'Distinct texts: **{sum(r["unique_contents"] for r in tasks.values()):,}**; '
             f'exact duplicate rows excluded: **{sum(r["duplicate_records_excluded"] for r in tasks.values())}**; '
             f'duplicate groups with conflicting labels: **{sum(r["conflicting_label_groups"] for r in tasks.values())}**.', '']
    for budget in BUDGETS:
        lines += [f'## Accepted-error budget: {pct(budget)}', '',
                  '| Task | Rule | Cal / holdout | Threshold | Accepted errors / accepted | Holdout error (95% interval) | Review | Input bytes withheld* |',
                  '| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |']
        for name, task in tasks.items():
            for policy in task['policies']:
                if policy['error_budget'] != budget:
                    continue
                h = policy['holdout']
                ci = h['accepted_error_95ci']
                interval = f'{pct(ci[0])}–{pct(ci[1])}' if ci else '—'
                threshold = policy['selected_threshold']
                label = 'review all' if threshold is None else f'{threshold:g}'
                lines.append(f'| {name} | {policy["method"]} | {len(task["calibration_ids"])} / {len(task["holdout_ids"])} | '
                             f'{label} | {h["accepted_errors"]} / {h["accepted"]} | {pct(h["accepted_error_rate"])} ({interval}) | '
                             f'{pct(h["review_fraction"])} | {pct(h["input_bytes_kept_out_of_review_fraction"])} |')
        lines.append('')
    lines += ['*Input-only canonical JSONL bytes withheld from review. This excludes call/summary overhead, '
              'MCP framing, tokenizer differences and agent reasoning. It is neither the parent report’s '
              'full-review JSON metric nor billed-token savings.', '',
              '## Reproduce', '', 'Prepare the sources using the [parent instructions](../README.md), then run:', '',
              '```sh', 'uv run --locked python benchmarks/multitask/validate_thresholds.py --self-test',
              'uv run --locked python benchmarks/multitask/validate_thresholds.py --root /tmp/decide-multitask --check',
              '```', '', 'Omit `--check` to regenerate these artifacts. The check recomputes all splits, '
              'selections, errors, intervals and input byte counts and compares both artifacts exactly.', '',
              'Methods: [R exact binomial intervals](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/binom.test.html) '
              'and [NIST Bonferroni inequality](https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm).', '']
    return '\n'.join(lines)


def self_test():
    assert upper_error(0, 0) is None and upper_error(10, 10) == 1
    assert math.isclose(upper_error(0, 10), 1 - ALPHA ** .1)
    assert math.isclose(upper_error(9, 10), (1 - ALPHA) ** .1)
    p = upper_error(3, 10)
    assert math.isclose(sum(math.comb(10, k) * p**k * (1-p)**(10-k) for k in range(4)), ALPHA)
    # Enumerate a small binomial experiment independently: upper bounds must not undercover.
    for count in (5, 20):
        for probability in (.01, .1, .5, .9, .99):
            noncoverage = sum(math.comb(count, k) * probability**k * (1-probability)**(count-k)
                              for k in range(count + 1) if upper_error(k, count) < probability)
            assert noncoverage <= ALPHA + 1e-12
    records = {'a': {'choice': 'yes', 'confidence': 1}, 'b': {'choice': 'no', 'confidence': .8},
               'c': {'error': 'invalid_provider_response'}}
    labels = {key: {'expected': 'yes'} for key in records}
    inputs = {key: {'id': key, 'content': key} for key in records}
    candidates = [measure(records, labels, inputs, t) for t in THRESHOLDS]
    assert choose(candidates, .01, 'empirical') == .9
    assert choose(candidates, .01, 'bounded') is None  # One correct example cannot justify 1% risk.
    abstain = measure(records, labels, inputs, None)
    assert abstain['accepted'] == 0 and abstain['review'] == 3 and abstain['accepted_error_rate'] is None
    assert abstain['input_bytes_kept_out_of_review_fraction'] == 0
    assert abstain['failed'] == 1
    assert measure(records, labels, inputs, .8)['accepted_errors'] == 1
    print('Exact-bound, selection, failure and abstention checks passed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        if args.root is None:
            parser.error('--root is required unless --self-test is used')
        report = evaluate(args.root)
        output = HERE / 'threshold-validation'
        artifacts = {'report.json': json.dumps(report, indent=2) + '\n', 'README.md': render(report)}
        if args.check:
            for name, content in artifacts.items():
                assert (output / name).read_text(encoding='utf-8') == content, name
        else:
            output.mkdir(exist_ok=True)
            for name, content in artifacts.items():
                (output / name).write_text(content, encoding='utf-8')
        print(('Verified' if args.check else 'Wrote'), '60 selected-policy results; no paid calls.')
