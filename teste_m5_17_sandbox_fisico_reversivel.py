#!/usr/bin/env python3
"""Validação M5.17 — sandbox físico reversível."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_adaptador_sandbox_fisico import AdaptadorSandboxFisicoNixOS
from nixal_gateway_atuacao import GatewayAtuacaoNixOS
from nixal_plano_central_controle import PlanoCentralControleNixOS


def criar_plano(acao: str) -> dict:
    plano = PlanoCentralControleNixOS().gerar_plano(
        ciclo={"sucesso": True},
        fisiologia={
            "estado_fisiologico": "normal",
            "heartbeat": {"estado": "regular"},
            "termico": {"estado_termico": "normal"},
        },
    )
    plano["decisao"]["acao_planejada"] = acao
    return plano


def main() -> None:
    pasta = Path(tempfile.mkdtemp(prefix="nyxos_m5_17_"))

    sandbox_bloqueado = AdaptadorSandboxFisicoNixOS(
        diretorio_sandbox=pasta / "bloqueado",
        habilitada=False,
    )
    bloqueado = sandbox_bloqueado.executar("preservar_estado")
    assert bloqueado["estado"] == "bloqueado"
    assert bloqueado["motivo"] == "sandbox_fisico_desabilitado"

    sandbox = AdaptadorSandboxFisicoNixOS(
        diretorio_sandbox=pasta / "sandbox",
        habilitada=True,
    )
    gateway = GatewayAtuacaoNixOS(
        executor=sandbox,
        execucao_fisica_habilitada=True,
    )

    plano = criar_plano("preservar_estado")
    operacao = gateway.preparar(plano=plano)

    sem_autorizacao = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=False,
    )
    assert sem_autorizacao["estado"] == "bloqueado"
    assert sem_autorizacao["motivo"] == "autorizacao_explicita_ausente"

    executado = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=True,
    )
    assert executado["estado"] == "executado"
    assert executado["executada"] is True
    resultado = executado["resultado_executor"]
    assert resultado["atuacao_fisica"] is True
    assert resultado["mutacao_host"] is True

    arquivo = Path(resultado["resultado"]["arquivo"])
    token = resultado["resultado"]["rollback_token"]
    assert arquivo.is_file()
    assert arquivo.resolve().is_relative_to(
        (pasta / "sandbox").resolve()
    )

    rollback = sandbox.rollback(token)
    assert rollback["sucesso"] is True
    assert rollback["rollback_executado"] is True
    assert not arquivo.exists()

    reduzir = sandbox.executar("reduzir_carga")
    assert reduzir["estado"] == "bloqueado"
    assert reduzir["motivo"] == "atuacao_fisica_nao_implementada"

    contexto = sandbox.contexto()
    assert contexto["habilitada"] is True
    assert contexto["rollback_disponivel"] is True

    print("TESTE_M5_17_SANDBOX_FISICO_REVERSIVEL_OK")
    print("AUTORIZACAO_EXPLICITA: OBRIGATORIA")
    print("MUTACAO: CONFINADA_AO_SANDBOX")
    print("ROLLBACK: VALIDADO")
    print("REDUZIR_CARGA: BLOQUEADO")


if __name__ == "__main__":
    main()
