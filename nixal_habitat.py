#!/usr/bin/env python3
"""
NIXAL — HABITAT M5.1

Ponte somente leitura entre o NyxOS e o sistema hospedeiro.

A camada usa o corpo computacional já existente e devolve somente os
dados necessários para observabilidade do habitat.
"""

from __future__ import annotations

import platform
import time
from typing import Any

from corpo_nixal import perceber_corpo


class HabitatNixOS:
    """Adaptador de observabilidade do host para o habitat NyxOS."""

    FONTE = "habitat_nyxos"
    VERSAO = "5.1.0"
    INTERVALO_CPU_SEGUNDOS = 0.12

    def snapshot(self) -> dict[str, Any]:
        primeiro, cpu_anterior = perceber_corpo()

        time.sleep(self.INTERVALO_CPU_SEGUNDOS)

        atual, _ = perceber_corpo(cpu_anterior)

        corpo = atual.get("corpo", {}) if isinstance(atual, dict) else {}

        return {
            "sucesso": True,
            "estado": "habitat_observado",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "host": {
                "sistema": platform.system() or "desconhecido",
                "release": platform.release() or None,
                "arquitetura": platform.machine() or None,
                "modo": "somente_leitura",
            },
            "recursos": self._sanitizar_recursos(corpo),
            "timestamp": (
                atual.get("percepcao", {}).get("timestamp")
                if isinstance(atual, dict)
                else None
            ),
            "persistente": False,
            "arquitetura_modificada": False,
        }

    @staticmethod
    def _sanitizar_recursos(corpo: dict[str, Any]) -> dict[str, Any]:
        cpu = corpo.get("cpu") or {}
        memoria = corpo.get("memoria") or {}
        armazenamento = corpo.get("armazenamento") or {}
        gpus = corpo.get("gpu") or []

        gpu_resumida: list[dict[str, Any]] = []

        if isinstance(gpus, list):
            for gpu in gpus:
                if not isinstance(gpu, dict):
                    continue

                temperaturas = gpu.get("temperaturas") or []
                temperatura = None

                if isinstance(temperaturas, list) and temperaturas:
                    primeira = temperaturas[0]
                    if isinstance(primeira, dict):
                        temperatura = primeira.get("temperatura_c")

                gpu_resumida.append(
                    {
                        "uso_percentual": gpu.get("uso_percentual"),
                        "estado_uso": gpu.get("estado_uso"),
                        "temperatura_c": temperatura,
                    }
                )

        return {
            "cpu": {
                "uso_percentual": cpu.get("uso_percentual"),
                "estado": cpu.get("estado"),
                "calibrada": cpu.get("calibrada"),
            },
            "memoria": {
                "uso_percentual": memoria.get("uso_percentual"),
                "estado": memoria.get("estado"),
                "usado_gb": memoria.get("usado_gb"),
                "total_gb": memoria.get("total_gb"),
            },
            "armazenamento": {
                "ponto": armazenamento.get("ponto"),
                "uso_percentual": armazenamento.get("uso_percentual"),
                "estado": armazenamento.get("estado"),
            },
            "processos": corpo.get("processos"),
            "uptime_segundos": corpo.get("uptime_segundos"),
            "gpu": gpu_resumida,
        }


__all__ = ["HabitatNixOS"]
