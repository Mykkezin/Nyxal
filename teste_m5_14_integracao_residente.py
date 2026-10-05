#!/usr/bin/env python3
"""Validação da integração M5.14 com o ciclo residente."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_ciclo_residente import CicloResidenteNixOS
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
            "estado_fisiologico": "febre",
            "heartbeat": {"estado": "regular"},
            "termico": {"estado_termico": "muito_quente"},
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


def main() -> None:
    pasta = Path(tempfile.mkdtemp(prefix="nyxos_m5_14_integracao_"))
    plano = PlanoCentralControleNixOS(
        arquivo=pasta / "plano.json"
    )
    residente = CicloResidenteNixOS(
        RuntimeFalso(),
        fisiologia_operacional=FisiologiaFalsa(),
        plano_central_controle=plano,
        intervalo_segundos=0,
    )

    resultados = residente.executar(max_ciclos=1)

    assert len(resultados) == 1
    resultado = resultados[0]
    assert resultado["sucesso"] is True
    assert resultado["fisiologia"]["estado_fisiologico"] == "febre"

    plano_resultado = resultado["plano_central_controle"]
    assert plano_resultado["decisao"]["acao_planejada"] == "reduzir_carga"
    assert len(plano_resultado["plano_id"]) == 64
    assert plano_resultado["execucao"]["executada"] is False
    assert plano_resultado["execucao"]["gateway_atuacao"] is False
    assert plano_resultado["governanca"]["autorizacao_explicita"] is False
    assert plano_resultado["governanca"]["integracao_executada"] is False
    assert plano_resultado["governanca"]["arquitetura_modificada"] is False
    assert (pasta / "plano.json").is_file()

    contexto = residente.contexto()
    assert contexto["plano_central_controle_habilitado"] is True

    print("TESTE_M5_14_INTEGRACAO_RESIDENTE_OK")
    print("FISIOLOGIA: CONSUMIDA_PELO_PLANO")
    print("DECISAO: INTEGRADA_AO_CICLO")
    print("EXECUCAO_FISICA: DESABILITADA")
    print("GATEWAY_ATUACAO: DESABILITADO")
    print("GOVERNANCA: PRESERVADA")


if __name__ == "__main__":
    main()
