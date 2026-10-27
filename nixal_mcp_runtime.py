#!/usr/bin/env python3
"""Ciclo de vida e autenticação do MCP HTTP opcional da Nyxal."""
from __future__ import annotations
import ipaddress
import os
import re
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9._~-]{32,256}\Z")
_READINESS_TIMEOUT = 6.0

@dataclass(frozen=True)
class ConfiguracaoMCPHTTP:
    host: str
    port: int
    token: str

    @property
    def url(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}/mcp"

def _token_valido(token: str) -> bool:
    return isinstance(token, str) and _TOKEN_PATTERN.fullmatch(token) is not None

def configuracao_mcp_http(env=None, *, api_port: int | None = None) -> ConfiguracaoMCPHTTP | None:
    """HTTP permanece desligado até existir opt-in explícito."""
    values = os.environ if env is None else env
    if str(values.get("NYXAL_MCP_HTTP_ENABLED", "")).strip().lower() not in _TRUTHY:
        return None
    host = str(values.get("NYXAL_MCP_HTTP_HOST", "127.0.0.1")).strip()
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("NYXAL_MCP_HTTP_HOST precisa ser um IP literal de loopback.") from exc
    if not address.is_loopback:
        raise ValueError("O servidor MCP HTTP só pode escutar em loopback.")
    try:
        port = int(str(values.get("NYXAL_MCP_HTTP_PORT", "8765")).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("NYXAL_MCP_HTTP_PORT precisa ser numérica.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("NYXAL_MCP_HTTP_PORT está fora do intervalo permitido.")
    if api_port is not None and port == api_port:
        raise ValueError("O MCP HTTP precisa usar uma porta diferente da API Nyxal.")
    token = str(values.get("NYXAL_MCP_HTTP_TOKEN", ""))
    if not _token_valido(token):
        raise ValueError("NYXAL_MCP_HTTP_TOKEN precisa ter 32 a 256 caracteres ASCII seguros; gere um token aleatório.")
    return ConfiguracaoMCPHTTP(host, port, token)

class MCPBearerTokenMiddleware:
    """Verifica um token bearer em toda requisição HTTP, sem comparar em tempo variável."""
    def __init__(self, app, token: str) -> None:
        if not _token_valido(token):
            raise ValueError("Token bearer MCP inválido.")
        self.app = app
        self._expected = ("Bearer " + token).encode("ascii")

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        values = [value for key, value in scope.get("headers", []) if key.lower() == b"authorization"]
        valid = len(values) == 1 and secrets.compare_digest(values[0], self._expected)
        if not valid:
            body = b'{"error":"unauthorized"}'
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                    (b"www-authenticate", b'Bearer realm="Nyxal MCP"'),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)

def _mcp_http_pronto(url: str) -> bool:
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=0.4) as response:
            status = getattr(response, "status", 200)
    except HTTPError as exc:
        status = exc.code
    except (URLError, TimeoutError, OSError):
        return False
    return status == 401

def iniciar_mcp_http(base_dir: str | Path, *, api_port: int, env=None, readiness_timeout: float = _READINESS_TIMEOUT) -> subprocess.Popen | None:
    """Inicia o servidor filho apenas no modo opt-in e confirma o guard bearer."""
    values = dict(os.environ if env is None else env)
    config = configuracao_mcp_http(values, api_port=api_port)
    if config is None:
        return None
    child_env = dict(values)
    child_env.update({
        "NYXAL_MCP_TRANSPORT": "streamable-http",
        "NYXAL_MCP_HTTP_ENABLED": "1",
        "NYXAL_MCP_HTTP_HOST": config.host,
        "NYXAL_MCP_HTTP_PORT": str(config.port),
        "NYXAL_MCP_HTTP_TOKEN": config.token,
    })
    executable = sys.executable
    command = [executable, str(Path(base_dir) / "nyxal_mcp_tools.py")]
    process = subprocess.Popen(
        command,
        cwd=str(base_dir),
        env=child_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + max(0.1, readiness_timeout)
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("O processo MCP terminou antes de ficar pronto; consulte o log do serviço.")
            if _mcp_http_pronto(config.url):
                return process
            time.sleep(0.1)
        raise RuntimeError("O servidor MCP HTTP não confirmou readiness com autenticação.")
    except Exception:
        encerrar_mcp_http(process)
        raise

def encerrar_mcp_http(process: subprocess.Popen | None, timeout: float = 5.0) -> None:
    """Finaliza o processo MCP e usa kill se ele ignorar terminate."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=max(0.1, timeout))
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=max(0.1, timeout))
