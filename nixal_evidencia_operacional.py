from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping, Tuple

from nixal_analise_operacional import AnaliseOperacional
from nixal_normalizador_operacional import RelacaoOperacional


@dataclass(frozen=True)
class EvidenciaOperacional:
    identidade: str
    total_relacoes: int
    total_nos: int
    total_ciclos: int
    autoridades: Mapping[str, int]
    tipos: Mapping[str, int]
    relacoes_por_ciclo: Mapping[object, int]
    pares: Mapping[Tuple[str, object], int]
    relacoes: Tuple[RelacaoOperacional, ...]


@dataclass(frozen=True)
class ResultadoEvidencia:
    sucesso: EvidenciaOperacional | None = None
    erro: str | None = None

    @property
    def rejeitado(self) -> bool:
        return self.erro is not None


def _congelar_mapeamento(mapeamento):
    return MappingProxyType(dict(mapeamento))


def _identidade(
    total_relacoes,
    total_nos,
    total_ciclos,
    autoridades,
    tipos,
    relacoes_por_ciclo,
    pares,
    relacoes,
):
    partes = [
        str(total_relacoes),
        str(total_nos),
        str(total_ciclos),
        repr(sorted(autoridades.items(), key=repr)),
        repr(sorted(tipos.items(), key=repr)),
        repr(sorted(relacoes_por_ciclo.items(), key=repr)),
        repr(sorted(pares.items(), key=repr)),
        repr(relacoes),
    ]

    material = "\n".join(partes).encode("utf-8")

    return "EVID-" + sha256(material).hexdigest()[:24]


def consolidar(analise: AnaliseOperacional) -> ResultadoEvidencia:
    if not isinstance(analise, AnaliseOperacional):
        return ResultadoEvidencia(
            erro="A entrada deve ser uma instância de AnaliseOperacional."
        )

    relacoes = tuple(analise.relacoes)

    identidade = _identidade(
        analise.total_relacoes,
        analise.total_nos,
        analise.total_ciclos,
        analise.autoridades,
        analise.tipos,
        analise.relacoes_por_ciclo,
        analise.pares,
        relacoes,
    )

    evidencia = EvidenciaOperacional(
        identidade=identidade,
        total_relacoes=analise.total_relacoes,
        total_nos=analise.total_nos,
        total_ciclos=analise.total_ciclos,
        autoridades=_congelar_mapeamento(analise.autoridades),
        tipos=_congelar_mapeamento(analise.tipos),
        relacoes_por_ciclo=_congelar_mapeamento(
            analise.relacoes_por_ciclo
        ),
        pares=_congelar_mapeamento(analise.pares),
        relacoes=relacoes,
    )

    return ResultadoEvidencia(sucesso=evidencia)
