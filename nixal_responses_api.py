#!/usr/bin/env python3
"""Adaptador mínimo e restrito para a Responses API de OpenAI e xAI."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _settings(provider: str) -> dict[str, str]:
    if provider == "openai":
        return {
            "host": "api.openai.com",
            "base": _env("NYXAL_OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "key": _env("NYXAL_OPENAI_API_KEY") or _env("OPENAI_API_KEY"),
            "model": _env("NYXAL_OPENAI_MODEL"),
        }
    if provider == "grok":
        return {
            "host": "api.x.ai",
            "base": _env("NYXAL_GROK_BASE_URL", "https://api.x.ai/v1"),
            "key": _env("NYXAL_GROK_API_KEY") or _env("XAI_API_KEY"),
            "model": _env("NYXAL_GROK_MODEL"),
        }
    return {}


def _base_is_safe(base: str, expected_host: str) -> bool:
    try:
        parsed = urlsplit(base.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and host == expected_host
        and port in {None, 443}
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
        and parsed.path.rstrip("/") in {"", "/v1"}
    )


def provider_configured(provider: str) -> bool:
    config = _settings(provider)
    return bool(
        config
        and config["key"]
        and config["model"]
        and _base_is_safe(config["base"], config["host"])
    )


class _RejectRedirects(HTTPRedirectHandler):
    """Do not forward provider credentials through HTTP redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def ask(
    provider: str,
    message: str,
    system_prompt: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Call an explicitly configured provider; never route arbitrary hosts."""
    config = _settings(provider)
    if not provider_configured(provider):
        raise RuntimeError(
            f"O provedor '{provider}' exige uma chave, um modelo e a URL oficial."
        )
    inputs: list[dict[str, str]] = []
    for item in (history or [])[-20:]:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            inputs.append({"role": role, "content": content[:12000]})
    inputs.append({"role": "user", "content": message.strip()[:12000]})
    base = config["base"].rstrip("/")
    endpoint = base + ("/responses" if base.endswith("/v1") else "/v1/responses")
    payload: dict[str, Any] = {
        "model": config["model"],
        "instructions": system_prompt[:16000],
        "input": inputs,
    }
    if provider == "openai":
        payload["store"] = False
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config["key"],
        },
        method="POST",
    )
    try:
        opener = build_opener(_RejectRedirects())
        with opener.open(request, timeout=180) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise RuntimeError("Resposta do provedor excedeu 2 MiB.")
        result = json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as exc:
        raise RuntimeError(f"O provedor retornou HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Não foi possível comunicar com o provedor ({type(exc).__name__})."
        ) from exc
    if not isinstance(result, dict):
        raise RuntimeError("O provedor retornou um formato inesperado.")
    direct = result.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    parts: list[str] = []
    output = result.get("output", [])
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict) or item.get("role") not in {None, "assistant"}:
                continue
            content = item.get("content", [])
            if isinstance(content, str) and content.strip():
                parts.append(content.strip())
            elif isinstance(content, list):
                for segment in content:
                    if (
                        isinstance(segment, dict)
                        and segment.get("type") in {"output_text", "text"}
                        and isinstance(segment.get("text"), str)
                        and segment["text"].strip()
                    ):
                        parts.append(segment["text"].strip())
    answer = "\n".join(parts).strip()
    if not answer:
        state = str(result.get("status") or "desconhecido")
        raise RuntimeError(
            f"O provedor '{provider}' não retornou texto utilizável (status: {state})."
        )
    return answer


__all__ = ["ask", "provider_configured"]
