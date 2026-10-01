#!/usr/bin/env python3

"""
NIXAL — PREPARAÇÃO CONTROLADA DO TESTE DE HIPÓTESE

Microetapa 56.4.30

Responsabilidade:
    Receber uma hipótese já integrada ao ciclo formal e preparar
    uma entrada explícita para uma camada posterior de execução
    de teste.

Fluxo:
    56.4.29 — hipótese integrada no ciclo
             ↓
    56.4.30 — preparação do teste
             ↓
    entrada de teste preparada
             ↓
    futura execução do teste

Princípios:
1. A entrada precisa representar uma hipótese integrada no ciclo.
2. A hipótese precisa estar no estado "provisoria".
3. Esta camada não executa o teste.
4. Esta camada não inventa resultado de teste.
5. Esta camada não inventa evidências.
6. O resultado do teste permanece ausente até execução posterior.
7. A hipótese não é avaliada nesta camada.
8. Conhecimento permanente continua falso.
9. A arquitetura não é modificada.
10. Nenhuma capacidade é executada.
11. A entrada original permanece isolada por cópia profunda.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class PreparacaoTesteHipoteseNixal:
    """Prepara uma hipótese provisória para futura execução de teste."""

    FONTE = "preparacao_teste_hipotese_nixal"

    def preparar(
        self,
        resultado_integracao: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            resultado_integracao,
            dict,
        ):
            return self._negado(
                "Resultado de integração inválido."
            )

        if resultado_integracao.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "A integração da hipótese precisa estar bem-sucedida."
            )

        if resultado_integracao.get(
            "estado"
        ) != "hipotese_integrada_no_ciclo":
            return self._negado(
                "Somente hipóteses no estado "
                "'hipotese_integrada_no_ciclo' podem ser preparadas."
            )

        valor = resultado_integracao.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return self._negado(
                "O resultado da integração não possui valor válido."
            )

        if valor.get(
            "hipotese_integrada"
        ) is not True:
            return self._negado(
                "A entrada não declara a hipótese como integrada."
            )

        if valor.get(
            "ciclo_iniciado"
        ) is not True:
            return self._negado(
                "A entrada não declara o ciclo como iniciado."
            )

        ciclo = valor.get(
            "ciclo"
        )

        if not isinstance(
            ciclo,
            dict,
        ):
            return self._negado(
                "O resultado integrado não contém ciclo válido."
            )

        if ciclo.get(
            "estado_atual"
        ) != "provisoria":
            return self._negado(
                "Somente ciclos no estado 'provisoria' podem ser "
                "preparados para teste."
            )

        if ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "O ciclo não pode indicar conhecimento permanente."
            )

        hipotese = valor.get(
            "hipotese"
        )

        if not isinstance(
            hipotese,
            dict,
        ):
            return self._negado(
                "A entrada integrada não contém hipótese válida."
            )

        if hipotese.get(
            "estado"
        ) != "provisoria":
            return self._negado(
                "A hipótese precisa permanecer provisória."
            )

        if hipotese.get(
            "confirmada"
        ) is not False:
            return self._negado(
                "A hipótese não pode aparecer como confirmada."
            )

        if hipotese.get(
            "testada"
        ) is not False:
            return self._negado(
                "A hipótese não pode aparecer como já testada."
            )

        entrada_teste = {
            "hipotese": deepcopy(
                hipotese
            ),
            "necessidade": hipotese.get(
                "necessidade"
            ),
            "pergunta": hipotese.get(
                "pergunta"
            ),
            "estado_hipotese": "provisoria",
            "estado_teste": "nao_executado",
            "pode_executar_teste": False,
            "teste_executado": False,
            "resultado_teste": None,
            "evidencias_do_teste": [],
            "suporte": None,
            "contraria": None,
            "inconclusivo": None,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

        return {
            "sucesso": True,
            "estado": "entrada_teste_preparada",
            "origem": self.FONTE,
            "valor": {
                "resultado_integracao": deepcopy(
                    resultado_integracao
                ),
                "ciclo": deepcopy(
                    ciclo
                ),
                "entrada_teste": entrada_teste,
                "teste_preparado": True,
                "teste_executado": False,
                "resultado_teste_disponivel": False,
                "hipotese_avaliada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "A hipótese provisória foi preparada para um "
                    "teste posterior. Nenhum teste foi executado e "
                    "nenhum resultado ou evidência de teste foi inventado."
                ),
            },
        }

    def executar_teste(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoTesteHipoteseNixal não executa testes"
        )

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoTesteHipoteseNixal não avalia hipóteses"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoTesteHipoteseNixal não promove conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoTesteHipoteseNixal não modifica a arquitetura"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "PreparacaoTesteHipoteseNixal não executa capacidades"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "preparacao_teste_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "PreparacaoTesteHipoteseNixal",
]
