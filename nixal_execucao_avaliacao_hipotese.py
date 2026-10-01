#!/usr/bin/env python3

"""
NIXAL — EXECUÇÃO CONTROLADA DA AVALIAÇÃO DA HIPÓTESE

Microetapa 56.4.33

Responsabilidade:
    Receber uma entrada de teste concluído e executar a avaliação
    formal através da camada AvaliacaoHipoteseNixal.

Fluxo:
    56.4.32 — teste integrado ao ciclo
             ↓
    56.4.33 — avaliação controlada
             ↓
    hipótese avaliada
             ↓
    56.4.34 — futura integração da avaliação ao ciclo

Princípios:
1. A entrada precisa representar um teste já integrado.
2. A hipótese precisa permanecer explicitamente provisória antes da avaliação.
3. O avaliador formal já existente é reutilizado.
4. O resultado do teste precisa fornecer as três flags booleanas exigidas
   pela camada de avaliação: suporte, contrária ou inconclusiva.
5. A avaliação deve escolher exatamente uma dessas classificações.
6. Esta camada não altera o ciclo formal.
7. Esta camada não promove conhecimento permanente.
8. A arquitetura não é modificada.
9. Nenhuma capacidade é descoberta ou executada.
10. A entrada original permanece isolada por cópia profunda.
11. A camada aceita tanto o resultado observado direto quanto o envelope
    produzido pela 56.4.31 e preservado pela 56.4.32.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_avaliacao_hipotese import (
    AvaliacaoHipoteseNixal,
)
from nixal_integracao_teste_ciclo_hipotese import (
    IntegracaoTesteCicloHipoteseNixal,
)


class ExecucaoAvaliacaoHipoteseNixal:
    """Executa de forma controlada a avaliação de uma hipótese."""

    FONTE = "execucao_avaliacao_hipotese_nixal"

    def __init__(
        self,
        avaliador: AvaliacaoHipoteseNixal | None = None,
    ) -> None:
        self.avaliador = (
            avaliador
            if avaliador is not None
            else AvaliacaoHipoteseNixal()
        )

    def executar(
        self,
        resultado_integracao_teste: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            resultado_integracao_teste,
            dict,
        ):
            return self._negado(
                "Resultado de integração do teste inválido."
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
                "Somente testes no estado "
                "'teste_integrado_no_ciclo' podem ser avaliados."
            )

        valor = resultado_integracao_teste.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return self._negado(
                "A integração do teste não possui valor válido."
            )

        if valor.get(
            "teste_integrado"
        ) is not True:
            return self._negado(
                "A entrada não declara o teste como integrado."
            )

        if valor.get(
            "hipotese_testada"
        ) is not True:
            return self._negado(
                "A entrada não declara a hipótese como testada."
            )

        if valor.get(
            "hipotese_avaliada"
        ) is not False:
            return self._negado(
                "A entrada já declara a hipótese como avaliada."
            )

        if valor.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "A entrada não pode indicar conhecimento permanente."
            )

        ciclo = valor.get(
            "ciclo"
        )

        if not isinstance(
            ciclo,
            dict,
        ):
            return self._negado(
                "A entrada não contém ciclo válido."
            )

        if ciclo.get(
            "estado_atual"
        ) != "testada":
            return self._negado(
                "Somente ciclos no estado 'testada' podem ser avaliados."
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
                "A entrada não contém hipótese válida."
            )

        if hipotese.get(
            "estado"
        ) != "provisoria":
            return self._negado(
                "A hipótese precisa permanecer provisória antes da avaliação."
            )

        resultado_teste = valor.get(
            "resultado_teste"
        )

        if not isinstance(
            resultado_teste,
            dict,
        ):
            return self._negado(
                "O resultado do teste precisa ser estruturado."
            )

        # A 56.4.32 preserva o resultado completo produzido pela 56.4.31.
        # Nesse caso, o resultado observado real fica em:
        #
        # resultado_teste
        #     └── valor
        #          └── resultado_teste
        #
        # A 56.4.33 consome o resultado observado. Portanto, quando
        # recebe esse envelope completo, normaliza exatamente uma camada.
        envelope_resultado = resultado_teste.get(
            "valor"
        )

        if (
            resultado_teste.get("estado") == "teste_concluido"
            and isinstance(
                envelope_resultado,
                dict,
            )
            and isinstance(
                envelope_resultado.get("resultado_teste"),
                dict,
            )
        ):
            resultado_teste = deepcopy(
                envelope_resultado["resultado_teste"]
            )

        if resultado_teste.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "O resultado do teste precisa estar marcado como bem-sucedido."
            )

        # A avaliação 56.4.13 exige exatamente uma classificação
        # explicitamente declarada no resultado do teste.
        suporte = resultado_teste.get(
            "suporte"
        )
        contraria = resultado_teste.get(
            "contraria"
        )
        inconclusivo = resultado_teste.get(
            "inconclusivo"
        )

        if not isinstance(
            suporte,
            bool,
        ) or not isinstance(
            contraria,
            bool,
        ) or not isinstance(
            inconclusivo,
            bool,
        ):
            return self._negado(
                "O resultado do teste precisa declarar suporte, contraria "
                "e inconclusivo como booleanos."
            )

        if sum(
            [
                suporte,
                contraria,
                inconclusivo,
            ]
        ) != 1:
            return self._negado(
                "O resultado do teste precisa declarar exatamente uma "
                "classificação para a avaliação."
            )

        evidencias = resultado_teste.get(
            "evidencias"
        )

        if not isinstance(
            evidencias,
            list,
        ):
            return self._negado(
                "O resultado do teste precisa fornecer uma lista de evidências."
            )

        resultado_avaliacao = self.avaliador.avaliar(
            deepcopy(hipotese),
            {
                "estado": "teste_concluido",
                "suporte": suporte,
                "contraria": contraria,
                "inconclusivo": inconclusivo,
                "evidencias": deepcopy(evidencias),
            },
        )

        if not isinstance(
            resultado_avaliacao,
            dict,
        ):
            return self._negado(
                "O avaliador retornou resultado inválido."
            )

        if resultado_avaliacao.get(
            "sucesso"
        ) is not True:
            return {
                "sucesso": False,
                "estado": "avaliacao_nao_concluida",
                "origem": self.FONTE,
                "valor": {
                    "resultado_integracao_teste": deepcopy(
                        resultado_integracao_teste
                    ),
                    "resultado_avaliacao": deepcopy(
                        resultado_avaliacao
                    ),
                    "hipotese_avaliada": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
                "motivo": (
                    "A camada de avaliação não produziu uma "
                    "classificação utilizável."
                ),
            }

        estado_avaliacao = resultado_avaliacao.get(
            "estado"
        )

        estados_permitidos = {
            "suportada",
            "enfraquecida",
            "refutada",
            "inconclusiva",
        }

        if estado_avaliacao not in estados_permitidos:
            return {
                "sucesso": True,
                "estado": "avaliacao_nao_concluida",
                "origem": self.FONTE,
                "valor": {
                    "resultado_integracao_teste": deepcopy(
                        resultado_integracao_teste
                    ),
                    "resultado_avaliacao": deepcopy(
                        resultado_avaliacao
                    ),
                    "hipotese_avaliada": False,
                    "conhecimento_permanente": False,
                },
                "motivo": (
                    "A avaliação não produziu um estado final reconhecido."
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
                "A avaliação concluída não possui valor válido."
            )

        if valor_avaliacao.get(
            "conhecimento_permanente"
        ) is not False:
            return self._negado(
                "A avaliação não pode promover conhecimento permanente."
            )

        return {
            "sucesso": True,
            "estado": "hipotese_avaliada",
            "origem": self.FONTE,
            "valor": {
                "resultado_integracao_teste": deepcopy(
                    resultado_integracao_teste
                ),
                "resultado_avaliacao": deepcopy(
                    resultado_avaliacao
                ),
                "hipotese": deepcopy(
                    hipotese
                ),
                "ciclo": deepcopy(
                    ciclo
                ),
                "estado_avaliacao": estado_avaliacao,
                "hipotese_avaliada": True,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
                "interpretacao": (
                    "A hipótese foi avaliada a partir do resultado "
                    "observado e recebeu uma classificação formal. "
                    "Nenhum conhecimento permanente foi promovido."
                ),
            },
        }

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoAvaliacaoHipoteseNixal não promove conhecimento permanente"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoAvaliacaoHipoteseNixal não modifica a arquitetura"
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ExecucaoAvaliacaoHipoteseNixal não executa capacidades"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "execucao_avaliacao_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ExecucaoAvaliacaoHipoteseNixal",
]
