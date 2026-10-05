#!/usr/bin/env python3
"""
NYXOS — M5.11 CONTROLE DE PROCESSOS E APLICATIVOS

Ações concretas de host que atravessam exclusivamente o gateway M5.10.

Regras:
- nenhum comando é aceito como entrada;
- aplicativos são resolvidos por mapa fixo de executáveis;
- lançamento usa lista de argumentos e shell desabilitado;
- encerramento só atinge processos do usuário atual;
- Nyxal não pode encerrar o próprio processo;
- encerramento usa SIGTERM, nunca SIGKILL;
- toda atuação exige autorização explícita no gateway;
- dry-run e observabilidade são fornecidos pelo gateway.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from nixal_delta import RegistroDeltaNixOS
from nixal_gateway_atuacao_host import (
    ContratoAcaoHost,
    GatewayAtuacaoHostNixOS,
)


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_DELTA_PADRAO = BASE_DIR / "delta_nyxos.json"

APLICATIVOS_CONHECIDOS: dict[str, tuple[str, ...]] = {
    "terminal": (
        "/usr/bin/gnome-terminal",
        "/usr/bin/kgx",
        "/usr/bin/konsole",
        "/usr/bin/xterm",
        "/usr/bin/alacritty",
    ),
    "navegador": (
        "/usr/bin/firefox",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
    ),
}


def _resolver_executavel(aplicativo: str) -> str:
    opcoes = APLICATIVOS_CONHECIDOS.get(aplicativo)

    if opcoes is None:
        raise ValueError(
            f"aplicativo_nao_conhecido:{aplicativo}"
        )

    for caminho in opcoes:
        caminho_path = Path(caminho)
        if (
            caminho_path.is_file()
            and os.access(caminho_path, os.X_OK)
        ):
            return caminho

    raise FileNotFoundError(
        f"executavel_nao_instalado:{aplicativo}"
    )


def executar_aplicativo_conhecido(
    *,
    aplicativo: str,
) -> dict[str, Any]:
    executavel = _resolver_executavel(
        aplicativo
    )

    processo = subprocess.Popen(
        [executavel],
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return {
        "executada": True,
        "operacao": "iniciar_aplicativo_conhecido",
        "aplicativo": aplicativo,
        "executavel": executavel,
        "pid": processo.pid,
    }


def _uid_processo(pid: int) -> int | None:
    caminho = Path(
        f"/proc/{pid}/status"
    )

    try:
        texto = caminho.read_text(
            encoding="utf-8"
        )
    except (
        OSError,
        UnicodeDecodeError,
    ):
        return None

    for linha in texto.splitlines():
        if not linha.startswith("Uid:"):
            continue

        partes = linha.split()
        if len(partes) < 2:
            return None

        try:
            return int(partes[1])
        except ValueError:
            return None

    return None


def encerrar_processo_usuario(
    *,
    pid: int,
) -> dict[str, Any]:
    if not isinstance(pid, int) or isinstance(pid, bool):
        raise TypeError(
            "pid_precisa_ser_integer"
        )

    if pid <= 1:
        raise ValueError(
            "pid_protegido"
        )

    if pid == os.getpid():
        raise PermissionError(
            "nyxal_nao_pode_encerrar_o_proprio_processo"
        )

    if not Path(
        f"/proc/{pid}"
    ).is_dir():
        raise ProcessLookupError(
            f"processo_inexistente:{pid}"
        )

    uid_atual = os.getuid()
    uid_alvo = _uid_processo(pid)

    if uid_alvo is None:
        raise ProcessLookupError(
            f"uid_processo_indisponivel:{pid}"
        )

    if uid_alvo != uid_atual:
        raise PermissionError(
            "processo_nao_pertence_ao_usuario_atual"
        )

    os.kill(
        pid,
        signal.SIGTERM,
    )

    return {
        "executada": True,
        "operacao": "encerrar_processo_usuario",
        "pid": pid,
        "sinal": "SIGTERM",
    }


def criar_gateway_processos(
    *,
    arquivo_log: str | Path | None = None,
    delta_nyxos: RegistroDeltaNixOS | None = None,
) -> GatewayAtuacaoHostNixOS:
    log = (
        Path(arquivo_log)
        if arquivo_log is not None
        else BASE_DIR / "log_atuacao_host_nixal.json"
    )

    contratos = {
        "iniciar_aplicativo_conhecido": ContratoAcaoHost(
            nome="iniciar_aplicativo_conhecido",
            descricao=(
                "Inicia somente um aplicativo presente no mapa fixo."
            ),
            objetivo=(
                "Abrir um aplicativo conhecido sem interpretar comandos."
            ),
            argumentos={
                "aplicativo": {
                    "tipo": "string",
                    "obrigatorio": True,
                    "valores": sorted(
                        APLICATIVOS_CONHECIDOS
                    ),
                }
            },
            dominio="processos_aplicativos",
            nivel_risco="medio",
            reversivel=True,
            requer_autorizacao_explicita=True,
        ),
        "encerrar_processo_usuario": ContratoAcaoHost(
            nome="encerrar_processo_usuario",
            descricao=(
                "Encerra com SIGTERM um processo do usuário atual."
            ),
            objetivo=(
                "Permitir encerramento controlado de processo pertencente "
                "ao usuário, sem atingir o processo da Nyxal."
            ),
            argumentos={
                "pid": {
                    "tipo": "integer",
                    "obrigatorio": True,
                }
            },
            dominio="processos_aplicativos",
            nivel_risco="alto",
            reversivel=False,
            requer_autorizacao_explicita=True,
        ),
    }

    executores = {
        "iniciar_aplicativo_conhecido":
            executar_aplicativo_conhecido,
        "encerrar_processo_usuario":
            encerrar_processo_usuario,
    }

    return GatewayAtuacaoHostNixOS(
        contratos=contratos,
        executores=executores,
        arquivo_log=log,
        delta_nyxos=delta_nyxos,
    )


__all__ = [
    "APLICATIVOS_CONHECIDOS",
    "criar_gateway_processos",
    "executar_aplicativo_conhecido",
    "encerrar_processo_usuario",
]


if __name__ == "__main__":
    gateway = criar_gateway_processos(
        delta_nyxos=RegistroDeltaNixOS(
            ARQUIVO_DELTA_PADRAO
        )
    )

    print("M5.11 — CONTROLE DE PROCESSOS E APLICATIVOS")
    print("Ações:")
    for acao in gateway.listar_acoes():
        print(
            "-",
            acao["nome"],
            "| risco:",
            acao["nivel_risco"],
            "| reversível:",
            acao["reversivel"],
        )

    print()
    print("Contexto:")
    print(gateway.contexto())
    print()
    print(
        "Python:",
        sys.executable,
    )
