#!/usr/bin/env python3
"""Smoke test for Nyxal's optional MCP stdio server using the MCP Python SDK v2."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

BASE_DIR = Path(__file__).resolve().parent
PYTHON = Path(sys.executable)
SERVER = BASE_DIR / "nyxal_mcp_tools.py"
REQUIRED_TOOLS = {
    "status_ferramentas",
    "consultar_metar_taf",
    "consultar_notam_aisweb",
    "consultar_cartas_aisweb",
    "diagnosticar_sistema",
}


async def main() -> None:
    if not SERVER.is_file():
        raise SystemExit(f"Servidor MCP ausente: {SERVER}")

    params = StdioServerParameters(
        command=str(PYTHON),
        args=[str(SERVER)],
    )
    async with Client(params) as client:
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        missing = REQUIRED_TOOLS - names
        if missing:
            raise RuntimeError(f"Ferramentas MCP ausentes: {sorted(missing)}")

        status = await client.call_tool("status_ferramentas", {})
        if status.is_error:
            raise RuntimeError("A consulta status_ferramentas retornou erro.")
        status_text = "\n".join(
            getattr(item, "text", "")
            for item in (status.content or [])
        )
        try:
            status_payload = __import__("json").loads(status_text)
        except (ValueError, TypeError) as erro:
            raise RuntimeError("status_ferramentas não retornou JSON válido.") from erro
        notas_status = status_payload.get("notas_lembretes", {})
        if "arquivo" in notas_status:
            raise RuntimeError("status_ferramentas expôs o caminho local das notas.")
        if "/home/" in status_text or "/Users/" in status_text:
            raise RuntimeError("status_ferramentas expôs um caminho absoluto de usuário.")

        # Sem opt-in, mesmo os diagnósticos de sistema não podem revelar
        # processos, métricas de disco/memória ou outras informações locais.
        privado = await client.call_tool("diagnosticar_sistema", {"tipo": "sistema"})
        if privado.is_error:
            raise RuntimeError("A chamada de diagnóstico privado não foi tratada com segurança.")
        privado_text = "\n".join(
            getattr(item, "text", "")
            for item in (privado.content or [])
        )
        if "opt_in_privacidade_ausente" not in privado_text:
            raise RuntimeError("O diagnóstico privado não respeitou a política de opt-in.")

        print("MCP conectado.")
        print(f"Ferramentas anunciadas: {len(names)}")
        print("Contrato de status e privacidade: OK")


if __name__ == "__main__":
    asyncio.run(main())
