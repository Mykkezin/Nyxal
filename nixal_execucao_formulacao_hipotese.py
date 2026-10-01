#!/usr/bin/env python3

"""
NIXAL — EXECUÇÃO CONTROLADA DA FORMULAÇÃO DE HIPÓTESE

Microetapa 56.4.28

Responsabilidade:
    Receber uma entrada preparada pela 56.4.27 e executar a
    formulação de hipótese exclusivamente através da camada
    FormulacaoHipotesesNixal.

Fluxo:
    evidências consolidadas
             ↓
    56.4.27 — entrada preparada
             ↓
    56.4.28 — formulação controlada
             ↓
    hipótese provisória

Princípios:
1. A entrada precisa estar explicitamente no estado
   "entrada_formulacao_preparada".
2. A camada reutiliza a formulação de hipóteses já existente.
3. A hipótese resultante precisa permanecer provisória.
4. A hipótese não é tratada como verdade.
5. A hipótese não é avaliada nesta camada.
6. A hipótese não é incorporada como conhecimento permanente.
7. A arquitetura não é modificada.
8. Nenhuma capacidade nova é executada aqui.
9. A investigação e as evidências de entrada são preservadas.
10. Resultado "desconhecido" não é promovido artificialmente.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_formulacao_hipoteses import (
    FormulacaoHipotesesNixal,
)


class ExecucaoFormulacaoHipoteseNixal:
    """Executa de forma controlada a formulação de hipótese."""

    FONTE = "execucao_formulacao_hipotese_nixal"

    def __init__(
        self,
        formulador: FormulacaoHipotesesNixal | None = None,
    ) -> None:
        self.formulador = (
            formulador
            if formulador is not None
            else FormulacaoHipotesesNixal()
        )

    def executar(
        self,
        entrada_preparada: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            entrada_preparada,
            dict,
        ):
            return self._negado(
                "Entrada de formulação inválida."
            )

        if entrada_preparada.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "A entrada de formulação precisa estar bem-sucedida."
            )

        if entrada_preparada.get(
            "estado"
        ) != "entrada_formulacao_preparada":
            return self._negado(
                "Somente entradas no estado "
                "'entrada_formulacao_preparada' podem ser executadas."
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

        entrada = valor.get(
            "entrada_formulacao"
        )

        if not isinstance(
            entrada,
            dict,
        ):
            return self._negado(
                "A entrada preparada não contém 'entrada_formulacao'."
            )

        if valor.get(
            "pode_formular_hipotese"
        ) is not True:
            return self._negado(
                "A entrada não autoriza a formulação da hipótese."
            )

        investigacao = deepcopy(
            entrada
        )

        resultado = self.formulador.formular(
            investigacao
        )

        if not isinstance(
            resultado,
            dict,
        ):
            return self._negado(
                "O formulador retornou resultado inválido."
            )

        if resultado.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "falha_formulacao",
                "origem": self.FONTE,
                "valor": {
                    "entrada_preparada": deepcopy(
                        entrada_preparada
                    ),
                    "resultado_formulador": deepcopy(
                        resultado
                    ),
                    "hipotese_formulada": False,
                },
                "motivo": (
                    "A formulação não produziu uma hipótese utilizável."
                ),
            }

        estado_resultado = resultado.get(
            "estado"
        )

        if estado_resultado != "hipotese_provisoria":
            return {
                "sucesso": True,
                "estado": "formulacao_nao_concluida",
                "origem": self.FONTE,
                "valor": {
                    "entrada_preparada": deepcopy(
                        entrada_preparada
                    ),
                    "resultado_formulador": deepcopy(
                        resultado
                    ),
                    "hipotese_formulada": False,
                    "conhecimento_permanente": False,
                },
                "motivo": (
                    "A formulação não atingiu o estado "
                    "'hipotese_provisoria'."
                ),
            }

        hipotese = resultado.get(
            "valor"
        )

        if not isinstance(
            hipotese,
            dict,
        ):
            return self._negado(
                "A hipótese formulada não possui estrutura válida."
            )

        if hipotese.get(
            "estado"
        ) != "provisoria":
            return self._negado(
                "A hipótese formulada não permaneceu provisória."
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

        return {
            "sucesso": True,
            "estado": "hipotese_provisoria_criada",
            "origem": self.FONTE,
            "valor": {
                "entrada_preparada": deepcopy(
                    entrada_preparada
                ),
                "investigacao_utilizada": deepcopy(
                    investigacao
                ),
                "resultado_formulador": deepcopy(
                    resultado
                ),
                "hipotese": deepcopy(
                    hipotese
                ),
                "hipotese_formulada": True,
                "hipotese_avaliada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "Uma hipótese provisória foi criada a partir "
                    "das evidências encaminhadas. Ela ainda precisa "
                    "ser testada e avaliada por camadas posteriores."
                ),
            },
        }

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoFormulacaoHipoteseNixal não avalia hipóteses"
        )

    def testar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoFormulacaoHipoteseNixal não testa hipóteses"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoFormulacaoHipoteseNixal não promove conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoFormulacaoHipoteseNixal não modifica a arquitetura"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoFormulacaoHipoteseNixal não executa capacidades"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "execucao_formulacao_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ExecucaoFormulacaoHipoteseNixal",
]
