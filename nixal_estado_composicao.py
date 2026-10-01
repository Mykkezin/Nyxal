#!/usr/bin/env python3

"""
NIXAL — ESTADO COMPOSTO DE AUTORREPRESENTAÇÃO

Microetapa 56.4.7

Responsabilidade:
    Reunir, em uma única estrutura formal, os principais aspectos
    conhecidos pela Nixal sobre si mesma.

Princípios:
1. A fonte factual continua sendo a autorrepresentação.
2. Não acessar a planta diretamente.
3. Não executar capacidades.
4. Não modificar a planta ou a autorrepresentação.
5. Não inventar componentes, capacidades ou fatos.
6. Preservar explicitamente estados de conhecimento.
7. O estado composto é somente leitura.
"""

from __future__ import annotations

from typing import Any

from nixal_autorreprentacao import AutorreprentacaoNixal
from nixal_consulta_interna import ConsultaInternaNixal
from nixal_estado_conhecimento import (
    ESTADO_CONHECIDO,
    EstadoConhecimentoNixal,
)


class EstadoCompostoAutorreprentacaoNixal:
    """Modelo interno agregado do conhecimento declarado da Nixal."""

    FONTE = "estado_composto_autorreprentacao"

    def __init__(
        self,
        autorrepresentacao: AutorreprentacaoNixal | None = None,
        consulta_interna: ConsultaInternaNixal | None = None,
        estado_conhecimento: EstadoConhecimentoNixal | None = None,
    ) -> None:
        self.autorrepresentacao = (
            autorrepresentacao
            if autorrepresentacao is not None
            else AutorreprentacaoNixal()
        )

        self.consulta_interna = (
            consulta_interna
            if consulta_interna is not None
            else ConsultaInternaNixal(
                autorrepresentacao=self.autorrepresentacao
            )
        )

        self.estado_conhecimento = (
            estado_conhecimento
            if estado_conhecimento is not None
            else EstadoConhecimentoNixal(
                consulta_interna=self.consulta_interna
            )
        )

    def construir(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": ESTADO_CONHECIDO,
            "origem": self.FONTE,
            "valor": {
                "identidade": self.autorrepresentacao.identidade(),
                "estado_arquitetura": (
                    self.autorrepresentacao.estado_arquitetura()
                ),
                "componentes": self.autorrepresentacao.componentes(),
                "capacidades": self.autorrepresentacao.capacidades(),
                "limites": self.autorrepresentacao.limites(),
                "regras_modificacao": (
                    self.autorrepresentacao.regras_modificacao()
                ),
            },
        }

    def estado_componente(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        return self.estado_conhecimento.componente(componente_id)

    def estado_capacidade(
        self,
        capacidade: str,
    ) -> dict[str, Any]:
        return self.estado_conhecimento.capacidade(capacidade)

    def estado_funcao_componente(
        self,
        componente_id: str,
    ) -> dict[str, Any]:
        return self.estado_conhecimento.funcao_componente(
            componente_id
        )

    def consultar_campo(
        self,
        campo: str,
    ) -> dict[str, Any]:
        snapshot = self.construir()
        valor = snapshot["valor"]

        if campo not in valor:
            return {
                "sucesso": True,
                "estado": "desconhecido",
                "origem": self.FONTE,
                "valor": None,
            }

        return {
            "sucesso": True,
            "estado": ESTADO_CONHECIDO,
            "origem": self.FONTE,
            "valor": valor[campo],
        }

    def resumo(self) -> dict[str, Any]:
        identidade = self.autorrepresentacao.identidade()
        estado = self.autorrepresentacao.estado_arquitetura()

        identidade_valor = identidade.get("valor", {})
        estado_valor = estado.get("valor", {})

        return {
            "sucesso": True,
            "estado": ESTADO_CONHECIDO,
            "origem": self.FONTE,
            "valor": {
                "nome": identidade_valor.get("nome"),
                "versao_arquitetura": identidade_valor.get(
                    "versao_arquitetura"
                ),
                "fundacao": estado_valor.get("fundacao"),
                "autorrepresentacao": estado_valor.get(
                    "autorrepresentacao"
                ),
                "evolucao_autonoma": estado_valor.get(
                    "evolucao_autonoma"
                ),
            },
        }

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": self.FONTE,
            "valor": None,
            "motivo": (
                "O estado composto de autorrepresentação "
                "não executa capacidades."
            ),
        }

    def modificar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": self.FONTE,
            "valor": None,
            "motivo": (
                "O estado composto de autorrepresentação "
                "é somente leitura."
            ),
        }


def main() -> None:
    estado = EstadoCompostoAutorreprentacaoNixal()

    print("=" * 60)
    print("NIXAL — ESTADO COMPOSTO 56.4.7")
    print("=" * 60)
    print()
    print("Resumo:")
    print(estado.resumo())
    print()
    print("Estado da capacidade ler_estado_corpo:")
    print(estado.estado_capacidade("ler_estado_corpo"))


if __name__ == "__main__":
    main()
