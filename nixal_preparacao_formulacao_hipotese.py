#!/usr/bin/env python3

"""
NIXAL — PREPARAÇÃO PARA FORMULAÇÃO DE HIPÓTESE

Microetapa 56.4.27

Responsabilidade:
    Criar a entrada estruturada para a formulação de hipóteses
    a partir de uma investigação e de suas evidências já
    consolidadas.

Esta camada é uma ponte de integração.

Fluxo:
    investigação contextualizada
             +
    evidências consolidadas
             ↓
    entrada para formulação de hipótese

Princípios:
1. A investigação atual precisa ser fornecida explicitamente.
2. As evidências precisam vir de uma consolidação bem-sucedida.
3. A pergunta, necessidade e tipo são preservados da investigação.
4. As evidências não são inventadas nem alteradas.
5. A consolidação precisa estar marcada como evidência consolidada.
6. Histórico continua separado de evidência atual.
7. Esta camada não formula a hipótese.
8. Esta camada não avalia a hipótese.
9. Esta camada não executa novas capacidades.
10. Esta camada não modifica a arquitetura.
11. Esta camada não promove conhecimento permanente.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class PreparacaoFormulacaoHipoteseNixal:
    """Prepara a entrada exata esperada pela formulação de hipóteses."""

    FONTE = "preparacao_formulacao_hipotese_nixal"

    def preparar(
        self,
        investigacao: dict[str, Any],
        consolidacao: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            investigacao,
            dict,
        ):
            return self._negado(
                "Investigação inválida."
            )

        if not isinstance(
            consolidacao,
            dict,
        ):
            return self._negado(
                "Consolidação inválida."
            )

        pergunta = investigacao.get(
            "pergunta"
        )

        necessidade = investigacao.get(
            "necessidade"
        )

        tipo = investigacao.get(
            "tipo_investigacao"
        )

        if not isinstance(
            pergunta,
            str,
        ) or not pergunta.strip():
            return self._negado(
                "A investigação precisa possuir pergunta válida."
            )

        if not isinstance(
            tipo,
            str,
        ) or not tipo.strip():
            return self._negado(
                "A investigação precisa possuir tipo válido."
            )

        if consolidacao.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "A consolidação precisa estar bem-sucedida."
            )

        if consolidacao.get(
            "estado"
        ) != "evidencias_consolidadas":
            return self._negado(
                "A consolidação precisa estar no estado "
                "'evidencias_consolidadas'."
            )

        valor_consolidacao = consolidacao.get(
            "valor"
        )

        if not isinstance(
            valor_consolidacao,
            dict,
        ):
            return self._negado(
                "A consolidação não possui valor válido."
            )

        if valor_consolidacao.get(
            "evidencia_consolidada"
        ) is not True:
            return self._negado(
                "A consolidação precisa marcar explicitamente "
                "que as evidências foram consolidadas."
            )

        evidencias = valor_consolidacao.get(
            "evidencias"
        )

        if not isinstance(
            evidencias,
            list,
        ):
            return self._negado(
                "As evidências consolidadas precisam ser uma lista."
            )

        if not evidencias:
            return self._negado(
                "Não existem evidências consolidadas para preparar."
            )

        referencias_validas: list[dict[str, Any]] = []

        for indice, evidencia in enumerate(
            evidencias,
            start=1,
        ):
            if not isinstance(
                evidencia,
                dict,
            ):
                return self._negado(
                    f"Evidência consolidada {indice} é inválida."
                )

            fonte = evidencia.get(
                "fonte"
            )

            if not isinstance(
                fonte,
                str,
            ) or not fonte.strip():
                return self._negado(
                    f"Evidência consolidada {indice} não possui fonte."
                )

            referencia = deepcopy(
                evidencia
            )
            referencias_validas.append(
                referencia
            )

        entrada = {
            "necessidade": necessidade,
            "pergunta": pergunta,
            "tipo_investigacao": tipo,
            "investigacao_original": deepcopy(
                investigacao
            ),
            "valor": {
                "evidencias": deepcopy(
                    referencias_validas
                ),
                "origem_evidencias": (
                    "consolidacao_evidencias_nixal"
                ),
                "quantidade_evidencias": len(
                    referencias_validas
                ),
            },
            "historico_consultado": bool(
                investigacao.get(
                    "historico_consultado",
                    False,
                )
            ),
            "historico_encontrado": bool(
                investigacao.get(
                    "historico_encontrado",
                    False,
                )
            ),
            "historico_nao_equivale_a_verdade": True,
            "evidencias_nao_equivalem_a_conhecimento_permanente": True,
        }

        return {
            "sucesso": True,
            "estado": "entrada_formulacao_preparada",
            "origem": self.FONTE,
            "valor": {
                "entrada_formulacao": entrada,
                "investigacao_preservada": deepcopy(
                    investigacao
                ),
                "evidencias_consolidadas": deepcopy(
                    referencias_validas
                ),
                "quantidade_evidencias": len(
                    referencias_validas
                ),
                "pode_formular_hipotese": True,
                "hipotese_formulada": False,
                "hipotese_avaliada": False,
                "conhecimento_permanente": False,
                "interpretacao": (
                    "A entrada foi preparada para a camada de "
                    "formulação de hipóteses. Nenhuma hipótese "
                    "foi formulada nesta etapa; as evidências "
                    "continuam separadas de conhecimento permanente."
                ),
            },
        }

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoFormulacaoHipoteseNixal não formula hipóteses"
        )

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoFormulacaoHipoteseNixal não avalia hipóteses"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoFormulacaoHipoteseNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoFormulacaoHipoteseNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoFormulacaoHipoteseNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "preparacao_formulacao_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "PreparacaoFormulacaoHipoteseNixal",
]
