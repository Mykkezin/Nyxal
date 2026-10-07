from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Tuple


@dataclass(frozen=True)
class OcorrenciaPadrao:
    identidade_evidencia: str
    ciclo: Any
    relacao: Any
    posicao: int


@dataclass(frozen=True)
class PadraoRecorrente:
    assinatura: Tuple[Any, ...]
    ocorrencias: Tuple[OcorrenciaPadrao, ...]
    evidencias_distintas: Tuple[str, ...]
    ciclos_observados: Tuple[Any, ...]
    frequencia_evidencias: int


@dataclass(frozen=True)
class ResultadoPadroRecorrente:
    padroes: Tuple[PadraoRecorrente, ...]
    total_padroes: int
    total_evidencias: int


def _atributo(obj: Any, nome: str) -> Any:
    if not hasattr(obj, nome):
        raise ValueError(f"atributo ausente: {nome}")
    return getattr(obj, nome)


def _validar_evidencia(evidencia: Any) -> tuple[str, Tuple[Any, ...]]:
    identidade = _atributo(evidencia, "identidade")
    estado = _atributo(evidencia, "estado")
    relacoes = _atributo(evidencia, "relacoes")

    if not identidade:
        raise ValueError("identidade_evidencia_invalida")

    if estado != "qualificada":
        raise ValueError("evidencia_nao_qualificada")

    if not isinstance(relacoes, tuple):
        raise ValueError("relacoes_deve_ser_tuple")

    return identidade, relacoes


def _assinatura(relacao: Any) -> Tuple[Any, ...]:
    origem = _atributo(relacao, "origem")
    destino = _atributo(relacao, "destino")
    tipo = _atributo(relacao, "tipo")
    autoridade = _atributo(relacao, "autoridade")

    return (
        origem,
        destino,
        tipo,
        autoridade,
    )


def _chave_assinatura(assinatura: Tuple[Any, ...]) -> Tuple[str, ...]:
    return tuple(repr(valor) for valor in assinatura)


def detectar(
    evidencias: Iterable[Any],
) -> ResultadoPadroRecorrente:
    if isinstance(evidencias, (str, bytes)):
        raise ValueError("entrada_nao_iteravel_de_evidencias")

    try:
        lista = tuple(evidencias)
    except TypeError as exc:
        raise ValueError(
            "entrada_nao_iteravel_de_evidencias"
        ) from exc

    if not lista:
        raise ValueError("conjunto_de_evidencias_vazio")

    grupos: dict[
        Tuple[Any, ...],
        list[OcorrenciaPadrao],
    ] = {}

    identidades: list[str] = []

    for evidencia in lista:
        identidade, relacoes = _validar_evidencia(evidencia)

        identidades.append(identidade)

        for posicao, relacao in enumerate(relacoes):
            assinatura = _assinatura(relacao)

            ocorrencia = OcorrenciaPadrao(
                identidade_evidencia=identidade,
                ciclo=_atributo(relacao, "ciclo"),
                relacao=relacao,
                posicao=posicao,
            )

            grupos.setdefault(assinatura, []).append(
                ocorrencia
            )

    padroes: list[PadraoRecorrente] = []

    for assinatura, ocorrencias in grupos.items():
        evidencias_distintas = tuple(
            dict.fromkeys(
                ocorrencia.identidade_evidencia
                for ocorrencia in ocorrencias
            )
        )

        if len(evidencias_distintas) < 2:
            continue

        ciclos_observados = tuple(
            dict.fromkeys(
                ocorrencia.ciclo
                for ocorrencia in ocorrencias
            )
        )

        padroes.append(
            PadraoRecorrente(
                assinatura=assinatura,
                ocorrencias=tuple(ocorrencias),
                evidencias_distintas=evidencias_distintas,
                ciclos_observados=ciclos_observados,
                frequencia_evidencias=len(
                    evidencias_distintas
                ),
            )
        )

    padroes.sort(
        key=lambda padrao: _chave_assinatura(
            padrao.assinatura
        )
    )

    return ResultadoPadroRecorrente(
        padroes=tuple(padroes),
        total_padroes=len(padroes),
        total_evidencias=len(
            tuple(dict.fromkeys(identidades))
        ),
    )
