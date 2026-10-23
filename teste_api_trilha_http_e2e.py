#!/usr/bin/env python3
"""Testes de integração HTTP para correlação e privacidade da trilha Nyxal."""
from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.modules.setdefault("ollama", types.SimpleNamespace())

import nyxal_web_api as api  # noqa: E402
from nixal_trilha_http import RegistroTrilhaHTTP  # noqa: E402


class TestTrilhaHTTPIntegracao(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.trace_path = Path(self.temp.name) / "http-traces.jsonl"
        self.trace_original = api.TRILHA_HTTP
        self.token_original = api.API_TOKEN
        self.proxy_original = api.PROXY_MODE
        self.host_original = api.HOST
        api.TRILHA_HTTP = RegistroTrilhaHTTP(self.trace_path)
        api.API_TOKEN = ""
        api.PROXY_MODE = False
        api.HOST = "127.0.0.1"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), api.NyxalAPIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        api.TRILHA_HTTP = self.trace_original
        api.API_TOKEN = self.token_original
        api.PROXY_MODE = self.proxy_original
        api.HOST = self.host_original
        self.temp.cleanup()

    def request(self, method: str, path: str, *, body: bytes = b"", headers: dict[str, str] | None = None):
        request_headers = {"Content-Length": str(len(body)), "Connection": "close"}
        request_headers.update(headers or {})
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            response_headers = {key.lower(): value for key, value in response.getheaders()}
            return response.status, response_headers, response.read()
        finally:
            connection.close()

    def records(self) -> list[dict]:
        if not self.trace_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.trace_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def wait_for_record(self, request_id: str, timeout: float = 2.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            record = next(
                (item for item in self.records() if item["request_id"] == request_id),
                None,
            )
            if record is not None:
                return record
            time.sleep(0.01)
        self.fail(f"Evento HTTP não foi gravado para request_id={request_id}")

    def wait_for_records(self, request_ids: list[str], timeout: float = 2.0) -> list[dict]:
        wanted = set(request_ids)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            found = [item for item in self.records() if item["request_id"] in wanted]
            if len(found) == len(wanted):
                return found
            time.sleep(0.01)
        self.fail(f"Trilha incompleta: esperados {len(wanted)} eventos, vistos {len(found)}")

    def test_resposta_e_evento_compartilham_request_id_e_redigem_segredos(self) -> None:
        status, headers, body = self.request("GET", "/health")
        self.assertEqual(status, 200, body.decode("utf-8"))
        self.assertIn("x-request-id", headers)
        self.assertTrue(headers["x-request-id"])
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        health_event = self.wait_for_record(headers["x-request-id"])
        self.assertEqual(health_event["route"], "/health")
        self.assertEqual(health_event["status_code"], 200)

        body_canary = "TRACE_BODY_CANARY_8ad1"
        header_canary = "TRACE_HEADER_CANARY_91bc"
        fake_result = {
            "sucesso": True,
            "sessao": "session-e2e",
            "valor": {"transporte": {"resposta": {"resposta": "resposta simulada"}}},
        }
        with patch.object(
            api.INTEGRACAO_CONVERSACIONAL,
            "processar_mensagem",
            return_value=fake_result,
        ):
            status, headers, body = self.request(
                "POST",
                "/api/chat",
                body=json.dumps({"mensagem": body_canary, "sessao": "session-e2e"}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {header_canary}",
                },
            )
        self.assertEqual(status, 200, body.decode("utf-8"))
        chat_event = self.wait_for_record(headers["x-request-id"])
        self.assertEqual(chat_event["route"], "/api/chat")
        self.assertEqual(chat_event["status_code"], 200)

        query_canary = "TRACE_QUERY_CANARY_d28e"
        status, query_headers, _ = self.request("GET", f"/rota-inexistente?token={query_canary}")
        self.assertEqual(status, 404)
        query_event = self.wait_for_record(query_headers["x-request-id"])
        self.assertEqual(query_event["route"], "/rota-inexistente")
        raw_trace = self.trace_path.read_text(encoding="utf-8")
        for canary in (body_canary, header_canary, query_canary):
            self.assertNotIn(canary, raw_trace)

    def test_concorrencia_preserva_uma_linha_por_request_com_ids_unicos(self) -> None:
        def one_request(_: int):
            status, headers, _body = self.request("GET", "/health")
            self.assertEqual(status, 200)
            return headers["x-request-id"]

        with ThreadPoolExecutor(max_workers=8) as executor:
            ids = list(executor.map(one_request, range(16)))
        self.assertEqual(len(ids), 16)
        self.assertEqual(len(set(ids)), 16)
        selected = self.wait_for_records(ids)
        self.assertEqual(len(selected), 16)
        self.assertTrue(all(row["status_code"] == 200 for row in selected))

    def test_trilha_desativada_nao_grava_mas_mantem_cabecalho_de_correlacao(self) -> None:
        api.TRILHA_HTTP = RegistroTrilhaHTTP(self.trace_path, habilitado=False)
        status, headers, _body = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertTrue(headers.get("x-request-id"))
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        self.assertFalse(self.trace_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
