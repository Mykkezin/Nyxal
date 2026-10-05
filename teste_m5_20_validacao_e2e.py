#!/usr/bin/env python3
"""M5.20 — validação E2E da cadeia operacional governada."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_adaptador_sandbox_fisico import AdaptadorSandboxFisicoNixOS
from nixal_auditoria_atuacao import AuditoriaAtuacaoNixOS
from nixal_ciclo_residente import CicloResidenteNixOS
from nixal_gateway_atuacao import GatewayAtuacaoNixOS
from nixal_plano_central_controle import PlanoCentralControleNixOS


class RuntimeFalso:
    def executar_ciclo(self) -> dict:
        return {
            "sucesso": True,
            "estado": "ciclo_concluido",
            "valor": {
                "etapas": [
                    {
                        "etapa": "percepcao",
                        "estado": {
                            "cpu": {"uso_percentual": 10.0},
                            "memoria": {"uso_percentual": 20.0},
                        },
                    }
                ]
            },
        }


class FisiologiaFalsa:
    FONTE = "fisiologia_falsa"

    def registrar_ciclo(self, *, estado_corpo, sucesso):
        return {
            "sucesso": True,
            "estado_fisiologico": "normal",
            "heartbeat": {"estado": "regular"},
            "termico": {"estado_termico": "normal"},
        }


def main() -> None:
    pasta = Path(tempfile.mkdtemp(prefix="nyxos_m5_20_"))
    auditoria = AuditoriaAtuacaoNixOS(
        arquivo=pasta / "auditoria.jsonl"
    )
    sandbox = AdaptadorSandboxFisicoNixOS(
        diretorio_sandbox=pasta / "sandbox",
        habilitada=True,
        auditoria=auditoria,
    )
    gateway = GatewayAtuacaoNixOS(
        arquivo=pasta / "gateway.json",
        executor=sandbox,
        auditoria=auditoria,
        execucao_fisica_habilitada=True,
    )
    plano = PlanoCentralControleNixOS(
        arquivo=pasta / "plano.json"
    )

    residente = CicloResidenteNixOS(
        RuntimeFalso(),
        fisiologia_operacional=FisiologiaFalsa(),
        plano_central_controle=plano,
        gateway_atuacao=gateway,
        intervalo_segundos=0,
    )

    # A residência prepara a operação, mas nunca concede autorização.
    resultados = residente.executar(max_ciclos=1)
    assert len(resultados) == 1
    resultado = resultados[0]
    operacao = resultado["gateway_atuacao"]
    assert operacao["estado"] == "preparada"
    assert operacao["executada"] is False

    # A primeira tentativa deve ser bloqueada sem autorização.
    bloqueado = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=False,
    )
    assert bloqueado["estado"] == "bloqueado"
    assert bloqueado["motivo"] == "autorizacao_explicita_ausente"

    # Somente a autorização explícita libera a mutação confinada.
    executado = gateway.executar(
        operacao=operacao,
        autorizacao_explicita=True,
    )
    assert executado["estado"] == "executado"
    assert executado["executada"] is True
    rollback_token = executado["resultado_executor"]["resultado"]["rollback_token"]

    # A mutação ocorre apenas no sandbox e deve ser reversível.
    arquivo_sandbox = Path(
        executado["resultado_executor"]["resultado"]["arquivo"]
    )
    assert arquivo_sandbox.is_file()

    rollback = sandbox.rollback(rollback_token)
    assert rollback["sucesso"] is True
    assert not arquivo_sandbox.exists()

    # A cadeia de auditoria deve permanecer íntegra.
    validacao = auditoria.validar()
    assert validacao["valido"] is True
    assert validacao["registros"] == 5

    eventos = [
        json.loads(linha)["evento"]
        for linha in (pasta / "auditoria.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if linha.strip()
    ]
    assert eventos == [
        "operacao_preparada",
        "operacao_bloqueada",
        "atuacao_sandbox_executada",
        "operacao_executada",
        "rollback_executado",
    ]

    # O ciclo residente nunca marca autorização/integracão como concedidas.
    contexto = residente.contexto()
    assert contexto["autorizacao_explicita"] is False
    assert contexto["integracao_executada"] is False
    assert contexto["arquitetura_modificada"] is False

    print("TESTE_M5_20_E2E_OK")
    print("CADEIA: PERCEPCAO_FISIOLOGIA_PLANO_GATEWAY")
    print("AUTORIZACAO: EXPLICITA")
    print("MUTACAO: CONFINADA_AO_SANDBOX")
    print("ROLLBACK: VALIDADO")
    print("AUDITORIA: INTEGRIDADE_VALIDADA")
    print("RESIDENTE: NAO_AUTORIZA_AUTOMATICAMENTE")


if __name__ == "__main__":
    main()
