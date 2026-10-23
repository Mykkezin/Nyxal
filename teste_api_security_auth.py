#!/usr/bin/env python3
"""Testes HTTP mínimos para os limites de autenticação da API Nyxal."""
from __future__ import annotations

import http.client
import sys
import threading
import types
import unittest
from http.server import ThreadingHTTPServer

# A API de chat não precisa carregar um modelo real para validar a camada HTTP.
sys.modules.setdefault("ollama", types.SimpleNamespace())

import nyxal_web_api as api  # noqa: E402


class TestSegurancaAPIHTTP(unittest.TestCase):
    def setUp(self) -> None:
        self.token_original = api.API_TOKEN
        self.proxy_original = api.PROXY_MODE
        self.host_original = api.HOST
        api.API_TOKEN = ""
        api.PROXY_MODE = True
        api.HOST = "127.0.0.1"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), api.NyxalAPIHandler)
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

    def request(self, method: str, path: str, *, body: bytes = b"", headers: dict[str, str] | None = None):
        cabecalhos = {"Content-Length": str(len(body)), "Connection": "close"}
        cabecalhos.update(headers or {})
        conexao = http.client.HTTPConnection(self.host, self.port, timeout=3)
        try:
            conexao.request(method, path, body=body, headers=cabecalhos)
            resposta = conexao.getresponse()
            return resposta.status, resposta.read().decode("utf-8", errors="replace")
        finally:
            conexao.close()

    def test_acoes_vps_exigem_autenticacao_no_modo_proxy(self) -> None:
        status, corpo = self.request(
            "POST", "/api/vps/action", body=b'{"nome":"vm-teste","acao":"stop"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", corpo)

    def test_chat_stt_e_tts_exigem_token_quando_expostos(self) -> None:
        casos = [
            ("POST", "/api/chat", b'{"mensagem":"teste"}'),
            ("POST", "/api/stt", b"audio"),
            ("POST", "/api/tts", b'{"texto":"teste"}'),
        ]
        for metodo, rota, corpo in casos:
            with self.subTest(rota=rota):
                status, resposta = self.request(
                    metodo, rota, body=corpo,
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(status, 503)
                self.assertIn("NYXAL_API_TOKEN", resposta)

    def test_dados_operacionais_nao_ficam_publicos_em_modo_proxy(self) -> None:
        for rota in ("/api/vps/status", "/api/vps/instances", "/api/vps/contexto", "/api/public/delta"):
            with self.subTest(rota=rota):
                status, corpo = self.request("GET", rota)
                self.assertEqual(status, 503)
                self.assertIn("NYXAL_API_TOKEN", corpo)

    def test_cabecalho_de_proxy_forca_autenticacao_mesmo_em_loopback(self) -> None:
        api.PROXY_MODE = False
        status, corpo = self.request(
            "POST", "/api/chat", body=b'{"mensagem":"teste"}',
            headers={
                "Content-Type": "application/json",
                "X-Forwarded-For": "203.0.113.10",
            },
        )
        self.assertEqual(status, 503)
        self.assertIn("NYXAL_API_TOKEN", corpo)

    def test_token_valido_permite_avancar_ate_validacao_do_payload(self) -> None:
        api.API_TOKEN = "token-de-teste"
        status, corpo = self.request(
            "POST", "/api/chat", body=b"",
            headers={"Authorization": "Bearer token-de-teste"},
        )
        self.assertEqual(status, 400)
        self.assertIn("obrigatório", corpo)

    def test_loopback_direto_mantem_compatibilidade_local(self) -> None:
        api.PROXY_MODE = False
        status, corpo = self.request(
            "POST", "/api/chat", body=b"",
        )
        self.assertEqual(status, 400)
        self.assertNotIn("NYXAL_API_TOKEN", corpo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
