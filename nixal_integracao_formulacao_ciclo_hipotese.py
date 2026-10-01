#!/usr/bin/env python3

"""
NIXAL — INTEGRAÇÃO DA FORMULAÇÃO COM O CICLO DA HIPÓTESE

Microetapa 56.4.29

Responsabilidade:
    Conectar a hipótese provisória produzida pela 56.4.28 ao
    ciclo formal de vida da hipótese, usando a integração já
    existente entre ciclo e memória da 56.4.16.

Fluxo:
    56.4.28 — hipótese provisória criada
             ↓
    56.4.29 — valida e inicia ciclo formal
             ↓
    56.4.16 — persiste estado do ciclo
             ↓
    hipótese em ciclo "provisoria"

Princípios:
1. A entrada precisa ser uma hipótese provisória produzida pela 56.4.28.
2. A entrada é validada antes de qualquer execução downstream.
3. Esta camada não reformula a hipótese.
4. O ciclo formal continua responsável pelas transições.
5. A persistência continua sendo responsabilidade da 56.4.16.
6. Esta camada apenas coordena as responsabilidades existentes.
7. A hipótese continua sendo provisória.
8. A hipótese não é testada nem avaliada aqui.
9. Conhecimento permanente continua falso.
10. A arquitetura não é modificada.
11. Nenhuma capacidade é executada.
12. A entrada original permanece isolada por cópia profunda.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_execucao_formulacao_hipotese import (
    ExecucaoFormulacaoHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)


class IntegracaoFormulacaoCicloHipoteseNixal:
    """Integra a hipótese formulada ao ciclo formal e à persistência."""

    FONTE = "integracao_formulacao_ciclo_hipotese_nixal"

    def __init__(
        self,
        executor_formulacao: ExecucaoFormulacaoHipoteseNixal,
        ciclo_memoria: CicloMemoriaHipoteseNixal,
    ) -> None:
        if not isinstance(
            executor_formulacao,
            ExecucaoFormulacaoHipoteseNixal,
        ):
            raise TypeError(
                "executor_formulacao deve ser uma instância de "
                "ExecucaoFormulacaoHipoteseNixal"
            )

        if not isinstance(
            ciclo_memoria,
            CicloMemoriaHipoteseNixal,
        ):
            raise TypeError(
                "ciclo_memoria deve ser uma instância de "
                "CicloMemoriaHipoteseNixal"
            )

        self._executor_formulacao = executor_formulacao
        self._ciclo_memoria = ciclo_memoria

    def executar(
        self,
        entrada_preparada: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            entrada_preparada,
            dict,
        ):
            return self._negado(
                "Entrada preparada inválida."
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
                "'entrada_formulacao_preparada' podem ser integradas."
            )

        resultado_formulacao = (
            self._executor_formulacao.executar(
                deepcopy(entrada_preparada)
            )
        )

        if not isinstance(
            resultado_formulacao,
            dict,
        ):
            return self._negado(
                "A execução da formulação retornou resultado inválido."
            )

        if resultado_formulacao.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "formulacao_nao_integrada",
                "origem": self.FONTE,
                "valor": {
                    "resultado_formulacao": deepcopy(
                        resultado_formulacao
                    ),
                    "ciclo_iniciado": False,
                    "hipotese_integrada": False,
                },
                "motivo": (
                    "A hipótese não foi formulada com sucesso."
                ),
            }

        if resultado_formulacao.get(
            "estado"
        ) != "hipotese_provisoria_criada":
            return {
                "sucesso": True,
                "estado": "formulacao_nao_integrada",
                "origem": self.FONTE,
                "valor": {
                    "resultado_formulacao": deepcopy(
                        resultado_formulacao
                    ),
                    "ciclo_iniciado": False,
                    "hipotese_integrada": False,
                    "conhecimento_permanente": False,
                },
                "motivo": (
                    "Somente uma hipótese no estado "
                    "'hipotese_provisoria_criada' pode iniciar o ciclo."
                ),
            }

        valor_formulacao = resultado_formulacao.get(
            "valor"
        )

        if not isinstance(
            valor_formulacao,
            dict,
        ):
            return self._negado(
                "O resultado da formulação não possui valor válido."
            )

        hipotese = valor_formulacao.get(
            "hipotese"
        )

        if not isinstance(
            hipotese,
            dict,
        ):
            return self._negado(
                "O resultado da formulação não contém hipótese válida."
            )

        if hipotese.get(
            "estado"
        ) != "provisoria":
            return self._negado(
                "A hipótese recebida não está provisória."
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

        resultado_ciclo = self._ciclo_memoria.iniciar(
            deepcopy(hipotese)
        )

        if not isinstance(
            resultado_ciclo,
            dict,
        ):
            return self._negado(
                "A integração ciclo-memória retornou resultado inválido."
            )

        if resultado_ciclo.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "ciclo_nao_iniciado",
                "origem": self.FONTE,
                "valor": {
                    "resultado_formulacao": deepcopy(
                        resultado_formulacao
                    ),
                    "resultado_ciclo": deepcopy(
                        resultado_ciclo
                    ),
                    "ciclo_iniciado": False,
                    "hipotese_integrada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O ciclo da hipótese não pôde ser iniciado."
                ),
            }

        ciclo = resultado_ciclo.get(
            "valor"
        )

        if not isinstance(
            ciclo,
            dict,
        ):
            return self._negado(
                "O ciclo iniciado não possui estrutura válida."
            )

        if ciclo.get(
            "estado_atual"
        ) != "provisoria":
            return self._negado(
                "O ciclo iniciado não permaneceu no estado provisório."
            )

        if ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "O ciclo não pode promover conhecimento permanente."
            )

        return {
            "sucesso": True,
            "estado": "hipotese_integrada_no_ciclo",
            "origem": self.FONTE,
            "valor": {
                "entrada_preparada": deepcopy(
                    entrada_preparada
                ),
                "resultado_formulacao": deepcopy(
                    resultado_formulacao
                ),
                "resultado_ciclo": deepcopy(
                    resultado_ciclo
                ),
                "hipotese": deepcopy(
                    hipotese
                ),
                "ciclo": deepcopy(
                    ciclo
                ),
                "hipotese_formulada": True,
                "ciclo_iniciado": True,
                "hipotese_integrada": True,
                "hipotese_testada": False,
                "hipotese_avaliada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "A hipótese provisória foi integrada ao ciclo formal "
                    "de vida e seu estado inicial foi persistido pela "
                    "integração ciclo-memória."
                ),
            },
        }

    def testar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoFormulacaoCicloHipoteseNixal não testa hipóteses"
        )

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoFormulacaoCicloHipoteseNixal não avalia hipóteses"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoFormulacaoCicloHipoteseNixal não promove "
            "conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoFormulacaoCicloHipoteseNixal não modifica a arquitetura"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoFormulacaoCicloHipoteseNixal não executa capacidades"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "integracao_formulacao_ciclo_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "IntegracaoFormulacaoCicloHipoteseNixal",
]
