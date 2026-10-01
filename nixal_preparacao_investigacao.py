#!/usr/bin/env python3

"""
NIXAL — PREPARAÇÃO CONTEXTUAL DA INVESTIGAÇÃO

Microetapa 56.4.22

Responsabilidade:
    Incorporar contexto histórico relevante a uma investigação
    formulada, sem executar a investigação e sem transformar o
    histórico em verdade.

Fluxo:
    investigação formulada
           ↓
    histórico relevante
           ↓
    investigação contextualizada

Princípios:
1. A investigação original é preservada.
2. O contexto histórico é separado da investigação atual.
3. Histórico não é tratado como verdade.
4. Histórico não substitui nova investigação.
5. Ausência de histórico não é tratada como ausência de necessidade.
6. A memória persistida não é modificada.
7. Esta camada não executa capacidades.
8. Esta camada não formula hipóteses.
9. Esta camada não modifica a arquitetura.
10. Esta camada não promove conhecimento permanente.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_contexto_historico_relevante import (
    ContextoHistoricoRelevanteNixal,
)
from nixal_memoria_investigacao import (
    MemoriaInvestigacaoNixal,
)


class PreparacaoInvestigacaoNixal:
    """Prepara uma investigação adicionando contexto histórico explícito."""

    FONTE = "preparacao_investigacao_nixal"

    def __init__(
        self,
        memoria: MemoriaInvestigacaoNixal,
    ) -> None:
        if not isinstance(
            memoria,
            MemoriaInvestigacaoNixal,
        ):
            raise TypeError(
                "memoria deve ser uma instância de "
                "MemoriaInvestigacaoNixal"
            )

        self._contexto = (
            ContextoHistoricoRelevanteNixal(
                memoria
            )
        )

    def preparar(
        self,
        investigacao: dict[str, Any],
        limite_historico: int = 5,
    ) -> dict[str, Any]:
        if not isinstance(
            investigacao,
            dict,
        ):
            return self._negado(
                "Investigação inválida."
            )

        pergunta = investigacao.get(
            "pergunta"
        )

        if not isinstance(
            pergunta,
            str,
        ) or not pergunta.strip():
            return self._negado(
                "A investigação precisa possuir uma pergunta válida."
            )

        if not isinstance(
            limite_historico,
            int,
        ) or isinstance(
            limite_historico,
            bool,
        ):
            return self._negado(
                "Limite histórico precisa ser um inteiro."
            )

        if limite_historico <= 0:
            return self._negado(
                "Limite histórico precisa ser maior que zero."
            )

        necessidade = investigacao.get(
            "necessidade"
        )

        resultado_contexto = (
            self._contexto.analisar(
                necessidade=necessidade,
                hipotese=pergunta,
                limite=limite_historico,
            )
        )

        if resultado_contexto.get(
            "sucesso"
        ) is not True:
            return deepcopy(
                resultado_contexto
            )

        valor_contexto = resultado_contexto.get(
            "valor"
        )

        if not isinstance(
            valor_contexto,
            dict,
        ):
            return self._negado(
                "O contexto histórico retornado é inválido."
            )

        investigacao_original = deepcopy(
            investigacao
        )

        investigacao_contextualizada = deepcopy(
            investigacao
        )

        investigacao_contextualizada[
            "contexto_historico_relevante"
        ] = deepcopy(
            valor_contexto.get(
                "contextos",
                [],
            )
        )

        investigacao_contextualizada[
            "historico_consultado"
        ] = True

        investigacao_contextualizada[
            "historico_encontrado"
        ] = bool(
            valor_contexto.get(
                "historico_encontrado",
                False,
            )
        )

        investigacao_contextualizada[
            "historico_nao_equivale_a_verdade"
        ] = True

        investigacao_contextualizada[
            "historico_nao_substitui_investigacao"
        ] = True

        investigacao_contextualizada[
            "limite_historico_utilizado"
        ] = limite_historico

        return {
            "sucesso": True,
            "estado": "investigacao_contextualizada",
            "origem": self.FONTE,
            "valor": {
                "investigacao_original": investigacao_original,
                "investigacao_contextualizada": (
                    investigacao_contextualizada
                ),
                "contexto_historico_relevante": deepcopy(
                    valor_contexto.get(
                        "contextos",
                        [],
                    )
                ),
                "interpretacao": (
                    "O histórico foi anexado como contexto explícito. "
                    "Ele não determina a verdade da investigação atual "
                    "e não substitui uma nova investigação."
                ),
            },
        }

    def executar_investigacao(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoInvestigacaoNixal não executa investigações"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoInvestigacaoNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoInvestigacaoNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoInvestigacaoNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "preparacao_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "PreparacaoInvestigacaoNixal",
]
