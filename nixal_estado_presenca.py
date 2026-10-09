#!/usr/bin/env python3
"""Deriva a presença pública usando heartbeats residentes recentes.

O antigo estado_nixal.json pertence ao ciclo legado. O runtime residente
atualiza presenca_maquina_nyxos.json; os dois sinais são verificados com
timestamps recentes para evitar apresentar registros antigos como online.
"""

from __future__ import annotations

from datetime import datetime
import time
from typing import Any

PRESENCA_TTL_SEGUNDOS = 90
TOLERANCIA_RELOGIO_SEGUNDOS = 5
_ESTADOS_PRESENCA_ATIVA = frozenset({"ativo", "heartbeat"})
_ESTADOS_RESIDENTE_INATIVOS = frozenset({
    "erro",
    "falhou",
    "interrompido",
    "concluido",
    "encerrado",
    "parado",
})


def _heartbeat_recente(
    timestamp: Any,
    *,
    agora_epoch: float,
    ttl_segundos: float,
) -> tuple[bool, float | None]:
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        return False, None

    idade = agora_epoch - float(timestamp)
    recente = -TOLERANCIA_RELOGIO_SEGUNDOS <= idade <= ttl_segundos
    return recente, max(0.0, idade)


def _timestamp_iso_recente(
    valor: Any,
    *,
    agora: datetime,
    ttl_segundos: float,
) -> bool:
    if not isinstance(valor, str) or not valor.strip():
        return False

    try:
        instante = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
        if instante.tzinfo is None:
            instante = instante.astimezone()
        idade = (agora - instante).total_seconds()
    except (ValueError, OverflowError):
        return False

    return -TOLERANCIA_RELOGIO_SEGUNDOS <= idade <= ttl_segundos


def compor_presenca_efetiva(
    *,
    presenca_legada: dict[str, Any] | None,
    estado_legado: dict[str, Any] | None,
    presenca_maquina: dict[str, Any] | None,
    persistencia_operacional: dict[str, Any] | None = None,
    agora_epoch: float | None = None,
    agora: datetime | None = None,
    ttl_segundos: float = PRESENCA_TTL_SEGUNDOS,
) -> dict[str, Any]:
    """Retorna a presença ativa somente se um sinal residente estiver fresco.

    O heartbeat da residência moderna tem precedência quando está atual.
    O estado legado só conta como ativo quando seu último ciclo também é
    recente. Valores antigos são preservados como metadados, não como prova
    de que a Nyxal está online.
    """
    legado = presenca_legada if isinstance(presenca_legada, dict) else {}
    estado_old = estado_legado if isinstance(estado_legado, dict) else {}
    maquina = presenca_maquina if isinstance(presenca_maquina, dict) else {}
    operacional = (
        persistencia_operacional
        if isinstance(persistencia_operacional, dict)
        else {}
    )

    epoch = time.time() if agora_epoch is None else float(agora_epoch)
    agora_dt = datetime.now().astimezone() if agora is None else agora

    estado_maquina = str(maquina.get("estado_presenca") or "").strip().lower()
    residencia = maquina.get("residencia")
    residencia = residencia if isinstance(residencia, dict) else {}
    estado_residente = str(residencia.get("estado_residente") or "").strip().lower()
    heartbeat_ok, heartbeat_age = _heartbeat_recente(
        maquina.get("ultimo_heartbeat"),
        agora_epoch=epoch,
        ttl_segundos=ttl_segundos,
    )
    maquina_ativa = (
        estado_maquina in _ESTADOS_PRESENCA_ATIVA
        and heartbeat_ok
        and maquina.get("encerrado_em") is None
        and estado_residente not in _ESTADOS_RESIDENTE_INATIVOS
    )

    legado_ativo = (
        legado.get("ativa") is True
        and _timestamp_iso_recente(
            legado.get("ultimo_ciclo"),
            agora=agora_dt,
            ttl_segundos=ttl_segundos,
        )
        and str(estado_old.get("status") or "").strip().lower()
        not in {"encerrada", "encerrado", "inativa", "inativo", "erro", "falhou"}
    )

    ultimo_ciclo_legado = legado.get("ultimo_ciclo")
    ciclos_legados = legado.get("ciclos")

    if maquina_ativa:
        ultimo_ciclo_operacional = operacional.get("ultimo_ciclo")
        ultimo_ciclo_operacional = (
            ultimo_ciclo_operacional
            if isinstance(ultimo_ciclo_operacional, dict)
            else {}
        )
        ultimo_ciclo = (
            ultimo_ciclo_operacional.get("concluido_em")
            or operacional.get("ultima_persistencia")
        )
        ciclos = None
        ativa = True
        origem = "presenca_maquina_nyxos"
    elif legado_ativo:
        ultimo_ciclo = ultimo_ciclo_legado
        ciclos = ciclos_legados
        ativa = True
        origem = "estado_nixal.json"
    else:
        ultimo_ciclo = ultimo_ciclo_legado
        ciclos = ciclos_legados
        ativa = False
        origem = "sem_sinal_recente"

    return {
        "ativa": ativa,
        "ultimo_ciclo": ultimo_ciclo,
        "ciclos": ciclos,
        "origem": origem,
        "heartbeat_atrasado_segundos": (
            round(heartbeat_age, 1) if heartbeat_age is not None else None
        ),
        "estado_residente": estado_residente or None,
    }


__all__ = [
    "PRESENCA_TTL_SEGUNDOS",
    "compor_presenca_efetiva",
]
