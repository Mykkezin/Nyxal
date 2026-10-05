#!/usr/bin/env python3
"""
NIXAL — PROCESSOS DO HABITAT M5.2

Adaptador somente leitura para transformar processos do host Linux
em entidades sanitizadas do habitat NyxOS.

Nenhum comando externo é executado e nenhuma ação é aplicada aos
processos observados.
"""

from __future__ import annotations

import glob
import os
import re
import time
from typing import Any


class ProcessosHabitat:
    """Observa processos reais do host sem controlá-los."""

    FONTE = "processos_habitat_nyxos"
    VERSAO = "5.2.0"
    INTERVALO_AMOSTRAGEM_SEGUNDOS = 0.12
    LIMITE_PADRAO = 12
    LIMITE_MINIMO = 1
    LIMITE_MAXIMO = 50

    def __init__(self, limite: int | None = None) -> None:
        self.limite = self._normalizar_limite(limite)

    @classmethod
    def _normalizar_limite(cls, limite: int | None) -> int:
        if limite is None:
            limite = cls.LIMITE_PADRAO

        try:
            valor = int(limite)
        except (TypeError, ValueError):
            valor = cls.LIMITE_PADRAO

        return max(
            cls.LIMITE_MINIMO,
            min(cls.LIMITE_MAXIMO, valor),
        )

    @staticmethod
    def _ler_texto(caminho: str) -> str | None:
        try:
            with open(caminho, "r", encoding="utf-8") as arquivo:
                return arquivo.read().strip()
        except (OSError, UnicodeDecodeError):
            return None

    @staticmethod
    def _ler_stat(pid: int) -> dict[str, Any] | None:
        texto = ProcessosHabitat._ler_texto(f"/proc/{pid}/stat")

        if not texto:
            return None

        fechamento_nome = texto.rfind(")")
        if fechamento_nome < 0:
            return None

        prefixo = texto[:fechamento_nome]
        restante = texto[fechamento_nome + 2 :]

        try:
            pid_lido = int(prefixo.split("(", 1)[0].strip())
        except (TypeError, ValueError, IndexError):
            return None

        partes = restante.split()

        # Após o campo comm, o primeiro item é state.
        # utime = campo 14, stime = 15, starttime = 22.
        if len(partes) < 20:
            return None

        try:
            return {
                "pid": pid_lido,
                "nome": prefixo.split("(", 1)[1],
                "estado": partes[0],
                "jiffies_cpu": int(partes[11]) + int(partes[12]),
                "inicio_ticks": int(partes[19]),
            }
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ler_memoria(pid: int) -> int | None:
        texto = ProcessosHabitat._ler_texto(f"/proc/{pid}/status")
        if not texto:
            return None

        for linha in texto.splitlines():
            if not linha.startswith("VmRSS:"):
                continue

            partes = linha.split()
            if len(partes) < 2:
                return None

            try:
                return int(partes[1])
            except ValueError:
                return None

        return None

    @classmethod
    def _coletar_amostra(cls) -> tuple[int, dict[int, dict[str, Any]]]:
        total_cpu = 0
        sistema = ProcessosHabitat._ler_texto("/proc/stat")

        if sistema:
            for linha in sistema.splitlines():
                if not linha.startswith("cpu "):
                    continue

                partes = linha.split()[1:8]
                try:
                    total_cpu = sum(int(valor) for valor in partes)
                except ValueError:
                    total_cpu = 0
                break

        processos: dict[int, dict[str, Any]] = {}

        for caminho in glob.glob("/proc/[0-9]*"):
            nome_dir = os.path.basename(caminho)
            if not nome_dir.isdigit():
                continue

            pid = int(nome_dir)
            estatisticas = cls._ler_stat(pid)
            if estatisticas is None:
                continue

            memoria_kb = cls._ler_memoria(pid)
            estatisticas["memoria_rss_kb"] = memoria_kb
            processos[pid] = estatisticas

        return total_cpu, processos

    @staticmethod
    def _limpar_nome(nome: Any) -> str | None:
        if not isinstance(nome, str):
            return None

        limpo = re.sub(r"[\x00-\x1f\x7f]", "", nome).strip()
        if not limpo:
            return None

        return limpo[:80]

    @staticmethod
    def _memoria_total_kb() -> int | None:
        texto = ProcessosHabitat._ler_texto("/proc/meminfo")
        if not texto:
            return None

        for linha in texto.splitlines():
            if not linha.startswith("MemTotal:"):
                continue

            partes = linha.split()
            if len(partes) < 2:
                return None

            try:
                return int(partes[1])
            except ValueError:
                return None

        return None

    def snapshot(self) -> dict[str, Any]:
        total_cpu_anterior, anterior = self._coletar_amostra()

        time.sleep(self.INTERVALO_AMOSTRAGEM_SEGUNDOS)

        total_cpu_atual, atual = self._coletar_amostra()

        delta_cpu_sistema = total_cpu_atual - total_cpu_anterior
        nucleos = os.cpu_count() or 1
        memoria_total_kb = self._memoria_total_kb()

        entidades: list[dict[str, Any]] = []

        for pid, processo_atual in atual.items():
            processo_anterior = anterior.get(pid)
            if processo_anterior is None:
                continue

            inicio_atual = processo_atual.get("inicio_ticks")
            inicio_anterior = processo_anterior.get("inicio_ticks")

            # Evita atribuir CPU de um processo novo ao PID reutilizado.
            if inicio_atual != inicio_anterior:
                continue

            uso_cpu = None
            delta_processo = (
                processo_atual.get("jiffies_cpu", 0)
                - processo_anterior.get("jiffies_cpu", 0)
            )

            if delta_cpu_sistema > 0 and delta_processo >= 0:
                uso_cpu = round(
                    min(
                        100.0,
                        max(
                            0.0,
                            (delta_processo / delta_cpu_sistema)
                            * nucleos
                            * 100.0,
                        ),
                    ),
                    2,
                )

            memoria_kb = processo_atual.get("memoria_rss_kb")
            memoria_percentual = None

            if (
                memoria_total_kb
                and isinstance(memoria_kb, int)
                and memoria_kb >= 0
            ):
                memoria_percentual = round(
                    (memoria_kb / memoria_total_kb) * 100.0,
                    4,
                )

            entidades.append(
                {
                    "id": (
                        f"processo:{pid}:"
                        f"{processo_atual.get('inicio_ticks')}"
                    ),
                    "pid": pid,
                    "nome": self._limpar_nome(
                        processo_atual.get("nome")
                    ),
                    "estado": processo_atual.get("estado"),
                    "uso_cpu_percentual": uso_cpu,
                    "memoria_rss_percentual": memoria_percentual,
                    "memoria_rss_mb": (
                        round(memoria_kb / 1024, 2)
                        if isinstance(memoria_kb, int)
                        else None
                    ),
                }
            )

        entidades.sort(
            key=lambda item: (
                item.get("uso_cpu_percentual") is None,
                -(item.get("uso_cpu_percentual") or 0.0),
                -(item.get("memoria_rss_percentual") or 0.0),
            )
        )

        return {
            "sucesso": True,
            "estado": "processos_observados",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "modo": "somente_leitura",
            "total": len(atual),
            "limite": self.limite,
            "entidades": entidades[: self.limite],
            "persistente": False,
            "controle_habilitado": False,
        }


__all__ = ["ProcessosHabitat"]
