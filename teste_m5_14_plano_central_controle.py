#!/usr/bin/env python3
"""Validação M5.14 — plano central de controle."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_plano_central_controle import PlanoCentralControleNixOS


def fisiologia(estado: str) -> dict:
    return {
        "estado_fisiologico": estado,
        "heartbeat": {"estado": "regular"},
        "termico": {"estado_termico": "muito_quente"},
    }


def main() -> None:
    pasta = Path(tempfile.mkdtemp(prefix="nyxal_m5_14_"))
    plano = PlanoCentralControleNixOS(
        arquivo=pasta / "plano.json"
    )

    base = plano.gerar_plano(
        ciclo={"sucesso": True},
        fisiologia=fisiologia("normal"),
    )
    assert base["decisao"]["acao_planejada"] == "aguardar"
    assert base["execucao"]["executada"] is False

    estresse = plano.gerar_plano(
        ciclo={"sucesso": True},
        fisiologia=fisiologia("estresse_termico"),
    )
    assert estresse["decisao"]["acao_planejada"] == "reduzir_carga"

    febre = plano.gerar_plano(
        ciclo={"sucesso": True},
        fisiologia=fisiologia("febre"),
    )
    assert febre["decisao"]["acao_planejada"] == "reduzir_carga"

    recuperacao = plano.gerar_plano(
        ciclo={"sucesso": True},
        fisiologia=fisiologia("recuperacao"),
    )
    assert recuperacao["decisao"]["acao_planejada"] == "aguardar"

    falha = plano.gerar_plano(
        ciclo={"sucesso": False},
        fisiologia=fisiologia("normal"),
    )
    assert falha["decisao"]["acao_planejada"] == "preservar_estado"

    assert len(base["plano_id"]) == 64
    assert base["governanca"]["autorizacao_explicita"] is False
    assert base["governanca"]["integracao_executada"] is False
    assert base["governanca"]["stable_modificada"] is False
    assert base["governanca"]["arquitetura_modificada"] is False

    contexto = plano.contexto()
    assert contexto["execucao_fisica_habilitada"] is False
    assert contexto["gateway_atuacao_habilitado"] is False
    assert (pasta / "plano.json").is_file()

    print("TESTE_M5_14_PLANO_CENTRAL_CONTROLE_OK")
    print("DECISAO: DETERMINISTICA")
    print("EXECUCAO_FISICA: DESABILITADA")
    print("GATEWAY_ATUACAO: DESABILITADO")
    print("GOVERNANCA: PRESERVADA")


if __name__ == "__main__":
    main()
