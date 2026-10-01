#!/usr/bin/env python3

"""
NIXAL — INTEGRAÇÃO DO RESULTADO DO TESTE AO CICLO

Microetapa 56.4.32

Responsabilidade:
    Receber uma entrada de teste preparada, executar o teste através
    da 56.4.31 e registrar o resultado no ciclo formal através da
    integração ciclo-memória da 56.4.16.

Contrato real da 56.4.16:
    CicloMemoriaHipoteseNixal.registrar_teste(resultado_teste)

A instância de CicloMemoriaHipoteseNixal mantém internamente o ciclo
atual. Portanto, esta camada valida o ciclo recebido na entrada contra
o ciclo interno antes de registrar o resultado.

Princípios:
1. A entrada precisa estar no estado "entrada_teste_preparada".
2. O teste precisa estar explicitamente preparado.
3. O executor do teste é fornecido pela 56.4.31.
4. Esta camada não avalia o resultado.
5. Esta camada não decide suporte, refutação ou inconclusão.
6. O ciclo formal continua responsável pela transição para "testada".
7. A persistência continua sendo responsabilidade da 56.4.16.
8. Nenhum conhecimento permanente é criado.
9. A arquitetura não é modificada.
10. Nenhuma capacidade é descoberta ou executada nesta camada.
11. A entrada original permanece isolada por cópia profunda.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_execucao_teste_hipotese import (
    ExecucaoTesteHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)


class IntegracaoTesteCicloHipoteseNixal:
    """Integra o resultado do teste ao ciclo formal e à persistência."""

    FONTE = "integracao_teste_ciclo_hipotese_nixal"

    def __init__(
        self,
        executor_teste: ExecucaoTesteHipoteseNixal,
        ciclo_memoria: CicloMemoriaHipoteseNixal,
    ) -> None:
        if not isinstance(
            executor_teste,
            ExecucaoTesteHipoteseNixal,
        ):
            raise TypeError(
                "executor_teste deve ser uma instância de "
                "ExecucaoTesteHipoteseNixal"
            )

        if not isinstance(
            ciclo_memoria,
            CicloMemoriaHipoteseNixal,
        ):
            raise TypeError(
                "ciclo_memoria deve ser uma instância de "
                "CicloMemoriaHipoteseNixal"
            )

        self._executor_teste = executor_teste
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
                "A entrada de teste precisa estar bem-sucedida."
            )

        if entrada_preparada.get(
            "estado"
        ) != "entrada_teste_preparada":
            return self._negado(
                "Somente entradas no estado "
                "'entrada_teste_preparada' podem iniciar esta integração."
            )

        resultado_teste = self._executor_teste.executar(
            deepcopy(
                entrada_preparada
            )
        )

        if not isinstance(
            resultado_teste,
            dict,
        ):
            return self._negado(
                "A execução do teste retornou resultado inválido."
            )

        if resultado_teste.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "teste_nao_integrado",
                "origem": self.FONTE,
                "valor": {
                    "entrada_preparada": deepcopy(
                        entrada_preparada
                    ),
                    "resultado_teste": deepcopy(
                        resultado_teste
                    ),
                    "ciclo_atualizado": False,
                    "teste_integrado": False,
                    "hipotese_avaliada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O teste não foi concluído com sucesso e, "
                    "portanto, não foi integrado ao ciclo."
                ),
            }

        if resultado_teste.get(
            "estado"
        ) != "teste_concluido":
            return {
                "sucesso": True,
                "estado": "teste_nao_integrado",
                "origem": self.FONTE,
                "valor": {
                    "entrada_preparada": deepcopy(
                        entrada_preparada
                    ),
                    "resultado_teste": deepcopy(
                        resultado_teste
                    ),
                    "ciclo_atualizado": False,
                    "teste_integrado": False,
                    "hipotese_avaliada": False,
                    "conhecimento_permanente": False,
                },
                "motivo": (
                    "Somente resultados no estado "
                    "'teste_concluido' podem ser registrados no ciclo."
                ),
            }

        valor_teste = resultado_teste.get(
            "valor"
        )

        if not isinstance(
            valor_teste,
            dict,
        ):
            return self._negado(
                "O resultado do teste não possui valor válido."
            )

        if valor_teste.get(
            "teste_executado"
        ) is not True:
            return self._negado(
                "O resultado não declara explicitamente que o teste foi executado."
            )

        if valor_teste.get(
            "resultado_teste_disponivel"
        ) is not True:
            return self._negado(
                "O resultado não declara explicitamente que o resultado está disponível."
            )

        ciclo = self._extrair_ciclo(
            entrada_preparada
        )

        if ciclo is None:
            return self._negado(
                "Não foi possível localizar o ciclo da hipótese na entrada de teste."
            )

        entrada_valor = entrada_preparada.get(
            "valor"
        )

        if not isinstance(
            entrada_valor,
            dict,
        ):
            return self._negado(
                "A entrada preparada não possui valor válido."
            )

        entrada_teste = entrada_valor.get(
            "entrada_teste"
        )

        if not isinstance(
            entrada_teste,
            dict,
        ):
            return self._negado(
                "A entrada preparada não contém 'entrada_teste' válido."
            )

        hipotese = entrada_teste.get(
            "hipotese"
        )

        if not isinstance(
            hipotese,
            dict,
        ):
            return self._negado(
                "A entrada de teste não contém hipótese estruturada."
            )

        if hipotese.get(
            "estado"
        ) != "provisoria":
            return self._negado(
                "A hipótese encaminhada ao ciclo precisa permanecer provisória."
            )

        if hipotese.get(
            "confirmada"
        ) is not False:
            return self._negado(
                "A hipótese encaminhada não pode aparecer como confirmada."
            )

        if hipotese.get(
            "testada"
        ) is not False:
            return self._negado(
                "A hipótese encaminhada não pode aparecer como já testada."
            )

        if ciclo.get(
            "estado_atual"
        ) != "provisoria":
            return self._negado(
                "Somente ciclos provisórios podem receber o registro inicial do teste."
            )

        if ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "O ciclo não pode indicar conhecimento permanente."
            )

        ciclo_atual = self._ciclo_memoria.obter_ciclo()

        if not isinstance(
            ciclo_atual,
            dict,
        ):
            return self._negado(
                "A memória do ciclo não possui um ciclo atual definido."
            )

        if ciclo_atual != ciclo:
            return self._negado(
                "O ciclo da entrada diverge do ciclo atualmente mantido "
                "pela integração ciclo-memória."
            )

        resultado_observado = valor_teste.get(
            "resultado_teste"
        )

        if not isinstance(
            resultado_observado,
            dict,
        ):
            return self._negado(
                "O resultado observado do teste precisa ser estruturado."
            )

        resultado_registro = {
            "estado": "teste_concluido",
            "resultado": deepcopy(
                resultado_observado
            ),
        }

        # Contrato real da 56.4.16:
        # registrar_teste(resultado_teste)
        resultado_ciclo = self._ciclo_memoria.registrar_teste(
            deepcopy(
                resultado_registro
            )
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
                    "entrada_preparada": deepcopy(
                        entrada_preparada
                    ),
                    "resultado_teste": deepcopy(
                        resultado_teste
                    ),
                    "resultado_ciclo": deepcopy(
                        resultado_ciclo
                    ),
                    "ciclo_atualizado": False,
                    "teste_integrado": False,
                    "hipotese_avaliada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "O teste foi executado, mas não pôde ser registrado no ciclo."
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
        ) != "testada":
            return self._negado(
                "O ciclo atualizado não alcançou o estado 'testada'."
            )

        if novo_ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "O ciclo atualizado não pode promover conhecimento permanente."
            )

        return {
            "sucesso": True,
            "estado": "teste_integrado_no_ciclo",
            "origem": self.FONTE,
            "valor": {
                "entrada_preparada": deepcopy(
                    entrada_preparada
                ),
                "resultado_teste": deepcopy(
                    resultado_teste
                ),
                "resultado_ciclo": deepcopy(
                    resultado_ciclo
                ),
                "ciclo_anterior": deepcopy(
                    ciclo
                ),
                "ciclo": deepcopy(
                    novo_ciclo
                ),
                "hipotese": deepcopy(
                    hipotese
                ),
                "teste_executado": True,
                "teste_integrado": True,
                "ciclo_atualizado": True,
                "hipotese_testada": True,
                "hipotese_avaliada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "O resultado observado do teste foi registrado "
                    "formalmente no ciclo da hipótese. A hipótese agora "
                    "está marcada como testada, mas ainda não foi avaliada."
                ),
            },
        }

    @staticmethod
    def _extrair_ciclo(
        entrada_preparada: dict[str, Any],
    ) -> dict[str, Any] | None:
        valor = entrada_preparada.get(
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

        resultado_integracao = valor.get(
            "resultado_integracao"
        )

        if isinstance(
            resultado_integracao,
            dict,
        ):
            valor_integracao = resultado_integracao.get(
                "valor"
            )

            if isinstance(
                valor_integracao,
                dict,
            ) and isinstance(
                valor_integracao.get("ciclo"),
                dict,
            ):
                return deepcopy(
                    valor_integracao["ciclo"]
                )

        return None

    @staticmethod
    def _extrair_ciclo_obrigatorio(
        entrada_preparada: dict[str, Any],
    ) -> dict[str, Any]:
        ciclo = IntegracaoTesteCicloHipoteseNixal._extrair_ciclo(
            entrada_preparada
        )

        if ciclo is None:
            raise ValueError(
                "Ciclo da hipótese não encontrado."
            )

        return ciclo

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoTesteCicloHipoteseNixal não avalia hipóteses"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoTesteCicloHipoteseNixal não promove conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoTesteCicloHipoteseNixal não modifica a arquitetura"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "IntegracaoTesteCicloHipoteseNixal não executa capacidades"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "integracao_teste_ciclo_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "IntegracaoTesteCicloHipoteseNixal",
]
