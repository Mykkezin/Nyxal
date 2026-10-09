#!/usr/bin/env python3
"""Observabilidade local de sistema em modo somente leitura.

Executa apenas consultas fixas e não aceita comandos fornecidos pelo usuário.
"""
from __future__ import annotations

import json
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
        temperaturas = self._temperaturas()
        gpu = self._gpu()
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
            "temperaturas": temperaturas,
            "gpu": gpu,
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
    def _temperaturas() -> dict[str, Any]:
        readings: list[dict[str, Any]] = []
        sensors_bin = shutil.which("sensors")
        if sensors_bin:
            try:
                result = subprocess.run(
                    [sensors_bin, "-j"],
                    capture_output=True,
                    text=True,
                    timeout=4,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    parsed = json.loads(result.stdout)

                    def collect(value: Any, prefix: str = "") -> None:
                        if isinstance(value, dict):
                            for key, item in value.items():
                                label = f"{prefix}/{key}" if prefix else str(key)
                                if (
                                    "temp" in str(key).lower()
                                    and str(key).endswith("_input")
                                    and isinstance(item, (int, float))
                                    and not isinstance(item, bool)
                                ):
                                    readings.append({
                                        "sensor": label[:180],
                                        "celsius": round(float(item), 1),
                                        "origem": "lm-sensors",
                                    })
                                else:
                                    collect(item, label)
                        elif isinstance(value, list):
                            for index, item in enumerate(value):
                                collect(item, f"{prefix}[{index}]")

                    collect(parsed)
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
                readings = []

        # Fallback somente leitura para sysfs caso lm-sensors não esteja disponível.
        if not readings:
            root = Path("/sys/class/thermal")
            try:
                zones = sorted(root.glob("thermal_zone*"))
            except OSError:
                zones = []
            for zone in zones[:32]:
                try:
                    raw = float((zone / "temp").read_text(encoding="utf-8").strip())
                    label = (zone / "type").read_text(encoding="utf-8").strip()[:120]
                    temperature = raw / 1000.0 if abs(raw) >= 1000 else raw
                    readings.append({
                        "sensor": label or zone.name,
                        "celsius": round(temperature, 1),
                        "origem": "sysfs-thermal",
                    })
                except (OSError, ValueError):
                    continue

        return {
            "estado": "observado" if readings else "indisponivel",
            "quantidade": len(readings),
            "sensores": readings[:32],
            "somente_leitura": True,
        }

    @staticmethod
    def _gpu() -> dict[str, Any]:
        devices: list[dict[str, Any]] = []
        root = Path("/sys/class/drm")
        try:
            candidates = sorted(root.glob("card[0-9]*/device"))
        except OSError:
            candidates = []

        vendor_names = {
            "0x1002": "AMD",
            "0x10de": "NVIDIA",
            "0x8086": "Intel",
        }
        for device_path in candidates[:8]:
            try:
                vendor_id = (device_path / "vendor").read_text(encoding="utf-8").strip().lower()
            except OSError:
                continue
            if vendor_id not in vendor_names:
                continue
            try:
                device_id = (device_path / "device").read_text(encoding="utf-8").strip().lower()
            except OSError:
                device_id = ""
            record: dict[str, Any] = {
                "nome": f"{vendor_names[vendor_id]} GPU" + (f" ({device_id})" if device_id else ""),
                "fabricante": vendor_names[vendor_id],
                "uso_percentual": None,
                "vram_total_bytes": None,
                "vram_usada_bytes": None,
                "vram_uso_percentual": None,
                "temperatura_celsius": None,
                "origem": "sysfs-drm",
            }
            for attr, target in (
                ("gpu_busy_percent", "uso_percentual"),
                ("mem_info_vram_total", "vram_total_bytes"),
                ("mem_info_vram_used", "vram_usada_bytes"),
            ):
                try:
                    value = int((device_path / attr).read_text(encoding="utf-8").strip())
                    record[target] = value
                except (OSError, ValueError):
                    continue

            total = record["vram_total_bytes"]
            used = record["vram_usada_bytes"]
            if isinstance(total, int) and total > 0 and isinstance(used, int):
                record["vram_uso_percentual"] = round(min(100.0, max(0.0, used / total * 100)), 2)

            try:
                hwmon_dirs = sorted((device_path / "hwmon").glob("hwmon*"))
            except OSError:
                hwmon_dirs = []
            for hwmon in hwmon_dirs:
                for temp_path in sorted(hwmon.glob("temp*_input")):
                    try:
                        raw = float(temp_path.read_text(encoding="utf-8").strip())
                        record["temperatura_celsius"] = round(raw / 1000.0 if abs(raw) >= 1000 else raw, 1)
                        break
                    except (OSError, ValueError):
                        continue
                if record["temperatura_celsius"] is not None:
                    break
            devices.append(record)

        # Consulta fixa extra para enriquecer dados NVIDIA quando o driver disponibiliza a ferramenta.
        nvidia_bin = shutil.which("nvidia-smi")
        if nvidia_bin and not any(
            item.get("uso_percentual") is not None or item.get("vram_total_bytes") is not None
            for item in devices
        ):
            try:
                result = subprocess.run(
                    [
                        nvidia_bin,
                        "--query-gpu=name,utilization.gpu,memory.total,memory.used,temperature.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=4,
                    check=False,
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines()[:8]:
                        columns = [item.strip() for item in line.split(",")]
                        if len(columns) != 5:
                            continue

                        def number(value: str) -> float | None:
                            if value.upper() in {"N/A", "[N/A]", ""}:
                                return None
                            try:
                                return float(value)
                            except ValueError:
                                return None

                        usage = number(columns[1])
                        total_mb = number(columns[2])
                        used_mb = number(columns[3])
                        temperature = number(columns[4])
                        detected = {
                            "nome": columns[0][:180],
                            "fabricante": "NVIDIA",
                            "uso_percentual": usage,
                            "vram_total_bytes": int(total_mb * 1024 * 1024) if total_mb is not None else None,
                            "vram_usada_bytes": int(used_mb * 1024 * 1024) if used_mb is not None else None,
                            "vram_uso_percentual": round(used_mb / total_mb * 100, 2) if total_mb and used_mb is not None else None,
                            "temperatura_celsius": temperature,
                            "origem": "nvidia-smi",
                        }
                        existing = next((
                            item for item in devices
                            if item.get("fabricante") == "NVIDIA"
                            and item.get("uso_percentual") is None
                            and item.get("vram_total_bytes") is None
                        ), None)
                        if existing is not None:
                            existing.update(detected)
                        else:
                            devices.append(detected)
            except (OSError, subprocess.TimeoutExpired):
                pass

        return {
            "estado": "observado" if devices else "indisponivel",
            "quantidade": len(devices),
            "dispositivos": devices,
            "somente_leitura": True,
        }

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
