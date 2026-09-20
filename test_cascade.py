"""Offline accounting checks; mocked answers are not evidence of model quality."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx2 as httpx

import benchmark_cascade as app


def response(ids, wrong=()):
    return {'status': 'completed', 'model': 'test-model', 'service_tier': 'default',
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps({
                'decisions': [{'id': key, 'choice': 'skip' if key in wrong else 'keep'} for key in ids]})}]}],
            'usage': {'input_tokens': 1000, 'input_tokens_details': {'cached_tokens': 200, 'cache_write_tokens': 300},
                      'output_tokens': 100, 'output_tokens_details': {'reasoning_tokens': 40}}}


class CascadeTests(unittest.TestCase):
    def test_review_errors_are_measured_and_accepted_errors_cannot_be_repaired(self):
        calls = [{'arm': 'baseline', 'ids': ['a', 'b', 'c', 'd'], 'request_sha256': 'one'},
                 {'arm': 'review', 'ids': ['c', 'd'], 'request_sha256': 'two'}]
        plan = {'calls': calls, 'ids': ['a', 'b', 'c', 'd'], 'criteria': ['keep', 'skip'],
                'jev_accepted': {'a': 'skip', 'b': 'keep'}, 'mode': 'test', 'model': 'test-model',
                'jev_known_usd': .001, 'jev_cost_complete': True}
        records = [{'index': i, 'request_sha256': call['request_sha256'], 'arm': call['arm'],
                    'body': response(call['ids'], wrong=['c'] if i else []), 'status_code': 200, 'elapsed_seconds': 1}
                   for i, call in enumerate(calls)]
        labels = {key: {'expected': 'keep'} for key in plan['ids']}
        rates = {'input': 10, 'cached_input': 1, 'cache_write': 12.5, 'output': 50}
        prices = {'model': 'test-model', 'long_context_above_tokens': 272000, 'short': rates, 'long': rates}
        result = app.score(plan, records, labels, prices)
        self.assertEqual(result['baseline']['accuracy'], 1)
        self.assertEqual(result['cascade']['accuracy'], .5)
        self.assertEqual(result['ideal_review_accuracy_ceiling'], .75)
        # Cache read/write buckets are disjoint; reasoning is already in output_tokens.
        self.assertAlmostEqual(result['cost_estimate']['baseline_known_usd'], .01395)
        self.assertAlmostEqual(result['cost_estimate']['cascade_known_usd'], .01495)
        self.assertLess(result['cost_estimate']['savings_fraction'], 0)
        self.assertEqual(result['paired_correctness'], {'both_correct': 2, 'baseline_only_correct': 2,
                                                       'cascade_only_correct': 0, 'both_wrong': 0})
        self.assertFalse(result['controlled_sample_comparison']['observed_tradeoff_met'])
        missing = copy.deepcopy(records)
        del missing[1]['body']['usage']
        self.assertIsNone(app.score(plan, missing, labels, prices)['cost_estimate']['savings_fraction'])
        self.assertIsNone(app.score(plan, missing, labels, prices)['controlled_sample_comparison']['observed_tradeoff_met'])
        equal = copy.deepcopy(records)
        equal[0]['body'] = response(calls[0]['ids'], wrong=['a'])
        equal[0]['body']['usage']['input_tokens'] = 4000
        equal[1]['body'] = response(calls[1]['ids'])
        comparison = app.score(plan, equal, labels, prices)['controlled_sample_comparison']
        self.assertTrue(comparison['quality_not_worse'])
        self.assertTrue(comparison['observed_tradeoff_met'])
        equal[1]['body']['model'] = 'different-model'
        self.assertIsNone(app.score(plan, equal, labels, prices)['controlled_sample_comparison']['observed_tradeoff_met'])
        with self.assertRaises(ValueError):
            app.score(plan, records[:-1], labels)
        records[1]['body'] = response(['c', 'c'])
        failed = app.score(plan, records, labels)
        self.assertEqual(failed['failed_items']['review'], 2)
        self.assertEqual(failed['cascade']['accuracy'], .25)
        self.assertIsNone(failed['controlled_sample_comparison']['observed_tradeoff_met'])

    def test_paid_request_is_not_retried_or_silently_repeated(self):
        body = {'model': 'test-model'}
        plan = {'calls': [{'arm': 'baseline', 'ids': ['a'], 'body': body, 'request_sha256': app.digest(body)}]}
        seen = []
        def handler(request):
            seen.append(request)
            return httpx.Response(429, json={'error': {'message': 'rate limit test-only'}})
        real_client = httpx.Client
        with tempfile.TemporaryDirectory() as temp, patch.dict(app.os.environ, {'OPENAI_API_KEY': 'test-only'}):
            with patch.object(app.httpx, 'Client', side_effect=lambda **kwargs: real_client(
                    **kwargs, transport=httpx.MockTransport(handler))):
                with self.assertRaises(RuntimeError):
                    app.run(plan, Path(temp))
                with self.assertRaises(FileExistsError):
                    app.run(plan, Path(temp))
            self.assertEqual(len(seen), 1)
            saved = (Path(temp)/'responses.jsonl').read_text()
            self.assertNotIn('test-only', saved)
            self.assertEqual(json.loads(saved)['status_code'], 429)


if __name__ == '__main__':
    unittest.main()
