#!/usr/bin/env python3
"""Validação M5.11 — processos/aplicativos atravessam somente M5.10."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from nixal_controle_processos_aplicativos import (
    criar_gateway_processos,
    encerrar_processo_usuario,
)
from nixal_delta import RegistroDeltaNixOS


def main() -> None:
    pasta = Path(
        tempfile.mkdtemp(prefix="nyxal_m5_11_")
    )

    delta = RegistroDeltaNixOS(
        pasta / "delta.json"
    )

    gateway = criar_gateway_processos(
        arquivo_log=pasta / "gateway.json",
        delta_nyxos=delta,
    )

    contexto = gateway.contexto()

    assert contexto["quantidade_acoes"] == 2
    assert contexto["shell_arbitrario"] is False
    assert contexto["qwen_executor_direto"] is False
    assert contexto["autorizacao_evolucao"] is False
    assert contexto["integracao_executada"] is False
    assert contexto["arquitetura_modificada"] is False

    # Sem autorização, uma ação de host não executa.
    sem_autorizacao = gateway.executar(
        {
            "acao": "iniciar_aplicativo_conhecido",
            "argumentos": {
                "aplicativo": "terminal",
            },
        }
    )

    assert sem_autorizacao["sucesso"] is False
    assert (
        sem_autorizacao["valor"]["politica"]["estado"]
        == "autorizacao_acao_necessaria"
    )

    # Aplicativo fora do mapa fixo é rejeitado pela política.
    desconhecido = gateway.executar(
        {
            "acao": "iniciar_aplicativo_conhecido",
            "argumentos": {
                "aplicativo": "calculadora_qualquer",
            },
        },
        autorizacao_acao=True,
    )

    assert desconhecido["sucesso"] is False
    assert (
        desconhecido["valor"]["politica"]["estado"]
        == "argumentos_invalidos"
    )

    # Dry-run não abre nenhum aplicativo.
    dry_run = gateway.executar(
        {
            "acao": "iniciar_aplicativo_conhecido",
            "argumentos": {
                "aplicativo": "terminal",
            },
        },
        autorizacao_acao=True,
        dry_run=True,
    )

    assert dry_run["sucesso"] is True
    assert dry_run["estado"] == "acao_simulada"

    # Ação de encerramento exige inteiro e autorização.
    pid_invalido = gateway.executar(
        {
            "acao": "encerrar_processo_usuario",
            "argumentos": {
                "pid": "123",
            },
        },
        autorizacao_acao=True,
    )

    assert pid_invalido["sucesso"] is False
    assert (
        pid_invalido["valor"]["politica"]["estado"]
        == "argumentos_invalidos"
    )

    # A Nyxal não pode encerrar o próprio processo.
    try:
        encerrar_processo_usuario(
            pid=os.getpid()
        )
    except PermissionError:
        pass
    else:
        raise AssertionError(
            "o próprio processo da Nyxal não foi protegido"
        )

    # Validação real e segura do SIGTERM: filho temporário criado pelo teste.
    filho = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import time; time.sleep(30)",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for _ in range(20):
            if Path(
                f"/proc/{filho.pid}"
            ).is_dir():
                break
            time.sleep(0.05)

        real = gateway.executar(
            {
                "acao": "encerrar_processo_usuario",
                "argumentos": {
                    "pid": filho.pid,
                },
            },
            autorizacao_acao=True,
        )

        assert real["sucesso"] is True
        assert real["estado"] == "acao_executada"
        assert real["valor"]["resultado"]["sinal"] == "SIGTERM"

        filho.wait(timeout=5)

    finally:
        if filho.poll() is None:
            filho.terminate()
            filho.wait(timeout=5)

    # O gateway registrou a atuação real no Delta.
    assert delta.quantidade() == 1

    # O módulo de M5.11 não aceita comando arbitrário como parâmetro.
    codigo = Path(
        "nixal_controle_processos_aplicativos.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "shell=False" in codigo
    assert "SIGKILL" not in codigo
    assert "os.system" not in codigo

    print("TESTE_M5_11_CONTROLE_PROCESSOS_APLICATIVOS_OK")
    print("ALLOWLIST_APLICATIVOS: FIXA")
    print("AUTORIZACAO_EXPLICITA: OK")
    print("PROCESSO: SOMENTE_USUARIO_ATUAL")
    print("TERMINACAO: SIGTERM")
    print("SHELL: DESABILITADO")
    print("DELTA: REGISTRADO")


if __name__ == "__main__":
    main()
