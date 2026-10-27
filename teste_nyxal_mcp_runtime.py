#!/usr/bin/env python3
"""Testes do MCP HTTP opcional: configuração, bearer guard e ciclo de vida."""
from __future__ import annotations
import asyncio
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
import nixal_mcp_runtime as runtime

TOKEN = "Nyxal-local-test-token-0123456789abcdef"

class TestConfiguracaoMCPHTTP(unittest.TestCase):
    def test_desligado_por_padrao(self):
        self.assertIsNone(runtime.configuracao_mcp_http({}))

    def test_configuracao_padrao_e_ipv6_loopback(self):
        config = runtime.configuracao_mcp_http({"NYXAL_MCP_HTTP_ENABLED":"true","NYXAL_MCP_HTTP_TOKEN":TOKEN}, api_port=8010)
        self.assertEqual(config.url, "http://127.0.0.1:8765/mcp")
        ipv6 = runtime.configuracao_mcp_http({"NYXAL_MCP_HTTP_ENABLED":"1","NYXAL_MCP_HTTP_HOST":"::1","NYXAL_MCP_HTTP_PORT":"8766","NYXAL_MCP_HTTP_TOKEN":TOKEN}, api_port=8010)
        self.assertEqual(ipv6.url, "http://[::1]:8766/mcp")

    def test_recusa_tokens_ausentes_curto_ou_com_caracter_inseguro(self):
        for token in ("", "curto", "token com espaços e comprimento acima de trinta"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                runtime.configuracao_mcp_http({"NYXAL_MCP_HTTP_ENABLED":"1","NYXAL_MCP_HTTP_TOKEN":token}, api_port=8010)

    def test_recusa_bind_remoto_porta_invalida_e_conflito_com_api(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            runtime.configuracao_mcp_http({"NYXAL_MCP_HTTP_ENABLED":"1","NYXAL_MCP_HTTP_HOST":"0.0.0.0","NYXAL_MCP_HTTP_TOKEN":TOKEN}, api_port=8010)
        for port in ("0", "65536", "abc", "8010"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                runtime.configuracao_mcp_http({"NYXAL_MCP_HTTP_ENABLED":"1","NYXAL_MCP_HTTP_PORT":port,"NYXAL_MCP_HTTP_TOKEN":TOKEN}, api_port=8010)

class TestMCPBearerTokenMiddleware(unittest.TestCase):
    def invoke(self, auth_values, scope_type="http"):
        calls, events = [], []
        async def app(_scope, _receive, send):
            calls.append("invoked")
            await send({"type":"http.response.start","status":204,"headers":[]})
            await send({"type":"http.response.body","body":b""})
        async def send(event):
            events.append(event)
        middleware = runtime.MCPBearerTokenMiddleware(app, TOKEN)
        scope = {"type":scope_type,"method":"POST","headers":[(b"authorization",v) for v in auth_values]}
        asyncio.run(middleware(scope, None, send))
        status = next((e["status"] for e in events if e["type"]=="http.response.start"), None)
        body = next((e.get("body",b"") for e in events if e["type"]=="http.response.body"), b"")
        return status, body, calls, events

    def test_missing_invalid_or_duplicate_bearer_is_rejected_before_mcp(self):
        cases = ([], [b"Bearer wrong-token"], [(b"Bearer "+TOKEN.encode()), (b"Bearer "+TOKEN.encode())])
        for auth in cases:
            with self.subTest(auth=auth):
                status, body, calls, events = self.invoke(auth)
                self.assertEqual(status, 401)
                self.assertEqual(body, b'{"error":"unauthorized"}')
                self.assertEqual(calls, [])
                self.assertIn((b"cache-control",b"no-store"), events[0]["headers"])
                self.assertNotIn(TOKEN.encode(), body)

    def test_valid_bearer_reaches_mcp_app(self):
        status, _, calls, _ = self.invoke([(b"Bearer "+TOKEN.encode())])
        self.assertEqual(status, 204)
        self.assertEqual(calls, ["invoked"])

    def test_asgi_lifespan_passes_through(self):
        calls = []
        async def app(scope, _receive, _send):
            calls.append(scope["type"])
        middleware = runtime.MCPBearerTokenMiddleware(app, TOKEN)
        asyncio.run(middleware({"type":"lifespan","headers":[]},None,None))
        self.assertEqual(calls, ["lifespan"])

class TestCicloDeVidaMCPHTTP(unittest.TestCase):
    def test_disabled_never_spawns_process(self):
        with patch("nixal_mcp_runtime.subprocess.Popen") as popen:
            result = runtime.iniciar_mcp_http(Path("/tmp/Nyxal"), api_port=8010, env={})
        self.assertIsNone(result)
        popen.assert_not_called()

    def test_spawns_and_accepts_only_bearer_guard_readiness(self):
        process = Mock()
        process.poll.return_value = None
        response = HTTPError("http://127.0.0.1:8765/mcp",401,"Unauthorized",{},None)
        with patch("nixal_mcp_runtime.subprocess.Popen",return_value=process) as popen, patch("nixal_mcp_runtime.urlopen",side_effect=response):
            result = runtime.iniciar_mcp_http(Path("/tmp/Nyxal"),api_port=8010,env={"NYXAL_MCP_HTTP_ENABLED":"1","NYXAL_MCP_HTTP_TOKEN":TOKEN})
        self.assertIs(result,process)
        args,kwargs=popen.call_args
        self.assertEqual(args[0][-1],"/tmp/Nyxal/nyxal_mcp_tools.py")
        self.assertEqual(kwargs["env"]["NYXAL_MCP_TRANSPORT"],"streamable-http")
        self.assertEqual(kwargs["env"]["NYXAL_MCP_HTTP_TOKEN"],TOKEN)
        self.assertNotIn(TOKEN,args[0])
        self.assertEqual(kwargs["stdin"],subprocess.DEVNULL)

    def test_startup_fails_if_child_exits_before_ready(self):
        process=Mock()
        process.poll.return_value=1
        with patch("nixal_mcp_runtime.subprocess.Popen",return_value=process):
            with self.assertRaisesRegex(RuntimeError,"terminou antes de ficar pronto"):
                runtime.iniciar_mcp_http(Path("/tmp/Nyxal"),api_port=8010,env={"NYXAL_MCP_HTTP_ENABLED":"1","NYXAL_MCP_HTTP_TOKEN":TOKEN})
        process.terminate.assert_not_called()

    def test_stop_kills_process_that_ignores_terminate(self):
        process=Mock()
        process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired("mcp",0.1),0]
        runtime.encerrar_mcp_http(process,timeout=0.1)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count,2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
