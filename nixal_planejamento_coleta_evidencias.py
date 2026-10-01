#!/usr/bin/env python3

"""
NIXAL — PLANEJAMENTO DA COLETA DE EVIDÊNCIAS

Microetapa 56.4.24

Responsabilidade:
    Transformar lacunas de investigação já identificadas em um
    plano explícito de coleta de evidências.

Esta camada planeja a investigação.
Ela não executa capacidades, não coleta evidências, não formula
hipóteses e não altera a arquitetura.

Princípios:
1. O plano nasce de lacunas já identificadas.
2. Cada plano mantém a descrição da lacuna de origem.
3. Fontes só podem ser selecionadas dentre as fontes já permitidas
   pela investigação interna.
4. Tipo de investigação desconhecido não recebe fonte inventada.
5. Planejamento não é execução.
6. Histórico continua sendo contexto, não prova automática.
7. A investigação permanece aberta até que evidências reais sejam
   coletadas e avaliadas por etapas posteriores.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


FONTES_AUTORIZADAS_INVESTIGACAO_INTERNA = {
    "listar_arquivos",
    "ler_arquivo",
    "obter_hora",
    "ler_estado_corpo",
    "ler_memoria_corporal",
}


MAPA_FONTES_POR_TIPO: dict[str, list[str]] = {
    "mapeamento_arquitetural": [
        "listar_arquivos",
        "ler_arquivo",
    ],
    "identidade": [
        "ler_estado_corpo",
    ],
    "mapeamento_capacidades": [
        "ler_arquivo",
    ],
    "limites": [
        "ler_arquivo",
    ],
    "seguranca_arquitetural": [
        "ler_arquivo",
    ],
    "integridade": [
        "ler_arquivo",
    ],
}


class PlanejamentoColetaEvidenciasNixal:
    """Cria planos de coleta sem executar a investigação."""

    FONTE = "planejamento_coleta_evidencias_nixal"

    def planejar(
        self,
        analise_lacunas: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            analise_lacunas,
            dict,
        ):
            return self._negado(
                "Análise de lacunas inválida."
            )

        if analise_lacunas.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "A análise de lacunas precisa estar válida."
            )

        valor = analise_lacunas.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return self._negado(
                "A análise de lacunas não possui valor válido."
            )

        lacunas = valor.get(
            "lacunas_abertas"
        )

        if not isinstance(
            lacunas,
            list,
        ):
            return self._negado(
                "As lacunas abertas precisam ser uma lista."
            )

        pergunta = valor.get(
            "pergunta"
        )

        tipo_investigacao = (
            valor.get(
                "investigacao_original",
                {},
            ).get(
                "tipo_investigacao"
            )
            if isinstance(
                valor.get(
                    "investigacao_original"
                ),
                dict,
            )
            else None
        )

        planos: list[dict[str, Any]] = []

        fontes = deepcopy(
            MAPA_FONTES_POR_TIPO.get(
                tipo_investigacao,
                [],
            )
        )

        fontes_validas = [
            fonte
            for fonte in fontes
            if fonte
            in FONTES_AUTORIZADAS_INVESTIGACAO_INTERNA
        ]

        if not lacunas:
            return self._negado(
                "Não existem lacunas abertas para planejar."
            )

        for indice, lacuna in enumerate(
            lacunas,
            start=1,
        ):
            if not isinstance(
                lacuna,
                dict,
            ):
                return self._negado(
                    f"Lacuna inválida na posição {indice}."
                )

            estado_lacuna = lacuna.get(
                "estado"
            )

            if estado_lacuna != "aberta":
                return self._negado(
                    f"A lacuna {indice} não está aberta."
                )

            descricao = lacuna.get(
                "descricao"
            )

            if not isinstance(
                descricao,
                str,
            ) or not descricao.strip():
                return self._negado(
                    f"A lacuna {indice} precisa possuir descrição."
                )

            if fontes_validas:
                estado_plano = "planejada"
                estrategia = (
                    "investigacao_interna_controlada"
                )
            else:
                estado_plano = (
                    "sem_estrategia_declarada"
                )
                estrategia = None

            planos.append(
                {
                    "id": f"plano-{indice}",
                    "estado": estado_plano,
                    "lacuna_origem": deepcopy(
                        lacuna
                    ),
                    "descricao_alvo": descricao,
                    "tipo_investigacao": tipo_investigacao,
                    "pergunta": pergunta,
                    "estrategia": estrategia,
                    "fontes_autorizadas": deepcopy(
                        fontes_validas
                    ),
                    "pode_executar": False,
                    "evidencia_coletada": False,
                }
            )

        investigacao_original = deepcopy(
            valor.get(
                "investigacao_original"
            )
        )

        return {
            "sucesso": True,
            "estado": "plano_coleta_criado",
            "origem": self.FONTE,
            "valor": {
                "investigacao_original": (
                    investigacao_original
                ),
                "pergunta": pergunta,
                "tipo_investigacao": (
                    tipo_investigacao
                ),
                "planos": planos,
                "quantidade_planos": len(
                    planos
                ),
                "planejamento_nao_e_execucao": True,
                "evidencia_ainda_nao_coletada": True,
                "historico_nao_evidencia_automatica": True,
                "interpretacao": (
                    "O plano descreve como a lacuna poderá ser "
                    "investigada usando fontes já autorizadas. "
                    "Nenhuma capacidade foi executada nesta etapa."
                ),
            },
        }

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PlanejamentoColetaEvidenciasNixal não executa capacidades"
        )

    def executar_investigacao(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PlanejamentoColetaEvidenciasNixal não executa investigação"
        )

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PlanejamentoColetaEvidenciasNixal não formula hipóteses"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PlanejamentoColetaEvidenciasNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PlanejamentoColetaEvidenciasNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "planejamento_coleta_evidencias_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "PlanejamentoColetaEvidenciasNixal",
    "FONTES_AUTORIZADAS_INVESTIGACAO_INTERNA",
    "MAPA_FONTES_POR_TIPO",
]
