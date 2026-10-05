#!/usr/bin/env python3
"""Teste deterministico do LLC.4 — evidencia ambiental real/observacional."""

from __future__ import annotations

from nixal_habitat import HabitatNixOS
from nixal_evidencia_ambiental_llc import EvidenciaAmbientalLLC


def snapshot(cpu, memoria, processos, timestamp):
    return {
        "sucesso": True,
        "estado": "habitat_observado",
        "origem": HabitatNixOS.FONTE,
        "versao": HabitatNixOS.VERSAO,
        "host": {
            "sistema": "Linux",
            "release": "teste",
            "arquitetura": "x86_64",
            "modo": "somente_leitura",
        },
        "recursos": {
            "cpu": {"uso_percentual": cpu, "estado": "normal", "calibrada": True},
            "memoria": {"uso_percentual": memoria, "estado": "normal"},
            "processos": processos,
            "uptime_segundos": 1000.0,
        },
        "timestamp": timestamp,
    }


def main() -> int:
    s1 = snapshot(40.0, 50.0, 200, "2026-10-05T10:00:00+00:00")
    s2 = snapshot(30.0, 45.0, 180, "2026-10-05T10:01:00+00:00")

    coletor = EvidenciaAmbientalLLC(
        observador=lambda: s1,
    )

    real = coletor.capturar_snapshot()
    assert real["sucesso"] is True
    assert real["modo"] == "somente_leitura"
    assert real["evidencia_ambiental_observacional"] is True
    assert real["causalidade_ambiental_comprovada"] is False
    assert real["stable_modificada"] is False

    real2 = EvidenciaAmbientalLLC(
        observador=lambda: s2,
    ).capturar_snapshot()

    antes = EvidenciaAmbientalLLC.observar_metrica(
        snapshot=real,
        caminho="recursos.cpu.uso_percentual",
        nome="cpu_uso",
        unidade="%",
        direcao_melhor="menor",
    )
    depois = EvidenciaAmbientalLLC.observar_metrica(
        snapshot=real2,
        caminho="cpu.uso_percentual",
        nome="cpu_uso",
        unidade="%",
        direcao_melhor="menor",
    )
    assert antes["sucesso"] is True
    assert depois["sucesso"] is True

    comparacao = EvidenciaAmbientalLLC.comparar_observacoes(
        antes=antes["observacao"],
        depois=depois["observacao"],
    )
    assert comparacao["sucesso"] is True
    assert comparacao["antes"] == 40.0
    assert comparacao["depois"] == 30.0
    assert comparacao["delta_observado"] == -10.0
    assert comparacao["evidencia_ambiental_observacional"] is True
    assert comparacao["causalidade_ambiental_comprovada"] is False

    nao_declarada = EvidenciaAmbientalLLC.observar_metrica(
        snapshot=real,
        caminho="cpu.temperatura_fake",
        nome="temperatura_fake",
        unidade="celsius",
        direcao_melhor="menor",
    )
    assert nao_declarada["sucesso"] is False
    assert nao_declarada["estado"] == "metrica_nao_declarada"

    contexto = EvidenciaAmbientalLLC.contexto()
    assert contexto["versao"] == "LLC.4.0.0"
    assert contexto["evidencia_ambiental_observacional"] is True
    assert contexto["causalidade_ambiental"] is False
    assert contexto["coleta_automatica"] is False

    habitacional = EvidenciaAmbientalLLC()
    snapshot_real = habitacional.capturar_snapshot()
    assert snapshot_real["sucesso"] is True
    assert snapshot_real["modo"] == "somente_leitura"
    assert isinstance(snapshot_real.get("recursos"), dict)
    assert snapshot_real["arquitetura_modificada"] is False
    assert snapshot_real["causalidade_ambiental_comprovada"] is False

    print("TESTE_LLC4_EVIDENCIA_AMBIENTAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
