#!/usr/bin/env python3
"""Smoke test for the optional MCP stdio server (Python MCP SDK v2)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from mcp import Client, StdioServerParameters

BASE_DIR = Path(__file__).resolve().parent
PYTHON = BASE_DIR / ".venv" / "bin" / "python"
SERVER = BASE_DIR / "nyxal_mcp_tools.py"
REQUIRED_TOOLS = {
    "status_ferramentas",
    "consultar_metar_taf",
    "consultar_notam_aisweb",
    "consultar_cartas_aisweb",
}


async def main() -> None:
    if not PYTHON.is_file():
        raise SystemExit(
            f"Virtualenv ausente: {PYTHON}. Instale a dependência MCP opcional primeiro."
        )
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

        print("MCP conectado.")
        print(f"Ferramentas anunciadas: {len(names)}")
        print("Contrato de status: OK")


if __name__ == "__main__":
    asyncio.run(main())
