#!/usr/bin/env python3
"""Fast, microphone-free contract tests for the optional voice adapter."""

import unittest

from nyxal_pipecat_agent import (
    _chat_payload,
    _extract_reply,
    _returned_session_id,
    _spoken_text,
)


class NyxalPipecatContractTests(unittest.TestCase):
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
            "Status Voz feminina ativada.",
        )


if __name__ == "__main__":
    unittest.main()
