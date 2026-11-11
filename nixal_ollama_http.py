#!/usr/bin/env python3
"""Cliente leve para API HTTP nativa do Ollama (sem pacote ollama)."""
from __future__ import annotations

import json
import os
import builtins
from collections.abc import Iterator
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class OllamaHTTPError(RuntimeError):
    """Falha sanitizada ao consultar o servidor Ollama."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _base_url() -> str:
    value = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").strip()
    if "://" not in value:
        value = "http://" + value
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise OllamaHTTPError("OLLAMA_HOST inválido; informe somente host e porta.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise OllamaHTTPError("Porta Ollama inválida.") from exc
    authority = parsed.hostname
    if ":" in authority:
        authority = f"[{authority}]"
    if port:
        authority += f":{port}"
    return f"{parsed.scheme}://{authority}"


def _request(path: str, *, payload: dict[str, Any] | None = None, timeout: float | None = None):
    base = _base_url()
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        base + path,
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        opener = build_opener(_RejectRedirects())
        response = opener.open(
            request,
            timeout=timeout or float(os.environ.get("NYXAL_OLLAMA_TIMEOUT", "180")),
        )
        return response
    except HTTPError as exc:
        raise OllamaHTTPError(f"Ollama respondeu HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise OllamaHTTPError(f"Ollama indisponível ({type(exc).__name__}).") from None


def _decode(response) -> dict[str, Any]:
    try:
        raw = response.read(4 * 1024 * 1024 + 1)
    finally:
        response.close()
    if len(raw) > 4 * 1024 * 1024:
        raise OllamaHTTPError("Resposta Ollama excedeu 4 MiB.")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise OllamaHTTPError("Ollama retornou JSON inválido.") from None
    if not isinstance(value, dict):
        raise OllamaHTTPError("Ollama retornou uma resposta inválida.")
    return value


def chat(
    *, model: str, messages: list[dict[str, Any]], options: dict[str, Any] | None = None,
    tools: list[dict[str, Any]] | None = None, stream: bool = False,
    timeout: float | None = None, **kwargs: Any,
) -> dict[str, Any] | Iterator[dict[str, Any]]:
    """Compatibilidade com a forma `ollama.chat`; suporta tools e NDJSON."""
    if not isinstance(model, str) or not model.strip():
        raise ValueError("O modelo Ollama é obrigatório.")
    if not isinstance(messages, builtins.list) or not messages:
        raise ValueError("As mensagens Ollama são obrigatórias.")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": bool(stream),
    }
    if options is not None:
        payload["options"] = options
    if tools:
        payload["tools"] = tools
    payload.update({key: value for key, value in kwargs.items() if key in {"keep_alive", "format"}})
    response = _request("/api/chat", payload=payload, timeout=timeout)
    if not stream:
        return _decode(response)

    def chunks() -> Iterator[dict[str, Any]]:
        try:
            for line in response:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                    raise OllamaHTTPError("Ollama retornou um bloco de streaming inválido.") from None
                if not isinstance(item, dict):
                    raise OllamaHTTPError("Bloco de streaming Ollama inválido.")
                yield item
        finally:
            response.close()
    return chunks()


def list(*, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
    return _decode(_request("/api/tags", timeout=timeout))


def version(*, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
    return _decode(_request("/api/version", timeout=timeout))


class OllamaHTTPClient:
    """Interface pequena de geração, streaming, catálogo e saúde."""

    engine_id = "ollama"

    def generate(self, messages, *, model, temperature=0.4, max_tokens=1024, **kwargs):
        options = dict(kwargs.pop("options", {}) or {})
        options.update(temperature=temperature, num_predict=max_tokens)
        return chat(model=model, messages=messages, options=options, **kwargs)

    def stream(self, messages, *, model, temperature=0.4, max_tokens=1024, **kwargs):
        options = dict(kwargs.pop("options", {}) or {})
        options.update(temperature=temperature, num_predict=max_tokens)
        return chat(model=model, messages=messages, options=options, stream=True, **kwargs)

    def list_models(self) -> list[str]:
        result = list()
        models = result.get("models", [])
        return [item["name"] for item in models if isinstance(item, dict) and isinstance(item.get("name"), str)]

    def model_catalog(self) -> list[dict[str, Any]]:
        """Return facts reported by Ollama; never infer chat/vision support."""
        result = list()
        models = result.get("models", [])
        return [
            {
                "id": item.get("name"),
                "capabilities": item.get("capabilities", []),
                "details": item.get("details", {}),
            }
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]

    def can_serve(self, model: str) -> bool:
        return model in self.list_models()

    def health(self) -> bool:
        try:
            version()
            return True
        except OllamaHTTPError:
            return False


__all__ = ["OllamaHTTPClient", "OllamaHTTPError", "chat", "list", "version"]
