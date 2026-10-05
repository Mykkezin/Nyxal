#!/usr/bin/env python3
"""Validação M5.19 — integração residente do sandbox + auditoria."""

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
            "valor": {"etapas": []},
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
    pasta = Path(tempfile.mkdtemp(prefix="nyxos_m5_19_"))
    auditoria = AuditoriaAtuacaoNixOS(
        arquivo=pasta / "auditoria.jsonl"
    )
    sandbox = AdaptadorSandboxFisicoNixOS(
        diretorio_sandbox=pasta / "sandbox",
        habilitada=False,
        auditoria=auditoria,
    )
    gateway = GatewayAtuacaoNixOS(
        arquivo=pasta / "gateway.json",
        executor=sandbox,
        auditoria=auditoria,
        execucao_fisica_habilitada=False,
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

    resultados = residente.executar(max_ciclos=1)
    assert len(resultados) == 1
    resultado = resultados[0]

    gateway_resultado = resultado["gateway_atuacao"]
    assert gateway_resultado["estado"] == "preparada"
    assert gateway_resultado["executada"] is False
    assert gateway_resultado["execucao_fisica_habilitada"] is False
    assert gateway_resultado["executor_disponivel"] is True

    contexto = residente.contexto()
    assert contexto["gateway_atuacao_habilitado"] is True
    assert contexto["execucao_fisica_habilitada"] is False

    assert (pasta / "gateway.json").is_file()
    linhas = [
        json.loads(linha)
        for linha in (pasta / "auditoria.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        if linha.strip()
    ]
    assert [linha["evento"] for linha in linhas] == [
        "operacao_preparada"
    ]
    assert auditoria.validar()["valido"] is True

    assert list((pasta / "sandbox").glob("estado-*.json")) == []

    print("TESTE_M5_19_INTEGRACAO_RESIDENTE_OK")
    print("RESIDENTE: INTEGRADO")
    print("SANDBOX: DISPONIVEL_E_DESABILITADO")
    print("GATEWAY: PREPARADO_SEM_EXECUCAO")
    print("AUDITORIA: ATIVA")
    print("MUTACAO_HOST: DESABILITADA")


if __name__ == "__main__":
    main()
