#!/usr/bin/env python3
from __future__ import annotations
import os
import unittest
from unittest.mock import patch
from urllib.request import Request
from nixal_agent_hub import NyxalAgentHub, _RejectProviderRedirects

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
            "NYXAL_AGENT_PROVIDER": "auto",
        }, clear=True):
            hub = NyxalAgentHub()
            self.assertEqual(hub.resolve_provider(), "nyxal")
            self.assertFalse(hub.provider_configured("hermes"))

    def test_auto_nao_tenta_provedores_externos(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_HERMES_API_KEY": "hermes-key",
            "NYXAL_AGENT_PROVIDER": "auto",
        }, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "_responder_provedor") as remote:
                result = hub.responder("Olá", provedor="auto")
        self.assertTrue(result["fallback_local"])
        self.assertEqual(result["provedor"], "nyxal")
        remote.assert_not_called()

    def test_gemini_chat_nao_e_invocado_pelo_roteamento_publico(self):
        with patch.dict(os.environ, {"NYXAL_GEMINI_API_KEY": "test-key"}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "_ask_gemini") as gemini:
                result = hub.responder("Olá", provedor="auto")
        self.assertTrue(result["fallback_local"])
        gemini.assert_not_called()

    def test_provedores_externos_explicitos_sao_bloqueados(self):
        with patch.dict(os.environ, {
            "NYXAL_GEMINI_API_KEY": "test-key",
            "NYXAL_OPENAI_API_KEY": "test-key",
            "NYXAL_OPENAI_MODEL": "test-model",
            "NYXAL_GROK_API_KEY": "test-key",
            "NYXAL_GROK_MODEL": "test-model",
        }, clear=True):
            hub = NyxalAgentHub()
            for provider in ("gemini", "hermes", "letta", "openai", "grok"):
                with self.subTest(provider=provider):
                    with self.assertRaises(ValueError):
                        hub.resolve_provider(provider)
                    self.assertFalse(hub.provider_configured(provider))

    def test_chat_api_forces_local_nyxal_even_when_client_requests_gemini(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parent / "nyxal_web_api.py").read_text(encoding="utf-8")
        self.assertIn('provedor = "nyxal"', source)
        self.assertIn("ignora configurações antigas de Gemini", source)

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
            "NYXAL_OPENAI_API_KEY": "test-key",
            "NYXAL_OPENAI_MODEL": "test-model",
        }, clear=True):
            status = NyxalAgentHub().contexto()
            self.assertEqual(status["modo_conversa"], "somente_nyxal_local")
            self.assertEqual(status["provedor_resolvido"], "nyxal")
            for provider in ("gemini", "hermes", "letta", "openai", "grok"):
                self.assertFalse(status["provedores"][provider]["configurado"])
            self.assertEqual(status["voz"]["voz_configurada"], "pf_dora")


    def test_external_core_history_is_not_duplicated_in_hub_memory(self):
        hub = NyxalAgentHub()
        external_history = [
            {"role": "user", "content": "pergunta anterior"},
            {"role": "assistant", "content": "resposta anterior"},
        ]
        with patch.object(hub, "_system_prompt_base", return_value="identidade"):
            with patch.object(hub, "_letta_memory_context", return_value=""):
                with patch("nixal_agent_hub.ask_responses_api", return_value="resposta atual"):
                    result = hub._responder_provedor(
                        "pergunta atual",
                        "openai",
                        "sessao-core",
                        None,
                        historico_externo=external_history,
                    )
        self.assertTrue(result["sucesso"])
        self.assertEqual(hub._historico("sessao-core"), [])

    def test_shared_provider_client_rejects_redirects(self):
        handler = _RejectProviderRedirects()
        request = Request("https://generativelanguage.googleapis.com/v1beta/models")
        self.assertIsNone(
            handler.redirect_request(
                request, None, 307, "Temporary Redirect", {},
                "https://attacker.invalid/collect",
            )
        )

    def test_openai_and_grok_chat_remain_disabled_even_with_credentials(self):
        with patch.dict(os.environ, {
            "NYXAL_OPENAI_API_KEY": "test-openai-key",
            "NYXAL_OPENAI_MODEL": "test-model",
            "NYXAL_GROK_API_KEY": "test-grok-key",
            "NYXAL_GROK_MODEL": "test-model",
        }, clear=True):
            hub = NyxalAgentHub()
            self.assertFalse(hub.provider_configured("openai"))
            self.assertFalse(hub.provider_configured("grok"))
            self.assertEqual(hub.resolve_provider(), "nyxal")

    def test_openai_responses_api_disables_storage_and_redirects(self):
        with patch.dict(os.environ, {
            "NYXAL_OPENAI_API_KEY": "test-openai-key",
            "NYXAL_OPENAI_MODEL": "test-model",
        }, clear=True):
            with patch("nixal_responses_api.build_opener") as opener:
                response = __import__("io").BytesIO(
                    b'{"output_text":"resposta de teste"}'
                )
                opener.return_value.open.return_value.__enter__.return_value = response
                answer = __import__("nixal_responses_api").ask(
                    "openai", "pergunta", "identidade", []
                )
        self.assertEqual(answer, "resposta de teste")
        self.assertTrue(opener.called)
        self.assertEqual(opener.return_value.open.call_args.args[0].full_url, "https://api.openai.com/v1/responses")
        sent = __import__("json").loads(opener.return_value.open.call_args.args[0].data.decode("utf-8"))
        self.assertFalse(sent["store"])
        self.assertEqual(sent["model"], "test-model")

    def test_grok_responses_api_uses_only_official_host(self):
        with patch.dict(os.environ, {
            "NYXAL_GROK_API_KEY": "test-grok-key",
            "NYXAL_GROK_MODEL": "test-model",
        }, clear=True):
            with patch("nixal_responses_api.build_opener") as opener:
                response = __import__("io").BytesIO(
                    b'{"output":[{"type":"message","role":"assistant","content":[{"type":"output_text","text":"resposta Grok"}]}]}'
                )
                response.__enter__ = lambda: response
                response.__exit__ = lambda *args: None
                opener.return_value.open.return_value.__enter__.return_value = response
                answer = __import__("nixal_responses_api").ask(
                    "grok", "pergunta", "identidade", []
                )
        self.assertEqual(answer, "resposta Grok")
        self.assertEqual(opener.return_value.open.call_args.args[0].full_url, "https://api.x.ai/v1/responses")
        sent = __import__("json").loads(opener.return_value.open.call_args.args[0].data.decode("utf-8"))
        self.assertNotIn("store", sent)

    def test_auto_route_for_tools_prefers_hermes(self):
        with patch.dict(os.environ, {}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "provider_configured", return_value=True):
                with patch.object(hub, "_responder_provedor", side_effect=lambda mensagem, resolved, sessao, contexto: {
                    "sucesso": True, "provedor": resolved, "resposta": "ok", "sessao": sessao
                }) as call:
                    result = hub.responder("Execute os testes no repositório do GitHub.")
        self.assertEqual(result["roteamento"]["classe"], "ferramentas_e_operacao")
        self.assertEqual(result["provedor"], "hermes")
        self.assertEqual(call.call_args.args[1], "hermes")

    def test_auto_route_general_reasoning_prefers_openai_when_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "provider_configured", return_value=True):
                with patch.object(hub, "_responder_provedor", side_effect=lambda mensagem, resolved, sessao, contexto: {
                    "sucesso": True, "provedor": resolved, "resposta": "ok", "sessao": sessao
                }):
                    result = hub.responder("Explique como funciona a relatividade geral.")
        self.assertEqual(result["roteamento"]["classe"], "conhecimento_geral")
        self.assertEqual(result["provedor"], "openai")

    def test_memory_intent_prefers_letta_and_telemetry_omits_prompt(self):
        with patch.dict(os.environ, {}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "provider_configured", return_value=True):
                with patch.object(hub, "_responder_provedor", side_effect=lambda mensagem, resolved, sessao, contexto: {
                    "sucesso": True, "provedor": resolved, "resposta": "ok", "sessao": sessao
                }):
                    result = hub.responder("Me lembra o que combinamos na conversa anterior.")
        self.assertEqual(result["roteamento"]["classe"], "memoria_continuidade")
        self.assertEqual(result["provedor"], "letta")
        telemetry = hub._routing_telemetry.snapshot()
        self.assertEqual(telemetry["eventos_em_memoria"], 1)
        latest = telemetry["ultimos_eventos"][0]
        self.assertNotIn("mensagem", latest)
        self.assertNotIn("prompt", latest)
        self.assertIn("latencia_ms", latest)

    def test_intent_classifier_normalizes_accents_and_does_not_match_ram_as_memory(self):
        from nixal_intent_router import classificar_intencao
        self.assertEqual(
            classificar_intencao("Me lembra o que combinamos")["classe"],
            "memoria_continuidade",
        )
        self.assertEqual(
            classificar_intencao("Quanto de memória RAM está em uso?")["classe"],
            "conhecimento_geral",
        )

    def test_hub_registers_as_shared_runtime_instance(self):
        from nixal_agent_hub import get_shared_agent_hub
        hub = NyxalAgentHub()
        self.assertIs(get_shared_agent_hub(), hub)

    def test_reverse_engineering_gets_dedicated_route(self):
        from nixal_intent_router import classificar_intencao, ordem_provedores
        result = classificar_intencao("Faça engenharia reversa autorizada deste repositório")
        self.assertEqual(result["classe"], "engenharia_reversa")
        self.assertEqual(ordem_provedores("engenharia_reversa")[0], "hermes")

    def test_reverse_engineering_adds_scope_and_evidence_guidance(self):
        with patch.dict(os.environ, {}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "provider_configured", return_value=True):
                with patch.object(hub, "_responder_provedor", side_effect=lambda mensagem, resolved, sessao, contexto, **kwargs: {
                    "sucesso": True, "provedor": resolved, "resposta": "análise", "sessao": sessao,
                    "prompt_extra_capturado": kwargs.get("prompt_sistema_extra", ""),
                }):
                    result = hub.responder("Faça engenharia reversa autorizada deste repositório")
        self.assertEqual(result["roteamento"]["classe"], "engenharia_reversa")
        self.assertIn("permissão para examinar", result["prompt_extra_capturado"])
        self.assertIn("resultado verificável", result["prompt_extra_capturado"])
        self.assertIn("Playbook da habilidade versionado no projeto", result["prompt_extra_capturado"])
        self.assertIn("Critérios de conclusão", result["prompt_extra_capturado"])

    def test_cybersecurity_and_data_science_use_specialist_prompts(self):
        from nixal_intent_router import classificar_intencao
        self.assertEqual(
            classificar_intencao("Ative o modo de cibersegurança defensiva")[ "classe" ],
            "ciberseguranca_defensiva",
        )
        self.assertEqual(
            classificar_intencao("Quero fazer uma análise de Data Science com dataset"),
            {"classe": "ciencia_dados", "motivo": "O pedido envolve análise de dados, estatística ou modelagem."},
        )
        with patch.dict(os.environ, {}, clear=True):
            hub = NyxalAgentHub()
            with patch.object(hub, "provider_configured", return_value=True):
                with patch.object(hub, "_responder_provedor", side_effect=lambda mensagem, resolved, sessao, contexto, **kwargs: {
                    "sucesso": True, "provedor": resolved, "resposta": "análise", "sessao": sessao,
                    "prompt_extra_capturado": kwargs.get("prompt_sistema_extra", ""),
                }):
                    cyber = hub.responder("Ative o modo de cibersegurança defensiva")
                    data = hub.responder("Quero fazer uma análise de Data Science com dataset")
        self.assertIn("cibersegurança defensiva", cyber["prompt_extra_capturado"])
        self.assertIn("Data Science", data["prompt_extra_capturado"])
        self.assertIn("Playbook da habilidade versionado no projeto", cyber["prompt_extra_capturado"])
        self.assertIn("Playbook da habilidade versionado no projeto", data["prompt_extra_capturado"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
