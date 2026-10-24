#!/usr/bin/env python3
"""Testes determinísticos das políticas HTTP de segurança da Nyxal."""

from __future__ import annotations

from pathlib import Path

from nixal_seguranca_http import (
    host_loopback,
    origin_permitida,
    parse_allowed_origins,
)


def deve_rejeitar_origem(valor: str) -> None:
    try:
        parse_allowed_origins(valor, default_origins={"http://localhost:8010"})
    except ValueError:
        return
    raise AssertionError(f"origem insegura foi aceita: {valor!r}")


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
    assert "self._send_security_headers()" in api_source

    assert host_loopback("127.0.0.1")
    assert host_loopback("::1")
    assert host_loopback("localhost")
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
    print("CORS_EXATO_SEM_CURINGAS: OK")
    print("ORIGEM_NULL_E_ORIGENS_ESTRANHAS: REJEITADAS")


if __name__ == "__main__":
    main()
