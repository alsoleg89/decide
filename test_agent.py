"""The tool loop must never silently accept a missing or duplicated decision."""
import unittest
from benchmark_agent import validate_write, write_tool


class AgentContractTests(unittest.TestCase):
    def test_exact_batch_write(self):
        ids, labels = ['a', 'b'], ['yes', 'no']
        self.assertEqual(write_tool(ids, labels)['parameters']['properties']['decisions']['required'], ids)
        self.assertEqual(validate_write('{"decisions":{"a":"yes","b":"no"}}', ids, labels), {'a': 'yes', 'b': 'no'})
        for arguments in ['{"decisions":{"a":"yes"}}', '{"decisions":{"a":"yes","a":"no","b":"no"}}',
                          '{"decisions":{"a":"maybe","b":"no"}}', '{"decisions":{"a":"yes","b":"no","c":"yes"}}']:
            with self.assertRaises(ValueError):
                validate_write(arguments, ids, labels)

    def test_two_arms_write_same_file_and_count_every_model_turn(self):
        import asyncio
        import json
        from pathlib import Path
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        import benchmark_agent as app

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [{'id': str(i), 'content': 'untrusted text'} for i in range(30)]
            (root / 'items.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
            (root / 'labels.jsonl').write_text(''.join(json.dumps({'id': r['id'], 'expected': 'yes'}) + '\n' for r in rows))
            app.save(root / 'rubric.json', {'question': 'Relevant?', 'criteria': {'yes': 'yes', 'no': 'no'}, 'confidence_thresholds': {'no': 0.9}})
            directory = root / 'experiment'
            app.prepare(root, directory)

            class FakeMCP:
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
                async def call_tool(self, name, arguments):
                    self_name = name
                    assert self_name == 'decide' and arguments['confidence_threshold'] == 0
                    assert arguments['confidence_thresholds'] == {'no': 0.9}
                    path = root / 'mcp-results.jsonl'
                    path.write_text(''.join(json.dumps({'id': r['id'], 'status': 'review' if i == 0 else 'accepted',
                                                       'choice': 'yes'}) + '\n' for i, r in enumerate(rows)))
                    return SimpleNamespace(is_error=False, structured_content={'results_path': str(path),
                        'usage': {'input_tokens': 1000, 'complete': True}})

            seen = []
            def api(plan, turn):
                body = plan['calls'][0]['body']
                seen.append(body)
                tools = body['tools']
                self.assertEqual(body['tool_choice'], 'required' if tools else 'none')
                if tools:
                    name = tools[0]['name']
                    arguments = {'decisions': {key: 'yes' for key in tools[0]['parameters']['properties']['decisions']['required']}} if name == 'write_decisions' else {}
                    output = [{'type': 'function_call', 'call_id': str(len(seen)), 'name': name,
                               'arguments': json.dumps(arguments)}]
                else:
                    output = [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'Saved.'}]}]
                record = {'elapsed_seconds': 1, 'body': {'status': 'completed', 'model': app.MODEL,
                    'service_tier': 'default', 'output': output, 'usage': {'input_tokens': 1000, 'output_tokens': 100,
                    'input_tokens_details': {'cached_tokens': 0}, 'output_tokens_details': {'reasoning_tokens': 0}}}}
                (turn / 'responses.jsonl').write_text(json.dumps(record) + '\n')

            with patch.object(app, 'api_run', side_effect=api), patch.object(app, 'Client', return_value=FakeMCP()), \
                 patch.dict(app.os.environ, {'OPENAI_API_KEY': 'test', 'TYPESAFE_API_KEY': 'test'}):
                for arm, calls in [('baseline', 6), ('decide', 6)]:
                    report = asyncio.run(app.run(root, directory, arm))
                    self.assertTrue(report['artifact_complete'])
                    self.assertTrue(report['cost_complete'])
                    self.assertEqual(report['model_calls'], calls)
                    self.assertEqual(report['classification']['accuracy'], 1)
                    self.assertAlmostEqual(report['mini_known_usd'], calls * .00056)
                self.assertEqual((directory / 'baseline/decisions.jsonl').read_bytes(),
                                 (directory / 'decide/decisions.jsonl').read_bytes())
                with self.assertRaises(FileExistsError):
                    asyncio.run(app.run(root, directory, 'baseline'))
            # Completed batch payloads disappear from the next read request in both arms.
            for body in seen:
                if body['tools'] and body['tools'][0]['name'] in {'read_next', 'finish'}:
                    self.assertNotIn('untrusted text', json.dumps(body))
            # Losing a billable response must not make the experiment look cheaper and complete.
            missing = directory / 'baseline/turns/003/responses.jsonl'
            original = missing.read_bytes()
            missing.unlink()
            incomplete = app.score(directory, 'baseline')
            self.assertFalse(incomplete['cost_complete'])
            self.assertFalse(incomplete['artifact_complete'])
            missing.write_bytes(original)
            final = directory / 'baseline/final.json'
            original = final.read_bytes()
            final.write_text('[]')
            self.assertFalse(app.score(directory, 'baseline')['artifact_complete'])
            self.assertTrue(app.score(directory, 'baseline')['cost_complete'])
            final.write_bytes(original)
            self.assertTrue(app.score(directory, 'baseline')['artifact_complete'])
            (directory / 'decide/turns/000/inflight.json').write_text('{}')
            self.assertFalse(app.score(directory, 'decide')['cost_complete'])
