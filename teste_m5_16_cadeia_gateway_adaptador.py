#!/usr/bin/env python3
"""Validação M5.16 — cadeia gateway + adaptador controlado."""

from __future__ import annotations

from nixal_adaptador_host_controlado import AdaptadorHostControladoNixOS
from nixal_gateway_atuacao import GatewayAtuacaoNixOS
from nixal_plano_central_controle import PlanoCentralControleNixOS


def plano_com_acao(acao: str) -> dict:
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
    adaptador = AdaptadorHostControladoNixOS()

    gateway = GatewayAtuacaoNixOS(
        executor=adaptador,
        execucao_fisica_habilitada=True,
    )

    plano_observar = plano_com_acao("observar")
    operacao_observar = gateway.preparar(plano=plano_observar)

    bloqueado = gateway.executar(
        operacao=operacao_observar,
        autorizacao_explicita=False,
    )
    assert bloqueado["estado"] == "bloqueado"
    assert bloqueado["motivo"] == "autorizacao_explicita_ausente"

    executado = gateway.executar(
        operacao=operacao_observar,
        autorizacao_explicita=True,
    )
    assert executado["estado"] == "executado"
    assert executado["executada"] is True
    assert executado["resultado_executor"]["atuacao_fisica"] is False
    assert executado["resultado_executor"]["mutacao_host"] is False

    plano_fisico = plano_com_acao("reduzir_carga")
    operacao_fisica = gateway.preparar(plano=plano_fisico)
    bloqueado_fisico = gateway.executar(
        operacao=operacao_fisica,
        autorizacao_explicita=True,
    )
    assert bloqueado_fisico["estado"] == "executado"
    assert bloqueado_fisico["executada"] is True
    assert bloqueado_fisico["resultado_executor"]["estado"] == "bloqueado"
    assert bloqueado_fisico["resultado_executor"]["motivo"] == (
        "atuacao_fisica_nao_implementada"
    )
    assert bloqueado_fisico["resultado_executor"]["mutacao_host"] is False

    print("TESTE_M5_16_CAIXA_COMPLETA_OK")
    print("GATEWAY: VALIDADO")
    print("AUTORIZACAO_EXPLICITA: OBRIGATORIA")
    print("ADAPTADOR: CONECTADO")
    print("LEITURA: EXECUTAVEL")
    print("MUTACAO_FISICA: BLOQUEADA")


if __name__ == "__main__":
    main()
