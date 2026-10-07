from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping


ORDEM_CADEIA = (
    "O9",
    "O10",
    "O11",
    "O12",
    "O13",
    "O14",
)


@dataclass(frozen=True)
class FechamentoCadeiaOperacional:
    identidade: str
    estado: str
    etapas: tuple[str, ...]
    identidades_artefatos: tuple[str, ...]
    identidade_candidato: str
    cadeia_fechada: bool
    handoff_preparado: bool


def _valor(
    etapa: Mapping[str, Any],
    nome: str,
) -> Any:
    if nome not in etapa:
        raise ValueError(
            f"campo_ausente:{nome}"
        )

    return etapa[nome]


def _validar_etapa(
    etapa: Mapping[str, Any],
    esperada: str,
) -> str:
    if not isinstance(etapa, Mapping):
        raise ValueError(
            f"etapa_invalida:{esperada}"
        )

    etapa_id = _valor(
        etapa,
        "etapa",
    )

    if etapa_id != esperada:
        raise ValueError(
            f"ordem_invalida:{esperada}"
        )

    identidade = _valor(
        etapa,
        "identidade",
    )

    if not isinstance(
        identidade,
        str,
    ) or not identidade:
        raise ValueError(
            f"identidade_invalida:{esperada}"
        )

    estado = _valor(
        etapa,
        "estado",
    )

    if estado in {
        "aprendido",
        "integrado",
    }:
        raise ValueError(
            f"estado_ultrapassa_fronteira:{esperada}"
        )

    if etapa_id != "O14":
        return identidade

    if estado != "candidato":
        raise ValueError(
            "O14_nao_esta_em_estado_candidato"
        )

    if etapa.get(
        "autorizacao_integracao",
        False,
    ):
        raise ValueError(
            "autorizacao_integracao_nao_permitida"
        )

    if etapa.get(
        "integrado",
        False,
    ):
        raise ValueError(
            "integracao_nao_permitida"
        )

    return identidade


def _identidade_fechamento(
    identidades: tuple[str, ...],
) -> str:
    material = "|".join(
        identidades
    )

    digest = hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()

    return f"CHAIN-{digest[:24]}"


def fechar(
    cadeia: tuple[Mapping[str, Any], ...],
) -> FechamentoCadeiaOperacional:
    if not isinstance(
        cadeia,
        tuple,
    ):
        raise ValueError(
            "cadeia_deve_ser_tuple"
        )

    if len(cadeia) != len(
        ORDEM_CADEIA
    ):
        raise ValueError(
            "cadeia_incompleta"
        )

    identidades = []

    for etapa, esperada in zip(
        cadeia,
        ORDEM_CADEIA,
    ):
        identidade = _validar_etapa(
            etapa,
            esperada,
        )
        identidades.append(
            identidade
        )

    identidades_tuple = tuple(
        identidades
    )

    identidade_candidato = (
        identidades_tuple[-1]
    )

    identidade_fechamento = (
        _identidade_fechamento(
            identidades_tuple
        )
    )

    return FechamentoCadeiaOperacional(
        identidade=identidade_fechamento,
        estado="fechado",
        etapas=ORDEM_CADEIA,
        identidades_artefatos=identidades_tuple,
        identidade_candidato=identidade_candidato,
        cadeia_fechada=True,
        handoff_preparado=True,
    )
