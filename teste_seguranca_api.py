#!/usr/bin/env python3
"""Testes determinísticos das políticas HTTP de segurança da Nyxal."""

from __future__ import annotations

import ast
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from secrets import compare_digest
from types import MethodType
from urllib.parse import urlsplit

from nixal_seguranca_http import (
    client_requires_bearer,
    host_loopback,
    origin_host_loopback,
    origin_permitida,
    parse_allowed_origins,
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

    print("HTTP_HANDLER_ISOLATED_AUTH_TESTS: OK")


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

    testar_handler_http(api_source)

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

    print("API_POLICY_WIRING: OK")
    print("TESTE_SEGURANCA_HTTP_OK")
    print("BIND_LOOPBACK: OK")
    print("REMOTE_ORIGIN_REQUIRES_BEARER: OK")
    print("PROXY_LOOPBACK_SPOOFING_POLICY: OK")
    print("CORS_EXATO_SEM_CURINGAS: OK")
    print("ORIGEM_NULL_E_ORIGENS_ESTRANHAS: REJEITADAS")


if __name__ == "__main__":
    main()
