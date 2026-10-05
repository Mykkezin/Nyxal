#!/usr/bin/env python3
"""Teste deterministico do LLC.6."""
from __future__ import annotations

import copy

from nixal_evidencia_ambiental_llc import EvidenciaAmbientalLLC
from nixal_proveniencia_evidencia_llc import ProvenienciaEvidenciaLLC


def snapshot() -> dict:
    habitat = {
        "host": {
            "sistema": "Linux",
            "release": "6.8",
            "arquitetura": "x86_64",
        },
        "recursos": {
            "cpu": {"uso_percentual": 40.0},
            "memoria": {"uso_percentual": 50.0},
        },
        "timestamp": "2026-10-05T11:00:00+00:00",
    }
    corpo_minimo = {
        "host": {
            **habitat["host"],
            "modo": "somente_leitura",
        },
        "recursos": copy.deepcopy(habitat["recursos"]),
        "timestamp": habitat["timestamp"],
    }
    habitat["snapshot_id"] = EvidenciaAmbientalLLC._hash(corpo_minimo)
    habitat["modo"] = "somente_leitura"
    habitat["evidencia_ambiental_observacional"] = True
    habitat["causalidade_ambiental_comprovada"] = False
    return habitat


def metrica() -> dict:
    return {
        "nome": "cpu_uso",
        "caminho": "recursos.cpu.uso_percentual",
        "unidade": "%",
        "fonte": "habitat_nyxos",
        "direcao_melhor": "menor",
    }


def evidencia_valida() -> dict:
    snap = snapshot()
    resultado = EvidenciaAmbientalLLC.observar_metrica(
        snapshot=snap,
        caminho="recursos.cpu.uso_percentual",
        nome="cpu_uso",
        unidade="%",
        direcao_melhor="menor",
        fonte="habitat_nyxos",
    )
    assert resultado["sucesso"] is True
    return {
        "origem": resultado["origem"],
        "versao": resultado["versao"],
        "modo": resultado["observacao"]["modo"],
        "snapshot": snap,
        "observacao": resultado["observacao"],
    }


def validar(evidencia: dict) -> dict:
    return ProvenienciaEvidenciaLLC.validar(
        evidencia=evidencia,
        metrica=metrica(),
        transicao_id="transicao-1",
        ciclo_id="ciclo-1",
    )


def main() -> int:
    ok = validar(evidencia_valida())
    assert ok["estado"] == "proveniencia_evidencia_valida"
    assert ok["proveniencia_evidencia_valida"] is True
    assert ok["erros"] == []
    assert ok["proveniencia"]["snapshot_id"]
    assert ok["proveniencia"]["observacao_id"]

    adulterado_id = evidencia_valida()
    adulterado_id["observacao"]["id"] = "adulterado"
    resultado = validar(adulterado_id)
    assert resultado["proveniencia_evidencia_valida"] is False
    assert "observacao_id_integro_invalido" in resultado["erros"]

    adulterado_snapshot = evidencia_valida()
    adulterado_snapshot["snapshot"]["recursos"]["cpu"]["uso_percentual"] = 99.0
    resultado = validar(adulterado_snapshot)
    assert resultado["proveniencia_evidencia_valida"] is False
    assert "snapshot_id_integro_invalido" in resultado["erros"]

    origem = evidencia_valida()
    origem["origem"] = "outra_fonte"
    resultado = validar(origem)
    assert resultado["proveniencia_evidencia_valida"] is False
    assert "origem_llc4_invalida" in resultado["erros"]

    modo = evidencia_valida()
    modo["modo"] = "escrita"
    resultado = validar(modo)
    assert resultado["proveniencia_evidencia_valida"] is False
    assert "modo_nao_somente_leitura" in resultado["erros"]

    timestamp = evidencia_valida()
    timestamp["observacao"]["timestamp"] = "nao-e-um-timestamp"
    resultado = validar(timestamp)
    assert resultado["proveniencia_evidencia_valida"] is False
    assert "observacao_timestamp_invalido" in resultado["erros"]

    metrica_divergente = evidencia_valida()
    resultado = ProvenienciaEvidenciaLLC.validar(
        evidencia=metrica_divergente,
        metrica={**metrica(), "unidade": "ms"},
        transicao_id="transicao-1",
        ciclo_id="ciclo-1",
    )
    assert resultado["proveniencia_evidencia_valida"] is False
    assert "metrica_unidade_divergente" in resultado["erros"]

    cadeia = evidencia_valida()
    resultado = validar(cadeia)
    assert resultado["proveniencia"]["transicao_id"] == "transicao-1"
    assert resultado["proveniencia"]["ciclo_id"] == "ciclo-1"

    causal = evidencia_valida()
    causal["observacao"]["causalidade_ambiental_comprovada"] = True
    resultado = validar(causal)
    assert resultado["proveniencia_evidencia_valida"] is False
    assert "observacao_com_causalidade_preexistente" in resultado["erros"]

    origem_codigo = open("nixal_proveniencia_evidencia_llc.py", encoding="utf-8").read()
    assert "subprocess" not in origem_codigo
    assert "os.system" not in origem_codigo
    assert "Popen" not in origem_codigo
    assert "git merge" not in origem_codigo
    assert "exec(" not in origem_codigo

    print("TESTE_LLC6_PROVENIENCIA_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
