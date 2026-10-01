#!/usr/bin/env python3

import asyncio
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


BASE_DIR = Path(__file__).resolve().parent


async def main():
    servidor = StdioServerParameters(
        command=str(BASE_DIR / ".venv" / "bin" / "python"),
        args=["nyxal_mcp_server.py"],
        cwd=BASE_DIR,
    )

    async with stdio_client(servidor) as (leitura, escrita):
        async with ClientSession(leitura, escrita) as sessao:
            await sessao.initialize()

            ferramentas = await sessao.list_tools()

            print("MCP conectado.")
            print("Ferramentas:")
            for ferramenta in ferramentas.tools:
                print(f" - {ferramenta.name}")

            resultado = await sessao.call_tool(
                "status_nyxal",
                {},
            )

            print("\nResposta de status_nyxal:")
            for conteudo in resultado.content:
                if hasattr(conteudo, "text"):
                    print(conteudo.text)


if __name__ == "__main__":
    asyncio.run(main())
