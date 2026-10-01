#!/usr/bin/env python3

"""
NIXAL — INTEGRAÇÃO DO CICLO COM MEMÓRIA

Microetapa 56.4.16

Responsabilidade:
    Conectar o ciclo formal de vida da hipótese à memória persistente
    de investigação.

Princípios:
1. O ciclo de vida continua responsável pelas transições formais.
2. A memória continua responsável somente pela persistência.
3. Esta camada apenas coordena as duas responsabilidades.
4. Cada transição bem-sucedida do ciclo pode ser persistida.
5. A memória continua podendo deduplicar estados idênticos.
6. Nenhuma camada desta integração executa capacidades.
7. Nenhuma camada desta integração modifica a arquitetura.
8. Nenhuma camada desta integração promove conhecimento permanente.
9. A API utilizada respeita o contrato real do ciclo 56.4.14:
       iniciar(hipotese)
       registrar_teste(ciclo, resultado_teste)
       registrar_avaliacao(ciclo, avaliacao)
       reabrir(ciclo)
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from nixal_ciclo_vida_hipotese import CicloVidaHipoteseNixal
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal


class CicloMemoriaHipoteseNixal:
    """
    Coordena o ciclo de vida da hipótese e sua persistência.

    Esta classe não substitui nenhuma das duas camadas:
    - CicloVidaHipoteseNixal trata as transições;
    - MemoriaInvestigacaoNixal trata a persistência.
    """

    FONTE = "ciclo_memoria_hipotese_nixal"

    def __init__(
        self,
        memoria: MemoriaInvestigacaoNixal,
        ciclo: Optional[dict[str, Any]] = None,
    ) -> None:
        if not isinstance(
            memoria,
            MemoriaInvestigacaoNixal,
        ):
            raise TypeError(
                "memoria deve ser uma instância de "
                "MemoriaInvestigacaoNixal"
            )

        if ciclo is not None and not isinstance(
            ciclo,
            dict,
        ):
            raise TypeError(
                "ciclo deve ser um dicionário ou None"
            )

        self._memoria = memoria
        self._motor = CicloVidaHipoteseNixal()
        self._ciclo = (
            deepcopy(ciclo)
            if ciclo is not None
            else None
        )

    # ============================================================
    # CICLO ATUAL
    # ============================================================

    def definir_ciclo(
        self,
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            ciclo,
            dict,
        ):
            raise TypeError(
                "ciclo deve ser um dicionário"
            )

        self._ciclo = deepcopy(ciclo)

        return {
            "sucesso": True,
            "estado": "ciclo_definido",
            "origem": self.FONTE,
            "valor": deepcopy(self._ciclo),
        }

    def obter_ciclo(
        self,
    ) -> dict[str, Any] | None:
        if self._ciclo is None:
            return None

        return deepcopy(self._ciclo)

    def registrar_ciclo_atual(
        self,
    ) -> dict[str, Any]:
        self._exigir_ciclo()

        return deepcopy(
            self._memoria.registrar(
                self._ciclo
            )
        )

    # ============================================================
    # TRANSIÇÕES
    # ============================================================

    def iniciar(
        self,
        hipotese: dict[str, Any],
    ) -> dict[str, Any]:
        resultado = self._motor.iniciar(
            hipotese
        )

        if resultado.get("sucesso") is not True:
            return deepcopy(resultado)

        novo_ciclo = resultado.get(
            "valor"
        )

        if not isinstance(
            novo_ciclo,
            dict,
        ):
            return self._erro(
                "O ciclo iniciado não retornou um objeto válido."
            )

        self._ciclo = deepcopy(
            novo_ciclo
        )

        persistencia = self._persistir_estado_atual()

        return {
            "sucesso": True,
            "estado": resultado.get(
                "estado"
            ),
            "origem": self.FONTE,
            "valor": deepcopy(
                self._ciclo
            ),
            "persistencia": persistencia,
        }

    def registrar_teste(
        self,
        resultado_teste: dict[str, Any],
    ) -> dict[str, Any]:
        self._exigir_ciclo()

        resultado = self._motor.registrar_teste(
            self._ciclo,
            resultado_teste,
        )

        if resultado.get("sucesso") is not True:
            return deepcopy(resultado)

        novo_ciclo = resultado.get(
            "valor"
        )

        if not isinstance(
            novo_ciclo,
            dict,
        ):
            return self._erro(
                "O registro do teste não retornou um ciclo válido."
            )

        self._ciclo = deepcopy(
            novo_ciclo
        )

        persistencia = self._persistir_estado_atual()

        return {
            "sucesso": True,
            "estado": resultado.get(
                "estado"
            ),
            "origem": self.FONTE,
            "valor": deepcopy(
                self._ciclo
            ),
            "persistencia": persistencia,
        }

    def registrar_avaliacao(
        self,
        avaliacao: dict[str, Any],
    ) -> dict[str, Any]:
        self._exigir_ciclo()

        resultado = self._motor.registrar_avaliacao(
            self._ciclo,
            avaliacao,
        )

        if resultado.get("sucesso") is not True:
            return deepcopy(resultado)

        novo_ciclo = resultado.get(
            "valor"
        )

        if not isinstance(
            novo_ciclo,
            dict,
        ):
            return self._erro(
                "O registro da avaliação não retornou um ciclo válido."
            )

        self._ciclo = deepcopy(
            novo_ciclo
        )

        persistencia = self._persistir_estado_atual()

        return {
            "sucesso": True,
            "estado": resultado.get(
                "estado"
            ),
            "origem": self.FONTE,
            "valor": deepcopy(
                self._ciclo
            ),
            "persistencia": persistencia,
        }

    def reabrir(
        self,
    ) -> dict[str, Any]:
        self._exigir_ciclo()

        resultado = self._motor.reabrir(
            self._ciclo
        )

        if resultado.get("sucesso") is not True:
            return deepcopy(resultado)

        novo_ciclo = resultado.get(
            "valor"
        )

        if not isinstance(
            novo_ciclo,
            dict,
        ):
            return self._erro(
                "A reabertura não retornou um ciclo válido."
            )

        self._ciclo = deepcopy(
            novo_ciclo
        )

        persistencia = self._persistir_estado_atual()

        return {
            "sucesso": True,
            "estado": resultado.get(
                "estado"
            ),
            "origem": self.FONTE,
            "valor": deepcopy(
                self._ciclo
            ),
            "persistencia": persistencia,
        }

    # ============================================================
    # MEMÓRIA
    # ============================================================

    def listar_memoria(
        self,
    ) -> list[dict[str, Any]]:
        return deepcopy(
            self._memoria.listar()
        )

    def obter_memoria(
        self,
        registro_id: str,
    ) -> dict[str, Any] | None:
        return deepcopy(
            self._memoria.obter(
                registro_id
            )
        )

    # ============================================================
    # PROTEÇÕES
    # ============================================================

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "CicloMemoriaHipoteseNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "CicloMemoriaHipoteseNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "CicloMemoriaHipoteseNixal não promove conhecimento permanente"
        )

    # ============================================================
    # AUXILIARES
    # ============================================================

    def _persistir_estado_atual(
        self,
    ) -> dict[str, Any]:
        self._exigir_ciclo()

        return deepcopy(
            self._memoria.registrar(
                self._ciclo
            )
        )

    def _exigir_ciclo(
        self,
    ) -> None:
        if self._ciclo is None:
            raise ValueError(
                "nenhum ciclo foi definido"
            )

    def _erro(
        self,
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "erro",
            "origem": self.FONTE,
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "CicloMemoriaHipoteseNixal",
]
