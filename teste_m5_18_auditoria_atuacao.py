#!/usr/bin/env python3
"""Validação M5.18 — auditoria encadeada da atuação física."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_adaptador_sandbox_fisico import AdaptadorSandboxFisicoNixOS
from nixal_auditoria_atuacao import AuditoriaAtuacaoNixOS
from nixal_gateway_atuacao import GatewayAtuacaoNixOS
from nixal_plano_central_controle import PlanoCentralControleNixOS


def criar_plano() -> dict:
    return PlanoCentralControleNixOS().gerar_plano(
        ciclo={"sucesso": True},
        fisiologia={
            "estado_fisiologico": "normal",
            "heartbeat": {"estado": "regular"},
            "termico": {"estado_termico": "normal"},
        },
    )


def main() -> None:
    pasta = Path(tempfile.mkdtemp(prefix="nyxos_m5_18_"))
    arquivo_auditoria = pasta / "auditoria.jsonl"

    auditoria = AuditoriaAtuacaoNixOS(arquivo=arquivo_auditoria)
    sandbox = AdaptadorSandboxFisicoNixOS(
        diretorio_sandbox=pasta / "sandbox",
        habilitada=True,
        auditoria=auditoria,
    )
    gateway = GatewayAtuacaoNixOS(
        executor=sandbox,
        execucao_fisica_habilitada=True,
        auditoria=auditoria,
    )

    plano = criar_plano()
    plano["decisao"]["acao_planejada"] = "preservar_estado"
    operacao = gateway.preparar(plano=plano)

    bloqueado = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=False,
    )
    assert bloqueado["estado"] == "bloqueado"

    executado = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=True,
    )
    assert executado["estado"] == "executado"
    token = executado["resultado_executor"]["resultado"]["rollback_token"]

    rollback = sandbox.rollback(token)
    assert rollback["sucesso"] is True

    validacao = auditoria.validar()
    assert validacao["valido"] is True
    assert validacao["registros"] == 5

    linhas = arquivo_auditoria.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 5

    eventos = [json.loads(linha)["evento"] for linha in linhas]
    assert eventos == [
        "operacao_preparada",
        "operacao_bloqueada",
        "atuacao_sandbox_executada",
        "operacao_executada",
        "rollback_executado",
    ]

    # Uma segunda instância/processo deve continuar a cadeia sem repetir
    # sequência ou hash anterior.
    auditoria_2 = AuditoriaAtuacaoNixOS(arquivo=arquivo_auditoria)
    segundo = auditoria_2.registrar(
        evento="teste_segunda_instancia",
        dados={"origem": "teste"},
    )
    assert segundo["sequencia"] == 6
    assert segundo["hash_anterior"] == validacao["ultimo_hash"]

    validacao_2 = auditoria_2.validar()
    assert validacao_2["valido"] is True
    assert validacao_2["registros"] == 6

    linhas_apos_segunda_instancia = arquivo_auditoria.read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(linhas_apos_segunda_instancia) == 6
    assert json.loads(linhas_apos_segunda_instancia[-1])["evento"] == (
        "teste_segunda_instancia"
    )

    # Um arquivo truncado/corrompido não pode derrubar o residente.
    arquivo_corrompido = pasta / "auditoria-corrompida.jsonl"
    arquivo_corrompido.write_text(
        '{"sequencia":1,"hash":"incompleto"}\\n{"sequencia":2,',
        encoding="utf-8",
    )
    recuperada = AuditoriaAtuacaoNixOS(arquivo=arquivo_corrompido)
    assert recuperada.contexto()["sequencia"] == 0
    assert recuperada.contexto()["arquivo_recuperado"] is not None
    nova = recuperada.registrar(
        evento="apos_recuperacao",
        dados={"recuperado": True},
    )
    assert nova["sequencia"] == 1
    assert recuperada.validar()["valido"] is True

    print("TESTE_M5_18_AUDITORIA_ATUACAO_OK")
    print("EVENTOS: ENCADEADOS")
    print("INTEGRIDADE: VALIDADA")
    print("ROLLBACK: AUDITADO")
    print("AUTORIZACAO: REGISTRADA")
    print("MUTACAO: CONFINADA_AO_SANDBOX")


if __name__ == "__main__":
    main()
