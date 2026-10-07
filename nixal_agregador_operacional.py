import datetime
from types import MappingProxyType
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Union, Mapping

from nixal_normalizador_operacional import RelacaoOperacional


@dataclass(frozen=True)
class RejeicaoAgregacao:
    """Estrutura imutável representando a falha de validação da entrada."""
    motivo: str
    regra_violada: str
    indice_falha: Optional[int] = None


@dataclass(frozen=True)
class GrafoOperacional:
    """Estrutura imutável representando a topologia operacional do ciclo."""
    nos: Tuple[str, ...]
    relacoes: Tuple[RelacaoOperacional, ...]
    ciclos: Mapping[Optional[str], Tuple[RelacaoOperacional, ...]]
    metadados: Mapping[str, Union[str, int]]


@dataclass(frozen=True)
class ResultadoAgregacao:
    """Invólucro determinístico e imutável de retorno (Sucesso ou Falha)."""
    sucesso: Optional[GrafoOperacional] = None
    rejeicao: Optional[RejeicaoAgregacao] = None

    @property
    def rejeitado(self) -> bool:
        return self.rejeicao is not None


def agregar(relacoes: List[RelacaoOperacional]) -> ResultadoAgregacao:
    """
    Constrói a topologia operacional a partir de relações validadas.
    Cumpre os invariantes O7.1 (Entrada Exclusiva) e O7-I1 (Conservação).
    """
    if not isinstance(relacoes, list):
        return ResultadoAgregacao(
            rejeicao=RejeicaoAgregacao(
                motivo="A entrada deve ser uma lista rigorosa.",
                regra_violada="O7.1 - Entrada Exclusiva",
            )
        )

    nos_unicos_dict = {}
    ciclos_dict: Dict[Optional[str], List[RelacaoOperacional]] = {}

    for idx, relacao in enumerate(relacoes):
        if not isinstance(relacao, RelacaoOperacional):
            return ResultadoAgregacao(
                rejeicao=RejeicaoAgregacao(
                    motivo=(
                        f"O elemento no índice {idx} não é uma instância "
                        "validada de RelacaoOperacional."
                    ),
                    regra_violada="O7.1 - Entrada Exclusiva",
                    indice_falha=idx,
                )
            )

        if relacao.autoridade == "arquitetural":
            return ResultadoAgregacao(
                rejeicao=RejeicaoAgregacao(
                    motivo="Autoridade arquitetural não é permitida no O7.",
                    regra_violada="O7-I2 - Conservação Epistemológica",
                    indice_falha=idx,
                )
            )

        nos_unicos_dict[relacao.origem] = None

        if relacao.destino is not None:
            nos_unicos_dict[relacao.destino] = None

        chave_ciclo = relacao.ciclo

        if chave_ciclo not in ciclos_dict:
            ciclos_dict[chave_ciclo] = []

        ciclos_dict[chave_ciclo].append(relacao)

    ciclos_imutaveis = {
        chave: tuple(relacoes_ciclo)
        for chave, relacoes_ciclo in ciclos_dict.items()
    }

    tupla_relacoes = tuple(relacoes)
    tupla_nos = tuple(nos_unicos_dict.keys())

    metadados = {
        "instante_agregacao": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "total_relacoes": len(tupla_relacoes),
        "total_nos": len(tupla_nos),
        "total_ciclos": len(ciclos_imutaveis),
    }

    grafo = GrafoOperacional(
        nos=tupla_nos,
        relacoes=tupla_relacoes,
        ciclos=MappingProxyType(ciclos_imutaveis),
        metadados=MappingProxyType(metadados),
    )

    return ResultadoAgregacao(sucesso=grafo)
