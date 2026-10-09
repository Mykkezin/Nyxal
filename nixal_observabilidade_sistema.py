#!/usr/bin/env python3
"""Observabilidade local de sistema em modo somente leitura.

Executa apenas consultas fixas e não aceita comandos fornecidos pelo usuário.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


class ObservabilidadeSistemaNixOS:
    FONTE = "observabilidade_sistema_nyxos"
    VERSAO = "1.0.0"

    def snapshot(self) -> dict[str, Any]:
        try:
            disk = shutil.disk_usage(Path.home())
            armazenamento = {
                "total_bytes": disk.total,
                "usado_bytes": disk.used,
                "livre_bytes": disk.free,
                "uso_percentual": round((disk.used / disk.total) * 100, 2) if disk.total else None,
            }
        except OSError as exc:
            armazenamento = {"estado": "indisponivel", "erro": type(exc).__name__}

        memoria = self._memoria()
        processos = self._processos()
        servicos_usuario = self._servicos(user=True)
        servicos_sistema = self._servicos(user=False)

        try:
            load_avg = [round(value, 2) for value in os.getloadavg()]
        except (OSError, AttributeError):
            load_avg = None

        return {
            "sucesso": True,
            "estado": "observacao_concluida",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "modo": "somente_leitura",
            "host": {
                "sistema": platform.system(),
                "release": platform.release(),
                "arquitetura": platform.machine(),
                "python": platform.python_version(),
                "hostname": platform.node(),
            },
            "cpu": {"load_average_1_5_15": load_avg},
            "memoria": memoria,
            "armazenamento_home": armazenamento,
            "processos": processos,
            "servicos_usuario": servicos_usuario,
            "servicos_sistema": servicos_sistema,
            "governanca": {
                "comandos_arbitrarios_habilitados": False,
                "alteracao_de_arquivos_habilitada": False,
                "controle_de_servicos_habilitado": False,
            },
        }

    @staticmethod
    def _memoria() -> dict[str, Any]:
        info: dict[str, int] = {}
        try:
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                name, _, rest = line.partition(":")
                if name in {"MemTotal", "MemAvailable", "MemFree", "SwapTotal", "SwapFree"}:
                    pieces = rest.strip().split()
                    if pieces:
                        info[name] = int(pieces[0]) * 1024
        except (OSError, ValueError):
            return {"estado": "indisponivel"}
        total = info.get("MemTotal")
        available = info.get("MemAvailable")
        used = total - available if total is not None and available is not None else None
        return {
            "total_bytes": total,
            "disponivel_bytes": available,
            "usado_bytes": used,
            "uso_percentual": round((used / total) * 100, 2) if used is not None and total else None,
            "swap_total_bytes": info.get("SwapTotal"),
            "swap_livre_bytes": info.get("SwapFree"),
        }

    @staticmethod
    def _processos() -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["ps", "-eo", "pid,comm,%cpu,%mem", "--sort=-%cpu"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if result.returncode != 0:
                return {"estado": "indisponivel"}
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            rows = []
            for line in lines[1:16]:
                parts = line.split(None, 3)
                if len(parts) != 4:
                    continue
                try:
                    rows.append({
                        "pid": int(parts[0]),
                        "nome": parts[1][:100],
                        "cpu_percentual": float(parts[2]),
                        "memoria_percentual": float(parts[3]),
                    })
                except ValueError:
                    continue
            return {"total_observado": max(0, len(lines) - 1), "top_cpu": rows, "comando": "ps -eo pid,comm,%cpu,%mem"}
        except (OSError, subprocess.TimeoutExpired):
            return {"estado": "indisponivel"}

    @staticmethod
    def _servicos(*, user: bool) -> dict[str, Any]:
        command = ["systemctl"]
        if user:
            command.append("--user")
        command.extend(["list-units", "--type=service", "--all", "--no-pager", "--no-legend"])
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
            if result.returncode != 0:
                return {"estado": "indisponivel", "codigo": result.returncode}
            rows = []
            for line in result.stdout.splitlines()[:50]:
                parts = line.split(None, 4)
                if len(parts) >= 4:
                    rows.append({
                        "unidade": parts[0][:160],
                        "load": parts[1],
                        "active": parts[2],
                        "sub": parts[3],
                        "descricao": parts[4][:180] if len(parts) > 4 else "",
                    })
            return {"estado": "observado", "tipo": "usuario" if user else "sistema", "unidades": rows}
        except (OSError, subprocess.TimeoutExpired):
            return {"estado": "indisponivel"}


__all__ = ["ObservabilidadeSistemaNixOS"]
