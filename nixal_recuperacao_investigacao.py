#!/usr/bin/env python3

"""
NIXAL — RECUPERAÇÃO DE INVESTIGAÇÃO PERSISTIDA

Microetapa 56.4.17

Responsabilidade:
    Reidratar um ciclo de hipótese anteriormente persistido na
    MemoriaInvestigacaoNixal.

Princípios:
1. Recuperar não significa validar como verdadeiro.
2. Recuperar não significa promover conhecimento permanente.
3. O registro persistido é tratado como estado histórico.
4. O ciclo recuperado é devolvido como cópia isolada.
5. O arquivo de memória continua sendo a única fonte persistente
   desta camada.
6. Esta camada não executa capacidades.
7. Esta camada não modifica a arquitetura.
8. Esta camada não altera o registro persistido durante a leitura.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_memoria_investigacao import MemoriaInvestigacaoNixal


class RecuperacaoInvestigacaoNixal:
    """Recupera ciclos persistidos sem transformá-los em conhecimento."""

    FONTE = "recuperacao_investigacao_nixal"

    CAMPOS_CICLO = {
        "hipotese",
        "estado_atual",
        "historico",
        "testes",
        "avaliacoes",
        "conhecimento_permanente",
    }

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

    def listar_registros(
        self,
    ) -> list[dict[str, Any]]:
        return deepcopy(
            self._memoria.listar()
        )

    def quantidade(
        self,
    ) -> int:
        return self._memoria.quantidade()

    def recuperar(
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

        valido, erro = self._validar_registro(
            registro
        )

        if not valido:
            return self._negado(
                erro or "Registro persistido inválido."
            )

        ciclo = deepcopy(
            registro["ciclo"]
        )

        return {
            "sucesso": True,
            "estado": "recuperado",
            "origem": self.FONTE,
            "valor": {
                "id": registro["id"],
                "versao_memoria": registro.get(
                    "versao_memoria"
                ),
                "ciclo": ciclo,
            },
        }

    def recuperar_ciclo(
        self,
        registro_id: str,
    ) -> dict[str, Any] | None:
        resultado = self.recuperar(
            registro_id
        )

        if resultado.get(
            "sucesso"
        ) is not True:
            return None

        valor = resultado.get(
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

        if not isinstance(
            ciclo,
            dict,
        ):
            return None

        return deepcopy(
            ciclo
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "RecuperacaoInvestigacaoNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "RecuperacaoInvestigacaoNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "RecuperacaoInvestigacaoNixal não promove conhecimento permanente"
        )

    def _validar_registro(
        self,
        registro: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if not isinstance(
            registro,
            dict,
        ):
            return (
                False,
                "Registro precisa ser um dicionário.",
            )

        registro_id = registro.get(
            "id"
        )

        if not isinstance(
            registro_id,
            str,
        ) or not registro_id.strip():
            return (
                False,
                "Registro não possui ID válido.",
            )

        ciclo = registro.get(
            "ciclo"
        )

        if not isinstance(
            ciclo,
            dict,
        ):
            return (
                False,
                "Registro não possui ciclo válido.",
            )

        ausentes = sorted(
            self.CAMPOS_CICLO
            - set(ciclo.keys())
        )

        if ausentes:
            return (
                False,
                "Ciclo persistido sem campos obrigatórios: "
                + ", ".join(ausentes),
            )

        if ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return (
                False,
                "Memória de investigação não pode recuperar "
                "conhecimento permanente como verdadeiro.",
            )

        if not isinstance(
            ciclo.get("hipotese"),
            str,
        ) or not ciclo.get(
            "hipotese",
            "",
        ).strip():
            return (
                False,
                "Texto da hipótese persistida inválido.",
            )

        if not isinstance(
            ciclo.get("estado_atual"),
            str,
        ):
            return (
                False,
                "Estado atual persistido inválido.",
            )

        if not isinstance(
            ciclo.get("historico"),
            list,
        ):
            return (
                False,
                "Histórico persistido inválido.",
            )

        if not isinstance(
            ciclo.get("testes"),
            list,
        ):
            return (
                False,
                "Lista de testes persistida inválida.",
            )

        if not isinstance(
            ciclo.get("avaliacoes"),
            list,
        ):
            return (
                False,
                "Lista de avaliações persistida inválida.",
            )

        return True, None

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "recuperacao_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "RecuperacaoInvestigacaoNixal",
]
