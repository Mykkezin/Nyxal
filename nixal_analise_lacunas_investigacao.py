#!/usr/bin/env python3

"""
NIXAL — ANÁLISE DE LACUNAS DA INVESTIGAÇÃO

Microetapa 56.4.23

Responsabilidade:
    Receber uma investigação já contextualizada e identificar,
    de forma estrutural, quais informações ainda precisam ser
    obtidas para responder à pergunta.

Esta camada não executa investigação, não interpreta evidências,
não confirma hipóteses e não encerra a investigação.

Princípios:
1. A investigação contextualizada é preservada.
2. A pergunta original é preservada.
3. A necessidade original é preservada.
4. A evidência necessária é tratada como requisito de investigação,
   não como evidência já obtida.
5. Histórico não fecha lacunas.
6. Ausência de histórico não elimina lacunas.
7. Uma lacuna estrutural não é uma conclusão sobre a realidade.
8. Esta camada não executa capacidades.
9. Esta camada não formula hipóteses.
10. Esta camada não modifica a arquitetura.
11. Esta camada não promove conhecimento permanente.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class AnaliseLacunasInvestigacaoNixal:
    """Identifica lacunas estruturais ainda abertas na investigação."""

    FONTE = "analise_lacunas_investigacao_nixal"

    def analisar(
        self,
        investigacao: dict[str, Any],
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

        evidencia_necessaria = investigacao.get(
            "evidencia_necessaria"
        )

        if not isinstance(
            evidencia_necessaria,
            str,
        ) or not evidencia_necessaria.strip():
            return self._negado(
                "A investigação precisa declarar a evidência necessária."
            )

        investigacao_original = deepcopy(
            investigacao
        )

        contexto_historico = investigacao.get(
            "contexto_historico_relevante",
            [],
        )

        if contexto_historico is None:
            contexto_historico = []

        if not isinstance(
            contexto_historico,
            list,
        ):
            return self._negado(
                "O contexto histórico relevante precisa ser uma lista."
            )

        lacunas = [
            {
                "tipo": "evidencia_necessaria",
                "estado": "aberta",
                "descricao": evidencia_necessaria,
                "origem": "investigacao_atual",
            }
        ]

        historico_encontrado = bool(
            investigacao.get(
                "historico_encontrado",
                False,
            )
        )

        contexto_disponivel = len(
            contexto_historico
        ) > 0

        return {
            "sucesso": True,
            "estado": "lacunas_identificadas",
            "origem": self.FONTE,
            "valor": {
                "investigacao_original": investigacao_original,
                "investigacao_permanece_aberta": True,
                "investigacao_necessaria": True,
                "pergunta": pergunta,
                "necessidade": investigacao.get(
                    "necessidade"
                ),
                "evidencia_necessaria": evidencia_necessaria,
                "lacunas_abertas": deepcopy(
                    lacunas
                ),
                "quantidade_lacunas": len(
                    lacunas
                ),
                "historico_consultado": bool(
                    investigacao.get(
                        "historico_consultado",
                        False,
                    )
                ),
                "historico_encontrado": historico_encontrado,
                "contexto_historico_disponivel": (
                    contexto_disponivel
                ),
                "historico_nao_fecha_lacunas": True,
                "interpretacao": (
                    "A lacuna foi identificada a partir do requisito "
                    "de evidência da investigação atual. O histórico "
                    "serve como contexto e não é tratado como prova "
                    "suficiente para fechar a lacuna."
                ),
            },
        }

    def executar_investigacao(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "AnaliseLacunasInvestigacaoNixal não executa investigação"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "AnaliseLacunasInvestigacaoNixal não executa capacidades"
        )

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "AnaliseLacunasInvestigacaoNixal não formula hipóteses"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "AnaliseLacunasInvestigacaoNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "AnaliseLacunasInvestigacaoNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "analise_lacunas_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "AnaliseLacunasInvestigacaoNixal",
]
