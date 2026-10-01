#!/usr/bin/env python3

"""
NIXAL — CONTEXTO HISTÓRICO RELEVANTE

Microetapa 56.4.21

Responsabilidade:
    Integrar a relevância do histórico (56.4.20) com a construção
    de contexto histórico (56.4.19), produzindo somente o contexto
    histórico relacionado a uma nova necessidade ou hipótese.

Princípios:
1. Histórico relacionado é contexto, não verdade.
2. O histórico não encerra uma nova investigação.
3. Necessidade exata tem prioridade de classificação.
4. Registros duplicados entre critérios aparecem uma única vez.
5. A ordem cronológica da memória é preservada.
6. Um limite explícito controla quanto histórico é entregue.
7. Nenhum registro persistido é alterado.
8. A camada não executa capacidades.
9. A camada não modifica a arquitetura.
10. A camada não promove conhecimento permanente.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_contexto_historico_investigacao import (
    ContextoHistoricoInvestigacaoNixal,
)
from nixal_memoria_investigacao import (
    MemoriaInvestigacaoNixal,
)
from nixal_relevancia_historico_investigacao import (
    RelevanciaHistoricoInvestigacaoNixal,
)


class ContextoHistoricoRelevanteNixal:
    """Entrega somente histórico relevante como contexto explícito."""

    FONTE = "contexto_historico_relevante_nixal"

    def __init__(
        self,
        memoria: MemoriaInvestigacaoNixal,
    ) -> None:
        if not isinstance(
            memoria,
            MemoriaInvestigacaoNixal,
        ):
            raise TypeError(
                "memoria deve ser uma instância de "
                "MemoriaInvestigacaoNixal"
            )

        self._memoria = memoria
        self._relevancia = (
            RelevanciaHistoricoInvestigacaoNixal(
                memoria
            )
        )
        self._contexto = (
            ContextoHistoricoInvestigacaoNixal(
                memoria
            )
        )

    def analisar(
        self,
        necessidade: str | None = None,
        hipotese: str | None = None,
        limite: int = 5,
    ) -> dict[str, Any]:
        if not self._possui_entrada(
            necessidade,
            hipotese,
        ):
            return self._negado(
                "É necessário fornecer necessidade, hipótese ou ambos."
            )

        if not isinstance(
            limite,
            int,
        ) or isinstance(
            limite,
            bool,
        ):
            return self._negado(
                "Limite precisa ser um inteiro."
            )

        if limite <= 0:
            return self._negado(
                "Limite precisa ser maior que zero."
            )

        resultado_relevancia = (
            self._relevancia.analisar(
                necessidade=necessidade,
                hipotese=hipotese,
            )
        )

        if resultado_relevancia.get(
            "sucesso"
        ) is not True:
            return deepcopy(
                resultado_relevancia
            )

        valor_relevancia = resultado_relevancia.get(
            "valor"
        )

        if not isinstance(
            valor_relevancia,
            dict,
        ):
            return self._negado(
                "A relevância do histórico não retornou dados válidos."
            )

        registros = self._selecionar_unicos(
            valor_relevancia,
            limite,
        )

        contextos: list[dict[str, Any]] = []

        for registro in registros:
            registro_id = registro.get(
                "id"
            )

            if not isinstance(
                registro_id,
                str,
            ):
                continue

            resultado_contexto = (
                self._contexto.obter(
                    registro_id
                )
            )

            if resultado_contexto.get(
                "sucesso"
            ) is not True:
                continue

            contexto = resultado_contexto.get(
                "valor"
            )

            if isinstance(
                contexto,
                dict,
            ):
                contextos.append(
                    deepcopy(
                        contexto
                    )
                )

        return {
            "sucesso": True,
            "estado": "contexto_relevante",
            "origem": self.FONTE,
            "valor": {
                "entrada": {
                    "necessidade": necessidade,
                    "hipotese": hipotese,
                },
                "historico_encontrado": bool(
                    contextos
                ),
                "quantidade": len(
                    contextos
                ),
                "limite": limite,
                "contextos": contextos,
                "interpretacao": (
                    "O histórico relevante foi recuperado como "
                    "contexto. Ele não determina a verdade da "
                    "hipótese atual e não encerra a investigação."
                    if contextos
                    else
                    "Nenhum histórico relevante foi recuperado. "
                    "Isso não prova que o tema nunca foi investigado."
                ),
            },
        }

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoRelevanteNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoRelevanteNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoRelevanteNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _selecionar_unicos(
        valor_relevancia: dict[str, Any],
        limite: int,
    ) -> list[dict[str, Any]]:
        diretos = valor_relevancia.get(
            "historico_direto",
            [],
        )

        relacionados = valor_relevancia.get(
            "historico_relacionado",
            [],
        )

        candidatos: list[dict[str, Any]] = []

        if isinstance(
            diretos,
            list,
        ):
            candidatos.extend(
                diretos
            )

        if isinstance(
            relacionados,
            list,
        ):
            candidatos.extend(
                relacionados
            )

        unicos: list[dict[str, Any]] = []
        ids_vistos: set[str] = set()

        for registro in candidatos:
            if not isinstance(
                registro,
                dict,
            ):
                continue

            registro_id = registro.get(
                "id"
            )

            if not isinstance(
                registro_id,
                str,
            ):
                continue

            if registro_id in ids_vistos:
                continue

            ids_vistos.add(
                registro_id
            )
            unicos.append(
                deepcopy(registro)
            )

        # A memória é cronológica. O corte deve ocorrer sobre o
        # final da sequência para recuperar os registros mais recentes.
        return unicos[-limite:]

    @staticmethod
    def _possui_entrada(
        necessidade: str | None,
        hipotese: str | None,
    ) -> bool:
        return (
            (
                isinstance(
                    necessidade,
                    str,
                )
                and bool(
                    necessidade.strip()
                )
            )
            or
            (
                isinstance(
                    hipotese,
                    str,
                )
                and bool(
                    hipotese.strip()
                )
            )
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "contexto_historico_relevante_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ContextoHistoricoRelevanteNixal",
]
