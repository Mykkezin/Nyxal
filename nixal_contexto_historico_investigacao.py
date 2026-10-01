#!/usr/bin/env python3

"""
NIXAL — CONTEXTO HISTÓRICO DE INVESTIGAÇÃO

Microetapa 56.4.19

Responsabilidade:
    Transformar registros persistidos de investigação em contexto
    histórico explícito para uso por camadas posteriores.

Princípios:
1. Histórico não é tratado como verdade.
2. Uma hipótese persistida continua sendo hipótese.
3. O estado da hipótese é preservado exatamente.
4. A origem do contexto é identificada pelo ID persistido.
5. Nenhum registro é alterado.
6. A camada não executa capacidades.
7. A camada não modifica a arquitetura.
8. A camada não promove conhecimento permanente.
9. O contexto é uma cópia isolada e pode ser descartado pelo consumidor.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_memoria_investigacao import MemoriaInvestigacaoNixal


class ContextoHistoricoInvestigacaoNixal:
    """Converte memória de investigação em contexto histórico explícito."""

    FONTE = "contexto_historico_investigacao_nixal"

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

    def obter(
        self,
        registro_id: str,
    ) -> dict[str, Any]:
        if not isinstance(
            registro_id,
            str,
        ) or not registro_id.strip():
            return self._negado(
                "ID de registro inválido."
            )

        registro = self._memoria.obter(
            registro_id
        )

        if registro is None:
            return self._negado(
                "Registro de investigação não encontrado."
            )

        ciclo = registro.get(
            "ciclo"
        )

        if not isinstance(
            ciclo,
            dict,
        ):
            return self._negado(
                "Registro não possui um ciclo válido."
            )

        contexto = self._construir_contexto(
            registro
        )

        return {
            "sucesso": True,
            "estado": "contexto_historico",
            "origem": self.FONTE,
            "valor": contexto,
        }

    def ultimos(
        self,
        limite: int = 5,
    ) -> dict[str, Any]:
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

        registros = self._memoria.listar()

        selecionados = registros[
            -limite:
        ]

        contexto = [
            self._construir_contexto(
                registro
            )
            for registro in selecionados
        ]

        return {
            "sucesso": True,
            "estado": "contexto_historico",
            "origem": self.FONTE,
            "valor": {
                "quantidade": len(
                    contexto
                ),
                "registros": deepcopy(
                    contexto
                ),
            },
        }

    def por_necessidade(
        self,
        necessidade: str,
        limite: int = 5,
    ) -> dict[str, Any]:
        if not self._texto_valido(
            necessidade
        ):
            return self._negado(
                "Necessidade inválida."
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

        registros = [
            registro
            for registro in self._memoria.listar()
            if self._ciclo(registro).get(
                "necessidade"
            )
            == necessidade
        ]

        selecionados = registros[
            -limite:
        ]

        contexto = [
            self._construir_contexto(
                registro
            )
            for registro in selecionados
        ]

        return {
            "sucesso": True,
            "estado": "contexto_historico",
            "origem": self.FONTE,
            "valor": {
                "necessidade": necessidade,
                "quantidade": len(
                    contexto
                ),
                "registros": deepcopy(
                    contexto
                ),
            },
        }

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoInvestigacaoNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoInvestigacaoNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoInvestigacaoNixal não promove conhecimento permanente"
        )

    def _construir_contexto(
        self,
        registro: dict[str, Any],
    ) -> dict[str, Any]:
        ciclo = self._ciclo(
            registro
        )

        return {
            "origem_historica": {
                "id": registro.get("id"),
                "versao_memoria": registro.get(
                    "versao_memoria"
                ),
            },
            "status_epistemico": {
                "tipo": "historico_de_investigacao",
                "nao_equivale_a_verdade": True,
                "conhecimento_permanente": ciclo.get(
                    "conhecimento_permanente"
                ) is True,
            },
            "investigacao": {
                "hipotese": ciclo.get(
                    "hipotese"
                ),
                "necessidade": ciclo.get(
                    "necessidade"
                ),
                "pergunta": ciclo.get(
                    "pergunta"
                ),
                "estado_atual": ciclo.get(
                    "estado_atual"
                ),
                "historico": deepcopy(
                    ciclo.get(
                        "historico",
                        [],
                    )
                ),
                "testes": deepcopy(
                    ciclo.get(
                        "testes",
                        [],
                    )
                ),
                "avaliacoes": deepcopy(
                    ciclo.get(
                        "avaliacoes",
                        [],
                    )
                ),
            },
        }

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

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "contexto_historico_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ContextoHistoricoInvestigacaoNixal",
]
