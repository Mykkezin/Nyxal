from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple


CRITERIOS_VALIDOS = frozenset(
    {
        "identidade",
        "par",
        "ciclo",
        "autoridade",
        "tipo",
    }
)


@dataclass(frozen=True)
class ReutilizacaoEvidencia:
    identidade_evidencia: str
    identidade_qualificacao: str
    criterio: tuple[str, Any]
    relacoes: Tuple[Any, ...]
    total_relacoes: int


@dataclass(frozen=True)
class ResultadoReutilizacao:
    reutilizada: bool
    resultado: Optional[ReutilizacaoEvidencia]
    motivos: Tuple[str, ...]


def _atributo(obj: Any, nome: str) -> Any:
    if not hasattr(obj, nome):
        raise ValueError(f"atributo ausente: {nome}")
    return getattr(obj, nome)


def _relacoes_da_evidencia(evidencia: Any) -> Tuple[Any, ...]:
    relacoes = _atributo(evidencia, "relacoes")
    if not isinstance(relacoes, tuple):
        raise ValueError("relacoes deve ser tuple")
    return relacoes


def _valor_relacao(relacao: Any, campo: str) -> Any:
    if not hasattr(relacao, campo):
        raise ValueError(
            f"relação sem campo necessário para o critério: {campo}"
        )
    return getattr(relacao, campo)


def _selecionar(
    relacoes: Tuple[Any, ...],
    criterio: str,
    valor: Any,
) -> Tuple[Any, ...]:
    if criterio == "identidade":
        return tuple(
            relacao
            for relacao in relacoes
            if _valor_relacao(relacao, "identidade") == valor
        )

    if criterio == "par":
        if (
            not isinstance(valor, tuple)
            or len(valor) != 2
        ):
            raise ValueError("critério par exige tuple (origem, destino)")

        origem, destino = valor

        return tuple(
            relacao
            for relacao in relacoes
            if (
                _valor_relacao(relacao, "origem") == origem
                and _valor_relacao(relacao, "destino") == destino
            )
        )

    if criterio == "ciclo":
        return tuple(
            relacao
            for relacao in relacoes
            if _valor_relacao(relacao, "ciclo") == valor
        )

    if criterio == "autoridade":
        return tuple(
            relacao
            for relacao in relacoes
            if _valor_relacao(relacao, "autoridade") == valor
        )

    if criterio == "tipo":
        return tuple(
            relacao
            for relacao in relacoes
            if _valor_relacao(relacao, "tipo") == valor
        )

    raise ValueError(f"critério inválido: {criterio}")


def reutilizar(
    evidencia: Any,
    qualificacao: Any,
    criterio: str,
    valor: Any,
) -> ResultadoReutilizacao:
    motivos = []

    try:
        identidade_evidencia = _atributo(
            evidencia,
            "identidade",
        )

        identidade_qualificacao = _atributo(
            qualificacao,
            "identidade",
        )

        estado = _atributo(
            qualificacao,
            "estado",
        )

        relacoes = _relacoes_da_evidencia(evidencia)

    except (AttributeError, ValueError) as exc:
        return ResultadoReutilizacao(
            reutilizada=False,
            resultado=None,
            motivos=(str(exc),),
        )

    if estado != "qualificada":
        motivos.append("evidencia_nao_qualificada")

    if identidade_evidencia != identidade_qualificacao:
        motivos.append("identidade_inconsistente")

    if criterio not in CRITERIOS_VALIDOS:
        motivos.append("criterio_invalido")

    if motivos:
        return ResultadoReutilizacao(
            reutilizada=False,
            resultado=None,
            motivos=tuple(motivos),
        )

    try:
        selecionadas = _selecionar(
            relacoes,
            criterio,
            valor,
        )
    except ValueError as exc:
        return ResultadoReutilizacao(
            reutilizada=False,
            resultado=None,
            motivos=(str(exc),),
        )

    resultado = ReutilizacaoEvidencia(
        identidade_evidencia=identidade_evidencia,
        identidade_qualificacao=identidade_qualificacao,
        criterio=(criterio, valor),
        relacoes=selecionadas,
        total_relacoes=len(selecionadas),
    )

    return ResultadoReutilizacao(
        reutilizada=True,
        resultado=resultado,
        motivos=(),
    )
