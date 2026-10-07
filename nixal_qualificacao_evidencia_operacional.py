from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping, Tuple

from nixal_evidencia_operacional import EvidenciaOperacional
from nixal_normalizador_operacional import RelacaoOperacional


@dataclass(frozen=True)
class QualificacaoEvidencia:
    estado: str
    identidade: str
    motivos: Tuple[str, ...]
    relacoes_verificadas: int
    nos_verificados: int
    ciclos_verificados: int
    evidencias_epistemicas: Mapping[str, int]


@dataclass(frozen=True)
class ResultadoQualificacao:
    sucesso: QualificacaoEvidencia | None = None
    erro: str | None = None

    @property
    def rejeitado(self) -> bool:
        return self.erro is not None


def _contar_relacoes(relacoes):
    autoridades = {}
    tipos = {}
    ciclos = {}
    pares = {}
    nos = {}

    for relacao in relacoes:
        autoridades[relacao.autoridade] = (
            autoridades.get(relacao.autoridade, 0) + 1
        )

        tipos[relacao.tipo] = tipos.get(relacao.tipo, 0) + 1

        ciclos[relacao.ciclo] = ciclos.get(relacao.ciclo, 0) + 1

        par = (relacao.origem, relacao.destino)
        pares[par] = pares.get(par, 0) + 1

        nos[relacao.origem] = None

        if relacao.destino is not None:
            nos[relacao.destino] = None

    return autoridades, tipos, ciclos, pares, nos


def _identidade_esperada(evidencia):
    material = [
        str(evidencia.total_relacoes),
        str(evidencia.total_nos),
        str(evidencia.total_ciclos),
        repr(sorted(evidencia.autoridades.items(), key=repr)),
        repr(sorted(evidencia.tipos.items(), key=repr)),
        repr(sorted(evidencia.relacoes_por_ciclo.items(), key=repr)),
        repr(sorted(evidencia.pares.items(), key=repr)),
        repr(evidencia.relacoes),
    ]

    digest = sha256(
        "\n".join(material).encode("utf-8")
    ).hexdigest()[:24]

    return "EVID-" + digest


def qualificar(
    evidencia: EvidenciaOperacional,
) -> ResultadoQualificacao:

    if not isinstance(evidencia, EvidenciaOperacional):
        return ResultadoQualificacao(
            erro="A entrada deve ser EvidenciaOperacional."
        )

    relacoes = tuple(evidencia.relacoes)

    autoridades, tipos, ciclos, pares, nos = _contar_relacoes(
        relacoes
    )

    erros = []

    # Cardinalidade
    if evidencia.total_relacoes != len(relacoes):
        erros.append("total_relacoes_inconsistente")

    if evidencia.total_nos != len(nos):
        erros.append("total_nos_inconsistente")

    if evidencia.total_ciclos != len(ciclos):
        erros.append("total_ciclos_inconsistente")

    # Distribuições
    if dict(evidencia.autoridades) != autoridades:
        erros.append("autoridades_inconsistentes")

    if dict(evidencia.tipos) != tipos:
        erros.append("tipos_inconsistentes")

    if dict(evidencia.relacoes_por_ciclo) != ciclos:
        erros.append("ciclos_inconsistentes")

    if dict(evidencia.pares) != pares:
        erros.append("pares_inconsistentes")

    # Identidade
    identidade_esperada = _identidade_esperada(evidencia)

    if evidencia.identidade != identidade_esperada:
        erros.append("identidade_inconsistente")

    if erros:
        return ResultadoQualificacao(
            sucesso=QualificacaoEvidencia(
                estado="rejeitada",
                identidade=evidencia.identidade,
                motivos=tuple(erros),
                relacoes_verificadas=len(relacoes),
                nos_verificados=len(nos),
                ciclos_verificados=len(ciclos),
                evidencias_epistemicas=MappingProxyType(
                    dict(autoridades)
                ),
            )
        )

    return ResultadoQualificacao(
        sucesso=QualificacaoEvidencia(
            estado="qualificada",
            identidade=evidencia.identidade,
            motivos=(),
            relacoes_verificadas=len(relacoes),
            nos_verificados=len(nos),
            ciclos_verificados=len(ciclos),
            evidencias_epistemicas=MappingProxyType(
                dict(autoridades)
            ),
        )
    )
