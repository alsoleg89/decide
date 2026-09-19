"""Provider corruption and retry-state transitions, using the real HTTP client."""

import asyncio
import copy
import json
import math
import unittest
from unittest.mock import AsyncMock, patch

import httpx2 as httpx

import decide as app
import test_decide as shared


class ProviderFaultTests(unittest.IsolatedAsyncioTestCase):
    setUp = shared.ProviderTests.setUp
    invoke = shared.ProviderTests.invoke

    async def check_corruption(self, path, value):
        raw = shared.response()
        target = raw
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = copy.deepcopy(value)
        result, sleep = await self.invoke(lambda request: httpx.Response(200, content=json.dumps(raw)))
        self.assertEqual(result, {"error": "invalid_provider_response", "attempts": 1})
        sleep.assert_not_awaited()

    async def test_deep_json_fails_closed_instead_of_cancelling_the_batch(self):
        result, sleep = await self.invoke(lambda request: httpx.Response(200, content="[" * 2000 + "0" + "]" * 2000))
        self.assertEqual(result, {"error": "invalid_provider_response", "attempts": 1})
        sleep.assert_not_awaited()

    async def test_last_attempt_long_cooldown_still_stops_the_batch(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(429, headers={"Retry-After": "120"} if len(calls) == 3 else {})
        result, sleep = await self.invoke(handler)
        self.assertEqual(result, {"error": "provider_retry_later", "attempts": 3})
        self.assertEqual(sleep.await_count, 2)

    async def test_cancellation_is_propagated_without_retry(self):
        def handler(request):
            raise asyncio.CancelledError()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch.object(app.asyncio, "sleep", new_callable=AsyncMock) as sleep:
                with self.assertRaises(asyncio.CancelledError):
                    await app.classify(client, self.payload)
                sleep.assert_not_awaited()

    async def test_cancellation_during_backoff_never_sends_next_request(self):
        calls = []
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(503))) as client:
            with patch.object(app.asyncio, "sleep", side_effect=asyncio.CancelledError):
                with self.assertRaises(asyncio.CancelledError):
                    await app.classify(client, self.payload)
        self.assertEqual(len(calls), 1)

    async def check_sequence(self, events, expected, attempts):
        called = []
        def handler(request):
            called.append(request.headers["X-TypeSafe-Retry-Count"])
            event = events[len(called) - 1]
            if event == "transport":
                raise httpx.ReadError("private request", request=request)
            if event == "bad_json":
                return httpx.Response(200, text="private body")
            return httpx.Response(event, json=shared.response())
        result, sleep = await self.invoke(handler)
        self.assertEqual(result["attempts"], attempts)
        self.assertEqual(called, [str(i) for i in range(attempts)])
        self.assertEqual(result.get("error", "success"), expected)
        self.assertEqual(sleep.await_count, attempts - 1)
        self.assertNotIn("private", app.encode(result))


BAD_VALUES = {
    "null": None, "boolean": True, "string": "0.8", "negative": -0.1,
    "too_large": 1.1, "nan": math.nan, "infinity": math.inf,
    "negative_infinity": -math.inf, "array": [], "object": {},
}
CORRUPTIONS = []
for field in ["confidence"]:
    for name, value in BAD_VALUES.items():
        CORRUPTIONS.append((f"{field}_{name}", ("answers", "decision", field), value))
for name, value in BAD_VALUES.items():
    CORRUPTIONS.append((f"probability_{name}", ("answers", "decision", "probabilities", "keep"), value))
for field in ["input_tokens", "output_tokens"]:
    for name, value in {**BAD_VALUES, "fraction": 3.5, "negative_integer": -1, "numeric_string": "12"}.items():
        # Positive 1.1 is also invalid as usage must be an integer.
        CORRUPTIONS.append((f"usage_{field}_{name}", ("usage", field), value))
for field, values in {
    "model": {"null": None, "boolean": True, "number": 1, "empty": "", "object": {}, "array": []},
    "choice": {"null": None, "boolean": True, "number": 1, "empty": "", "unknown": "elsewhere", "over_limit": "x" * 101, "array": []},
    "type": {"null": None, "boolean": True, "number": 1, "score": "score", "noul": "noul", "empty": "", "object": {}},
}.items():
    for name, value in values.items():
        CORRUPTIONS.append((f"{field}_{name}", ("model",) if field == "model" else ("answers", "decision", field), value))
for name, value in {
    "extra_label": {"keep": 0.98, "skip": 0.02, "other": 0},
    "missing_label": {"keep": 1}, "empty": {}, "array": [0.98, 0.02],
    "null": None, "bad_sum_low": {"keep": 0.6, "skip": 0.2},
    "bad_sum_high": {"keep": 0.8, "skip": 0.8},
    "wrong_winner": {"keep": 0.1, "skip": 0.9},
    "outside_rounding_tolerance": {"keep": 0.50002, "skip": 0.5},
}.items():
    CORRUPTIONS.append((f"distribution_{name}", ("answers", "decision", "probabilities"), value))


def corruption_case(path, value):
    async def test(self):
        await self.check_corruption(path, value)
    return test


def sequence_case(events, expected, attempts):
    async def test(self):
        await self.check_sequence(events, expected, attempts)
    return test


for name, path, value in CORRUPTIONS:
    setattr(ProviderFaultTests, f"test_reject_{name}", corruption_case(path, value))
for name, events, expected, attempts in [
    ("http_transport_success", [503, "transport", 200], "success", 3),
    ("transport_http_success", ["transport", 429, 200], "success", 3),
    ("http_permanent", [503, 422], "provider_http_422", 2),
    ("transport_permanent", ["transport", 401], "provider_http_401", 2),
    ("http_invalid_json", [503, "bad_json"], "invalid_provider_response", 2),
    ("transport_invalid_json", ["transport", "bad_json"], "invalid_provider_response", 2),
    ("http_transport_http", [503, "transport", 429], "provider_http_429", 3),
    ("http_http_transport", [503, 503, "transport"], "provider_unreachable", 3),
    ("transport_transport_http", ["transport", "transport", 503], "provider_http_503", 3),
    ("http_http_auth", [503, 503, 403], "provider_http_403", 3),
    ("http_http_invalid_json", [503, 503, "bad_json"], "invalid_provider_response", 3),
]:
    setattr(ProviderFaultTests, f"test_sequence_{name}", sequence_case(events, expected, attempts))
