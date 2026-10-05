#!/usr/bin/env python3
"""NYXOS — M5.12 corpo térmico e ventilação supervisionada."""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Any

import corpo_nixal


BASE_DIR = Path(__file__).resolve().parent
HISTERese_C = 3.0
LIMIAR_QUENTE_C = 65.0
LIMIAR_MUITO_QUENTE_C = 80.0


def _temperaturas(estado: dict[str, Any]) -> list[dict[str, Any]]:
    corpo = estado.get("corpo", {}) if isinstance(estado, dict) else {}
    gerais = corpo.get("temperaturas_gerais", [])
    resultado: list[dict[str, Any]] = []

    if isinstance(gerais, list):
        for sensor in gerais:
            if isinstance(sensor, dict) and isinstance(
                sensor.get("temperatura_c"), (int, float)
            ):
                resultado.append({
                    "origem": "thermal_zone",
                    "identificador": sensor.get("zona") or sensor.get("tipo"),
                    "temperatura_c": float(sensor["temperatura_c"]),
                    "estado": sensor.get("estado")
                    or corpo_nixal.classificar_temperatura(float(sensor["temperatura_c"])),
                })

    gpus = corpo.get("gpu", [])
    if isinstance(gpus, list):
        for gpu in gpus:
            if not isinstance(gpu, dict):
                continue
            sensores = gpu.get("temperaturas", [])
            if not isinstance(sensores, list):
                continue
            for sensor in sensores:
                if isinstance(sensor, dict) and isinstance(
                    sensor.get("temperatura_c"), (int, float)
                ):
                    valor = float(sensor["temperatura_c"])
                    resultado.append({
                        "origem": "gpu",
                        "identificador": sensor.get("sensor") or sensor.get("rotulo"),
                        "temperatura_c": valor,
                        "estado": sensor.get("estado")
                        or corpo_nixal.classificar_temperatura(valor),
                    })

    return resultado


def classificar_estado_histerese(
    temperatura_c: float,
    estado_anterior: str | None = None,
) -> str:
    if not isinstance(temperatura_c, (int, float)):
        raise TypeError("temperatura_precisa_ser_numerica")

    valor = float(temperatura_c)
    anterior = estado_anterior

    if anterior == "muito_quente" and valor >= LIMIAR_MUITO_QUENTE_C - HISTERese_C:
        return "muito_quente"
    if anterior == "quente" and valor >= LIMIAR_QUENTE_C - HISTERese_C:
        return "quente"

    if valor >= LIMIAR_MUITO_QUENTE_C:
        return "muito_quente"
    if valor >= LIMIAR_QUENTE_C:
        return "quente"
    if valor < 40.0:
        return "fria"
    return "normal"


def avaliar_corpo_termico(
    estado: dict[str, Any],
    estado_termico_anterior: str | None = None,
) -> dict[str, Any]:
    temperaturas = _temperaturas(estado)

    if not temperaturas:
        return {
            "sucesso": False,
            "estado": "sensores_termicos_indisponiveis",
            "origem": "corpo_termico_nyxos",
            "temperatura_maxima_c": None,
            "estado_termico": "indisponivel",
            "tendencia": "indisponivel",
            "sensores": [],
            "atuacao_ventilacao": {
                "permitida": False,
                "modo": "supervisionado",
                "motivo": "Sem evidência térmica confiável.",
            },
        }

    maxima = max(s["temperatura_c"] for s in temperaturas)
    estado_termico = classificar_estado_histerese(
        maxima, estado_termico_anterior
    )

    return {
        "sucesso": True,
        "estado": "corpo_termico_observado",
        "origem": "corpo_termico_nyxos",
        "temperatura_maxima_c": round(maxima, 2),
        "estado_termico": estado_termico,
        "tendencia": "estavel",
        "sensores": temperaturas[:32],
        "atuacao_ventilacao": {
            "permitida": False,
            "modo": "supervisionado",
            "motivo": "M5.12 não habilita controle físico contínuo.",
        },
    }


def comparar_tendencia(
    temperatura_anterior_c: float | None,
    temperatura_atual_c: float | None,
) -> dict[str, Any]:
    if not isinstance(temperatura_anterior_c, (int, float)) or not isinstance(
        temperatura_atual_c, (int, float)
    ):
        return {"estado": "indisponivel", "delta_c": None}

    delta = round(float(temperatura_atual_c) - float(temperatura_anterior_c), 2)
    if delta >= 1.0:
        estado = "subindo"
    elif delta <= -1.0:
        estado = "descendo"
    else:
        estado = "estavel"
    return {"estado": estado, "delta_c": delta}


def descobrir_controles_ventilacao() -> list[dict[str, Any]]:
    controles: list[dict[str, Any]] = []

    for hwmon in sorted(glob.glob("/sys/class/hwmon/hwmon[0-9]*")):
        nome_path = Path(hwmon) / "name"
        try:
            nome = nome_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            nome = None

        for pwm_path in sorted(Path(hwmon).glob("pwm[0-9]*")):
            try:
                valor = int(pwm_path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                valor = None

            controles.append({
                "id": str(pwm_path),
                "hwmon": hwmon,
                "nome": nome,
                "pwm": pwm_path.name,
                "valor_atual": valor,
                "escrita_habilitada": False,
                "observavel": True,
            })

    return controles[:32]


def planejar_ventilacao_supervisionada(
    estado_termico: dict[str, Any],
    *,
    controles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(estado_termico, dict):
        raise TypeError("estado_termico_invalido")

    if not estado_termico.get("sucesso"):
        return {
            "sucesso": False,
            "estado": "plano_sem_atuacao",
            "acao": "nao_atuar",
            "motivo": "Estado térmico sem evidência suficiente.",
        }

    estado = estado_termico.get("estado_termico")
    temperatura = estado_termico.get("temperatura_maxima_c")
    controles = controles if isinstance(controles, list) else []

    if estado == "muito_quente":
        acao = "maximizar_resfriamento_supervisionado"
    elif estado == "quente":
        acao = "aumentar_resfriamento_supervisionado"
    else:
        acao = "manter_resfriamento"

    return {
        "sucesso": True,
        "estado": "plano_ventilacao_pronto",
        "acao": acao,
        "temperatura_maxima_c": temperatura,
        "controles_disponiveis": len(controles),
        "atuacao_automatica": False,
        "autorizacao_fisica": False,
        "fallback": "nao_atuar_sem_sensor_confiavel",
    }


__all__ = [
    "avaliar_corpo_termico",
    "comparar_tendencia",
    "classificar_estado_histerese",
    "descobrir_controles_ventilacao",
    "planejar_ventilacao_supervisionada",
]
