from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class ComparacaoEvidencias:
    identidade_primeira: str
    identidade_segunda: str

    relacoes_primeira: Tuple[Any, ...]
    relacoes_segunda: Tuple[Any, ...]

    intersecao: Tuple[Any, ...]
    exclusivas_primeira: Tuple[Any, ...]
    exclusivas_segunda: Tuple[Any, ...]

    iguais: bool
    sobreposicao: bool

    total_primeira: int
    total_segunda: int
    total_intersecao: int
    total_exclusivas_primeira: int
    total_exclusivas_segunda: int


def _atributo(obj: Any, nome: str) -> Any:
    if not hasattr(obj, nome):
        raise ValueError(f"atributo ausente: {nome}")
    return getattr(obj, nome)


def _validar_evidencia(evidencia: Any) -> tuple[str, Tuple[Any, ...]]:
    identidade = _atributo(evidencia, "identidade")
    estado = _atributo(evidencia, "estado")

    if estado != "qualificada":
        raise ValueError("evidencia_nao_qualificada")

    relacoes = _atributo(evidencia, "relacoes")

    if not isinstance(relacoes, tuple):
        raise ValueError("relacoes_deve_ser_tuple")

    return identidade, relacoes


def _chave(relacao: Any) -> Any:
    """
    Identidade estrutural da relação.

    O12 não cria uma identidade nova.
    Quando a relação expõe 'identidade', ela é utilizada.
    Caso contrário, a própria relação é usada como chave.
    """
    if hasattr(relacao, "identidade"):
        return getattr(relacao, "identidade")

    return relacao


def _intersecao(
    primeira: Tuple[Any, ...],
    segunda: Tuple[Any, ...],
) -> Tuple[Any, ...]:
    chaves_segunda = {_chave(relacao) for relacao in segunda}

    return tuple(
        relacao
        for relacao in primeira
        if _chave(relacao) in chaves_segunda
    )


def _exclusivas(
    origem: Tuple[Any, ...],
    outra: Tuple[Any, ...],
) -> Tuple[Any, ...]:
    chaves_outra = {_chave(relacao) for relacao in outra}

    return tuple(
        relacao
        for relacao in origem
        if _chave(relacao) not in chaves_outra
    )


def comparar(
    primeira: Any,
    segunda: Any,
) -> ComparacaoEvidencias:
    identidade_primeira, relacoes_primeira = _validar_evidencia(
        primeira
    )

    identidade_segunda, relacoes_segunda = _validar_evidencia(
        segunda
    )

    intersecao = _intersecao(
        relacoes_primeira,
        relacoes_segunda,
    )

    exclusivas_primeira = _exclusivas(
        relacoes_primeira,
        relacoes_segunda,
    )

    exclusivas_segunda = _exclusivas(
        relacoes_segunda,
        relacoes_primeira,
    )

    iguais = relacoes_primeira == relacoes_segunda
    sobreposicao = bool(intersecao)

    return ComparacaoEvidencias(
        identidade_primeira=identidade_primeira,
        identidade_segunda=identidade_segunda,
        relacoes_primeira=relacoes_primeira,
        relacoes_segunda=relacoes_segunda,
        intersecao=intersecao,
        exclusivas_primeira=exclusivas_primeira,
        exclusivas_segunda=exclusivas_segunda,
        iguais=iguais,
        sobreposicao=sobreposicao,
        total_primeira=len(relacoes_primeira),
        total_segunda=len(relacoes_segunda),
        total_intersecao=len(intersecao),
        total_exclusivas_primeira=len(exclusivas_primeira),
        total_exclusivas_segunda=len(exclusivas_segunda),
    )
