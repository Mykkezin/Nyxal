#!/usr/bin/env python3

"""
NIXAL — CONSOLIDAÇÃO DE EVIDÊNCIAS

Microetapa 56.4.26

Responsabilidade:
    Receber o resultado de uma execução controlada de investigação
    e consolidar as evidências em um pacote estruturado e explícito.

Esta camada não coleta novas evidências, não formula hipóteses,
não avalia hipóteses e não promove conhecimento permanente.

Princípios:
1. A origem da execução precisa estar identificada.
2. Somente execuções bem-sucedidas com evidências em lista podem
   ser consolidadas como pacote de evidências.
3. Cada evidência precisa continuar ligada à sua fonte.
4. Evidência inválida é rejeitada; não é corrigida silenciosamente.
5. O pacote consolidado é uma cópia isolada.
6. A consolidação não interpreta evidências como verdade.
7. A consolidação não formula hipóteses.
8. A consolidação não modifica a arquitetura.
9. A consolidação não promove conhecimento permanente.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class ConsolidacaoEvidenciasNixal:
    """Valida e organiza evidências já coletadas."""

    FONTE = "consolidacao_evidencias_nixal"

    def consolidar(
        self,
        resultado_execucao: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            resultado_execucao,
            dict,
        ):
            return self._negado(
                "Resultado de execução inválido."
            )

        if resultado_execucao.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "Somente execuções bem-sucedidas podem ser consolidadas."
            )

        if resultado_execucao.get(
            "estado"
        ) != "plano_executado":
            return self._negado(
                "O resultado precisa estar no estado 'plano_executado'."
            )

        valor = resultado_execucao.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return self._negado(
                "O resultado de execução não possui valor válido."
            )

        evidencias = valor.get(
            "evidencias"
        )

        if not isinstance(
            evidencias,
            list,
        ):
            return self._negado(
                "As evidências precisam ser fornecidas como lista."
            )

        evidencias_validas: list[dict[str, Any]] = []

        for indice, evidencia in enumerate(
            evidencias,
            start=1,
        ):
            if not isinstance(
                evidencia,
                dict,
            ):
                return self._negado(
                    f"Evidência {indice} não é um objeto."
                )

            fonte = evidencia.get(
                "fonte"
            )

            if not isinstance(
                fonte,
                str,
            ) or not fonte.strip():
                return self._negado(
                    f"Evidência {indice} não possui fonte válida."
                )

            sucesso = evidencia.get(
                "sucesso"
            )

            if sucesso is not True:
                continue

            estado = evidencia.get(
                "estado"
            )

            if estado != "evidencia_disponivel":
                continue

            copia = deepcopy(
                evidencia
            )

            copia[
                "indice_consolidacao"
            ] = len(
                evidencias_validas
            ) + 1

            evidencias_validas.append(
                copia
            )

        if not evidencias_validas:
            return {
                "sucesso": True,
                "estado": "sem_evidencia_consolidada",
                "origem": self.FONTE,
                "valor": {
                    "plano": deepcopy(
                        valor.get(
                            "plano"
                        )
                    ),
                    "resultado_execucao": deepcopy(
                        resultado_execucao
                    ),
                    "evidencias": [],
                    "quantidade_evidencias": 0,
                    "evidencia_consolidada": False,
                    "conhecimento_permanente": False,
                    "hipotese_formulada": False,
                    "interpretacao": (
                        "A execução terminou, mas nenhuma evidência "
                        "válida ficou disponível para consolidação."
                    ),
                },
            }

        return {
            "sucesso": True,
            "estado": "evidencias_consolidadas",
            "origem": self.FONTE,
            "valor": {
                "plano": deepcopy(
                    valor.get(
                        "plano"
                    )
                ),
                "resultado_execucao": deepcopy(
                    resultado_execucao
                ),
                "evidencias": evidencias_validas,
                "quantidade_evidencias": len(
                    evidencias_validas
                ),
                "evidencia_consolidada": True,
                "conhecimento_permanente": False,
                "hipotese_formulada": False,
                "fontes": sorted(
                    {
                        evidencia["fonte"]
                        for evidencia
                        in evidencias_validas
                    }
                ),
                "interpretacao": (
                    "As evidências válidas foram consolidadas "
                    "sem receber interpretação adicional. "
                    "Elas continuam sendo evidências da investigação "
                    "e não constituem conhecimento permanente."
                ),
            },
        }

    def coletar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsolidacaoEvidenciasNixal não coleta novas evidências"
        )

    def formular_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsolidacaoEvidenciasNixal não formula hipóteses"
        )

    def avaliar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsolidacaoEvidenciasNixal não avalia hipóteses"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsolidacaoEvidenciasNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsolidacaoEvidenciasNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "consolidacao_evidencias_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ConsolidacaoEvidenciasNixal",
]
