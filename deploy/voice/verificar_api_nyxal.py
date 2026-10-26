#!/usr/bin/env python3
"""Microphone-free smoke test for the live Nyxal /api/chat session contract.

This sends two harmless, fixed prompts to the local API. It reports only
HTTP/state metadata and booleans; it never prints the prompts, response text,
or the session identifier.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from nixal_seguranca_http import host_loopback


API_BASE = os.environ.get("NYXAL_API_BASE", "http://127.0.0.1:8010").rstrip("/")
TIMEOUT_SECONDS = 180


def _request_headers(api_base: str) -> dict[str, str]:
    """Authenticate local smoke requests without permitting remote misrouting."""
    try:
        parsed = urlsplit(api_base)
        _ = parsed.port
    except ValueError as error:
        raise RuntimeError("NYXAL_API_BASE não é uma URL válida.") from error

    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("NYXAL_API_BASE precisa ser uma URL HTTP(S) sem credenciais, query ou fragmento.")

    if not host_loopback(parsed.hostname):
        raise RuntimeError("O smoke test só pode acessar a API local em localhost/loopback.")

    headers = {"Accept": "application/json"}
    token = os.environ.get("NYXAL_API_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(path: str, payload: dict | None = None) -> tuple[int, dict]:
    headers = _request_headers(API_BASE)
    data = None
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"

    request = Request(
        f"{API_BASE}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS if payload is not None else 5) as response:
            status = response.status
            raw = response.read()
    except HTTPError as error:
        status = error.code
        raw = error.read()
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"{path}: {type(error).__name__}") from error

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{path}: resposta não é JSON válido (HTTP {status})") from error

    if not isinstance(parsed, dict):
        raise RuntimeError(f"{path}: JSON não é um objeto (HTTP {status})")
    return status, parsed


def main() -> int:
    try:
        health_status, health = request_json("/health")
    except RuntimeError as error:
        print(f"FALHA API: {error}")
        return 1

    print(
        f"health: HTTP={health_status}, "
        f"estado={health.get('estado', 'ausente')}"
    )
    if health_status != 200:
        print("FALHA: API local não está saudável.")
        return 1

    # Intentionally omit 'sessao': the API must create the first real session.
    first_status, first = request_json(
        "/api/chat",
        {"mensagem": "Responda apenas com a palavra PRONTO."},
    )
    first_session = first.get("sessao")
    first_ok = (
        first_status == 200
        and first.get("sucesso") is True
        and isinstance(first.get("resposta"), str)
        and bool(first["resposta"].strip())
        and isinstance(first_session, str)
        and bool(first_session.strip())
    )
    print(
        f"turno 1: HTTP={first_status}, "
        f"sucesso={first.get('sucesso') is True}, "
        f"estado={first.get('estado', 'ausente')}, "
        f"resposta_textual={isinstance(first.get('resposta'), str) and bool(first.get('resposta', '').strip())}, "
        f"sessao_recebida={isinstance(first_session, str) and bool(first_session.strip())}"
    )
    if not first_ok:
        print("FALHA: primeiro turno não criou uma sessão válida ou não gerou resposta.")
        return 1

    second_status, second = request_json(
        "/api/chat",
        {
            "mensagem": "Agora responda apenas com a palavra CONTINUA.",
            "sessao": first_session,
        },
    )
    session_reused = second.get("sessao") == first_session
    second_ok = (
        second_status == 200
        and second.get("sucesso") is True
        and isinstance(second.get("resposta"), str)
        and bool(second["resposta"].strip())
        and session_reused
    )
    print(
        f"turno 2: HTTP={second_status}, "
        f"sucesso={second.get('sucesso') is True}, "
        f"estado={second.get('estado', 'ausente')}, "
        f"resposta_textual={isinstance(second.get('resposta'), str) and bool(second.get('resposta', '').strip())}, "
        f"mesma_sessao={session_reused}"
    )

    if not second_ok:
        print("FALHA: segundo turno não reutilizou a sessão válida ou não gerou resposta.")
        return 1

    print("OK: API, núcleo conversacional e contrato de sessão passaram no smoke test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
