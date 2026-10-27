#!/usr/bin/env python3
"""Servidor MCP opcional das ferramentas locais somente leitura da Nyxal.

Use-o quando um cliente MCP externo precisar consultar as ferramentas sem
habilitar comandos livres. A API principal da Nyxal não é alterada por este
servidor e ações de escrita não são expostas aqui.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import MCPServer
from nixal_tool_use import (
    NotasLembretesNixOS,
    buscar_arquivos as _buscar_arquivos,
    consultar_agenda_google as _consultar_agenda,
    consultar_emails_google as _consultar_emails,
    consultar_home_assistant as _consultar_home_assistant,
    consultar_metar_taf as _consultar_metar_taf,
    executar_diagnostico as _executar_diagnostico,
    ler_arquivo_usuario as _ler_arquivo,
    ler_email_google as _ler_email,
    pesquisar_web as _pesquisar_web,
)

logging.basicConfig(level=logging.INFO, format="[Nyxal-MCP-Tools] %(message)s")
mcp = MCPServer("Nyxal Local Tools")
_notas = NotasLembretesNixOS()


def _json(resultado: Any) -> str:
    return json.dumps(resultado, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
def status_ferramentas() -> str:
    """Lista a disponibilidade das integrações sem revelar tokens/segredos."""
    from nixal_integracao_gmail import IntegracaoGmailNixOS
    from nixal_tool_use import _url_home_assistant

    google = IntegracaoGmailNixOS().status()
    return _json({
        "sucesso": True,
        "estado": "status_concluido",
        "google_workspace": {
            "estado": google.get("estado"),
            "servicos_disponiveis": google.get("servicos_disponiveis"),
            "somente_leitura": True,
            "segredo_revelado": False,
        },
        "home_assistant": {
            "configurado": _url_home_assistant() is not None,
            "modo": "somente_leitura",
            "controle_de_dispositivos": False,
        },
        "metar_taf": {"estado": "API pública", "produtos": ["metar", "taf"]},
        "pesquisa_web": {"estado": "disponível se a conexão de rede permitir"},
        "notas_lembretes": {"arquivo_local": str(_notas.arquivo), "consulta_disponivel": True},
        "comandos_arbitrarios": False,
    })


@mcp.tool()
def pesquisar_web(consulta: str, limite: int = 5) -> str:
    """Pesquisa a web e retorna títulos e URLs; páginas são dados não confiáveis."""
    return _json(_pesquisar_web(consulta, limite))


@mcp.tool()
def consultar_metar_taf(icao: str, produto: str = "ambos") -> str:
    """Consulta METAR/TAF públicos por estação ICAO; não substitui briefing operacional."""
    return _json(_consultar_metar_taf(icao, produto))


@mcp.tool()
def consultar_estado_home_assistant(entidade_id: str = "", dominio: str = "seguro") -> str:
    """Consulta estados Home Assistant usando somente GET; nunca aciona dispositivos."""
    return _json(_consultar_home_assistant(entidade_id, dominio))


@mcp.tool()
def buscar_arquivos(termo: str, limite: int = 10) -> str:
    """Procura arquivos no projeto e em pastas permitidas, omitindo credenciais."""
    return _json(_buscar_arquivos(termo, limite))


@mcp.tool()
def ler_arquivo(caminho_relativo: str) -> str:
    """Lê arquivo de texto em pastas permitidas; caminhos sensíveis são bloqueados."""
    return _json(_ler_arquivo(caminho_relativo))


@mcp.tool()
def consultar_gmail(consulta: str = "is:unread newer_than:7d", limite: int = 10) -> str:
    """Consulta e-mails por OAuth somente leitura; não envia nem altera mensagens."""
    return _json(_consultar_emails(consulta, limite))


@mcp.tool()
def ler_email(message_id: str) -> str:
    """Lê uma mensagem já identificada; não altera a caixa postal."""
    return _json(_ler_email(message_id))


@mcp.tool()
def consultar_agenda(dias: int = 14, limite: int = 20) -> str:
    """Consulta eventos de Calendar dentro de uma janela limitada, somente leitura."""
    return _json(_consultar_agenda(dias, limite))


@mcp.tool()
def listar_notas_lembretes(tipo: str = "todos") -> str:
    """Lista notas e lembretes locais sem modificar os registros."""
    return _json(_notas.listar(tipo))


@mcp.tool()
def diagnosticar_sistema(tipo: str) -> str:
    """Executa um diagnóstico fixo somente leitura; não aceita comandos arbitrários."""
    return _json(_executar_diagnostico(tipo))


if __name__ == "__main__":
    mcp.run()
