#!/usr/bin/env python3
"""Unit tests for the restricted OpenAI/xAI Responses API adapter."""
from __future__ import annotations

import io
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.request import Request
from unittest.mock import patch

import nixal_responses_api as api


class TestResponsesAdapter(unittest.TestCase):
    def test_provider_requires_key_model_and_official_https_host(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(api.provider_configured("openai"))
            self.assertFalse(api.provider_configured("grok"))

        with patch.dict(os.environ, {
            "NYXAL_OPENAI_API_KEY": "test-key",
            "NYXAL_OPENAI_MODEL": "test-model",
            "NYXAL_GROK_API_KEY": "test-key",
            "NYXAL_GROK_MODEL": "test-model",
        }, clear=True):
            self.assertTrue(api.provider_configured("openai"))
            self.assertTrue(api.provider_configured("grok"))

        bad_bases = (
            "http://api.openai.com/v1",
            "https://attacker.invalid/v1",
            "https://api.openai.com:8443/v1",
            "https://user:pass@api.openai.com/v1",
            "https://api.openai.com/v1?forward=1",
            "https://api.openai.com/v1#fragment",
        )
        for base in bad_bases:
            with self.subTest(base=base), patch.dict(os.environ, {
                "NYXAL_OPENAI_API_KEY": "test-key",
                "NYXAL_OPENAI_MODEL": "test-model",
                "NYXAL_OPENAI_BASE_URL": base,
            }, clear=True):
                self.assertFalse(api.provider_configured("openai"))

    def test_redirect_handler_refuses_redirects(self):
        handler = api._RejectRedirects()
        request = Request("https://api.openai.com/v1/responses")
        self.assertIsNone(
            handler.redirect_request(
                request, None, 302, "Found", {}, "https://attacker.invalid/collect"
            )
        )

    def test_openai_request_disables_storage_and_bounds_history(self):
        history = [
            {"role": "user", "content": f"message-{index}"}
            for index in range(31)
        ]
        history.insert(-1, {"role": "system", "content": "must be filtered"})
        fake_response = io.BytesIO(b'{"output_text":"response-ok"}')
        with patch.dict(os.environ, {
            "NYXAL_OPENAI_API_KEY": "test-openai-key",
            "NYXAL_OPENAI_MODEL": "test-model",
        }, clear=True):
            with patch("nixal_responses_api.build_opener") as build:
                build.return_value.open.return_value.__enter__.return_value = fake_response
                answer = api.ask("openai", "current question", "S" * 17000, history)

        self.assertEqual(answer, "response-ok")
        self.assertIsInstance(build.call_args.args[0], api._RejectRedirects)
        request = build.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-openai-key")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertFalse(payload["store"])
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(len(payload["instructions"]), 16000)
        self.assertEqual(len(payload["input"]), 21)
        self.assertEqual(payload["input"][0]["content"], "message-12")
        self.assertEqual(payload["input"][-1]["content"], "current question")
        self.assertTrue(all(item["role"] in {"user", "assistant"} for item in payload["input"]))

    def test_grok_parses_structured_output_without_openai_store_flag(self):
        response_body = (
            b'{"output":[{"type":"message","role":"assistant","content":'
            b'[{"type":"output_text","text":"Grok response"}]}]}'
        )
        fake_response = io.BytesIO(response_body)
        with patch.dict(os.environ, {
            "NYXAL_GROK_API_KEY": "test-grok-key",
            "NYXAL_GROK_MODEL": "test-model",
        }, clear=True):
            with patch("nixal_responses_api.build_opener") as build:
                build.return_value.open.return_value.__enter__.return_value = fake_response
                answer = api.ask("grok", "question", "instructions")

        self.assertEqual(answer, "Grok response")
        request = build.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.x.ai/v1/responses")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertNotIn("store", payload)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-grok-key")

    def test_provider_http_error_does_not_leak_response_body(self):
        fake_error_body = io.BytesIO(b"PRIVATE_PROVIDER_ERROR_BODY")
        http_error = HTTPError(
            "https://api.openai.com/v1/responses",
            403,
            "Forbidden",
            {},
            fake_error_body,
        )
        with patch.dict(os.environ, {
            "NYXAL_OPENAI_API_KEY": "test-key",
            "NYXAL_OPENAI_MODEL": "test-model",
        }, clear=True):
            with patch("nixal_responses_api.build_opener") as build:
                build.return_value.open.side_effect = http_error
                with self.assertRaisesRegex(RuntimeError, "HTTP 403") as raised:
                    api.ask("openai", "question", "instructions")
        self.assertNotIn("PRIVATE_PROVIDER_ERROR_BODY", str(raised.exception))
        self.assertNotIn("test-key", str(raised.exception))

    def test_oversized_provider_response_is_rejected(self):
        fake_response = io.BytesIO(b"x" * (2 * 1024 * 1024 + 1))
        with patch.dict(os.environ, {
            "NYXAL_OPENAI_API_KEY": "test-key",
            "NYXAL_OPENAI_MODEL": "test-model",
        }, clear=True):
            with patch("nixal_responses_api.build_opener") as build:
                build.return_value.open.return_value.__enter__.return_value = fake_response
                with self.assertRaisesRegex(RuntimeError, "excedeu 2 MiB"):
                    api.ask("openai", "question", "instructions")


if __name__ == "__main__":
    unittest.main()
