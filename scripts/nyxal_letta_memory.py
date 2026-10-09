#!/usr/bin/env python3
"""Cliente local mínimo para a memória Letta compartilhada da Nyxal.

Lê configuração como texto (nunca executa o arquivo .env), usa apenas os
endpoints Letta fixos e nunca imprime valores de chaves/tokens.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


MAX_SUMMARY = 2000
DEFAULT_CONFIG = Path.home() / ".config" / "nyxal" / "nyxal.env"


def _read_local_env(path: Path = DEFAULT_CONFIG) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key.replace("_", "").isalnum():
            values[key] = value
    return values


def _request(url: str, *, method: str = "GET", payload: dict | None = None, key: str = "", timeout: float = 12) -> object:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["Authorization"] = "Bearer " + key
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(512 * 1024 + 1)
        if len(raw) > 512 * 1024:
            raise RuntimeError("A resposta de memória excedeu 512 KiB.")
        return json.loads(raw.decode("utf-8")) if raw else {}
    except HTTPError as exc:
        raise RuntimeError(f"Letta retornou HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Memória Letta indisponível ({type(exc).__name__}).") from exc


def _config() -> tuple[str, str, str, bool]:
    values = _read_local_env()
    base = values.get("LETTA_BASE_URL", "http://127.0.0.1:8283").rstrip("/")
    agent = values.get("LETTA_AGENT_ID", "").strip()
    key = values.get("LETTA_API_KEY", "").strip()
    write_enabled = values.get("LETTA_MEMORY_SYNC_ENABLED", "false").lower() in {"1", "true", "yes"}
    if not agent:
        raise RuntimeError("LETTA_AGENT_ID não está configurado em ~/.config/nyxal/nyxal.env.")
    if not base.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]", "https://api.letta.com")):
        raise RuntimeError("URL Letta bloqueada: use loopback local ou https://api.letta.com.")
    if base.startswith("https://api.letta.com") and not key:
        raise RuntimeError("LETTA_API_KEY é obrigatório para Letta Cloud.")
    return base, quote(agent, safe=""), key, write_enabled


def recall() -> int:
    base, agent, key, _ = _config()
    result = _request(base + f"/v1/agents/{agent}/core-memory/blocks", key=key)
    if isinstance(result, list):
        blocks = result
    elif isinstance(result, dict):
        blocks = result.get("blocks") or result.get("items") or result.get("data") or []
    else:
        blocks = []
    found = 0
    for block in blocks[:20] if isinstance(blocks, list) else []:
        if not isinstance(block, dict):
            continue
        label = str(block.get("label") or block.get("name") or "memória")[:100]
        value = block.get("value")
        if isinstance(value, str) and value.strip():
            print(f"[{label}] {value[:4000]}")
            found += 1
    if not found:
        print("A memória Letta está conectada, mas não retornou blocos legíveis.")
    return 0


def remember(summary: str) -> int:
    summary = summary.strip()
    if not summary:
        raise ValueError("Forneça um resumo não vazio.")
    if len(summary) > MAX_SUMMARY:
        raise ValueError(f"O resumo deve ter no máximo {MAX_SUMMARY} caracteres.")
    base, agent, key, write_enabled = _config()
    if not write_enabled:
        raise RuntimeError("Gravação Letta desabilitada. Habilite LETTA_MEMORY_SYNC_ENABLED após revisar a política de memória.")
    prompt = (
        "Atualize a memória persistente da Nyxal somente com fatos duradouros e preferências úteis "
        "contidos neste resumo. Não memorize senhas, tokens, códigos de autenticação, dados financeiros "
        "sensíveis ou conteúdo integral de e-mails. Não execute ferramentas externas nem envie mensagens. "
        "Se não houver fato duradouro, não altere a memória.\n\nResumo aprovado pelo operador:\n"
        + summary
    )
    result = _request(
        base + f"/v1/agents/{agent}/messages",
        method="POST",
        payload={"messages": [{"role": "user", "content": prompt}], "streaming": False, "max_steps": 1},
        key=key,
        timeout=30,
    )
    print("Resumo encaminhado ao agente Letta para atualização supervisionada da memória.")
    if isinstance(result, dict):
        messages = result.get("messages", [])
        for item in messages if isinstance(messages, list) else []:
            if not isinstance(item, dict):
                continue
            typ = str(item.get("message_type") or item.get("type") or "").lower()
            if "assistant" in typ and isinstance(item.get("content"), str):
                print(item["content"][:1000])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Consultar ou atualizar a memória persistente da Nyxal.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("recall", help="Ler os blocos de memória Letta.")
    remember_parser = subparsers.add_parser("remember", help="Pedir ao Letta para salvar um resumo aprovado.")
    remember_parser.add_argument("--summary", required=True, help="Resumo curto e não sensível; máximo 2.000 caracteres.")
    args = parser.parse_args()
    try:
        return recall() if args.command == "recall" else remember(args.summary)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
