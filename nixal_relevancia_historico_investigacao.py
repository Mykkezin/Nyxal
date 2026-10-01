#!/usr/bin/env python3

"""
NIXAL — RELEVÂNCIA DO HISTÓRICO DE INVESTIGAÇÃO

Microetapa 56.4.20

Responsabilidade:
    Determinar de forma explícita se já existem registros históricos
    relacionados a uma nova necessidade de investigação.

Princípios:
1. Histórico relacionado não é considerado verdade.
2. A existência de histórico não encerra uma nova investigação.
3. Correspondência exata de necessidade é evidência de histórico direto.
4. Correspondência textual na hipótese é evidência de histórico relacionado.
5. Ausência de correspondência não prova que o tema nunca foi investigado.
6. Nenhum registro persistido é alterado.
7. Esta camada não executa capacidades.
8. Esta camada não modifica a arquitetura.
9. Esta camada não promove conhecimento permanente.
10. Os registros retornados são cópias isoladas.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_memoria_investigacao import MemoriaInvestigacaoNixal


class RelevanciaHistoricoInvestigacaoNixal:
    """Avalia somente a presença de histórico relacionado."""

    FONTE = "relevancia_historico_investigacao_nixal"

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

    def analisar_necessidade(
        self,
        necessidade: str,
    ) -> dict[str, Any]:
        if not self._texto_valido(
            necessidade
        ):
            return self._negado(
                "Necessidade inválida."
            )

        registros = self._memoria.listar()

        diretos = [
            deepcopy(registro)
            for registro in registros
            if self._ciclo(registro).get(
                "necessidade"
            )
            == necessidade
        ]

        return self._resultado(
            necessidade=necessidade,
            historico_direto=diretos,
            historico_relacionado=[],
            criterio="necessidade_exata",
        )

    def analisar_hipotese(
        self,
        hipotese: str,
    ) -> dict[str, Any]:
        if not self._texto_valido(
            hipotese
        ):
            return self._negado(
                "Hipótese inválida."
            )

        termo = hipotese.strip().casefold()

        relacionados: list[dict[str, Any]] = []

        for registro in self._memoria.listar():
            texto = self._ciclo(
                registro
            ).get(
                "hipotese"
            )

            if not isinstance(
                texto,
                str,
            ):
                continue

            if termo in texto.casefold():
                relacionados.append(
                    deepcopy(registro)
                )

        return self._resultado(
            hipotese=hipotese,
            historico_direto=[],
            historico_relacionado=relacionados,
            criterio="texto_da_hipotese",
        )

    def analisar(
        self,
        necessidade: str | None = None,
        hipotese: str | None = None,
    ) -> dict[str, Any]:
        if not self._texto_valido(
            necessidade
        ) and not self._texto_valido(
            hipotese
        ):
            return self._negado(
                "É necessário fornecer necessidade, hipótese ou ambos."
            )

        registros = self._memoria.listar()

        diretos: list[dict[str, Any]] = []
        relacionados: list[dict[str, Any]] = []

        necessidade_valida = self._texto_valido(
            necessidade
        )
        hipotese_valida = self._texto_valido(
            hipotese
        )

        termo_hipotese = (
            hipotese.strip().casefold()
            if hipotese_valida
            else None
        )

        for registro in registros:
            ciclo = self._ciclo(
                registro
            )

            necessidade_exata = (
                necessidade_valida
                and ciclo.get(
                    "necessidade"
                )
                == necessidade
            )

            hipotese_relacionada = False

            texto = ciclo.get(
                "hipotese"
            )

            if (
                termo_hipotese is not None
                and isinstance(
                    texto,
                    str,
                )
            ):
                hipotese_relacionada = (
                    termo_hipotese
                    in texto.casefold()
                )

            if necessidade_exata:
                diretos.append(
                    deepcopy(registro)
                )
                continue

            if hipotese_relacionada:
                relacionados.append(
                    deepcopy(registro)
                )

        return self._resultado(
            necessidade=necessidade,
            hipotese=hipotese,
            historico_direto=diretos,
            historico_relacionado=relacionados,
            criterio="necessidade_exata_ou_texto_da_hipotese",
        )

    @staticmethod
    def _resultado(
        *,
        necessidade: str | None = None,
        hipotese: str | None = None,
        historico_direto: list[dict[str, Any]],
        historico_relacionado: list[dict[str, Any]],
        criterio: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "historico_analisado",
            "origem": RelevanciaHistoricoInvestigacaoNixal.FONTE,
            "valor": {
                "entrada": {
                    "necessidade": necessidade,
                    "hipotese": hipotese,
                },
                "criterio": criterio,
                "historico_encontrado": bool(
                    historico_direto
                    or historico_relacionado
                ),
                "quantidade_direta": len(
                    historico_direto
                ),
                "quantidade_relacionada": len(
                    historico_relacionado
                ),
                "historico_direto": deepcopy(
                    historico_direto
                ),
                "historico_relacionado": deepcopy(
                    historico_relacionado
                ),
                "interpretacao": (
                    "Há histórico relacionado; isso não determina "
                    "a verdade da hipótese e não encerra uma nova "
                    "investigação."
                    if (
                        historico_direto
                        or historico_relacionado
                    )
                    else
                    "Não foi encontrado histórico correspondente; "
                    "isso não prova que o tema nunca foi investigado."
                ),
            },
        }

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "RelevanciaHistoricoInvestigacaoNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "RelevanciaHistoricoInvestigacaoNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "RelevanciaHistoricoInvestigacaoNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _ciclo(
        registro: dict[str, Any],
    ) -> dict[str, Any]:
        ciclo = registro.get(
            "ciclo"
        )

        if isinstance(
            ciclo,
            dict,
        ):
            return ciclo

        return {}

    @staticmethod
    def _texto_valido(
        texto: str | None,
    ) -> bool:
        return (
            isinstance(
                texto,
                str,
            )
            and bool(
                texto.strip()
            )
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "relevancia_historico_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "RelevanciaHistoricoInvestigacaoNixal",
]
