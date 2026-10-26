#!/usr/bin/env python3
from __future__ import annotations
import os
import unittest
from unittest.mock import patch
from nixal_agent_hub import NyxalAgentHub

class TestNyxalAgentHub(unittest.TestCase):
    def test_auto_sem_credenciais_fica_local(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(NyxalAgentHub().resolve_provider(), "nyxal")

    def test_gemini_desativado_mesmo_quando_credencial_existe(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "GEMINI_API_KEY": "legacy-test-key",
            "NYXAL_AGENT_PROVIDER": "gemini",
        }, clear=True):
            hub = NyxalAgentHub()
            self.assertEqual(hub.resolve_provider(), "nyxal")
            self.assertFalse(hub.provider_configured("gemini"))
            with self.assertRaises(ValueError):
                hub.resolve_provider("gemini")

    def test_auto_permanece_local_mesmo_com_credenciais_remotas(self):
        with patch.dict(os.environ, {
            "NYXAL_HERMES_API_KEY": "test-key",
            "NYXAL_GEMINI_API_KEY": "gemini-key",
            "LETTA_AGENT_ID": "agent",
            "LETTA_API_KEY": "letta-key",
            "LETTA_BASE_URL": "https://api.letta.com",
            "NYXAL_AGENT_PROVIDER": "auto",
        }, clear=True):
            hub = NyxalAgentHub()
            self.assertEqual(hub.resolve_provider(), "nyxal")
            self.assertFalse(hub.provider_configured("hermes"))
            self.assertFalse(hub.provider_configured("letta"))

    def test_auto_nao_tenta_provedores_externos(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_HERMES_API_KEY": "test-hermes",
            "NYXAL_AGENT_PROVIDER": "auto",
        }, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "_responder_provedor") as remote:
                result = hub.responder("Olá", provedor="auto")
        self.assertTrue(result["fallback_local"])
        self.assertEqual(result["provedor"], "nyxal")
        self.assertEqual(result["provedores_tentados"], [])
        remote.assert_not_called()

    def test_gemini_chat_nao_e_invocado_por_nenhum_roteamento_publico(self):
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "_ask_gemini") as gemini:
                result = hub.responder("Olá", provedor="auto")
        self.assertTrue(result["fallback_local"])
        gemini.assert_not_called()

    def test_provedores_externos_explicitos_sao_bloqueados(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_HERMES_API_KEY": "test-key",
            "LETTA_AGENT_ID": "agent",
            "LETTA_API_KEY": "test-key",
        }, clear=True):
            hub = NyxalAgentHub()
            for provider in ("gemini", "hermes", "letta"):
                with self.subTest(provider=provider):
                    with self.assertRaises(ValueError):
                        hub.resolve_provider(provider)

    def test_chat_api_forces_local_nyxal_even_when_client_requests_gemini(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parent / "nyxal_web_api.py").read_text(encoding="utf-8")
        self.assertIn('provedor = "nyxal"', source)
        self.assertIn("ignora seleções antigas de Gemini", source)

    def test_bloqueia_url_arbitraria_para_hermes_e_letta(self):
        with patch.dict(os.environ, {
            "NYXAL_HERMES_API_KEY": "test",
            "NYXAL_HERMES_BASE_URL": "https://example.invalid/v1",
            "LETTA_AGENT_ID": "agent",
            "LETTA_API_KEY": "private-test-key",
            "LETTA_BASE_URL": "https://example.invalid",
        }, clear=True):
            hub = NyxalAgentHub()
            self.assertFalse(hub.provider_configured("hermes"))
            self.assertFalse(hub.provider_configured("letta"))

    def test_letta_nao_responde_chat_no_modo_somente_nyxal(self):
        with patch.dict(os.environ, {
            "LETTA_AGENT_ID": "agent",
            "LETTA_API_KEY": "private-test-key",
            "LETTA_BASE_URL": "https://api.letta.com",
        }, clear=True):
            self.assertFalse(NyxalAgentHub().provider_configured("letta"))
            self.assertEqual(NyxalAgentHub().resolve_provider(), "nyxal")

    def test_fallback_local_e_explicito_no_retorno(self):
        with patch.dict(os.environ, {}, clear=True):
            result = NyxalAgentHub().responder("Olá", provedor="auto")
            self.assertTrue(result["fallback_local"])
            self.assertEqual(result["provedor"], "nyxal")

    def test_identidade_versionada_e_compartilhada_com_os_provedores(self):
        prompt = NyxalAgentHub()._system_prompt_base()
        self.assertIn("Nyxal", prompt)
        self.assertIn("assistente feminina", prompt)
        self.assertIn("dados não confiáveis", prompt)
        self.assertIn("observação não autoriza alterações", prompt)

    def test_prompt_fallback_se_arquivo_de_identidade_nao_estiver_disponivel(self):
        hub = NyxalAgentHub()
        with patch("nixal_agent_hub.Path.read_text", side_effect=OSError("arquivo ausente")):
            self.assertEqual(hub._system_prompt_base(), hub.PROMPT_BASE)

    def test_status_marca_chat_externo_desativado_mesmo_com_chaves(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_HERMES_API_KEY": "test-key",
            "LETTA_AGENT_ID": "agent",
            "LETTA_API_KEY": "test-key",
        }, clear=True):
            status = NyxalAgentHub().contexto()
            self.assertEqual(status["modo_conversa"], "somente_nyxal_local")
            self.assertEqual(status["provedor_resolvido"], "nyxal")
            for provider in ("gemini", "hermes", "letta"):
                self.assertFalse(status["provedores"][provider]["configurado"])
                self.assertFalse(status["provedores"][provider]["habilitado"])
            self.assertEqual(status["voz"]["voz_configurada"], "pf_dora")

if __name__ == "__main__":
    unittest.main(verbosity=2)
