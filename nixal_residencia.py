#!/usr/bin/env python3
"""NYXOS — observação da residência systemd para a camada visual.

Somente leitura: descreve unidades conhecidas do NyxOS sem executar ações.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any


class ResidenciaNyxOS:
    FONTE = "residencia_nyxos"
    VERSAO = "1.0.0"
    UNIDADES = (
        "nyxos.target",
        "nyxal-api.service",
        "nyxos-residente.service",
        "nyxos-interface.service",
        "nyxos-display.service",
    )

    def __init__(self) -> None:
        self.systemctl = shutil.which("systemctl")

    def _show(self, unidade: str) -> dict[str, Any]:
        if not self.systemctl:
            return {
                "nome": unidade,
                "descricao": "",
                "status": "indisponivel",
                "subState": "systemctl_nao_instalado",
                "pid": None,
                "enabled": False,
                "memoryUsageMb": None,
                "cpuUsagePct": None,
            }

        proc = subprocess.run(
            [
                self.systemctl,
                "--user",
                "show",
                unidade,
                "--no-pager",
                "--property=Description,ActiveState,SubState,MainPID,UnitFileState,MemoryCurrent,CPUUsageNSec",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        valores: dict[str, str] = {}
        for linha in proc.stdout.splitlines():
            if "=" in linha:
                chave, valor = linha.split("=", 1)
                valores[chave] = valor

        if proc.returncode != 0:
            return {
                "nome": unidade,
                "descricao": valores.get("Description", ""),
                "status": "indisponivel",
                "subState": valores.get("SubState") or "nao_encontrado",
                "pid": None,
                "enabled": valores.get("UnitFileState") == "enabled",
                "memoryUsageMb": None,
                "cpuUsagePct": None,
            }

        pid_raw = valores.get("MainPID", "")
        memory_raw = valores.get("MemoryCurrent", "")

        try:
            pid = int(pid_raw) if pid_raw else None
        except ValueError:
            pid = None

        try:
            memory = int(memory_raw) / (1024 * 1024) if memory_raw.isdigit() else None
        except (OverflowError, ValueError):
            memory = None

        return {
            "nome": unidade,
            "descricao": valores.get("Description", ""),
            "status": valores.get("ActiveState", "unknown"),
            "subState": valores.get("SubState", "unknown"),
            "pid": pid if pid and pid > 0 else None,
            "enabled": valores.get("UnitFileState") == "enabled",
            "memoryUsageMb": round(memory, 1) if memory is not None else None,
            "cpuUsagePct": None,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "sucesso": bool(self.systemctl),
            "estado": "residencia_observada" if self.systemctl else "systemctl_indisponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "modo": "somente_leitura",
            "unidades": [self._show(unidade) for unidade in self.UNIDADES],
        }


__all__ = ["ResidenciaNyxOS"]
