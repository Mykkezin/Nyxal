from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable, Tuple


@dataclass(frozen=True)
class CandidatoAprendizado:
    identidade: str
    estado: str
    assinatura: Tuple[Any, ...]
    ocorrencias: Tuple[Any, ...]
    evidencias_distintas: Tuple[str, ...]
    ciclos_observados: Tuple[Any, ...]
    frequencia_evidencias: int
    justificativa: str


def _atributo(obj: Any, nome: str) -> Any:
    if not hasattr(obj, nome):
        raise ValueError(f"atributo ausente: {nome}")
    return getattr(obj, nome)


def _validar_padrao(padrao: Any) -> None:
    assinatura = _atributo(padrao, "assinatura")
    ocorrencias = _atributo(padrao, "ocorrencias")
    evidencias = _atributo(
        padrao,
        "evidencias_distintas",
    )
    frequencia = _atributo(
        padrao,
        "frequencia_evidencias",
    )

    if not isinstance(assinatura, tuple):
        raise ValueError("assinatura_invalida")

    if not assinatura:
        raise ValueError("assinatura_vazia")

    if not isinstance(ocorrencias, tuple):
        raise ValueError("ocorrencias_invalidas")

    if not ocorrencias:
        raise ValueError("padrao_sem_ocorrencias")

    if not isinstance(evidencias, tuple):
        raise ValueError(
            "evidencias_distintas_invalidas"
        )

    if len(evidencias) < 2:
        raise ValueError(
            "evidencias_distintas_insuficientes"
        )

    if not isinstance(frequencia, int):
        raise ValueError(
            "frequencia_evidencias_invalida"
        )

    if frequencia < 2:
        raise ValueError(
            "frequencia_evidencias_insuficiente"
        )

    if frequencia != len(evidencias):
        raise ValueError(
            "frequencia_incompativel_com_evidencias"
        )


def _material_canonico(
    assinatura: Tuple[Any, ...],
    evidencias: Tuple[str, ...],
    ocorrencias: Tuple[Any, ...],
) -> str:
    partes = [
        repr(assinatura),
        repr(evidencias),
        repr(
            tuple(
                (
                    getattr(
                        ocorrencia,
                        "identidade_evidencia",
                        None,
                    ),
                    getattr(
                        ocorrencia,
                        "ciclo",
                        None,
                    ),
                    getattr(
                        ocorrencia,
                        "posicao",
                        None,
                    ),
                )
                for ocorrencia in ocorrencias
            )
        ),
    ]

    return "|".join(partes)


def _identidade_candidato(
    assinatura: Tuple[Any, ...],
    evidencias: Tuple[str, ...],
    ocorrencias: Tuple[Any, ...],
) -> str:
    material = _material_canonico(
        assinatura,
        evidencias,
        ocorrencias,
    )

    digest = hashlib.sha256(
        material.encode("utf-8")
    ).hexdigest()

    return f"CAND-{digest[:24]}"


def formular(
    padroes: Iterable[Any],
) -> Tuple[CandidatoAprendizado, ...]:
    if isinstance(padroes, (str, bytes)):
        raise ValueError(
            "entrada_nao_iteravel_de_padroes"
        )

    try:
        lista = tuple(padroes)
    except TypeError as exc:
        raise ValueError(
            "entrada_nao_iteravel_de_padroes"
        ) from exc

    if not lista:
        raise ValueError(
            "conjunto_de_padroes_vazio"
        )

    candidatos = []

    for padrao in lista:
        _validar_padrao(padrao)

        assinatura = _atributo(
            padrao,
            "assinatura",
        )

        ocorrencias = _atributo(
            padrao,
            "ocorrencias",
        )

        evidencias = _atributo(
            padrao,
            "evidencias_distintas",
        )

        ciclos = _atributo(
            padrao,
            "ciclos_observados",
        )

        frequencia = _atributo(
            padrao,
            "frequencia_evidencias",
        )

        identidade = _identidade_candidato(
            assinatura,
            evidencias,
            ocorrencias,
        )

        justificativa = (
            "padrão estrutural observado em "
            f"{frequencia} evidências distintas; "
            "candidato não representa aprendizado."
        )

        candidatos.append(
            CandidatoAprendizado(
                identidade=identidade,
                estado="candidato",
                assinatura=assinatura,
                ocorrencias=ocorrencias,
                evidencias_distintas=evidencias,
                ciclos_observados=ciclos,
                frequencia_evidencias=frequencia,
                justificativa=justificativa,
            )
        )

    candidatos.sort(
        key=lambda candidato: candidato.identidade
    )

    return tuple(candidatos)
