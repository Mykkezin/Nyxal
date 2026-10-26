#!/usr/bin/env python3
"""Regressions for routing the primary chat through configured model providers."""
from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# This suite injects a fake client; importing the dialogue must not require Ollama.
sys.modules.setdefault("ollama", types.SimpleNamespace())

from nixal_agent_hub import NyxalAgentHub
from nixal_dialogo_qwen import DialogoQwenNixal


class FakeLocalChat:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return {"message": {"content": "Resposta local Qwen."}}


class TestNyxalPrimaryDialogueRouter(unittest.TestCase):
    def test_primary_dialogue_routes_when_cloud_provider_is_configured(self):
        client = FakeLocalChat()
        hub = Mock()
        hub.provider_configured.side_effect = lambda name: name == "openai"
        hub.responder.return_value = {
            "sucesso": True,
            "estado": "resposta_gerada",
            "provedor": "openai",
            "resposta": "Resposta natural pelo provedor configurado.",
            "roteamento": {"classe": "conhecimento_geral", "provedor": "openai"},
        }
        dialog = DialogoQwenNixal(cliente=client)
        dialog.agent_hub = hub
        previous = [
            {"papel": "user", "texto": "Qual é a ideia central?"},
            {"papel": "assistant", "texto": "A ideia central é preservar contexto."},
        ]

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "auto"}, clear=True):
            answer = dialog.responder("Explique com um exemplo.", historico=previous, sessao="sessao-teste")

        self.assertTrue(answer["sucesso"])
        self.assertEqual(answer["origem"], "nixal_agent_hub")
        self.assertEqual(answer["modelo"], "openai")
        self.assertEqual(answer["roteamento"]["provedor"], "openai")
        client_calls = client.calls
        self.assertEqual(client_calls, [])
        kwargs = hub.responder.call_args.kwargs
        self.assertEqual(kwargs["sessao"], "sessao-teste")
        self.assertEqual(kwargs["provedor"], "auto")
        self.assertEqual(kwargs["historico_externo"], [
            {"role": "user", "content": "Qual é a ideia central?"},
            {"role": "assistant", "content": "A ideia central é preservar contexto."},
        ])
        self.assertIn("naturalidade", kwargs["prompt_sistema_extra"])

    def test_primary_dialogue_keeps_local_qwen_when_no_remote_is_configured(self):
        client = FakeLocalChat()
        hub = Mock()
        hub.provider_configured.return_value = False
        dialog = DialogoQwenNixal(cliente=client)
        dialog.agent_hub = hub

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "auto"}, clear=True):
            answer = dialog.responder("Vamos conversar.")

        self.assertTrue(answer["sucesso"])
        self.assertEqual(answer["resposta"], "Resposta local Qwen.")
        self.assertEqual(answer["origem"], DialogoQwenNixal.FONTE)
        self.assertEqual(len(client.calls), 1)
        hub.responder.assert_not_called()

    def test_primary_dialogue_falls_back_to_local_if_remote_provider_fails(self):
        client = FakeLocalChat()
        hub = Mock()
        hub.provider_configured.side_effect = lambda name: name == "openai"
        hub.responder.side_effect = RuntimeError("provider timeout")
        dialog = DialogoQwenNixal(cliente=client)
        dialog.agent_hub = hub

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "auto"}, clear=True):
            answer = dialog.responder("Continue a conversa.", sessao="s-2")

        self.assertTrue(answer["sucesso"])
        self.assertEqual(answer["resposta"], "Resposta local Qwen.")
        self.assertEqual(len(client.calls), 1)
        hub.responder.assert_called_once()

    def test_dialogue_reuses_shared_runtime_hub_without_api_injection(self):
        shared = NyxalAgentHub()
        shared.responder = Mock(return_value={
            "sucesso": True,
            "estado": "resposta_gerada",
            "provedor": "openai",
            "resposta": "Resposta do hub compartilhado.",
            "roteamento": {"classe": "conhecimento_geral", "provedor": "openai"},
        })
        client = FakeLocalChat()
        dialog = DialogoQwenNixal(cliente=client)

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "openai"}, clear=True):
            answer = dialog.responder("Continue a conversa.", sessao="sessao-compartilhada")

        self.assertTrue(answer["sucesso"])
        self.assertEqual(answer["origem"], "nixal_agent_hub")
        self.assertEqual(answer["resposta"], "Resposta do hub compartilhado.")
        shared.responder.assert_called_once()
        self.assertEqual(shared.responder.call_args.kwargs["sessao"], "sessao-compartilhada")
        self.assertEqual(client.calls, [])

    def test_local_qwen_receives_reverse_engineering_specialist_guidance(self):
        client = FakeLocalChat()
        hub = Mock()
        hub.provider_configured.return_value = False
        dialog = DialogoQwenNixal(cliente=client)
        dialog.agent_hub = hub

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "auto"}, clear=True):
            answer = dialog.responder("Faça engenharia reversa autorizada deste repositório")

        self.assertTrue(answer["sucesso"])
        self.assertEqual(answer["origem"], DialogoQwenNixal.FONTE)
        system_prompt = client.calls[0]["messages"][0]["content"]
        self.assertIn("permissão para examinar", system_prompt)
        self.assertIn("Estilo conversacional", system_prompt)
        self.assertIn("Playbook da habilidade versionado no projeto", system_prompt)
        hub.responder.assert_not_called()

    def test_hub_passes_external_history_and_voice_style_to_provider(self):
        hub = NyxalAgentHub()
        history = [
            {"role": "user", "content": "Mensagem antiga"},
            {"role": "assistant", "content": "Resposta antiga"},
        ]
        with patch.object(hub, "_system_prompt_base", return_value="Prompt base da Nyxal"):
            with patch.object(hub, "_letta_memory_context", return_value=""):
                with patch("nixal_agent_hub.ask_responses_api", return_value="Resposta atual") as ask:
                    result = hub._responder_provedor(
                        "Mensagem atual",
                        "openai",
                        "sessao-privada",
                        None,
                        historico_externo=history,
                        prompt_sistema_extra="Converse com naturalidade em português.",
                    )
        self.assertEqual(result["resposta"], "Resposta atual")
        args = ask.call_args.args
        self.assertEqual(args[0:2], ("openai", "Mensagem atual"))
        self.assertIn("Converse com naturalidade", args[2])
        self.assertEqual(args[3], history)

    def test_primary_api_injects_router_and_core_passes_session(self):
        root = Path(__file__).resolve().parent
        api_source = (root / "nyxal_web_api.py").read_text(encoding="utf-8")
        core_source = (root / "nixal_nucleo_conversacional.py").read_text(encoding="utf-8")
        self.assertIn("NUCLEO_CONVERSACIONAL.dialogo.agent_hub = AGENTE_NYXAL", api_source)
        self.assertIn("historico=historico,\n                sessao=sessao,", core_source)


    def test_explicit_local_provider_overrides_auto_environment(self):
        client = FakeLocalChat()
        hub = Mock()
        hub.provider_configured.return_value = True
        dialog = DialogoQwenNixal(cliente=client)
        dialog.agent_hub = hub

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "auto"}, clear=True):
            answer = dialog.responder("Vamos conversar localmente.", provedor="nyxal")

        self.assertTrue(answer["sucesso"])
        self.assertEqual(answer["origem"], DialogoQwenNixal.FONTE)
        self.assertEqual(answer["resposta"], "Resposta local Qwen.")
        hub.responder.assert_not_called()
        self.assertEqual(len(client.calls), 1)

    def test_explicit_provider_receives_read_only_system_context(self):
        client = FakeLocalChat()
        hub = Mock()
        hub.responder.return_value = {
            "sucesso": True,
            "estado": "resposta_gerada",
            "provedor": "openai",
            "resposta": "Resumo contextual.",
            "roteamento": {"classe": "conhecimento_geral", "provedor": "openai"},
        }
        dialog = DialogoQwenNixal(cliente=client)
        dialog.agent_hub = hub
        contexto = {"observabilidade": {"cpu_percent": 23.0}}

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "nyxal"}, clear=True):
            answer = dialog.responder(
                "Resuma o estado atual.",
                historico=[{"papel": "user", "texto": "Contexto anterior"}],
                sessao="sessao-contextual",
                provedor="openai",
                contexto_sistema=contexto,
            )

        self.assertTrue(answer["sucesso"])
        self.assertEqual(answer["modelo"], "openai")
        kwargs = hub.responder.call_args.kwargs
        self.assertEqual(kwargs["provedor"], "openai")
        self.assertEqual(kwargs["sessao"], "sessao-contextual")
        self.assertEqual(kwargs["contexto_sistema"], contexto)
        self.assertEqual(kwargs["historico_externo"], [
            {"role": "user", "content": "Contexto anterior"},
        ])
        self.assertEqual(client.calls, [])

    def test_explicit_remote_provider_failure_does_not_silently_switch_models(self):
        client = FakeLocalChat()
        hub = Mock()
        hub.responder.side_effect = RuntimeError("PRIVATE_PROVIDER_SECRET")
        dialog = DialogoQwenNixal(cliente=client)
        dialog.agent_hub = hub

        with patch.dict(os.environ, {"NYXAL_AGENT_PROVIDER": "auto"}, clear=True):
            answer = dialog.responder("Continue.", sessao="sessao-remote", provedor="openai")

        self.assertFalse(answer["sucesso"])
        self.assertEqual(answer["estado"], "provedor_indisponivel")
        self.assertEqual(answer["erro"], "O provedor selecionado não está disponível.")
        self.assertNotIn("PRIVATE_PROVIDER_SECRET", str(answer))
        self.assertEqual(client.calls, [])

if __name__ == "__main__":
    unittest.main()
