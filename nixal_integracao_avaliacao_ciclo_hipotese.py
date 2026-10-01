#!/usr/bin/env python3

"""
NIXAL — INTEGRAÇÃO DA AVALIAÇÃO AO CICLO DA HIPÓTESE

Microetapa 56.4.34

Responsabilidade:
    Receber a hipótese avaliada pela 56.4.33 e registrar formalmente
    sua classificação no ciclo de vida através da integração
    ciclo-memória existente.

Fluxo:
    56.4.33 — hipótese avaliada
             ↓
    56.4.34 — integração da avaliação
             ↓
    56.4.16 — registra_avaliacao(...)
             ↓
    ciclo = suportada / enfraquecida / refutada / inconclusiva

Princípios:
1. A entrada precisa estar no estado "hipotese_avaliada".
2. A avaliação precisa possuir uma classificação reconhecida.
3. O ciclo precisa estar no estado "testada".
4. O resultado avaliado é registrado sem ser transformado em
   conhecimento permanente.
5. O ciclo formal continua responsável pela transição de estado.
6. A persistência continua sendo responsabilidade da 56.4.16.
7. Nenhuma nova avaliação é realizada nesta camada.
8. A arquitetura não é modificada.
9. Nenhuma capacidade é descoberta ou executada.
10. A entrada original permanece isolada por cópia profunda.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_execucao_avaliacao_hipotese import (
    ExecucaoAvaliacaoHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)


class IntegracaoAvaliacaoCicloHipoteseNixal:
    """Integra a avaliação concluída ao ciclo formal e à persistência."""

    FONTE = "integracao_avaliacao_ciclo_hipotese_nixal"

    ESTADOS_AVALIACAO = {
        "suportada",
        "enfraquecida",
        "refutada",
        "inconclusiva",
    }

    def __init__(
        self,
        executor_avaliacao: ExecucaoAvaliacaoHipoteseNixal,
        ciclo_memoria: CicloMemoriaHipoteseNixal,
    ) -> None:
        if not isinstance(
            executor_avaliacao,
            ExecucaoAvaliacaoHipoteseNixal,
        ):
            raise TypeError(
                "executor_avaliacao deve ser uma instância de "
                "ExecucaoAvaliacaoHipoteseNixal"
            )

        if not isinstance(
            ciclo_memoria,
            CicloMemoriaHipoteseNixal,
        ):
            raise TypeError(
                "ciclo_memoria deve ser uma instância de "
                "CicloMemoriaHipoteseNixal"
            )

        self._executor_avaliacao = executor_avaliacao
        self._ciclo_memoria = ciclo_memoria

    def executar(
        self,
        resultado_integracao_teste: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            resultado_integracao_teste,
            dict,
        ):
            return self._negado(
                "Entrada para avaliação inválida."
            )

        if resultado_integracao_teste.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "A integração do teste precisa estar bem-sucedida."
            )

        if resultado_integracao_teste.get(
            "estado"
        ) != "teste_integrado_no_ciclo":
            return self._negado(
                "Somente entradas no estado "
                "'teste_integrado_no_ciclo' podem ser avaliadas."
            )

        resultado_avaliacao = (
            self._executor_avaliacao.executar(
                deepcopy(
                    resultado_integracao_teste
                )
            )
        )

        if not isinstance(
            resultado_avaliacao,
            dict,
        ):
            return self._negado(
                "A execução da avaliação retornou resultado inválido."
            )

        if resultado_avaliacao.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "avaliacao_nao_integrada",
                "origem": self.FONTE,
                "valor": {
                    "resultado_integracao_teste": deepcopy(
                        resultado_integracao_teste
                    ),
                    "resultado_avaliacao": deepcopy(
                        resultado_avaliacao
                    ),
                    "avaliacao_integrada": False,
                    "ciclo_atualizado": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "A avaliação não foi concluída com sucesso."
                ),
            }

        if resultado_avaliacao.get(
            "estado"
        ) != "hipotese_avaliada":
            return {
                "sucesso": True,
                "estado": "avaliacao_nao_integrada",
                "origem": self.FONTE,
                "valor": {
                    "resultado_integracao_teste": deepcopy(
                        resultado_integracao_teste
                    ),
                    "resultado_avaliacao": deepcopy(
                        resultado_avaliacao
                    ),
                    "avaliacao_integrada": False,
                    "ciclo_atualizado": False,
                    "conhecimento_permanente": False,
                },
                "motivo": (
                    "Somente avaliações no estado "
                    "'hipotese_avaliada' podem ser registradas no ciclo."
                ),
            }

        valor_avaliacao = resultado_avaliacao.get(
            "valor"
        )

        if not isinstance(
            valor_avaliacao,
            dict,
        ):
            return self._negado(
                "O resultado da avaliação não possui valor válido."
            )

        if valor_avaliacao.get(
            "hipotese_avaliada"
        ) is not True:
            return self._negado(
                "A avaliação não declara explicitamente a hipótese como avaliada."
            )

        estado_avaliacao = valor_avaliacao.get(
            "estado_avaliacao"
        )

        if estado_avaliacao not in self.ESTADOS_AVALIACAO:
            return self._negado(
                "A avaliação não possui classificação reconhecida."
            )

        if valor_avaliacao.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "A avaliação não pode indicar conhecimento permanente."
            )

        ciclo = self._extrair_ciclo(
            resultado_integracao_teste
        )

        if ciclo is None:
            return self._negado(
                "Não foi possível localizar o ciclo da hipótese."
            )

        if ciclo.get(
            "estado_atual"
        ) != "testada":
            return self._negado(
                "Somente ciclos no estado 'testada' podem receber uma avaliação."
            )

        if ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "O ciclo não pode indicar conhecimento permanente."
            )

        resultado_ciclo = self._ciclo_memoria.registrar_avaliacao(
            {
                "estado": estado_avaliacao,
                "resultado": deepcopy(
                    valor_avaliacao
                ),
            }
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
                "estado": "ciclo_nao_atualizado",
                "origem": self.FONTE,
                "valor": {
                    "resultado_integracao_teste": deepcopy(
                        resultado_integracao_teste
                    ),
                    "resultado_avaliacao": deepcopy(
                        resultado_avaliacao
                    ),
                    "resultado_ciclo": deepcopy(
                        resultado_ciclo
                    ),
                    "avaliacao_integrada": False,
                    "ciclo_atualizado": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "A avaliação foi concluída, mas não pôde ser "
                    "registrada no ciclo."
                ),
            }

        novo_ciclo = resultado_ciclo.get(
            "valor"
        )

        if not isinstance(
            novo_ciclo,
            dict,
        ):
            return self._negado(
                "O ciclo atualizado não possui estrutura válida."
            )

        if novo_ciclo.get(
            "estado_atual"
        ) != estado_avaliacao:
            return self._negado(
                "O ciclo atualizado não alcançou a classificação avaliada."
            )

        if len(
            novo_ciclo.get(
                "avaliacoes",
                [],
            )
        ) < 1:
            return self._negado(
                "O ciclo atualizado não contém registro da avaliação."
            )

        if novo_ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "O ciclo atualizado não pode promover conhecimento permanente."
            )

        return {
            "sucesso": True,
            "estado": "avaliacao_integrada_no_ciclo",
            "origem": self.FONTE,
            "valor": {
                "resultado_integracao_teste": deepcopy(
                    resultado_integracao_teste
                ),
                "resultado_avaliacao": deepcopy(
                    resultado_avaliacao
                ),
                "ciclo_anterior": deepcopy(
                    ciclo
                ),
                "resultado_ciclo": deepcopy(
                    resultado_ciclo
                ),
                "ciclo": deepcopy(
                    novo_ciclo
                ),
                "estado_avaliacao": estado_avaliacao,
                "avaliacao_integrada": True,
                "ciclo_atualizado": True,
                "hipotese_avaliada": True,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "A avaliação da hipótese foi registrada formalmente "
                    "no ciclo. O ciclo agora preserva a classificação "
                    "observada, sem convertê-la em conhecimento permanente."
                ),
            },
        }

    @staticmethod
    def _extrair_ciclo(
        resultado_integracao_teste: dict[str, Any],
    ) -> dict[str, Any] | None:
        valor = resultado_integracao_teste.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return None

        ciclo = valor.get(
            "ciclo"
        )

        if isinstance(
            ciclo,
            dict,
        ):
            return deepcopy(
                ciclo
            )

        return None

    def executar_nova_avaliacao(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoAvaliacaoCicloHipoteseNixal não executa nova avaliação"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoAvaliacaoCicloHipoteseNixal não promove conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoAvaliacaoCicloHipoteseNixal não modifica a arquitetura"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoAvaliacaoCicloHipoteseNixal não executa capacidades"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "integracao_avaliacao_ciclo_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "IntegracaoAvaliacaoCicloHipoteseNixal",
]
