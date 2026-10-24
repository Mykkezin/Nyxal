#!/usr/bin/env python3
"""Testes determinísticos das políticas HTTP de segurança da Nyxal."""

from __future__ import annotations

import ast
import json
import socket
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from secrets import compare_digest
from threading import BoundedSemaphore
from types import MethodType
from urllib.parse import urlsplit

from nixal_seguranca_http import (
    client_requires_bearer,
    host_loopback,
    origin_host_loopback,
    origin_permitida,
    parse_allowed_origins,
    sanitize_http_log_message,
)


def deve_rejeitar_origem(valor: str) -> None:
    try:
        parse_allowed_origins(valor, default_origins={"http://localhost:8010"})
    except ValueError:
        return
    raise AssertionError(f"origem insegura foi aceita: {valor!r}")


def testar_handler_http(api_source: str) -> None:
    """Executa a classe real do handler com dependências externas isoladas."""
    tree = ast.parse(api_source)
    handler_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "NyxalAPIHandler"
    )
    isolated_tree = ast.Module(body=[handler_node], type_ignores=[])
    ast.fix_missing_locations(isolated_tree)

    namespace = {
        "BaseHTTPRequestHandler": BaseHTTPRequestHandler,
        "API_TOKEN": "test-secret",
        "CORS_ORIGINS": frozenset({
            "http://127.0.0.1:8010",
            "http://localhost:8010",
            "https://nyxal.example",
        }),
        "client_requires_bearer": client_requires_bearer,
        "origin_permitida": origin_permitida,
        "urlsplit": urlsplit,
        "compare_digest": compare_digest,
        "json_bytes": lambda payload: json.dumps(payload).encode("utf-8"),
    }
    exec(compile(isolated_tree, "nyxal_web_api.py", "exec"), namespace)
    handler_type = namespace["NyxalAPIHandler"]

    def create_handler(address: str, headers: dict[str, str]):
        instance = handler_type.__new__(handler_type)
        instance.client_address = (address, 12345)
        instance.headers = headers
        captured: list[tuple[int, dict]] = []
        instance._send_json = MethodType(
            lambda _self, status, payload: captured.append((status, payload)),
            instance,
        )
        return instance, captured

    local, local_responses = create_handler("127.0.0.1", {})
    assert local._local_ou_autorizado() is True
    assert local_responses == []

    proxy_no_token, proxy_responses = create_handler(
        "127.0.0.1", {"Origin": "https://nyxal.example"}
    )
    assert proxy_no_token._local_ou_autorizado() is False
    assert proxy_responses[-1][0] == 401

    proxy_with_token, proxy_auth_responses = create_handler(
        "127.0.0.1",
        {
            "Origin": "https://nyxal.example",
            "Authorization": "Bearer test-secret",
        },
    )
    assert proxy_with_token._local_ou_autorizado() is True
    assert proxy_auth_responses == []

    remote_with_token, remote_responses = create_handler(
        "198.51.100.9", {"Authorization": "Bearer test-secret"}
    )
    assert remote_with_token._local_ou_autorizado() is True
    assert remote_responses == []

    remote_no_token, remote_no_token_responses = create_handler(
        "198.51.100.9", {}
    )
    assert remote_no_token._local_ou_autorizado() is False
    assert remote_no_token_responses[-1][0] == 401

    disallowed, disallowed_responses = create_handler(
        "127.0.0.1", {"Origin": "https://attacker.example"}
    )
    disallowed.path = "/api/public/status"
    assert disallowed._origem_api_permitida() is False
    assert disallowed_responses[-1][0] == 403

    allowed, allowed_responses = create_handler(
        "127.0.0.1", {"Origin": "https://nyxal.example"}
    )
    allowed.path = "/api/public/status"
    assert allowed._origem_api_permitida() is True
    assert allowed_responses == []

    captured_allowed_headers: list[tuple[str, str]] = []
    allowed.send_header = MethodType(
        lambda _self, key, value: captured_allowed_headers.append((key, value)),
        allowed,
    )
    allowed._send_security_headers()
    assert (
        "Access-Control-Allow-Origin",
        "https://nyxal.example",
    ) in captured_allowed_headers
    assert ("X-Content-Type-Options", "nosniff") in captured_allowed_headers
    assert ("Referrer-Policy", "no-referrer") in captured_allowed_headers
    assert ("Cache-Control", "no-store") in captured_allowed_headers

    captured_disallowed_headers: list[tuple[str, str]] = []
    disallowed.send_header = MethodType(
        lambda _self, key, value: captured_disallowed_headers.append((key, value)),
        disallowed,
    )
    disallowed._send_security_headers()
    assert not any(
        key == "Access-Control-Allow-Origin"
        for key, _value in captured_disallowed_headers
    )

    no_origin, _ = create_handler("127.0.0.1", {})
    captured_no_origin_headers: list[tuple[str, str]] = []
    no_origin.send_header = MethodType(
        lambda _self, key, value: captured_no_origin_headers.append((key, value)),
        no_origin,
    )
    no_origin._send_security_headers()
    assert not any(
        key == "Access-Control-Allow-Origin"
        for key, _value in captured_no_origin_headers
    )

    print("HTTP_HANDLER_ISOLATED_AUTH_TESTS: OK")
    print("HTTP_SECURITY_HEADERS_TESTS: OK")


def testar_servidor_com_limite(api_source: str) -> None:
    """Valida rejeição de conexões acima do limite sem iniciar listeners reais."""
    tree = ast.parse(api_source)
    server_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "NyxalThreadingHTTPServer"
    )
    isolated_tree = ast.Module(body=[server_node], type_ignores=[])
    ast.fix_missing_locations(isolated_tree)

    class FakeThreadingHTTPServer:
        def __init__(self) -> None:
            self.closed_requests = []
            self.parent_request = None
            self.parent_thread_request = None

        def process_request(self, request, client_address) -> None:
            self.parent_request = (request, client_address)

        def process_request_thread(self, request, client_address) -> None:
            self.parent_thread_request = (request, client_address)

        def shutdown_request(self, request) -> None:
            self.closed_requests.append(request)

    namespace = {
        "ThreadingHTTPServer": FakeThreadingHTTPServer,
        "socket": socket,
        "HOST": "127.0.0.1",
        "BoundedSemaphore": BoundedSemaphore,
        "MAX_CONCURRENT_HTTP_REQUESTS": 1,
    }
    exec(compile(isolated_tree, "nyxal_web_api.py", "exec"), namespace)
    server_type = namespace["NyxalThreadingHTTPServer"]

    class FakeSocket:
        def __init__(self) -> None:
            self.sent = b""

        def sendall(self, data: bytes) -> None:
            self.sent += data

    server = server_type.__new__(server_type)
    FakeThreadingHTTPServer.__init__(server)
    blocker = server.request_slots
    assert blocker.acquire(blocking=False) is True

    overloaded = FakeSocket()
    server.process_request(overloaded, ("127.0.0.1", 12345))
    assert b"503 Service Unavailable" in overloaded.sent
    assert b"Connection: close" in overloaded.sent
    assert b"Retry-After: 1" in overloaded.sent
    assert server.closed_requests == [overloaded]
    assert server.parent_request is None
    blocker.release()

    accepted = FakeSocket()
    server.process_request(accepted, ("127.0.0.1", 12346))
    assert server.parent_request == (accepted, ("127.0.0.1", 12346))
    assert blocker.acquire(blocking=False) is False
    server.process_request_thread(accepted, ("127.0.0.1", 12346))
    assert server.parent_thread_request == (accepted, ("127.0.0.1", 12346))
    assert blocker.acquire(blocking=False) is True
    blocker.release()

    print("HTTP_SERVER_ISOLATED_LIMIT_TESTS: OK")


def main() -> None:
    api_source = (Path(__file__).resolve().parent / "nyxal_web_api.py").read_text(
        encoding="utf-8"
    )
    assert "CORS_ORIGIN," not in api_source
    assert "parse_allowed_origins(" in api_source
    assert "if not self._origem_api_permitida():" in api_source
    assert (
        "parsed_path.startswith" in api_source
        and "_local_ou_autorizado()" in api_source
    )
    assert "if not host_loopback(HOST):" in api_source
    assert "client_requires_bearer(endereco, origem)" in api_source
    assert "self._send_security_headers()" in api_source
    assert "sanitize_http_log_message(format_string % args)" in api_source

    testar_handler_http(api_source)
    testar_servidor_com_limite(api_source)

    assert "MAX_CONCURRENT_HTTP_REQUESTS = 8" in api_source
    assert "HTTP_REQUEST_TIMEOUT_SECONDS = 30" in api_source
    assert "self.connection.settimeout(HTTP_REQUEST_TIMEOUT_SECONDS)" in api_source
    assert "request_slots.acquire(blocking=False)" in api_source
    assert "HTTP/1.1 503 Service Unavailable" in api_source

    assert host_loopback("127.0.0.1")
    assert host_loopback("::1")
    assert host_loopback("localhost")
    assert origin_host_loopback("http://localhost:5173")
    assert origin_host_loopback("http://127.0.0.1:8010")
    assert origin_host_loopback("https://[::1]:8443")
    assert not origin_host_loopback("https://nyxal.example")
    assert not origin_host_loopback("null")
    assert not origin_host_loopback("https://localhost/path")

    assert not client_requires_bearer("127.0.0.1", None)
    assert not client_requires_bearer("::1", "http://localhost:8010")
    assert client_requires_bearer("127.0.0.1", "https://nyxal.example")
    assert client_requires_bearer("192.0.2.20", "http://localhost:8010")
    assert client_requires_bearer("192.0.2.20", None)
    assert client_requires_bearer(None, None)
    assert client_requires_bearer("not-an-ip", None)

    assert not host_loopback("0.0.0.0")
    assert not host_loopback("192.0.2.10")
    assert not host_loopback("nyxal.example")

    defaults = {"http://127.0.0.1:8010", "http://localhost:8010"}
    assert parse_allowed_origins(None, default_origins=defaults) == frozenset(defaults)
    assert parse_allowed_origins(
        "https://nyxal.example,http://localhost:5173",
        default_origins=defaults,
    ) == frozenset({"https://nyxal.example", "http://localhost:5173"})

    deve_rejeitar_origem("*")
    deve_rejeitar_origem("https://nyxal.example,*")
    deve_rejeitar_origem("null")
    deve_rejeitar_origem("https://nyxal.example/path")
    deve_rejeitar_origem("https://usuario:senha@nyxal.example")
    deve_rejeitar_origem("ftp://nyxal.example")
    deve_rejeitar_origem("https://nyxal.example:porta")

    permitidas = frozenset({"http://localhost:8010", "https://nyxal.example"})
    assert origin_permitida(None, permitidas)
    assert origin_permitida("http://localhost:8010", permitidas)
    assert origin_permitida("https://nyxal.example", permitidas)
    assert not origin_permitida("https://atacante.example", permitidas)
    assert not origin_permitida("null", permitidas)

    linha_log = '"GET /api/integracoes/gmail/mensagem?id=segredo HTTP/1.1" 200 -'
    assert sanitize_http_log_message(linha_log) == (
        '"GET /api/integracoes/gmail/mensagem HTTP/1.1" 200 -'
    )
    linha_injetada = 'GET /rota?consulta=x\r\nINTRUSO HTTP/1.1'
    limpa = sanitize_http_log_message(linha_injetada)
    assert "\r" not in limpa and "\n" not in limpa
    assert "\r\nINTRUSO" not in limpa
    assert len(sanitize_http_log_message("x" * 100, max_length=12)) == 12

    print("API_POLICY_WIRING: OK")
    print("HTTP_LOG_QUERY_REDACTION: OK")
    print("TESTE_SEGURANCA_HTTP_OK")
    print("BIND_LOOPBACK: OK")
    print("REMOTE_ORIGIN_REQUIRES_BEARER: OK")
    print("PROXY_LOOPBACK_SPOOFING_POLICY: OK")
    print("CORS_EXATO_SEM_CURINGAS: OK")
    print("ORIGEM_NULL_E_ORIGENS_ESTRANHAS: REJEITADAS")


if __name__ == "__main__":
    main()
