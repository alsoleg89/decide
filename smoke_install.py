"""Check an installed MCP command without a real key or paid inference."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

from mcp import Client, StdioServerParameters


async def check(command):
    with tempfile.TemporaryDirectory(prefix='decide-install-') as directory:
        root = Path(directory).resolve()
        row = {'id': 'oversized', 'content': 'x' * 128_001}
        (root / 'items.jsonl').write_text(json.dumps(row) + '\n', encoding='utf-8')
        environment = {**os.environ, 'DECIDE_ROOT': str(root), 'TYPESAFE_API_KEY': 'offline-install-check', 'PYTHONPATH': ''}
        environment.pop('OPENAI_API_KEY', None)
        server = StdioServerParameters(command=command[0], args=command[1:], env=environment, cwd=str(root))
        async with Client(server, read_timeout_seconds=60) as client:
            listed = await client.list_tools()
            assert [tool.name for tool in listed.tools] == ['decide']
            result = await client.call_tool('decide', {
                'question': 'Is this a feature request?', 'criteria': {'yes': 'Requests a feature', 'no': 'Other'},
                'source': {'kind': 'jsonl', 'paths': ['items.jsonl']}, 'confidence_threshold': 0,
                'confidence_thresholds': {'no': 0.9}})
            assert not result.is_error, 'Installed tool returned an MCP error'
        summary = result.structured_content
        assert summary['completed'] == summary['review_count'] == 1
        assert summary['requests_made'] == 0 and summary['usage']['complete']
        assert summary['confidence_thresholds'] == {'no': 0.9}
        assert summary['review_reasons'] == {'item_too_large': 1}
        assert json.loads(Path(summary['review_path']).read_text(encoding='utf-8')) == row
        decision = json.loads(Path(summary['results_path']).read_text(encoding='utf-8'))
        assert decision['id'] == row['id'] and decision['attempts'] == 0
        print('PASS: installed command, MCP handshake, source paths, label cutoffs, full review artifact; 0 provider requests.')


if __name__ == '__main__':
    command = sys.argv[1:] or ['decide-mcp']
    if command[0] == '--':
        command = command[1:]
    if not command:
        raise SystemExit('Usage: python smoke_install.py [--] [MCP command and arguments]')
    asyncio.run(check(command))
