#!/usr/bin/env python3
"""Validação do M5.10 — Gateway de atuação controlada do host."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_delta import RegistroDeltaNixOS
from nixal_gateway_atuacao_host import (
    ContratoAcaoHost,
    GatewayAtuacaoHostNixOS,
)


def novo_gateway():
    pasta = Path(tempfile.mkdtemp(prefix="nyxal_m5_10_"))
    delta = RegistroDeltaNixOS(pasta / "delta.json")
    contador = {"execucoes": 0}

    contrato = ContratoAcaoHost(
        nome="acao_teste_controlada",
        descricao="Ação falsa usada somente para validar o gateway.",
        objetivo=(
            "Comprovar que somente um executor registrado "
            "atravessa a política."
        ),
        argumentos={
            "valor": {
                "tipo": "string",
                "obrigatorio": True,
            }
        },
        dominio="teste",
        nivel_risco="baixo",
        reversivel=True,
        requer_autorizacao_explicita=True,
    )

    def executor_teste(*, valor: str) -> dict:
        contador["execucoes"] += 1
        return {"valor_recebido": valor}

    gateway = GatewayAtuacaoHostNixOS(
        contratos={contrato.nome: contrato},
        executores={contrato.nome: executor_teste},
        arquivo_log=pasta / "gateway.json",
        delta_nyxos=delta,
    )

    return gateway, contador, delta


def main() -> None:
    gateway, contador, delta = novo_gateway()

    natural = gateway.executar("abra o terminal")

    assert natural["sucesso"] is False
    assert natural["estado"] == "acao_rejeitada_pela_politica"
    assert (
        natural["valor"]["politica"]["estado"]
        == "entrada_invalida"
    )

    desconhecida = gateway.executar(
        {
            "acao": "executar_shell",
            "argumentos": {
                "comando": "echo proibido",
            },
        },
        autorizacao_acao=True,
    )

    assert desconhecida["sucesso"] is False
    assert (
        desconhecida["valor"]["politica"]["estado"]
        == "acao_nao_registrada"
    )

    sem_autorizacao = gateway.executar(
        {
            "acao": "acao_teste_controlada",
            "argumentos": {
                "valor": "teste",
            },
        }
    )

    assert sem_autorizacao["sucesso"] is False
    assert (
        sem_autorizacao["valor"]["politica"]["estado"]
        == "autorizacao_acao_necessaria"
    )
    assert contador["execucoes"] == 0

    argumento_extra = gateway.executar(
        {
            "acao": "acao_teste_controlada",
            "argumentos": {
                "valor": "teste",
                "comando": "não pode",
            },
        },
        autorizacao_acao=True,
    )

    assert argumento_extra["sucesso"] is False
    assert (
        argumento_extra["valor"]["politica"]["estado"]
        == "argumentos_invalidos"
    )
    assert contador["execucoes"] == 0

    simulacao = gateway.executar(
        {
            "acao": "acao_teste_controlada",
            "argumentos": {
                "valor": "simulacao",
            },
        },
        autorizacao_acao=True,
        dry_run=True,
    )

    assert simulacao["sucesso"] is True
    assert simulacao["estado"] == "acao_simulada"
    assert contador["execucoes"] == 0

    executada = gateway.executar(
        {
            "acao": "acao_teste_controlada",
            "argumentos": {
                "valor": "permitido",
            },
        },
        autorizacao_acao=True,
    )

    assert executada["sucesso"] is True
    assert executada["estado"] == "acao_executada"
    assert contador["execucoes"] == 1
    assert delta.quantidade() == 1

    contexto = gateway.contexto()

    assert contexto["shell_arbitrario"] is False
    assert contexto["entrada_linguagem_natural"] is False
    assert contexto["qwen_executor_direto"] is False
    assert contexto["autorizacao_evolucao"] is False
    assert contexto["integracao_executada"] is False
    assert contexto["arquitetura_modificada"] is False
    assert contexto["conhecimento_permanente"] is False

    codigo = Path(
        "nixal_gateway_atuacao_host.py"
    ).read_text(encoding="utf-8")

    proibidos = (
        "subprocess",
        "os.system",
        "Popen(",
        "shell=True",
        "eval(",
        "exec(",
    )

    for termo in proibidos:
        assert termo not in codigo, (
            f"mecanismo proibido encontrado: {termo}"
        )

    print("TESTE_M5_10_GATEWAY_ATUACAO_HOST_OK")
    print("ALLOWLIST: ATIVA")
    print("POLITICA_SEPARADA_DA_DECISAO: OK")
    print("SHELL_ARBITRARIO: DESABILITADO")
    print("QWEN_EXECUTOR_DIRETO: DESABILITADO")
    print("DRY_RUN: OK")
    print("DELTA: REGISTRADO")


if __name__ == "__main__":
    main()
