"""Measure compact review output through MCP using recorded decisions; no paid calls."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import decide
import benchmark
from mcp import Client
from analyze import read_rows
from evaluate import risk_coverage


async def run(root, output):
    for report_path in sorted(output.glob('*/report.json')):
        folder = root / report_path.parent.name
        report = json.loads(report_path.read_text())
        inputs = read_rows(folder / 'items.jsonl')
        labels = {row['id']: row['expected'] for row in read_rows(folder / 'labels.jsonl')}
        recorded = {row['id']: row for row in read_rows(report_path.parent / 'predictions.jsonl')}
        arguments = json.loads((folder / 'rubric.json').read_text())
        assert hashlib.sha256((folder/'items.jsonl').read_bytes()).hexdigest() == report['input_jsonl_sha256']
        async def replay(client, payload):
            row = recorded[payload['state']['item']['id']]
            return {key: row[key] for key in ['choice', 'confidence', 'probabilities', 'model', 'usage', 'attempts', 'error'] if key in row}
        threshold_measurements = []
        for threshold in [0, .5, .8, .9, .95, .99, 1]:
            sweep_arguments = {**arguments, 'confidence_threshold': threshold}
            with tempfile.TemporaryDirectory(prefix='decide-replay-') as temp:
                shutil.copyfile(folder / 'items.jsonl', Path(temp) / 'items.jsonl')
                with patch.dict(os.environ, {'DECIDE_ROOT':temp,'TYPESAFE_API_KEY':'offline-replay','DECIDE_MODEL':'jev-1.13.0'}), \
                     patch.object(decide, 'classify', replay), \
                     patch.object(decide.httpx.AsyncClient, 'post', side_effect=AssertionError('Replay must never call an API')):
                    async with Client(decide.mcp) as client:
                        call = await client.call_tool('decide', sweep_arguments)
                        assert not call.is_error, call.content
                        result = call.structured_content
                replayed = read_rows(Path(result['results_path']))
                strip_routing = lambda row: {key:value for key,value in row.items() if key not in {'status','reason'}}
                assert {row['id']:strip_routing(row) for row in replayed} == {key:strip_routing(row) for key,row in recorded.items()}
                if threshold == .8:
                    assert {row['id']:row for row in replayed} == recorded, 'Default routing changed'
                risk = risk_coverage(recorded, {key:{'expected':value} for key,value in labels.items()}, threshold)
                assert result['accepted'] == risk['accepted'] and result['review_count'] == risk['review']
                review = read_rows(Path(result['review_path']))
                assert all(set(row) == {'id','content'} for row in review)
                inline = {**sweep_arguments, 'items':inputs}
                del inline['source']
                metrics = benchmark.metrics(result, replayed, labels, len(decide.encode(inline).encode()),
                                            len(decide.encode(sweep_arguments).encode()), review)
            threshold_measurements.append({
                'threshold':threshold, 'accepted':risk['accepted'], 'review':risk['review'],
                'accepted_errors':risk['accepted_errors'], 'accepted_error_rate':risk['accepted_error_rate'],
                'measured_summary':result,
                **{key:metrics[key] for key in ['inline_input_bytes','source_call_and_result_bytes',
                    'all_review_records_bytes','context_bytes_reduction','context_bytes_reduction_with_all_reviews']}})
        default = next(row for row in threshold_measurements if row['threshold'] == .8)
        report['compact_review_replay'] = {
            'mode':'Recorded-response replay through MCP; no new Jev inference', 'paid_requests':0,
            'server_source_sha256':hashlib.sha256(Path(decide.__file__).read_bytes()).hexdigest(),
            'decisions_and_default_routing_identical':True,
            **default, 'thresholds':threshold_measurements}
        report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(report_path.parent.name,round(default['context_bytes_reduction_with_all_reviews']*100,2),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--results',type=Path,required=True)
    args=parser.parse_args()
    asyncio.run(run(args.root,args.results))
