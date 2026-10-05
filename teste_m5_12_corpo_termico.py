#!/usr/bin/env python3
"""Validação M5.12 — corpo térmico e ventilação supervisionada."""

from __future__ import annotations

from nixal_corpo_termico import (
    avaliar_corpo_termico,
    comparar_tendencia,
    classificar_estado_histerese,
    planejar_ventilacao_supervisionada,
)


def estado(temperaturas: list[float]) -> dict:
    return {
        "corpo": {
            "temperaturas_gerais": [
                {
                    "zona": f"thermal_zone_{i}",
                    "tipo": "teste",
                    "temperatura_c": valor,
                }
                for i, valor in enumerate(temperaturas)
            ],
            "gpu": [],
        }
    }


def main() -> None:
    assert classificar_estado_histerese(39.9) == "fria"
    assert classificar_estado_histerese(40.0) == "normal"
    assert classificar_estado_histerese(64.9) == "normal"
    assert classificar_estado_histerese(65.0) == "quente"
    assert classificar_estado_histerese(79.9) == "quente"
    assert classificar_estado_histerese(80.0) == "muito_quente"

    # Histerese evita alternância imediata quando a temperatura cruza
    # um limite em torno do estado anterior.
    assert classificar_estado_histerese(63.0, "quente") == "quente"
    assert classificar_estado_histerese(61.9, "quente") == "normal"
    assert classificar_estado_histerese(78.0, "muito_quente") == "muito_quente"
    assert classificar_estado_histerese(76.9, "muito_quente") == "quente"

    assert comparar_tendencia(70.0, 71.2)["estado"] == "subindo"
    assert comparar_tendencia(71.2, 70.0)["estado"] == "descendo"
    assert comparar_tendencia(70.0, 70.5)["estado"] == "estavel"

    observado = avaliar_corpo_termico(
        estado([58.0, 72.5]),
    )
    assert observado["sucesso"] is True
    assert observado["temperatura_maxima_c"] == 72.5
    assert observado["estado_termico"] == "quente"
    assert len(observado["sensores"]) == 2
    assert observado["atuacao_ventilacao"]["permitida"] is False

    frio = avaliar_corpo_termico(
        estado([35.0, 38.0]),
    )
    plano_frio = planejar_ventilacao_supervisionada(frio)
    assert plano_frio["acao"] == "manter_resfriamento"
    assert plano_frio["atuacao_automatica"] is False
    assert plano_frio["autorizacao_fisica"] is False

    quente = avaliar_corpo_termico(
        estado([81.0]),
    )
    plano_quente = planejar_ventilacao_supervisionada(quente)
    assert plano_quente["acao"] == "maximizar_resfriamento_supervisionado"
    assert plano_quente["atuacao_automatica"] is False

    indisponivel = avaliar_corpo_termico(
        {"corpo": {"temperaturas_gerais": [], "gpu": []}}
    )
    assert indisponivel["sucesso"] is False
    assert indisponivel["atuacao_ventilacao"]["permitida"] is False

    print("TESTE_M5_12_CORPO_TERMICO_OK")
    print("SENSORES: OBSERVADOS")
    print("HISTERESE: ATIVA")
    print("TENDENCIA: ATIVA")
    print("VENTILACAO_AUTOMATICA: DESABILITADA")
    print("FALLBACK_SEM_SENSOR: NAO_ATUAR")


if __name__ == "__main__":
    main()
