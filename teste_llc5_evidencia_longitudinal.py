#!/usr/bin/env python3
"""Teste determinístico do LLC.5."""
from __future__ import annotations

from nixal_evidencia_ambiental_llc import EvidenciaAmbientalLLC
from nixal_evidencia_longitudinal_llc import EvidenciaLongitudinalLLC


def obs(valor: float, timestamp: str, sid: str) -> dict:
    return {
        "snapshot_id": sid,
        "timestamp": timestamp,
        "nome": "cpu_uso",
        "caminho": "recursos.cpu.uso_percentual",
        "unidade": "%",
        "valor": valor,
        "direcao_melhor": "menor",
        "fonte": "habitat_nyxos",
        "evidencia_ambiental_observacional": True,
        "causalidade_ambiental_comprovada": False,
    }


def transicao(i: int, ia: float, id_: float, ca: float, cd: float) -> dict:
    return {
        "transicao_id": f"transicao-{i}",
        "ciclo_id": f"ciclo-{i}",
        "acao": "registrar_estado_corpo",
        "decisao": {
            "acao": "registrar_estado_corpo",
            "llc": {"influencia_decisoria_comprovada": True},
        },
        "acao_resultado": {
            "sucesso": True, "acao": "registrar_estado_corpo", "executada": True
        },
        "resultado_observado": {"sucesso": True},
        "intervencao_antes": obs(ia, f"2026-10-05T10:0{i}:00+00:00", f"{i}-ia"),
        "intervencao_depois": obs(id_, f"2026-10-05T10:1{i}:00+00:00", f"{i}-id"),
        "controle_antes": obs(ca, f"2026-10-05T10:2{i}:00+00:00", f"{i}-ca"),
        "controle_depois": obs(cd, f"2026-10-05T10:3{i}:00+00:00", f"{i}-cd"),
    }


def metrica() -> dict:
    return {
        "nome": "cpu_uso",
        "caminho": "recursos.cpu.uso_percentual",
        "unidade": "%",
        "fonte": "habitat_nyxos",
        "direcao_melhor": "menor",
    }


def main() -> int:
    amostras = [
        transicao(1, 40, 30, 35, 33),
        transicao(2, 42, 31, 37, 35),
        transicao(3, 38, 27, 34, 32),
    ]
    ok = EvidenciaLongitudinalLLC.avaliar(
        metrica=metrica(), transicoes=amostras,
        acao_esperada="registrar_estado_corpo",
    )
    assert ok["estado"] == "evidencia_causal_longitudinal"
    assert ok["causalidade_ambiental_comprovada"] is True
    assert ok["repeticoes"] == 3
    assert ok["ciclos_distintos"] == 3
    assert ok["estabilidade_direcional"] is True
    assert ok["efeito_medio_contrafactual"] == (-26.0 / 3.0)
    assert ok["erros"] == []

    menos = EvidenciaLongitudinalLLC.avaliar(
        metrica=metrica(), transicoes=amostras[:2],
        acao_esperada="registrar_estado_corpo",
    )
    assert menos["causalidade_ambiental_comprovada"] is False
    assert "repeticoes_insuficientes" in menos["erros"]

    sem_influencia = list(amostras)
    sem_influencia[0] = {**sem_influencia[0], "decisao": {
        "acao": "registrar_estado_corpo",
        "llc": {"influencia_decisoria_comprovada": False},
    }}
    sem = EvidenciaLongitudinalLLC.avaliar(
        metrica=metrica(), transicoes=sem_influencia,
        acao_esperada="registrar_estado_corpo",
    )
    assert sem["causalidade_ambiental_comprovada"] is False
    assert "influencia_decisoria_nao_comprovada" in sem["erros"]

    contexto = EvidenciaLongitudinalLLC.contexto()
    assert contexto["versao"] == "LLC.5.0.0"
    assert contexto["causalidade_ambiental"] is False

    origem = open("nixal_evidencia_longitudinal_llc.py", encoding="utf-8").read()
    assert "subprocess" not in origem
    assert "os.system" not in origem
    assert "Popen" not in origem
    assert "exec(" not in origem
    assert "git merge" not in origem

    # Garante compatibilidade com o formato de observação do LLC.4.
    assert "recursos.cpu.uso_percentual" in EvidenciaAmbientalLLC.METRICAS_NUMERICAS
    print("TESTE_LLC5_EVIDENCIA_LONGITUDINAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
