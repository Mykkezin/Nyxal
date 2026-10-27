#!/usr/bin/env python3
"""Smoke test end-to-end para o MCP Streamable HTTP autenticado."""
from __future__ import annotations

import asyncio
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

BASE_DIR = Path(__file__).resolve().parent
SERVER = BASE_DIR / "nyxal_mcp_tools.py"
REQUIRED_TOOLS = {
    "status_ferramentas",
    "consultar_metar_taf",
    "consultar_notam_aisweb",
    "consultar_cartas_aisweb",
    "diagnosticar_sistema",
}


def reservar_porta_loopback() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def aguardar_desafio_401(url: str, process: subprocess.Popen, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("O subprocesso MCP HTTP terminou antes de iniciar.")
        try:
            with urlopen(Request(url, method="GET"), timeout=0.3) as response:
                last_status = response.status
        except HTTPError as exc:
            last_status = exc.code
        except (URLError, TimeoutError, OSError):
            time.sleep(0.1)
            continue
        if last_status == 401:
            return
        raise RuntimeError(f"O endpoint MCP respondeu HTTP {last_status} sem bearer token; esperado 401.")
    raise RuntimeError("Timeout aguardando desafio bearer do servidor MCP HTTP.")


async def validar_cliente_mcp(url: str, token: str) -> set[str]:
    timeout = httpx2.Timeout(15.0, read=30.0)
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    ) as http_client:
        transport = streamable_http_client(url, http_client=http_client)
        async with Client(transport) as client:
            result = await client.list_tools()
            return {tool.name for tool in result.tools}


def main() -> None:
    if not SERVER.is_file():
        raise SystemExit(f"Servidor MCP ausente: {SERVER}")
    port = reservar_porta_loopback()
    token = secrets.token_urlsafe(32)
    host_url = f"http://127.0.0.1:{port}/mcp"
    env = os.environ.copy()
    # O smoke test nunca herda opt-ins de dados privados ou credenciais externas.
    for key in (
        "NYXAL_ENABLE_PRIVATE_READ_TOOLS",
        "NYXAL_ENABLE_MUTABLE_TOOLS",
        "NYXAL_AISWEB_API_KEY",
        "NYXAL_AISWEB_API_PASS",
        "NYXAL_HOME_ASSISTANT_TOKEN",
    ):
        env.pop(key, None)
    env.update({
        "NYXAL_MCP_TRANSPORT": "streamable-http",
        "NYXAL_MCP_HTTP_ENABLED": "1",
        "NYXAL_MCP_HTTP_HOST": "127.0.0.1",
        "NYXAL_MCP_HTTP_PORT": str(port),
        "NYXAL_MCP_HTTP_TOKEN": token,
    })
    process = subprocess.Popen(
        [sys.executable, str(SERVER)],
        cwd=BASE_DIR,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        aguardar_desafio_401(host_url, process)
        names = asyncio.run(validar_cliente_mcp(host_url, token))
        missing = REQUIRED_TOOLS - names
        if missing:
            raise AssertionError(f"Ferramentas MCP essenciais ausentes: {sorted(missing)}")
        print("MCP HTTP validado: bearer obrigatório e cliente autenticado lista as ferramentas esperadas.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stderr is not None:
            process.stderr.close()


if __name__ == "__main__":
    main()
