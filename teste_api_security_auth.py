#!/usr/bin/env python3
"""Testes de integração HTTP para os limites de autenticação e CORS da Nyxal."""
from __future__ import annotations

import json

import http.client
import sys
import threading
import types
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

# O teste cobre a fronteira HTTP sem carregar/consultar um modelo real.
ollama_fake = types.ModuleType("ollama")
ollama_fake.chat = lambda **_kwargs: {"message": {"content": "resposta simulada"}}
sys.modules.setdefault("ollama", ollama_fake)

import nyxal_web_api as api  # noqa: E402


class TestSegurancaAPIHTTP(unittest.TestCase):
    def setUp(self) -> None:
        self.token_original = api.API_TOKEN
        self.proxy_original = api.PROXY_MODE
        self.host_original = api.HOST
        self.cors_original = api.CORS_ORIGINS
        api.API_TOKEN = ""
        api.PROXY_MODE = True
        api.HOST = "127.0.0.1"
        api.CORS_ORIGINS = api.parse_allowed_origins("")
        self.server = api.NyxalThreadingHTTPServer(("127.0.0.1", 0), api.NyxalAPIHandler)
        self.server.request_slots = api.BoundedSemaphore(api.MAX_CONCURRENT_HTTP_REQUESTS)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        api.API_TOKEN = self.token_original
        api.PROXY_MODE = self.proxy_original
        api.HOST = self.host_original
        api.CORS_ORIGINS = self.cors_original

    def request_full(
        self, method: str, path: str, *, body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], str]:
        request_headers = {"Content-Length": str(len(body)), "Connection": "close"}
        request_headers.update(headers or {})
        connection = http.client.HTTPConnection(self.host, self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            response_headers = {key.lower(): value for key, value in response.getheaders()}
            text = response.read().decode("utf-8", errors="replace")
            return response.status, response_headers, text
        finally:
            connection.close()

    def request(
        self, method: str, path: str, *, body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        status, _headers, text = self.request_full(method, path, body=body, headers=headers)
        return status, text

    def test_acoes_vps_exigem_autenticacao_quando_expostas(self) -> None:
        with patch.object(api.VPS_NYXOS, "action", return_value={"sucesso": True}) as action:
            status, body = self.request(
                "POST", "/api/vps/action", body=b'{"nome":"vm-teste","acao":"stop"}',
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", body)
        action.assert_not_called()

    def test_chat_stt_e_tts_exigem_token_quando_expostos(self) -> None:
        casos = [
            ("POST", "/api/chat", b'{"mensagem":"teste"}'),
            ("POST", "/api/agent/chat", b'{"mensagem":"teste"}'),
            ("POST", "/api/amd-cloud/check", b"{}"),
            ("POST", "/api/vps/provisionar", b'{"nome":"vm-teste"}'),
            ("POST", "/api/stt", b"audio"),
            ("POST", "/api/tts", b'{"texto":"teste"}'),
            ("POST", "/api/agent/image", b'{"prompt":"teste"}'),
        ]
        for method, route, body in casos:
            with self.subTest(route=route):
                status, response = self.request(
                    method, route, body=body,
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(status, 503)
                self.assertIn("NYXAL_API_TOKEN", response)

    def test_dados_operacionais_exigem_token_em_modo_proxy(self) -> None:
        routes = (
            "/api/vps/status",
            "/api/vps/instances",
            "/api/vps/contexto",
            "/api/amd-cloud/status",
            "/api/agent/status",
            "/api/agent/contexto",
            "/api/integracoes/google/status",
            "/api/integracoes/google/agenda",
            "/api/integracoes/google/contatos",
            "/api/integracoes/google/drive",
            "/api/integracoes/gmail/status",
            "/api/integracoes/gmail/mensagens",
            "/api/integracoes/gmail/mensagem",
            "/api/status",
            "/api/ae5/valor",
            "/api/ae5/datasets",
            "/api/public/status",
            "/api/public/nyxos/contexto",
            "/api/public/residencia",
            "/api/public/delta",
            "/api/public/dataset",
            "/api/public/presenca",
            "/api/public/recursos",
            "/api/public/operacional",
            "/api/public/gateway",
            "/api/public/ae5",
            "/",
            "/display",
            "/display/index.html",
            "/interface/index.html",
        )
        for route in routes:
            with self.subTest(route=route):
                status, body = self.request("GET", route)
                self.assertEqual(status, 503)
                self.assertIn("NYXAL_API_TOKEN", body)

    def test_health_continua_publico_sem_expor_snapshot_operacional(self) -> None:
        status, headers, body = self.request_full("GET", "/health")
        self.assertEqual(status, 200)
        self.assertIn('"estado"', body)
        self.assertIn("x-content-type-options", headers)
        self.assertEqual(headers.get("cache-control"), "no-store")

    def test_modo_proxy_exige_bearer_ate_para_loopback_direto(self) -> None:
        with patch.object(api, "PROXY_MODE", True), patch.object(
            api, "API_TOKEN", "token-de-proxy"
        ):
            with patch.object(api.NUCLEO_CONVERSACIONAL, "processar") as processar:
                status, body = self.request(
                    "POST",
                    "/api/chat",
                    body=b'{"mensagem":"teste"}',
                    headers={"Content-Type": "application/json"},
                )
        self.assertEqual(status, 401)
        self.assertIn("nao_autorizado", body)
        processar.assert_not_called()

    def test_cabecalho_de_proxy_forca_autenticacao_mesmo_em_loopback(self) -> None:
        api.PROXY_MODE = False
        headers_de_proxy = (
            ("X-Forwarded-For", "203.0.113.10"),
            ("X-Forwarded-For", ""),
            ("Forwarded", ""),
            ("X-Real-IP", ""),
        )
        for nome, valor in headers_de_proxy:
            with self.subTest(header=nome, value=valor):
                with patch.object(api.VPS_NYXOS, "action", return_value={"sucesso": True}) as action:
                    status, body = self.request(
                        "POST", "/api/vps/action",
                        body=b'{"nome":"vm-teste","acao":"stop"}',
                        headers={"Content-Type": "application/json", nome: valor},
                    )
                self.assertEqual(status, 503)
                self.assertIn("NYXAL_API_TOKEN", body)
                action.assert_not_called()

    def test_origem_nao_autorizada_bloqueia_acao_antes_do_handler(self) -> None:
        with patch.object(api.VPS_NYXOS, "action", return_value={"sucesso": True}) as action:
            status, body = self.request(
                "POST", "/api/vps/action",
                body=b'{"nome":"vm-atacada","acao":"stop"}',
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://attacker.example",
                },
            )
        self.assertEqual(status, 403)
        self.assertIn("origem_nao_permitida", body)
        action.assert_not_called()

    def test_origem_local_do_display_e_permitida_por_padrao(self) -> None:
        status, headers, _body = self.request_full(
            "GET", "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), "http://localhost:3000")

    def test_html_estatico_recebe_cabecalhos_de_seguranca_e_cors(self) -> None:
        with patch.object(api, "PROXY_MODE", False), patch.object(
            api, "CORS_ORIGINS", api.parse_allowed_origins("")
        ):
            for path in ("/", "/interface/index.html"):
                with self.subTest(path=path):
                    status, headers, _body = self.request_full(
                        "GET", path,
                        headers={"Origin": "http://localhost:3000"},
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(headers.get("referrer-policy"), "no-referrer")
                    self.assertEqual(headers.get("x-content-type-options"), "nosniff")
                    self.assertEqual(headers.get("cache-control"), "no-store")
                    self.assertEqual(
                        headers.get("access-control-allow-origin"),
                        "http://localhost:3000",
                    )

    def test_token_ausente_e_incorreto_sao_rejeitados_quando_configurado(self) -> None:
        api.API_TOKEN = "segredo-configurado"
        status, body = self.request(
            "POST", "/api/chat", body=b'{"mensagem":"teste"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401)
        self.assertIn("nao_autorizado", body)

        status, body = self.request(
            "POST", "/api/chat", body=b'{"mensagem":"teste"}',
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer segredo-incorreto",
            },
        )
        self.assertEqual(status, 403)
        self.assertIn("acesso_negado", body)

        status, body = self.request(
            "POST", "/api/chat", body=b'{"mensagem":"teste"}',
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token-é",
            },
        )
        self.assertEqual(status, 403)
        self.assertIn("acesso_negado", body)

    def test_token_valido_permite_avancar_ate_validacao_do_payload(self) -> None:
        api.API_TOKEN = "token-de-teste"
        status, body = self.request(
            "POST", "/api/chat", body=b"",
            headers={"Authorization": "Bearer token-de-teste"},
        )
        self.assertEqual(status, 400)
        self.assertIn("obrigatório", body)

    def test_loopback_direto_mantem_chat_e_acao_vps_compatíveis(self) -> None:
        api.PROXY_MODE = False
        status, body = self.request("POST", "/api/chat", body=b"")
        self.assertEqual(status, 400)
        self.assertNotIn("NYXAL_API_TOKEN", body)

        with patch.object(api.VPS_NYXOS, "action", return_value={"sucesso": True}) as action:
            status, body = self.request(
                "POST", "/api/vps/action",
                body=b'{"nome":"vm-local","acao":"status"}',
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(status, 200, body)
        action.assert_called_once_with(nome="vm-local", acao="status")

    def test_cors_so_permite_origem_configurada_exatamente(self) -> None:
        api.CORS_ORIGINS = api.parse_allowed_origins("https://display.example")
        status, allowed, _ = self.request_full(
            "GET", "/health", headers={"Origin": "https://display.example"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(allowed.get("access-control-allow-origin"), "https://display.example")
        self.assertEqual(allowed.get("vary"), "Origin")

        status, denied, denied_body = self.request_full(
            "GET", "/health", headers={"Origin": "https://attacker.example"}
        )
        self.assertEqual(status, 403)
        self.assertIn("origem_nao_permitida", denied_body)
        self.assertNotIn("access-control-allow-origin", denied)

        # A mesma allowlist exata vale para respostas de áudio, não apenas JSON.
        # A origem CORS não substitui autenticação quando a origem é remota.
        api.PROXY_MODE = False
        api.API_TOKEN = "token-cors-test"
        with patch.object(api, "generate_kokoro_audio", return_value=b"fake audio"):
            status, audio_headers, audio_body = self.request_full(
                "POST", "/api/tts",
                body=b'{"texto":"teste"}',
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://display.example",
                    "Authorization": "Bearer token-cors-test",
                },
            )
        self.assertEqual(status, 200)
        self.assertEqual(audio_body, "fake audio")
        self.assertEqual(audio_headers.get("access-control-allow-origin"), "https://display.example")
        self.assertEqual(audio_headers.get("cache-control"), "no-store")

    def test_preflight_nao_emite_origem_vazia_ou_wildcard(self) -> None:
        api.CORS_ORIGINS = api.parse_allowed_origins("https://display.example")
        status, allowed, _ = self.request_full(
            "OPTIONS", "/api/chat", headers={"Origin": "https://display.example"}
        )
        self.assertEqual(status, 204)
        self.assertEqual(allowed.get("access-control-allow-origin"), "https://display.example")
        self.assertIn("Authorization", allowed.get("access-control-allow-headers", ""))

        api.CORS_ORIGINS = api.parse_allowed_origins("")
        status, no_origin, _ = self.request_full("OPTIONS", "/api/chat")
        self.assertEqual(status, 204)
        self.assertNotIn("access-control-allow-origin", no_origin)

        try:
            api.CORS_ORIGINS = api.parse_allowed_origins("*")
        except ValueError:
            api.CORS_ORIGINS = frozenset()
        status, wildcard, _ = self.request_full(
            "OPTIONS", "/api/chat", headers={"Origin": "https://attacker.example"}
        )
        self.assertEqual(status, 403)
        self.assertNotIn("access-control-allow-origin", wildcard)

    def test_log_http_nao_imprime_query_string(self) -> None:
        # O teste de 404 deve atravessar a autenticação; a API é configurada
        # com token falso somente para esta instância temporária do teste.
        api.API_TOKEN = "token-log-test"
        with patch("builtins.print") as output:
            status, _body = self.request(
                "GET",
                "/nao-existe?token=CANARY_SECRET_92af",
                headers={"Authorization": "Bearer token-log-test"},
            )
        self.assertEqual(status, 404)
        logs = " ".join(str(call.args) for call in output.call_args_list)
        self.assertNotIn("CANARY_SECRET_92af", logs)
        self.assertNotIn("/nao-existe", logs)
        self.assertIn("GET", logs)
        self.assertIn("status=404", logs)

    def test_origem_remota_exige_bearer_mesmo_com_socket_loopback(self) -> None:
        api.PROXY_MODE = False
        api.API_TOKEN = ""
        api.CORS_ORIGINS = api.parse_allowed_origins("https://display.example")
        with patch.object(
            api.VPS_NYXOS, "action", return_value={"sucesso": True}
        ) as action:
            status, body = self.request(
                "POST",
                "/api/vps/action",
                body=b'{"nome":"vm-remota","acao":"status"}',
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://display.example",
                },
            )
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", body)
        action.assert_not_called()

        # A mesma origem remota é aceita quando o gateway envia Bearer server-side.
        api.API_TOKEN = "token-remoto-valido"
        with patch.object(
            api.VPS_NYXOS, "action", return_value={"sucesso": True}
        ) as action_validada:
            status, body = self.request(
                "POST",
                "/api/vps/action",
                body=b'{"nome":"vm-remota","acao":"status"}',
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://display.example",
                    "Authorization": "Bearer token-remoto-valido",
                },
            )
        self.assertEqual(status, 200, body)
        action_validada.assert_called_once_with(nome="vm-remota", acao="status")

    def test_erro_interno_vps_nao_vaza_detalhes_para_cliente(self) -> None:
        api.PROXY_MODE = True
        api.API_TOKEN = "token-de-teste"
        detalhe_interno = "SEGREDO_INTERNO /root/nyxal.env token=nao-retornar"

        with patch.object(api.VPS_NYXOS, "action", side_effect=RuntimeError(detalhe_interno)) as action:
            status, body = self.request(
                "POST",
                "/api/vps/action",
                body=b'{"nome":"vm-teste","acao":"start"}',
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer token-de-teste",
                },
            )

        self.assertEqual(status, 500)
        self.assertIn("erro_vps", body)
        self.assertIn("A operação de VPS não pôde ser concluída.", body)
        self.assertNotIn("SEGREDO_INTERNO", body)
        self.assertNotIn("/root/nyxal.env", body)
        self.assertNotIn("nao-retornar", body)
        action.assert_called_once()

    def test_erros_internos_audio_chat_google_nao_sao_refletidos(self) -> None:
        api.PROXY_MODE = True
        api.API_TOKEN = "token-de-teste"
        detalhe_interno = "SEGREDO_INTERNO /root/nyxal.env token=nao-retornar"
        auth = {"Authorization": "Bearer token-de-teste"}

        with patch.object(api, "transcribe_audio", side_effect=RuntimeError(detalhe_interno)):
            status, body = self.request(
                "POST", "/api/stt", body=b"audio-de-teste",
                headers={**auth, "Content-Type": "audio/webm"},
            )
        self.assertEqual(status, 500)
        self.assertIn("A transcrição do áudio não pôde ser concluída.", body)
        self.assertNotIn("SEGREDO_INTERNO", body)
        self.assertNotIn("/root/nyxal.env", body)

        resposta_nucleo = {
            "sucesso": True,
            "estado": "resposta_pronta",
            "origem": "nucleo_conversacional_nixal",
            "resposta": "Resposta indisponível.",
            "sessao": "sessao-teste",
            "valor": {
                "texto": "Resposta indisponível.",
                "sessao": "sessao-teste",
                "modo": "dialogo_indisponivel",
            },
        }
        resultado_integracao = {
            "sucesso": True,
            "estado": "mensagem_processada_com_sessao",
            "sessao": "sessao-teste",
            "valor": {"transporte": {"resposta": resposta_nucleo}},
        }
        with patch.object(api.AGENTE_NYXAL, "resolve_provider", return_value="nyxal"):
            with patch.object(
                api.INTEGRACAO_CONVERSACIONAL,
                "processar_mensagem",
                return_value=resultado_integracao,
            ) as processar:
                with patch.object(api.AGENTE_NYXAL, "responder") as responder_direto:
                    status, body = self.request(
                        "POST", "/api/agent/chat",
                        body=b'{"mensagem":"teste","provedor":"gemini","sessao":"sessao-teste"}',
                        headers={**auth, "Content-Type": "application/json"},
                    )
        self.assertEqual(status, 503)
        self.assertIn("O provedor selecionado não está disponível.", body)
        self.assertNotIn("SEGREDO_INTERNO", body)
        self.assertNotIn("nao-retornar", body)
        processar.assert_called_once()
        self.assertEqual(processar.call_args.kwargs["provedor"], "nyxal")
        self.assertEqual(processar.call_args.kwargs["sessao_id"], "sessao-teste")
        responder_direto.assert_not_called()

        with patch.object(api, "generate_kokoro_audio", side_effect=RuntimeError(detalhe_interno)):
            with patch.object(api.Path, "exists", return_value=True):
                with patch.object(
                    api.subprocess,
                    "run",
                    return_value=types.SimpleNamespace(returncode=1, stderr=detalhe_interno),
                ):
                    status, body = self.request(
                        "POST", "/api/tts",
                        body=b'{"texto":"teste"}',
                        headers={**auth, "Content-Type": "application/json"},
                    )
        self.assertEqual(status, 500)
        self.assertIn("O Piper não conseguiu gerar o áudio.", body)
        self.assertNotIn("SEGREDO_INTERNO", body)
        self.assertNotIn("/root/nyxal.env", body)

        with patch.object(api.GMAIL_NYXOS, "listar_eventos", side_effect=RuntimeError(detalhe_interno)):
            status, body = self.request(
                "GET", "/api/integracoes/google/agenda?limit=20&days=14",
                headers=auth,
            )
        self.assertEqual(status, 503)
        self.assertIn("O serviço Google Workspace não está disponível.", body)
        self.assertNotIn("SEGREDO_INTERNO", body)
        self.assertNotIn("/root/nyxal.env", body)

    def test_agent_chat_supplies_readonly_system_context_to_local_dialogue(self) -> None:
        api.PROXY_MODE = True
        api.API_TOKEN = "token-de-teste"
        snapshot = {"cpu_percent": 12.5, "memoria": {"percent": 38.0}}
        residence = {"estado": "ativo", "unidades": []}
        answer = {
            "sucesso": True,
            "estado": "resposta_conversacional",
            "origem": "nucleo_conversacional_nixal",
            "resposta": "Uso atual recebido.",
            "sessao": "sessao-contexto-local",
            "valor": {
                "texto": "Uso atual recebido.",
                "sessao": "sessao-contexto-local",
                "modo": "resposta_conversacional",
            },
        }
        integration_result = {
            "sucesso": True,
            "estado": "mensagem_processada_com_sessao",
            "sessao": "sessao-contexto-local",
            "valor": {"transporte": {"resposta": answer}},
        }
        auth = {
            "Authorization": "Bearer token-de-teste",
            "Content-Type": "application/json",
        }
        with patch.object(api.AGENTE_NYXAL, "resolve_provider", return_value="nyxal"):
            with patch.object(api.OBSERVABILIDADE_NYXOS, "snapshot", return_value=snapshot) as observar:
                with patch.object(api, "residencia_snapshot", return_value=residence) as residencia:
                    with patch.object(
                        api.INTEGRACAO_CONVERSACIONAL,
                        "processar_mensagem",
                        return_value=integration_result,
                    ) as processar:
                        status, body = self.request(
                            "POST",
                            "/api/agent/chat",
                            body=(
                                b'{"mensagem":"Qual o uso de CPU, RAM, disco e GPU do sistema?",'
                                b'"provedor":"gemini","sessao":"sessao-contexto-local"}'
                            ),
                            headers=auth,
                        )

        self.assertEqual(status, 200, body)
        self.assertIn("Uso atual recebido.", body)
        observar.assert_called_once()
        residencia.assert_called_once()
        kwargs = processar.call_args.kwargs
        self.assertEqual(kwargs["provedor"], "nyxal")
        self.assertEqual(kwargs["sessao_id"], "sessao-contexto-local")
        self.assertEqual(
            kwargs["contexto_sistema"],
            {"observabilidade": snapshot, "residencia": residence},
        )

    def test_agent_chat_uses_core_session_integration_and_forces_local_provider(self) -> None:
        api.PROXY_MODE = True
        api.API_TOKEN = "token-de-teste"
        answer = {
            "sucesso": True,
            "estado": "resposta_conversacional",
            "origem": "nucleo_conversacional_nixal",
            "resposta": "Resposta pelo núcleo.",
            "sessao": "sessao-core-123",
            "valor": {
                "texto": "Resposta pelo núcleo.",
                "sessao": "sessao-core-123",
                "modo": "resposta_conversacional",
            },
        }
        integration_result = {
            "sucesso": True,
            "estado": "mensagem_processada_com_sessao",
            "sessao": "sessao-core-123",
            "valor": {"transporte": {"resposta": answer}},
        }
        auth = {
            "Authorization": "Bearer token-de-teste",
            "Content-Type": "application/json",
        }
        with patch.object(api.AGENTE_NYXAL, "resolve_provider", return_value="nyxal"):
            with patch.object(
                api.INTEGRACAO_CONVERSACIONAL,
                "processar_mensagem",
                return_value=integration_result,
            ) as processar:
                with patch.object(api.AGENTE_NYXAL, "responder") as responder_direto:
                    status, body = self.request(
                        "POST",
                        "/api/agent/chat",
                        body=b'{"mensagem":"Ol\u00e1","provedor":"openai","sessao":"sessao-core-123"}',
                        headers=auth,
                    )
        self.assertEqual(status, 200, body)
        self.assertIn("Resposta pelo núcleo.", body)
        self.assertEqual(json.loads(body)["sessao"], "sessao-core-123")
        processar.assert_called_once()
        kwargs = processar.call_args.kwargs
        self.assertEqual(kwargs["texto"], "Olá")
        self.assertEqual(kwargs["sessao_id"], "sessao-core-123")
        self.assertEqual(kwargs["provedor"], "nyxal")
        self.assertEqual(kwargs["contexto_sistema"], {})
        responder_direto.assert_not_called()

    def test_limites_de_corpo_sao_aplicados_antes_da_leitura(self) -> None:
        # Os corpos não são enviados intencionalmente: se uma rota tentar lê-los
        # antes de rejeitar o Content-Length, o teste estoura o timeout HTTP.
        api.PROXY_MODE = False
        casos = (
            ("/api/agent/image", 12 * 1024 * 1024 + 1),
            ("/api/vps/action", 32 * 1024 + 1),
            ("/api/stt", 15 * 1024 * 1024 + 1),
            ("/api/tts", 16 * 1024 + 1),
            ("/api/agent/chat", 64 * 1024 + 1),
        )
        for rota, tamanho in casos:
            with self.subTest(rota=rota, tamanho=tamanho):
                connection = http.client.HTTPConnection(
                    self.host, self.port, timeout=3
                )
                try:
                    connection.putrequest("POST", rota)
                    connection.putheader("Host", f"{self.host}:{self.port}")
                    connection.putheader("Content-Type", "application/json")
                    connection.putheader("Content-Length", str(tamanho))
                    connection.putheader("Connection", "close")
                    connection.endheaders()
                    response = connection.getresponse()
                    body = response.read().decode("utf-8", errors="replace")
                    self.assertEqual(response.status, 413, body)
                finally:
                    connection.close()

    def test_http_rejeita_enquadramento_ambiguo_antes_da_rota(self) -> None:
        casos = (
            (("Transfer-Encoding", "chunked"),),
            (("Content-Length", "0"), ("Content-Length", "1")),
        )
        for headers in casos:
            with self.subTest(headers=headers):
                connection = http.client.HTTPConnection(
                    self.host, self.port, timeout=3
                )
                try:
                    connection.putrequest("POST", "/api/chat")
                    for nome, valor in headers:
                        connection.putheader(nome, valor)
                    connection.putheader("Connection", "close")
                    connection.endheaders()
                    response = connection.getresponse()
                    body = response.read().decode("utf-8", errors="replace")
                    self.assertEqual(response.status, 400, body)
                    self.assertIn("enquadramento_http_invalido", body)
                finally:
                    connection.close()

    def test_saturacao_http_retorna_503_sem_criar_thread_adicional(self) -> None:
        self.server.request_slots = api.BoundedSemaphore(1)
        self.assertTrue(self.server.request_slots.acquire(blocking=False))
        status, headers, _body = self.request_full("GET", "/health")
        self.assertEqual(status, 503)
        self.assertEqual(headers.get("retry-after"), "1")
        self.assertEqual(headers.get("connection"), "close")
        self.assertEqual(headers.get("cache-control"), "no-store")
        # Liberar o slot para manter o teardown previsível.
        self.server.request_slots.release()

    def test_inicio_remoto_sem_token_e_recusado(self) -> None:
        api.HOST = "0.0.0.0"
        api.API_TOKEN = ""
        with patch.object(api, "NyxalThreadingHTTPServer") as server_class:
            with self.assertRaises(SystemExit):
                api.main()
        server_class.assert_not_called()

    def test_inicio_com_modo_proxy_sem_token_e_recusado(self) -> None:
        api.HOST = "127.0.0.1"
        api.PROXY_MODE = True
        api.API_TOKEN = ""
        with patch.object(api, "NyxalThreadingHTTPServer") as server_class:
            with self.assertRaises(SystemExit):
                api.main()
        server_class.assert_not_called()

    def test_rotas_api_novas_exigem_autenticacao_por_padrao(self) -> None:
        api.PROXY_MODE = True
        api.API_TOKEN = ""
        status, body = self.request("GET", "/api/futura/status")
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", body)

        status, body = self.request(
            "POST", "/api/futura/acao", body=b'{"acao":"executar"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", body)

    def test_bind_remoto_exige_token_mesmo_sem_modo_proxy(self) -> None:
        api.HOST = "0.0.0.0"
        api.PROXY_MODE = False
        api.API_TOKEN = ""

        status, body = self.request("GET", "/api/futura/status")
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", body)

        status, body = self.request(
            "POST", "/api/futura/acao", body=b'{"acao":"executar"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", body)

    def test_host_nao_local_e_bloqueado_em_loopback_direto(self) -> None:
        api.PROXY_MODE = False
        with patch.object(
            api.VPS_NYXOS, "status", return_value={"sucesso": True}
        ) as status_route:
            status_code, body = self.request(
                "GET",
                "/api/vps/status",
                headers={"Host": f"attacker.example:{self.port}"},
            )
        self.assertEqual(status_code, 403)
        self.assertIn("origem_nao_permitida", body)
        status_route.assert_not_called()


    def test_falhas_autenticacao_alimentam_defesa_sem_segredos(self) -> None:
        api.API_TOKEN = "token-secreto-de-teste"
        defesa_original = api.DEFESA_AUTONOMA_NYXAL
        eventos_originais = list(api.DEFESA_EVENTOS_RECIENTES)
        def restaurar_defesa() -> None:
            api.DEFESA_AUTONOMA_NYXAL = defesa_original
            api.DEFESA_EVENTOS_RECIENTES.clear()
            api.DEFESA_EVENTOS_RECIENTES.extend(eventos_originais)
        self.addCleanup(restaurar_defesa)
        api.DEFESA_AUTONOMA_NYXAL = api.DefesaAutonoma()
        api.DEFESA_EVENTOS_RECIENTES.clear()

        status, _ = self.request("GET", "/api/agent/contexto")
        self.assertEqual(status, 401)
        status, _ = self.request(
            "GET", "/api/agent/contexto",
            headers={
                "Authorization": "Bearer TOKEN-INCORRETO",
                "X-Forwarded-For": "203.0.113.99",
                "Forwarded": "for=203.0.113.99",
            },
        )
        self.assertEqual(status, 403)

        status, body = self.request(
            "GET", "/api/agent/defesa",
            headers={"Authorization": "Bearer token-secreto-de-teste"},
        )
        self.assertEqual(status, 200, body)
        payload = json.loads(body)
        eventos = payload.get("eventos", [])
        self.assertEqual(len(eventos), 2)
        self.assertEqual(payload.get("executor_ativo"), False)
        self.assertEqual(payload.get("persistencia"), False)
        self.assertEqual(payload.get("eventos_em_memoria_maximo"), 256)
        self.assertNotIn("token-secreto-de-teste", body)
        self.assertNotIn("TOKEN-INCORRETO", body)
        for evento in eventos:
            self.assertEqual(evento.get("tipo"), "falha_autenticacao")
            self.assertEqual(evento.get("fonte_sinal"), "api-auth")
            self.assertEqual(evento.get("origem_ip"), "127.0.0.1")
            self.assertFalse(evento.get("executor_autorizado"))
            self.assertFalse(evento.get("efeito_executado"))
            self.assertNotIn("headers", evento)
            self.assertFalse(any(
                recomendacao.get("tipo") in {
                    "limitar_taxa_origem",
                    "bloqueio_temporario_origem",
                }
                for recomendacao in evento.get("recomendacoes", [])
            ))
            for recomendacao in evento.get("recomendacoes", []):
                self.assertFalse(recomendacao.get("executor_autorizado"))
                self.assertFalse(recomendacao.get("efeito_executado"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
