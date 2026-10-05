#!/usr/bin/env python3
"""Validação M5.15 — gateway governado de atuação."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_ciclo_residente import CicloResidenteNixOS
from nixal_gateway_atuacao import GatewayAtuacaoNixOS
from nixal_plano_central_controle import PlanoCentralControleNixOS


def criar_plano() -> dict:
    plano = PlanoCentralControleNixOS()
    return plano.gerar_plano(
        ciclo={"sucesso": True},
        fisiologia={
            "estado_fisiologico": "febre",
            "heartbeat": {"estado": "regular"},
            "termico": {"estado_termico": "muito_quente"},
        },
    )


def main() -> None:
    pasta = Path(tempfile.mkdtemp(prefix="nyxos_m5_15_"))
    chamadas: list[str] = []

    def executor(acao: str) -> dict:
        chamadas.append(acao)
        return {"acao_recebida": acao}

    plano = criar_plano()

    gateway = GatewayAtuacaoNixOS(
        arquivo=pasta / "gateway.json",
        executor=executor,
    )

    operacao = gateway.preparar(plano=plano)
    assert operacao["acao"] == "reduzir_carga"
    assert operacao["estado"] == "preparada"
    assert operacao["gateway_atuacao"] is True
    assert operacao["executada"] is False

    bloqueado_sem_autorizacao = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=False,
    )
    assert bloqueado_sem_autorizacao["estado"] == "bloqueado"
    assert bloqueado_sem_autorizacao["motivo"] == "autorizacao_explicita_ausente"
    assert bloqueado_sem_autorizacao["executada"] is False
    assert chamadas == []

    bloqueado_por_padrao = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=True,
    )
    assert bloqueado_por_padrao["estado"] == "bloqueado"
    assert bloqueado_por_padrao["motivo"] == "execucao_fisica_desabilitada"
    assert bloqueado_por_padrao["executada"] is False
    assert chamadas == []

    gateway_ativo = GatewayAtuacaoNixOS(
        executor=executor,
        execucao_fisica_habilitada=True,
    )
    operacao_ativa = gateway_ativo.preparar(plano=plano)

    executado = gateway_ativo.executar(
        operacao=operacao_ativa,
        autorizacao_explicita=True,
    )
    assert executado["estado"] == "executado"
    assert executado["executada"] is True
    assert executado["autorizacao_explicita"] is True
    assert chamadas == ["reduzir_carga"]

    assert (pasta / "gateway.json").is_file()
    contexto = gateway.contexto()
    assert contexto["execucao_fisica_habilitada"] is False
    assert contexto["autorizacao_explicita"] is False

    print("TESTE_M5_15_GATEWAY_ATUACAO_OK")
    print("PLANO: VALIDADO")
    print("AUTORIZACAO_EXPLICITA: OBRIGATORIA")
    print("EXECUCAO_PADRAO: BLOQUEADA")
    print("EXECUCAO_FISICA: DESABILITADA")
    print("GATEWAY: ISOLADO_DO_HOST")


if __name__ == "__main__":
    main()
