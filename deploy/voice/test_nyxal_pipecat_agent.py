#!/usr/bin/env python3
"""Fast, microphone-free contract tests for the optional voice adapter."""

import unittest

from nyxal_pipecat_agent import _extract_reply, _spoken_text


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

    def test_removes_common_markdown_without_changing_words(self):
        self.assertEqual(
            _spoken_text("## Status\n- Voz **feminina** ativada."),
            "Status Voz feminina ativada.",
        )


if __name__ == "__main__":
    unittest.main()
