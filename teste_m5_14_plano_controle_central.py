#!/usr/bin/env python3
"""Validação M5.14 — plano central de controle."""

from __future__ import annotations

from nixal_plano_controle_central import PlanoControleCentralNixOS


class HabitatFalso:
    def snapshot(self):
        return {"sucesso": True, "estado": "habitat_observado", "modo": "somente_leitura"}


class FisiologiaFalsa:
    def contexto(self):
        return {"sucesso": True, "estado": "fisiologia_disponivel"}


class AgenteFalso:
    def selecionar_capacidade(self, necessidade: str):
        return {
            "sucesso": True,
            "capacidade": "ler_estado_corpo",
            "argumentos": {},
            "necessidade": necessidade,
        }


class GatewayFalso:
    def contexto(self):
        return {"sucesso": True, "estado": "gateway_atuacao_disponivel"}

    def executar(self, solicitacao, *, autorizacao_acao=False, dry_run=False):
        return {
            "sucesso": True,
            "estado": "acao_simulada" if dry_run else "acao_executada",
            "valor": {
                "solicitacao": solicitacao,
                "autorizacao_acao": autorizacao_acao,
                "dry_run": dry_run,
            },
        }


def main() -> None:
    plano = PlanoControleCentralNixOS(
        habitat=HabitatFalso(),
        fisiologia=FisiologiaFalsa(),
        gateway_host=GatewayFalso(),
        agente=AgenteFalso(),
    )

    contexto = plano.contexto()
    assert contexto["executor_proprio"] is False
    assert contexto["shell_arbitrario"] is False
    assert contexto["autorizacao_evolucao"] is False
    assert contexto["integracao_executada"] is False
    assert contexto["arquitetura_modificada"] is False
    assert contexto["conhecimento_permanente"] is False

    observado = plano.processar("observar")
    assert observado["sucesso"] is True
    assert observado["estado"] == "observacao_centralizada"
    assert observado["valor"]["habitat"]["estado"] == "habitat_observado"
    assert observado["valor"]["fisiologia"]["estado"] == "fisiologia_disponivel"
    assert observado["valor"]["gateway_atuacao"]["estado"] == "gateway_atuacao_disponivel"

    selecionado = plano.processar(
        "selecionar_capacidade",
        {"necessidade": "como está meu computador"},
    )
    assert selecionado["sucesso"] is True
    assert selecionado["valor"]["selecao"]["capacidade"] == "ler_estado_corpo"

    simulado = plano.processar(
        "atuar_host",
        {
            "solicitacao": {
                "acao": "acao_teste",
                "argumentos": {},
            },
            "autorizacao_acao": True,
            "dry_run": True,
        },
    )
    assert simulado["sucesso"] is True
    assert simulado["estado"] == "acao_simulada"

    natural = plano.processar(
        "abra o terminal",
    )
    assert natural["sucesso"] is False
    assert natural["estado"] == "operacao_nao_permitida"

    payload_invalido = plano.processar(
        "selecionar_capacidade",
        {"necessidade": 123},
    )
    assert payload_invalido["sucesso"] is False
    assert payload_invalido["estado"] == "necessidade_invalida"

    print("TESTE_M5_14_PLANO_CONTROLE_CENTRAL_OK")
    print("OBSERVACAO_CENTRALIZADA: OK")
    print("DECISAO_SEMANTICA_SEPARADA: OK")
    print("GATEWAY_UNICO_DE_ATUACAO: OK")
    print("EXECUTOR_PROPRIO: DESABILITADO")
    print("SHELL_ARBITRARIO: DESABILITADO")
    print("GOVERNANCA_EVOLUTIVA: PRESERVADA")


if __name__ == "__main__":
    main()
