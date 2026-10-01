#!/usr/bin/env python3

"""
NIXAL — GATE DE CONSOLIDAÇÃO DE CONHECIMENTO

Responsabilidade:
    Receber um ciclo de hipótese já avaliado e decidir se ele pode
    gerar um candidato a conhecimento.

Nesta primeira versão:
    - somente o estado "suportada" é consolidável;
    - o resultado é apenas um candidato;
    - nenhum conhecimento é gravado;
    - nenhum conhecimento vira permanente;
    - nenhuma modificação arquitetural é realizada.
"""

from __future__ import annotations

from typing import Any


ESTADOS_CONSOLIDAVEIS = {
    "suportada",
}

TIPOS_CONHECIMENTO_PERMITIDOS = {
    "definicao",
    "funcao",
    "origem",
    "teste",
    "resultado",
    "limite",
    "evolucao",
    "estrutura",
    "incerteza",
}


class ConsolidacaoConhecimentoNixal:
    """Gate inicial de consolidação de conhecimento da Nyxal."""

    FONTE = "nixal_consolidacao_conhecimento"
    VERSAO = "1.0"

    @staticmethod
    def consolidar_candidato(
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(ciclo, dict):
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": ConsolidacaoConhecimentoNixal.FONTE,
                "motivo": "Ciclo inválido.",
            }

        estado = ciclo.get("estado_atual")

        if estado not in ESTADOS_CONSOLIDAVEIS:
            return {
                "sucesso": True,
                "estado": "nao_consolidavel",
                "origem": ConsolidacaoConhecimentoNixal.FONTE,
                "motivo": (
                    "Somente hipóteses no estado suportada "
                    "podem gerar candidato nesta primeira versão."
                ),
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            }

        hipotese = ciclo.get("hipotese")

        if not isinstance(hipotese, str) or not hipotese.strip():
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": ConsolidacaoConhecimentoNixal.FONTE,
                "motivo": "O ciclo não possui hipótese textual válida.",
            }

        avaliacoes = ciclo.get("avaliacoes")

        if not isinstance(avaliacoes, list) or not avaliacoes:
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": ConsolidacaoConhecimentoNixal.FONTE,
                "motivo": "O ciclo não possui avaliação registrada.",
            }

        ultima_avaliacao = avaliacoes[-1]

        if not isinstance(ultima_avaliacao, dict):
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": ConsolidacaoConhecimentoNixal.FONTE,
                "motivo": "A última avaliação não é válida.",
            }

        resultado_avaliacao = ultima_avaliacao.get("resultado")

        if not isinstance(resultado_avaliacao, dict):
            return {
                "sucesso": False,
                "estado": "entrada_invalida",
                "origem": ConsolidacaoConhecimentoNixal.FONTE,
                "motivo": "A avaliação não possui resultado estruturado.",
            }

        if resultado_avaliacao.get("estado") != "suportada":
            return {
                "sucesso": True,
                "estado": "nao_consolidavel",
                "origem": ConsolidacaoConhecimentoNixal.FONTE,
                "motivo": "A última avaliação não é suportada.",
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            }

        candidato = {
            "texto": hipotese,
            "tipo": "estrutura",
            "origem": {
                "estado": "suportada",
                "indice_avaliacao": ultima_avaliacao.get("indice"),
            },
            "conhecimento_permanente": False,
            "gravado": False,
        }

        return {
            "sucesso": True,
            "estado": "candidato_conhecimento_criado",
            "origem": ConsolidacaoConhecimentoNixal.FONTE,
            "versao": ConsolidacaoConhecimentoNixal.VERSAO,
            "valor": candidato,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }
