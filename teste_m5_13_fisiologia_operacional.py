#!/usr/bin/env python3
"""Validação M5.13 — heartbeat e fisiologia operacional."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_delta import RegistroDeltaNixOS
from nixal_fisiologia_operacional import (
    FisiologiaOperacionalNixOS,
)


def corpo(temp: float) -> dict:
    return {
        "corpo": {
            "temperaturas_gerais": [
                {
                    "zona": "thermal_zone_0",
                    "tipo": "teste",
                    "temperatura_c": temp,
                }
            ],
            "gpu": [],
        }
    }


def main() -> None:
    pasta = Path(
        tempfile.mkdtemp(prefix="nyxal_m5_13_")
    )

    delta = RegistroDeltaNixOS(
        pasta / "delta.json"
    )

    fisio = FisiologiaOperacionalNixOS(
        intervalo_esperado_segundos=5.0,
        arquivo=pasta / "fisiologia.json",
        delta_nyxos=delta,
    )

    primeiro = fisio.registrar_ciclo(
        estado_corpo=corpo(50.0),
        timestamp=1000.0,
        sucesso=True,
    )
    assert primeiro["heartbeat"]["estado"] == "inicializando"
    assert primeiro["estado_fisiologico"] == "normal"
    assert primeiro["presenca_ativa"] is True

    segundo = fisio.registrar_ciclo(
        estado_corpo=corpo(50.0),
        timestamp=1005.0,
        sucesso=True,
    )
    assert segundo["heartbeat"]["estado"] == "regular"
    assert segundo["heartbeat"]["intervalo_segundos"] == 5.0

    atrasado = fisio.registrar_ciclo(
        estado_corpo=corpo(50.0),
        timestamp=1012.5,
        sucesso=True,
    )
    assert atrasado["heartbeat"]["estado"] == "atrasado"

    # Três amostras muito quentes geram febre sem qualquer ação física.
    fisio.registrar_ciclo(
        estado_corpo=corpo(81.0),
        timestamp=1017.5,
        sucesso=True,
    )
    fisio.registrar_ciclo(
        estado_corpo=corpo(82.0),
        timestamp=1022.5,
        sucesso=True,
    )
    febre = fisio.registrar_ciclo(
        estado_corpo=corpo(83.0),
        timestamp=1027.5,
        sucesso=True,
    )
    assert febre["estado_fisiologico"] == "febre"
    assert febre["termico"]["estado_termico"] == "muito_quente"

    # Três amostras normais encerram a recuperação e retornam ao normal.
    recuperacao_1 = fisio.registrar_ciclo(
        estado_corpo=corpo(55.0),
        timestamp=1032.5,
        sucesso=True,
    )
    assert recuperacao_1["estado_fisiologico"] == "recuperacao"

    recuperacao_2 = fisio.registrar_ciclo(
        estado_corpo=corpo(54.0),
        timestamp=1037.5,
        sucesso=True,
    )
    assert recuperacao_2["estado_fisiologico"] == "recuperacao"

    normal = fisio.registrar_ciclo(
        estado_corpo=corpo(53.0),
        timestamp=1042.5,
        sucesso=True,
    )
    assert normal["estado_fisiologico"] == "normal"

    # Reinício recupera o histórico limitado.
    fisio_reiniciada = FisiologiaOperacionalNixOS(
        intervalo_esperado_segundos=5.0,
        arquivo=pasta / "fisiologia.json",
    )
    contexto = fisio_reiniciada.contexto()
    assert contexto["historico_limitado"] is True
    assert contexto["historico_ciclos"] == 9
    assert contexto["estado_fisiologico"] == "normal"

    # Limite de histórico é rígido.
    for i in range(30):
        fisio_reiniciada.registrar_ciclo(
            estado_corpo=corpo(50.0),
            timestamp=2000.0 + i,
            sucesso=True,
        )
    assert fisio_reiniciada.contexto()["historico_ciclos"] == 20

    # Invariantes permanecem fora de atuação/evolução.
    contexto = fisio_reiniciada.contexto()
    assert contexto["autorizacao_explicita"] is False
    assert contexto["integracao_executada"] is False
    assert contexto["arquitetura_modificada"] is False
    assert contexto["conhecimento_permanente"] is False

    # Uma mudança de estado fisiológico produziu Delta, sem autorizar integração.
    assert delta.quantidade() >= 2

    print("TESTE_M5_13_FISIOLOGIA_OPERACIONAL_OK")
    print("HEARTBEAT: ATIVO")
    print("FEBRE: DERIVADA_DE_EVIDENCIA_PERSISTENTE")
    print("RECUPERACAO: ATIVA")
    print("HISTORICO_MAXIMO: 20")
    print("ATUACAO_FISICA: DESABILITADA")
    print("DELTA_TRANSICOES: REGISTRADO")


if __name__ == "__main__":
    main()
