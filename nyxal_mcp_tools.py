#!/usr/bin/env python3
"""Servidor MCP opcional da Nyxal expondo ferramentas locais de forma governada."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from mcp.server import MCPServer

from nixal_tool_use import (
    NotasLembretesNixOS,
    buscar_arquivos as _buscar_arquivos,
    consultar_agenda_google as _consultar_agenda,
    consultar_emails_google as _consultar_emails,
    consultar_home_assistant as _consultar_home_assistant,
    consultar_metar_taf as _consultar_metar_taf,
    consultar_notam_aisweb as _consultar_notam_aisweb,
    consultar_cartas_aisweb as _consultar_cartas_aisweb,
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


def _dados_privados_habilitados() -> bool:
    return os.environ.get(
        "NYXAL_ENABLE_PRIVATE_READ_TOOLS", ""
    ).strip().lower() in {"1", "true", "yes", "on"}


def _bloqueio_privacidade() -> str:
    return _json({
        "sucesso": False,
        "estado": "opt_in_privacidade_ausente",
        "motivo": (
            "Leituras de dados locais/pessoais exigem NYXAL_ENABLE_PRIVATE_READ_TOOLS=1 "
            "no ambiente do processo MCP."
        ),
    })


@mcp.tool()
def status_ferramentas() -> str:
    """Retorna o status das integrações sem revelar segredos."""
    from nixal_integracao_gmail import IntegracaoGmailNixOS
    from nixal_tool_use import _url_home_assistant

    status_google = IntegracaoGmailNixOS().status()
    return _json({
        "sucesso": True,
        "google_workspace": {
            "estado": status_google.get("estado"),
            "servicos_disponiveis": status_google.get("servicos_disponiveis"),
            "somente_leitura": True,
        },
        "home_assistant": {"configurado": _url_home_assistant() is not None, "somente_leitura": True},
        "aviao": {"produtos": ["METAR", "TAF", "NOTAM", "cartas"], "metar_taf_fonte": "AviationWeather.gov Data API", "notam_cartas_fonte": "AISWEB/DECEA", "aisweb_configurado": bool(os.environ.get("NYXAL_AISWEB_API_KEY") and os.environ.get("NYXAL_AISWEB_API_PASS"))},
        "pesquisa_web": "disponível quando a rede permitir",
        "notas_lembretes": {"armazenamento": "local_persistido", "modo": "somente leitura neste servidor MCP"},
        "comandos_arbitrarios": False,
        "segredos_incluidos": False,
    })


@mcp.tool()
def pesquisar_web(consulta: str, limite: int = 5) -> str:
    """Pesquisa na web e retorna títulos/URLs para inspeção humana."""
    return _json(_pesquisar_web(consulta, limite))


@mcp.tool()
def consultar_metar_taf(icao: str, produto: str = "ambos") -> str:
    """Consulta METAR/TAF públicos; não substitui o briefing operacional."""
    return _json(_consultar_metar_taf(icao, produto))


@mcp.tool()
def consultar_notam_aisweb(localidades: str, fir: str = "", limite: int = 20) -> str:
    """Consulta NOTAM no AISWEB/DECEA; confirmação oficial pré-voo permanece obrigatória."""
    return _json(_consultar_notam_aisweb(localidades, fir, limite))


@mcp.tool()
def consultar_cartas_aisweb(
    icao: str = "",
    especie: str = "",
    tipo: str = "",
    nome: str = "",
    dt: str = "",
    limite: int = 20,
) -> str:
    """Pesquisa metadados/links de cartas oficiais do AISWEB; não substitui briefing pré-voo."""
    return _json(_consultar_cartas_aisweb(icao, especie, tipo, nome, dt, limite))


@mcp.tool()
def consultar_home_assistant(entidade_id: str = "", dominio: str = "seguro") -> str:
    """Consulta estado dos dispositivos Home Assistant; não aciona dispositivos."""
    if not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_consultar_home_assistant(entidade_id, dominio))


@mcp.tool()
def buscar_arquivos(termo: str, limite: int = 10) -> str:
    """Busca arquivos em pastas permitidas, omitindo credenciais."""
    if not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_buscar_arquivos(termo, limite))


@mcp.tool()
def ler_arquivo(caminho_relativo: str) -> str:
    """Lê texto de arquivo em pastas permitidas e bloqueia arquivos sensíveis."""
    if not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_ler_arquivo(caminho_relativo))


@mcp.tool()
def consultar_gmail(consulta: str = "is:unread newer_than:7d", limite: int = 10) -> str:
    """Consulta Gmail OAuth apenas em modo de leitura."""
    if not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_consultar_emails(consulta, limite))


@mcp.tool()
def ler_email(message_id: str) -> str:
    """Lê uma mensagem específica; não altera a caixa de entrada."""
    if not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_ler_email(message_id))


@mcp.tool()
def consultar_agenda(dias: int = 14, limite: int = 20) -> str:
    """Consulta eventos Google Calendar, somente leitura."""
    if not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_consultar_agenda(dias, limite))


@mcp.tool()
def listar_notas_lembretes(tipo: str = "todos") -> str:
    """Lista notas/lembretes locais sem alterar registros."""
    if not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_notas.listar(tipo))


@mcp.tool()
def diagnosticar_sistema(tipo: str) -> str:
    """Executa diagnóstico fixo e somente leitura, sem shell livre."""
    if tipo in {"sistema", "processos", "disco", "memoria"} and not _dados_privados_habilitados():
        return _bloqueio_privacidade()
    return _json(_executar_diagnostico(tipo))


def main() -> None:
    """Usa stdio por padrão; HTTP local só existe com opt-in e token bearer."""
    transport = os.environ.get("NYXAL_MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
        return
    if transport != "streamable-http":
        raise SystemExit("NYXAL_MCP_TRANSPORT precisa ser stdio ou streamable-http.")

    from nixal_mcp_runtime import MCPBearerTokenMiddleware, configuracao_mcp_http
    config = configuracao_mcp_http(os.environ)
    if config is None:
        raise SystemExit("MCP HTTP recusado: configure NYXAL_MCP_HTTP_ENABLED=1.")
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("MCP HTTP requer mcp[cli] no ambiente da Nyxal.") from exc
    app = MCPBearerTokenMiddleware(mcp.streamable_http_app(), config.token)
    uvicorn.run(
        app, host=config.host, port=config.port, log_level="warning",
        access_log=False, server_header=False, date_header=False,
    )

if __name__ == "__main__":
    main()
