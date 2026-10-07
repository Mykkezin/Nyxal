from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional, Tuple

from nixal_agregador_operacional import GrafoOperacional
from nixal_normalizador_operacional import RelacaoOperacional


@dataclass(frozen=True)
class AnaliseOperacional:
    total_relacoes: int
    total_nos: int
    total_ciclos: int
    relacoes_por_ciclo: Mapping[Optional[str], int]
    autoridades: Mapping[str, int]
    tipos: Mapping[str, int]
    pares: Mapping[Tuple[str, Optional[str]], int]
    relacoes: Tuple[RelacaoOperacional, ...]


@dataclass(frozen=True)
class ResultadoAnalise:
    sucesso: Optional[AnaliseOperacional] = None
    erro: Optional[str] = None

    @property
    def rejeitado(self) -> bool:
        return self.erro is not None


def _contar(valores):
    contagem = {}
    for valor in valores:
        contagem[valor] = contagem.get(valor, 0) + 1
    return MappingProxyType(contagem)


def analisar(grafo: GrafoOperacional) -> ResultadoAnalise:
    if not isinstance(grafo, GrafoOperacional):
        return ResultadoAnalise(
            erro="A entrada deve ser uma instância de GrafoOperacional."
        )

    relacoes = tuple(grafo.relacoes)

    # O8-I1: as relações são somente referenciadas, nunca modificadas.
    autoridades = _contar(r.autoridade for r in relacoes)
    tipos = _contar(r.tipo for r in relacoes)
    relacoes_por_ciclo = _contar(r.ciclo for r in relacoes)

    pares = _contar(
        (r.origem, r.destino)
        for r in relacoes
    )

    resultado = AnaliseOperacional(
        total_relacoes=len(relacoes),
        total_nos=len(grafo.nos),
        total_ciclos=len(grafo.ciclos),
        relacoes_por_ciclo=relacoes_por_ciclo,
        autoridades=autoridades,
        tipos=tipos,
        pares=pares,
        relacoes=relacoes,
    )

    return ResultadoAnalise(sucesso=resultado)


def consultar_par(
    analise: AnaliseOperacional,
    origem: str,
    destino: Optional[str],
) -> Tuple[RelacaoOperacional, ...]:
    if not isinstance(analise, AnaliseOperacional):
        raise TypeError("A análise deve ser AnaliseOperacional.")

    return tuple(
        relacao
        for relacao in analise.relacoes
        if relacao.origem == origem
        and relacao.destino == destino
    )


def consultar_ciclo(
    analise: AnaliseOperacional,
    ciclo: Optional[str],
) -> Tuple[RelacaoOperacional, ...]:
    if not isinstance(analise, AnaliseOperacional):
        raise TypeError("A análise deve ser AnaliseOperacional.")

    return tuple(
        relacao
        for relacao in analise.relacoes
        if relacao.ciclo == ciclo
    )
