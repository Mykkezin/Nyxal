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

    def test_gemini_selecionado_quando_configurado(self):
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            self.assertEqual(NyxalAgentHub().resolve_provider(), "gemini")

    def test_hermes_tem_precedencia_no_modo_auto(self):
        with patch.dict(os.environ, {
            "NYXAL_HERMES_API_KEY": "test-key",
            "NYXAL_GEMINI_API_KEY": "gemini-key",
        }, clear=True):
            self.assertEqual(NyxalAgentHub().resolve_provider(), "hermes")

    def test_auto_recorre_ao_nucleo_local_se_gemini_indisponivel(self):
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "provider_configured", side_effect=lambda name: name == "gemini"):
                with patch.object(hub, "_responder_provedor", side_effect=RuntimeError("provedor fora do ar")):
                    result = hub.responder("Olá", provedor="auto")
        self.assertTrue(result["fallback_local"])
        self.assertEqual(result["provedor"], "nyxal")
        self.assertEqual(result["provedores_tentados"], ["gemini: RuntimeError"])

    def test_provedor_explicito_nao_configurado_falha(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                NyxalAgentHub().resolve_provider("gemini")

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

    def test_letta_cloud_so_usa_dominio_oficial(self):
        with patch.dict(os.environ, {
            "LETTA_AGENT_ID": "agent",
            "LETTA_API_KEY": "private-test-key",
            "LETTA_BASE_URL": "https://api.letta.com",
        }, clear=True):
            self.assertTrue(NyxalAgentHub().provider_configured("letta"))

    def test_fallback_local_e_explicito_no_retorno(self):
        with patch.dict(os.environ, {}, clear=True):
            result = NyxalAgentHub().responder("Olá", provedor="auto")
            self.assertTrue(result["fallback_local"])
            self.assertEqual(result["provedor"], "nyxal")

    def test_status_nao_declara_provedores_remotos_conectados_sem_chaves(self):
        with patch.dict(os.environ, {}, clear=True):
            status = NyxalAgentHub().contexto()
            self.assertFalse(status["provedores"]["gemini"]["configurado"])
            self.assertFalse(status["provedores"]["hermes"]["configurado"])
            self.assertEqual(status["voz"]["voz_configurada"], "pf_dora")

if __name__ == "__main__":
    unittest.main(verbosity=2)
