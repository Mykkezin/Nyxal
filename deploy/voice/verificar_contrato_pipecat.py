#!/usr/bin/env python3
"""Fast, microphone-free contract tests for the optional voice adapter."""

import os
import unittest
from unittest.mock import patch

from nyxal_pipecat_agent import (
    _api_request_headers,
    _chat_payload,
    _extract_reply,
    _returned_session_id,
    _spoken_text,
)


class NyxalPipecatContractTests(unittest.TestCase):
    def test_sends_configured_bearer_token_to_loopback_api(self):
        with patch.dict(os.environ, {"NYXAL_API_TOKEN": "local-secret"}, clear=True):
            headers = _api_request_headers("http://127.0.0.1:8010")
        self.assertEqual(headers["Authorization"], "Bearer local-secret")

    def test_never_sends_local_token_to_remote_api(self):
        with patch.dict(os.environ, {"NYXAL_API_TOKEN": "local-secret"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "localhost/loopback"):
                _api_request_headers("https://nyxal.example")

    def test_rejects_remote_api_even_without_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "localhost/loopback"):
                _api_request_headers("https://nyxal.example")

    def test_rejects_api_urls_with_embedded_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "sem credenciais"):
                _api_request_headers("http://user:pass@127.0.0.1:8010")

    def test_rejects_unexpected_local_api_port(self):
        with patch.dict(os.environ, {"NYXAL_API_PORT": "8010"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "porta 9999"):
                _api_request_headers("http://127.0.0.1:9999")

    def test_reads_the_existing_top_level_chat_response(self):
        self.assertEqual(
            _extract_reply({"sucesso": True, "resposta": "Olá, **Myke**!"}),
            "Olá, Myke!",
        )

    def test_reads_the_nested_core_response_fallback(self):
        payload = {
            "valor": {
                "transporte": {
                    "resposta": {"resposta": "A sessão continua ativa."}
                }
            }
        }
        self.assertEqual(
            _extract_reply(payload),
            "A sessão continua ativa.",
        )

    def test_empty_or_unrecognized_response_is_not_spoken(self):
        self.assertEqual(_extract_reply({"sucesso": False}), "")
        self.assertEqual(_extract_reply(None), "")

    def test_first_request_lets_nyxal_create_the_session(self):
        self.assertEqual(
            _chat_payload("Olá, Nyxal.", None),
            {"mensagem": "Olá, Nyxal."},
        )

    def test_follow_up_reuses_the_server_created_session(self):
        self.assertEqual(
            _chat_payload("E a segunda pergunta?", "sessao-real-123"),
            {
                "mensagem": "E a segunda pergunta?",
                "sessao": "sessao-real-123",
            },
        )

    def test_adopts_session_returned_by_the_api(self):
        self.assertEqual(
            _returned_session_id(
                {"sucesso": True, "sessao": "sessao-real-123"},
                None,
            ),
            "sessao-real-123",
        )
        self.assertEqual(
            _returned_session_id({"sessao": ""}, "sessao-atual"),
            "sessao-atual",
        )

    def test_removes_common_markdown_without_changing_words(self):
        self.assertEqual(
            _spoken_text("## Status\n- Voz **feminina** ativada."),
            "Status. Voz feminina ativada.",
        )


if __name__ == "__main__":
    unittest.main()
