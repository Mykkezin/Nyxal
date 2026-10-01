#!/usr/bin/env python3

"""
NIXAL — CONSULTA DO HISTÓRICO DE INVESTIGAÇÕES

Microetapa 56.4.18

Responsabilidade:
    Permitir consultar a memória persistente de investigações por
    critérios explícitos, sem alterar a memória.

Princípios:
1. Consulta somente dados já persistidos.
2. Não inventa investigações ausentes.
3. Não transforma hipótese em conhecimento.
4. Não modifica registros persistidos.
5. Não executa capacidades.
6. Não modifica a arquitetura.
7. Não promove conhecimento permanente.
8. A ordenação original da memória é preservada nas listagens.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_memoria_investigacao import MemoriaInvestigacaoNixal


class ConsultaMemoriaInvestigacaoNixal:
    """Consulta read-only do histórico persistido de investigações."""

    FONTE = "consulta_memoria_investigacao_nixal"

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

    def listar(
        self,
    ) -> list[dict[str, Any]]:
        return deepcopy(
            self._memoria.listar()
        )

    def quantidade(
        self,
    ) -> int:
        return self._memoria.quantidade()

    def por_estado(
        self,
        estado: str,
    ) -> list[dict[str, Any]]:
        if not self._texto_valido(
            estado
        ):
            return []

        return [
            deepcopy(registro)
            for registro in self._memoria.listar()
            if self._ciclo(registro).get(
                "estado_atual"
            )
            == estado
        ]

    def por_necessidade(
        self,
        necessidade: str,
    ) -> list[dict[str, Any]]:
        if not self._texto_valido(
            necessidade
        ):
            return []

        return [
            deepcopy(registro)
            for registro in self._memoria.listar()
            if self._ciclo(registro).get(
                "necessidade"
            )
            == necessidade
        ]

    def buscar_hipotese(
        self,
        texto: str,
    ) -> list[dict[str, Any]]:
        if not self._texto_valido(
            texto
        ):
            return []

        termo = texto.strip().casefold()

        resultados: list[dict[str, Any]] = []

        for registro in self._memoria.listar():
            hipotese = self._ciclo(
                registro
            ).get(
                "hipotese"
            )

            if not isinstance(
                hipotese,
                str,
            ):
                continue

            if termo in hipotese.casefold():
                resultados.append(
                    deepcopy(registro)
                )

        return resultados

    def ultima_por_necessidade(
        self,
        necessidade: str,
    ) -> dict[str, Any] | None:
        resultados = self.por_necessidade(
            necessidade
        )

        if not resultados:
            return None

        return deepcopy(
            resultados[-1]
        )

    def resumo(
        self,
    ) -> dict[str, Any]:
        registros = self._memoria.listar()

        estados: dict[str, int] = {}

        for registro in registros:
            estado = self._ciclo(
                registro
            ).get(
                "estado_atual"
            )

            if isinstance(
                estado,
                str,
            ):
                estados[estado] = (
                    estados.get(
                        estado,
                        0,
                    )
                    + 1
                )

        return {
            "sucesso": True,
            "estado": "consultado",
            "origem": self.FONTE,
            "valor": {
                "quantidade_registros": len(
                    registros
                ),
                "quantidade_estados": len(
                    estados
                ),
                "por_estado": dict(
                    sorted(
                        estados.items()
                    )
                ),
            },
        }

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsultaMemoriaInvestigacaoNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsultaMemoriaInvestigacaoNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ConsultaMemoriaInvestigacaoNixal não promove conhecimento permanente"
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
        texto: str,
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


__all__ = [
    "ConsultaMemoriaInvestigacaoNixal",
]
