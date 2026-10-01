#!/usr/bin/env python3

"""
NIXAL — EXECUÇÃO CONTROLADA DO TESTE DE HIPÓTESE

Microetapa 56.4.31

Responsabilidade:
    Receber uma entrada de teste preparada pela 56.4.30 e
    encaminhá-la a um executor de teste explicitamente fornecido.

Fluxo:
    56.4.30 — entrada de teste preparada
             ↓
    56.4.31 — execução controlada
             ↓
    teste_concluido
             ↓
    resultado observado
             ↓
    futuras camadas de ciclo e avaliação

Princípios:
1. A entrada precisa estar no estado "entrada_teste_preparada".
2. O teste precisa estar explicitamente marcado como preparado.
3. O executor do teste é fornecido externamente.
4. Esta camada não inventa resultado.
5. O executor externo deve retornar um resultado estruturado.
6. O resultado é registrado sem classificá-lo como verdade.
7. A classificação suportada/refutada/inconclusiva pertence à avaliação.
8. O ciclo formal pertence à camada de ciclo da hipótese.
9. Conhecimento permanente continua falso.
10. A arquitetura não é modificada.
11. Nenhuma capacidade é escolhida ou descoberta nesta camada.
12. A entrada original permanece isolada por cópia profunda.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class ExecucaoTesteHipoteseNixal:
    """Executa um teste através de um executor explicitamente fornecido."""

    FONTE = "execucao_teste_hipotese_nixal"

    def __init__(
        self,
        testador: Any,
    ) -> None:
        if not hasattr(
            testador,
            "executar",
        ) or not callable(
            testador.executar
        ):
            raise TypeError(
                "testador deve fornecer um método executável chamado 'executar'"
            )

        self._testador = testador

    def executar(
        self,
        entrada_preparada: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            entrada_preparada,
            dict,
        ):
            return self._negado(
                "Entrada de teste preparada inválida."
            )

        if entrada_preparada.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "A entrada de teste precisa estar bem-sucedida."
            )

        if entrada_preparada.get(
            "estado"
        ) != "entrada_teste_preparada":
            return self._negado(
                "Somente entradas no estado "
                "'entrada_teste_preparada' podem ser executadas."
            )

        valor = entrada_preparada.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return self._negado(
                "A entrada preparada não possui valor válido."
            )

        if valor.get(
            "teste_preparado"
        ) is not True:
            return self._negado(
                "A entrada não declara o teste como preparado."
            )

        if valor.get(
            "teste_executado"
        ) is not False:
            return self._negado(
                "O teste já aparece como executado."
            )

        if valor.get(
            "resultado_teste_disponivel"
        ) is not False:
            return self._negado(
                "A entrada já declara um resultado de teste disponível."
            )

        entrada_teste = valor.get(
            "entrada_teste"
        )

        if not isinstance(
            entrada_teste,
            dict,
        ):
            return self._negado(
                "A entrada preparada não contém 'entrada_teste'."
            )

        if entrada_teste.get(
            "estado_hipotese"
        ) != "provisoria":
            return self._negado(
                "Somente hipóteses provisórias podem ser testadas."
            )

        if entrada_teste.get(
            "estado_teste"
        ) != "nao_executado":
            return self._negado(
                "O estado do teste precisa ser 'nao_executado'."
            )

        if entrada_teste.get(
            "teste_executado"
        ) is not False:
            return self._negado(
                "A entrada de teste já indica execução."
            )

        entrada_para_testador = deepcopy(
            entrada_teste
        )

        resultado_teste = self._testador.executar(
            entrada_para_testador
        )

        if not isinstance(
            resultado_teste,
            dict,
        ):
            return self._negado(
                "O executor de teste retornou um resultado inválido."
            )

        if resultado_teste.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "teste_nao_concluido",
                "origem": self.FONTE,
                "valor": {
                    "entrada_preparada": deepcopy(
                        entrada_preparada
                    ),
                    "entrada_teste": deepcopy(
                        entrada_teste
                    ),
                    "resultado_teste": deepcopy(
                        resultado_teste
                    ),
                    "teste_executado": False,
                    "resultado_teste_disponivel": False,
                    "hipotese_avaliada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O executor não concluiu o teste com sucesso."
                ),
            }

        resultado = {
            "estado": "teste_concluido",
            "resultado": deepcopy(
                resultado_teste
            ),
        }

        retorno = {
            "sucesso": True,
            "estado": "teste_concluido",
            "origem": self.FONTE,
            "valor": {
                "entrada_preparada": deepcopy(
                    entrada_preparada
                ),
                "entrada_teste": deepcopy(
                    entrada_teste
                ),
                "resultado_teste": deepcopy(
                    resultado_teste
                ),
                "registro_teste": resultado,
                "teste_preparado": True,
                "teste_executado": True,
                "resultado_teste_disponivel": True,
                "hipotese_avaliada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "O teste foi executado por um executor externo "
                    "explicitamente fornecido e seu resultado foi "
                    "registrado sem avaliação da hipótese."
                ),
            },
        }

        return retorno

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoTesteHipoteseNixal não avalia hipóteses"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoTesteHipoteseNixal não promove conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoTesteHipoteseNixal não modifica a arquitetura"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoTesteHipoteseNixal não executa capacidades internas"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "execucao_teste_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ExecucaoTesteHipoteseNixal",
]
