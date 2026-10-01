#!/usr/bin/env python3

"""
NIXAL — EXECUÇÃO CONTROLADA DO PLANO DE INVESTIGAÇÃO

Microetapa 56.4.25

Responsabilidade:
    Receber um plano de coleta previamente criado e executar,
    de forma controlada, apenas a investigação correspondente.

Fluxo:
    análise de lacunas
           ↓
    plano de coleta
           ↓
    execução controlada
           ↓
    evidências coletadas

Esta camada faz a ponte entre planejamento e coleta real.

Princípios:
1. O plano precisa existir e estar no estado "planejada".
2. A execução precisa ser explicitamente permitida pelo plano.
3. A investigação executada precisa corresponder ao tipo declarado.
4. As fontes retornadas precisam pertencer às fontes autorizadas pelo plano.
5. O plano original não é alterado.
6. Evidência coletada não vira hipótese automaticamente.
7. Evidência coletada não vira conhecimento permanente automaticamente.
8. Esta camada não modifica a arquitetura.
9. Esta camada não promove conhecimento permanente.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_investigacao_interna import (
    InvestigacaoInternaNixal,
)


class ExecucaoPlanoInvestigacaoNixal:
    """Executa um plano de coleta de forma controlada."""

    FONTE = "execucao_plano_investigacao_nixal"

    def __init__(
        self,
        investigador: InvestigacaoInternaNixal | None = None,
    ) -> None:
        self.investigador = (
            investigador
            if investigador is not None
            else InvestigacaoInternaNixal()
        )

    def executar(
        self,
        plano: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            plano,
            dict,
        ):
            return self._negado(
                "Plano inválido."
            )

        if plano.get(
            "estado"
        ) != "planejada":
            return self._negado(
                "Somente planos no estado 'planejada' podem ser executados."
            )

        if plano.get(
            "pode_executar"
        ) is not False:
            return self._negado(
                "O plano precisa declarar explicitamente que a execução será controlada por esta camada."
            )

        tipo = plano.get(
            "tipo_investigacao"
        )

        pergunta = plano.get(
            "pergunta"
        )

        fontes_autorizadas = plano.get(
            "fontes_autorizadas",
            [],
        )

        if not isinstance(
            fontes_autorizadas,
            list,
        ):
            return self._negado(
                "As fontes autorizadas precisam ser uma lista."
            )

        if not isinstance(
            tipo,
            str,
        ) or not tipo.strip():
            return self._negado(
                "O plano precisa declarar o tipo da investigação."
            )

        if not isinstance(
            pergunta,
            str,
        ) or not pergunta.strip():
            return self._negado(
                "O plano precisa declarar a pergunta da investigação."
            )

        investigacao = {
            "pergunta": pergunta,
            "tipo_investigacao": tipo,
        }

        resultado = self.investigador.executar(
            investigacao
        )

        if not isinstance(
            resultado,
            dict,
        ):
            return self._negado(
                "O investigador retornou um resultado inválido."
            )

        if resultado.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "falha_execucao",
                "origem": self.FONTE,
                "valor": {
                    "plano": deepcopy(
                        plano
                    ),
                    "resultado_investigacao": deepcopy(
                        resultado
                    ),
                    "evidencia_coletada": False,
                },
                "motivo": (
                    "A investigação não conseguiu produzir "
                    "um resultado válido."
                ),
            }

        valor_investigacao = resultado.get(
            "valor",
            {},
        )

        if not isinstance(
            valor_investigacao,
            dict,
        ):
            return self._negado(
                "O resultado da investigação não possui valor válido."
            )

        fontes_utilizadas = valor_investigacao.get(
            "fontes_utilizadas",
            [],
        )

        if not isinstance(
            fontes_utilizadas,
            list,
        ):
            return self._negado(
                "As fontes utilizadas precisam ser uma lista."
            )

        fontes_nao_autorizadas = [
            fonte
            for fonte in fontes_utilizadas
            if fonte not in fontes_autorizadas
        ]

        if fontes_nao_autorizadas:
            return self._negado(
                "A investigação utilizou fonte não autorizada "
                "pelo plano: "
                + ", ".join(
                    map(
                        str,
                        fontes_nao_autorizadas,
                    )
                )
            )

        evidencias = valor_investigacao.get(
            "evidencias",
            [],
        )

        if not isinstance(
            evidencias,
            list,
        ):
            return self._negado(
                "As evidências retornadas precisam ser uma lista."
            )

        return {
            "sucesso": True,
            "estado": "plano_executado",
            "origem": self.FONTE,
            "valor": {
                "plano": deepcopy(
                    plano
                ),
                "resultado_investigacao": deepcopy(
                    resultado
                ),
                "fontes_utilizadas": deepcopy(
                    fontes_utilizadas
                ),
                "evidencias": deepcopy(
                    evidencias
                ),
                "quantidade_evidencias": len(
                    evidencias
                ),
                "evidencia_coletada": bool(
                    evidencias
                ),
                "hipotese_formulada": False,
                "conhecimento_permanente_promovido": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "O plano foi executado por meio da investigação "
                    "interna controlada. As evidências permanecem "
                    "evidências da investigação e ainda não são "
                    "hipótese ou conhecimento permanente."
                ),
            },
        }

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoPlanoInvestigacaoNixal não formula hipóteses"
        )

    def incorporar_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoPlanoInvestigacaoNixal não incorpora conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoPlanoInvestigacaoNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoPlanoInvestigacaoNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "execucao_plano_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ExecucaoPlanoInvestigacaoNixal",
]
