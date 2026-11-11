from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("ollama", types.SimpleNamespace())

from nixal_agent_hub import NyxalAgentHub
from nixal_dialogo_qwen import DialogoQwenNixal


class TestProvedorConversacional(unittest.TestCase):
    def test_openai_explicito_recebe_historico_e_retorna_modelo(self):
        env = {
            "NYXAL_OPENAI_API_KEY": "test-key",
            "NYXAL_OPENAI_MODEL": "modelo-teste",
            "NYXAL_AGENT_PROVIDER": "nyxal",
        }
        with patch.dict(os.environ, env, clear=True):
            hub = NyxalAgentHub()
            dialogo = DialogoQwenNixal(cliente=object())
            dialogo.agent_hub = hub
            with patch("nixal_agent_hub.ask_responses_api", return_value="resposta simulada") as ask:
                resultado = dialogo.responder(
                    "pergunta atual",
                    historico=[{"papel": "user", "texto": "contexto anterior"}],
                    sessao="sessao-teste",
                    provedor="openai",
                )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["resposta"], "resposta simulada")
        self.assertEqual(resultado["modelo"], "modelo-teste")
        self.assertEqual(resultado["provedor"], "openai")
        self.assertEqual(ask.call_args.args[1:3], ("pergunta atual", unittest.mock.ANY))
        self.assertEqual(ask.call_args.args[3], [{"role": "user", "content": "contexto anterior"}])

    def test_provedor_externo_sem_configuracao_e_recusado(self):
        with patch.dict(os.environ, {}, clear=True):
            hub = NyxalAgentHub()
            self.assertFalse(hub.provider_configured("openai"))
            with self.assertRaisesRegex(RuntimeError, "não está configurado"):
                hub.resolve_provider("openai")


if __name__ == "__main__":
    unittest.main(verbosity=2)
