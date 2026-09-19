"""Run with python -m unittest -v. No credentials or paid requests."""

import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx2 as httpx
from mcp import Client, StdioServerParameters

import decide as app

CRITERIA = {"keep": "Relevant", "skip": "Irrelevant"}


def response(confidence=0.95):
    return {"model": "jev-test", "answers": {"decision": {
        "type": "choice", "choice": "keep", "confidence": confidence,
        "probabilities": {"keep": 0.98, "skip": 0.02},
    }}, "usage": {"input_tokens": 100, "output_tokens": 10}}


class DecideTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.environment = patch.dict(os.environ, {
            "DECIDE_ROOT": str(self.root), "TYPESAFE_API_KEY": "test-key", "DECIDE_MODEL": "jev-test",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def mock_provider(self, handler):
        factory = httpx.AsyncClient
        mock = patch.object(app.httpx, "AsyncClient", side_effect=lambda **kw: factory(
            **kw, transport=httpx.MockTransport(handler),
        ))
        mock.start()
        self.addCleanup(mock.stop)

    async def call(self, **kwargs):
        async with Client(app.mcp) as client:
            result = await client.call_tool("decide", {"question": "Keep this?", "criteria": CRITERIA, **kwargs})
            self.assertFalse(result.is_error, str(result))
            return result.structured_content

    async def test_2000_lines_only_uncertain_content_enters_context(self):
        (self.root / "app.log").write_text("\n".join(f"line-{i}" for i in range(2000)))
        calls, active, peak = 0, 0, 0

        async def handler(request):
            nonlocal calls, active, peak
            self.assertEqual(str(request.url), app.API_URL)
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            payload = json.loads(request.content)
            self.assertEqual(payload["questions"]["decision"]["criteria"], CRITERIA)
            active += 1
            peak = max(peak, active)
            calls += 1
            await asyncio.sleep(0)
            active -= 1
            index = int(payload["state"]["item"]["content"].split("-")[1])
            return httpx.Response(200, json=response(0.4 if index % 20 == 0 else 0.95))

        self.mock_provider(handler)
        result = await self.call(source={"kind": "lines", "paths": ["app.log"]})
        self.assertEqual((calls, peak), (2000, 4))
        self.assertEqual((result["total"], result["accepted"], result["review_count"]), (2000, 1900, 100))
        self.assertEqual(result["review_fraction"], 0.05)
        self.assertEqual(result["review_omitted"], 80)
        self.assertEqual(result["usage"], {"input_tokens": 200000, "output_tokens": 20000, "complete": True})
        self.assertLess(len(app.encode(result["review"]).encode()), 21000)
        records = [json.loads(line) for line in Path(result["results_path"]).read_text().splitlines()]
        self.assertEqual(len({row["id"] for row in records}), 2000)
        self.assertTrue(all("content" not in row for row in records))
        review = [json.loads(line) for line in Path(result["review_path"]).read_text().splitlines()]
        self.assertEqual(len(review), 100)
        self.assertTrue(all(int(row["content"].split("-")[1]) % 20 == 0 for row in review))

    async def test_300_files_and_oversize_are_not_silently_truncated(self):
        folder = self.root / "src"
        folder.mkdir()
        for index in range(300):
            (folder / f"{index}.py").write_text(f"print({index})")
        (folder / "big.py").write_text("x" * (app.MAX_ITEM_BYTES + 1))
        (folder / ".env").write_text("must not send")
        sent = []

        def handler(request):
            sent.append(json.loads(request.content)["state"]["item"])
            return httpx.Response(200, json=response())

        self.mock_provider(handler)
        result = await self.call(source={"kind": "files", "paths": ["src/*", "src/*.py"]})
        self.assertEqual((result["total"], result["accepted"], result["failed"]), (301, 300, 1))
        self.assertEqual(len(sent), 300)
        self.assertEqual(result["review"][0]["reason"], "item_too_large")
        full_review = json.loads(Path(result["review_path"]).read_text())
        self.assertEqual(len(full_review["content"]), app.MAX_ITEM_BYTES + 1)

    async def test_retry_errors_validation_and_forced_review(self):
        attempts = Counter()

        def handler(request):
            key = json.loads(request.content)["state"]["item"]["id"]
            attempts[key] += 1
            if key == "retry" and attempts[key] == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            if key == "timeout":
                raise httpx.ReadTimeout("private request details", request=request)
            if key == "bad":
                bad = response()
                bad["answers"]["decision"]["probabilities"]["keep"] = 0.2
                return httpx.Response(200, json=bad)
            if key == "invalid_json":
                return httpx.Response(200, text="secret invalid content")
            return httpx.Response(200, json=response())

        self.mock_provider(handler)
        with patch.object(app.asyncio, "sleep", new_callable=AsyncMock):
            result = await self.call(items=[{"id": key, "content": "data"} for key in
                                           ["retry", "timeout", "bad", "invalid_json", "valid"]],
                                     review_labels=["keep"])
        self.assertEqual(result["accepted"], 0)
        self.assertEqual((result["review_count"], result["failed"]), (5, 3))
        self.assertEqual((attempts["retry"], attempts["timeout"]), (2, 3))
        self.assertNotIn("secret", app.encode(result))
        self.assertNotIn("private request", app.encode(result))
        self.assertFalse(result["usage"]["complete"])

    async def test_auth_failure_stops_following_requests(self):
        calls = []
        self.mock_provider(lambda request: calls.append(request) or httpx.Response(401))
        result = await self.call(items=[{"id": str(i), "content": "data"} for i in range(100)])
        self.assertLessEqual(len(calls), 4)
        self.assertEqual(result["failed"], 100)
        self.assertEqual(result["review_omitted"], 80)

    async def test_threshold_boundary_and_provider_confidence(self):
        values = iter([0.8, 0.79])
        self.mock_provider(lambda request: httpx.Response(200, json=response(next(values))))
        result = await self.call(items=[{"id": "equal", "content": "a"}, {"id": "below", "content": "b"}],
                                 concurrency=1)
        self.assertEqual((result["accepted"], result["review_count"]), (1, 1))
        self.assertEqual(result["review"][0]["id"], "below")

    async def test_jsonl_and_retry_accounting(self):
        (self.root / "tickets.jsonl").write_text(
            '\n{"id":"ticket-1","content":{"title":"Example"}}\n', encoding="utf-8")
        calls = []

        def handler(request):
            calls.append(json.loads(request.content))
            return httpx.Response(529) if len(calls) == 1 else httpx.Response(200, json=response())

        self.mock_provider(handler)
        with patch.object(app.asyncio, "sleep", new_callable=AsyncMock):
            result = await self.call(source={"kind": "jsonl", "paths": ["tickets.jsonl"]})
        self.assertEqual(calls[0]["state"]["item"], {"id": "ticket-1", "content": {"title": "Example"}})
        self.assertEqual((result["accepted"], result["requests_made"], result["retries"]), (1, 2, 1))
        self.assertFalse(result["usage"]["complete"])

    async def test_missing_key_is_actionable(self):
        os.environ.pop("TYPESAFE_API_KEY", None)
        async with Client(app.mcp) as client:
            result = await client.call_tool("decide", {"question": "Keep?", "criteria": CRITERIA,
                "items": [{"id": "a", "content": "data"}]})
            self.assertTrue(result.is_error)
            self.assertIn("TYPESAFE_API_KEY", str(result.content))
        self.assertFalse((self.root / ".decide").exists())

    async def test_bad_provider_values_fail_closed(self):
        variants = [response() for _ in range(6)]
        variants[0]["answers"]["decision"]["confidence"] = True
        variants[1]["answers"]["decision"]["probabilities"]["keep"] = "0.98"
        variants[2]["answers"]["decision"]["choice"] = "unknown"
        variants[3]["usage"]["input_tokens"] = -1
        variants[4]["answers"]["decision"]["probabilities"] = {"skip": 1}
        variants[5]["answers"]["decision"]["confidence"] = "NaN"
        values = iter(variants)
        self.mock_provider(lambda request: httpx.Response(200, json=next(values)))
        result = await self.call(items=[{"id": str(i), "content": "data"} for i in range(6)])
        self.assertEqual(result["failed"], 6)

    async def test_input_errors_happen_before_provider_calls(self):
        calls = []
        self.mock_provider(lambda request: calls.append(request) or httpx.Response(200, json=response()))
        (self.root / "bad.jsonl").write_text('{"id":"a","content":"ok"}\nnot json')
        (self.root / "outside").symlink_to(self.root.parent)
        invalid = [
            {"items": []}, {"items": [{"id": "a", "content": "x"}] * 2},
            {"source": {"kind": "jsonl", "paths": ["bad.jsonl"]}},
            {"source": {"kind": "lines", "paths": ["../escape"]}},
            {"source": {"kind": "lines", "paths": ["outside/escape"]}},
            {"source": {"kind": "files", "paths": ["missing/*.py"]}},
            {"items": [{"id": "a", "content": "x"}], "confidence_threshold": 1.1},
            {"items": [{"id": "a", "content": "x"}], "review_labels": ["unknown"]},
            {"items": [{"id": "a", "content": "x"}], "source": {"kind": "lines", "paths": ["a"]}},
        ]
        async with Client(app.mcp) as client:
            for arguments in invalid:
                with self.subTest(arguments=arguments):
                    result = await client.call_tool("decide", {"question": "Keep?", "criteria": CRITERIA, **arguments})
                    self.assertTrue(result.is_error)
        self.assertEqual(calls, [])
        self.assertFalse((self.root / ".decide").exists())

    async def test_stdio_subprocess_full_call(self):
        # The real SDK transport and server, with only the paid HTTP endpoint replaced.
        code = (
            "import httpx2, decide; from test_decide import response; "
            "factory=httpx2.AsyncClient; "
            "decide.httpx.AsyncClient=lambda **kw: factory(**kw, transport="
            "httpx2.MockTransport(lambda r: httpx2.Response(200,json=response(0.4)))); "
            "decide.main()"
        )
        server = StdioServerParameters(command=sys.executable, args=["-c", code],
            cwd=str(Path(__file__).parent), env={"DECIDE_ROOT": str(self.root), "TYPESAFE_API_KEY": "test"})
        async with Client(server) as client:
            tools = await client.list_tools()
            self.assertEqual([tool.name for tool in tools.tools], ["decide"])
            result = await client.call_tool("decide", {"question": "Keep?", "criteria": CRITERIA,
                "items": [{"id": "a", "content": "sample"}]})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["review_count"], 1)


if __name__ == "__main__":
    unittest.main()
