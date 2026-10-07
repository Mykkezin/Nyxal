from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from nixal_fechamento_cadeia_operacional import (
    FechamentoCadeiaOperacional,
    ORDEM_CADEIA,
)


DESTINO_LLC = "llc"


@dataclass(frozen=True)
class HandoffO15LLC:
    identidade: str
    identidade_fechamento: str
    identidade_candidato: str
    etapas: tuple[str, ...]
    identidades_artefatos: tuple[str, ...]
    destino: str
    estado: str
    aprendizado_executado: bool
    autorizacao_integracao: bool
    integracao_executada: bool


def _identidade_handoff(
    fechamento: FechamentoCadeiaOperacional,
) -> str:
    material = json.dumps(
        {
            "identidade_fechamento": fechamento.identidade,
            "identidade_candidato": fechamento.identidade_candidato,
            "etapas": fechamento.etapas,
            "identidades_artefatos": fechamento.identidades_artefatos,
            "destino": DESTINO_LLC,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()
    return f"HANDOFF-{digest[:24]}"


def preparar(
    fechamento: FechamentoCadeiaOperacional,
) -> HandoffO15LLC:
    if not isinstance(
        fechamento,
        FechamentoCadeiaOperacional,
    ):
        raise ValueError("fechamento_o15_invalido")

    if fechamento.estado != "fechado":
        raise ValueError("fechamento_o15_nao_fechado")

    if fechamento.cadeia_fechada is not True:
        raise ValueError("cadeia_o15_nao_fechada")

    if fechamento.handoff_preparado is not True:
        raise ValueError("handoff_o15_nao_preparado")

    if fechamento.etapas != ORDEM_CADEIA:
        raise ValueError("cadeia_o15_invalida")

    if not isinstance(
        fechamento.identidade_candidato,
        str,
    ) or not fechamento.identidade_candidato:
        raise ValueError("candidato_o15_invalido")

    if len(fechamento.identidades_artefatos) != len(
        ORDEM_CADEIA
    ):
        raise ValueError("artefatos_o15_incompletos")

    if any(
        not isinstance(identidade, str) or not identidade
        for identidade in fechamento.identidades_artefatos
    ):
        raise ValueError("identidade_artefato_invalida")

    return HandoffO15LLC(
        identidade=_identidade_handoff(fechamento),
        identidade_fechamento=fechamento.identidade,
        identidade_candidato=fechamento.identidade_candidato,
        etapas=tuple(fechamento.etapas),
        identidades_artefatos=tuple(
            fechamento.identidades_artefatos
        ),
        destino=DESTINO_LLC,
        estado="preparado",
        aprendizado_executado=False,
        autorizacao_integracao=False,
        integracao_executada=False,
    )


__all__ = [
    "DESTINO_LLC",
    "HandoffO15LLC",
    "preparar",
]
