"""Small exact cases for the post-hoc paired-statistics calculator."""
import json
from pathlib import Path
import tempfile
import unittest
from benchmarks.paired_statistics import analyze, mcnemar


class PairedStatisticsTests(unittest.TestCase):
    def test_exact_discordance_and_paired_bootstrap(self):
        self.assertEqual(mcnemar(0, 0), 1)
        self.assertEqual(mcnemar(5, 5), 1)
        self.assertEqual(mcnemar(0, 10), 2 / 1024)
        self.assertEqual(mcnemar(24, 84), mcnemar(84, 24))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'baseline').mkdir(); (root / 'decide').mkdir()
            gold = [{'id': str(i), 'expected': 'yes' if i % 2 else 'no'} for i in range(10)]
            (root / 'labels.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in gold))
            for arm in ['baseline', 'decide']:
                (root / arm / 'decisions.jsonl').write_text(''.join(json.dumps({'id': r['id'],
                    'choice': r['expected'] if arm == 'decide' else ('no' if r['expected'] == 'yes' else 'yes')}) + '\n' for r in gold))
            result = analyze(root, repetitions=100)
            self.assertEqual(result['mcnemar']['exact_two_sided_p'], 2 / 1024)
            self.assertEqual(result['deltas']['accuracy'], {'estimate': 1., 'ci95': [1., 1.]})
            self.assertEqual(result, analyze(root, repetitions=100))
            (root / 'decide/decisions.jsonl').write_text('')
            with self.assertRaises(ValueError):
                analyze(root)
