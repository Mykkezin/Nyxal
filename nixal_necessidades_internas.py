#!/usr/bin/env python3

"""
NIXAL — NECESSIDADES INTERNAS DA AUTORREPRESENTAÇÃO

Microetapa 56.4.9

Responsabilidade:
    Transformar achados do diagnóstico da autorrepresentação em
    necessidades internas estruturadas.

Esta camada não resolve as necessidades. Ela somente registra:
    problema detectado
    tipo do problema
    necessidade decorrente
    motivo
    prioridade estrutural

Princípios:
1. A origem factual continua sendo o diagnóstico da autorrepresentação.
2. Não acessar a planta diretamente.
3. Não executar capacidades.
4. Não modificar a arquitetura.
5. Não transformar uma necessidade em ação automática.
6. Não criar problemas que o diagnóstico não tenha apontado.
7. Hipóteses de solução permanecem fora desta camada.
"""

from __future__ import annotations

from typing import Any

from nixal_diagnostico_autorreprentacao import (
    ESTADO_INCOMPLETO,
    ESTADO_INCONSISTENTE,
    ESTADO_DESCONHECIDO,
    DiagnosticoAutorreprentacaoNixal,
)


class NecessidadesInternasNixal:
    """Extrai necessidades estruturadas a partir do diagnóstico."""

    FONTE = "necessidades_internas_nixal"

    _MAPA_LACUNAS: dict[str, dict[str, str]] = {
        "dependencias_arquiteturais_nao_declaradas": {
            "tipo": "conhecimento_arquitetural",
            "necessidade": "conhecer_dependencias_arquiteturais",
            "motivo": (
                "As relações de dependência entre componentes "
                "ainda não estão declaradas na autorrepresentação."
            ),
        },
        "identidade_nao_disponivel": {
            "tipo": "conhecimento_identidade",
            "necessidade": "recuperar_identidade",
            "motivo": (
                "A identidade declarada não está disponível."
            ),
        },
        "componentes_nao_disponiveis": {
            "tipo": "conhecimento_arquitetural",
            "necessidade": "recuperar_componentes",
            "motivo": (
                "Os componentes declarados não estão disponíveis."
            ),
        },
        "capacidades_nao_disponiveis": {
            "tipo": "conhecimento_capacidades",
            "necessidade": "recuperar_capacidades",
            "motivo": (
                "As capacidades declaradas não estão disponíveis."
            ),
        },
        "limites_nao_disponiveis": {
            "tipo": "conhecimento_limites",
            "necessidade": "recuperar_limites",
            "motivo": (
                "Os limites declarados não estão disponíveis."
            ),
        },
        "regras_modificacao_nao_disponiveis": {
            "tipo": "conhecimento_seguro",
            "necessidade": "recuperar_regras_modificacao",
            "motivo": (
                "As regras de modificação não estão disponíveis."
            ),
        },
    }

    def __init__(
        self,
        diagnostico: DiagnosticoAutorreprentacaoNixal | None = None,
    ) -> None:
        self.diagnostico = (
            diagnostico
            if diagnostico is not None
            else DiagnosticoAutorreprentacaoNixal()
        )

    # ============================================================
    # EXTRAÇÃO
    # ============================================================

    def analisar(self) -> dict[str, Any]:
        resultado = self.diagnostico.diagnosticar()

        estado_diagnostico = resultado.get("estado")
        valor = resultado.get("valor")

        if not isinstance(valor, dict):
            return {
                "sucesso": True,
                "estado": ESTADO_DESCONHECIDO,
                "origem": self.FONTE,
                "valor": {
                    "necessidades": [],
                    "diagnostico_estado": estado_diagnostico,
                },
            }

        necessidades: list[dict[str, Any]] = []

        lacunas = valor.get("lacunas", [])
        inconsistencias = valor.get("inconsistencias", [])

        if isinstance(lacunas, list):
            for lacuna in lacunas:
                if isinstance(lacuna, str):
                    necessidade = self._necessidade_de_lacuna(
                        lacuna
                    )

                    necessidades.append(
                        necessidade
                    )

        if isinstance(inconsistencias, list):
            for inconsistencia in inconsistencias:
                if isinstance(inconsistencia, str):
                    necessidades.append(
                        self._necessidade_de_inconsistencia(
                            inconsistencia
                        )
                    )

        if estado_diagnostico == ESTADO_DESCONHECIDO:
            estado_final = ESTADO_DESCONHECIDO
        elif necessidades:
            estado_final = "necessidades_detectadas"
        else:
            estado_final = "nenhuma_necessidade_detectada"

        return {
            "sucesso": True,
            "estado": estado_final,
            "origem": self.FONTE,
            "valor": {
                "diagnostico_estado": estado_diagnostico,
                "necessidades": necessidades,
            },
        }

    # ============================================================
    # LACUNAS
    # ============================================================

    def _necessidade_de_lacuna(
        self,
        lacuna: str,
    ) -> dict[str, Any]:
        dados = self._MAPA_LACUNAS.get(lacuna)

        if dados is None:
            return {
                "origem": "diagnostico_autorreprentacao",
                "problema": lacuna,
                "tipo_problema": "lacuna",
                "necessidade": "investigar_lacuna",
                "prioridade": "indeterminada",
                "motivo": (
                    "O diagnóstico encontrou uma lacuna sem "
                    "mapeamento específico nesta camada."
                ),
            }

        return {
            "origem": "diagnostico_autorreprentacao",
            "problema": lacuna,
            "tipo_problema": "lacuna",
            "tipo": dados["tipo"],
            "necessidade": dados["necessidade"],
            "prioridade": self._prioridade_lacuna(lacuna),
            "motivo": dados["motivo"],
        }

    # ============================================================
    # INCONSISTÊNCIAS
    # ============================================================

    def _necessidade_de_inconsistencia(
        self,
        inconsistencia: str,
    ) -> dict[str, Any]:
        return {
            "origem": "diagnostico_autorreprentacao",
            "problema": inconsistencia,
            "tipo_problema": "inconsistencia",
            "tipo": "integridade_autorreprentacao",
            "necessidade": "investigar_inconsistencia",
            "prioridade": "alta",
            "motivo": (
                "Existe uma contradição explícita na "
                "autorrepresentação e ela precisa ser investigada "
                "antes de qualquer evolução."
            ),
        }

    # ============================================================
    # PRIORIDADE ESTRUTURAL
    # ============================================================

    @staticmethod
    def _prioridade_lacuna(
        lacuna: str,
    ) -> str:
        if lacuna in {
            "regras_modificacao_nao_disponiveis",
        }:
            return "alta"

        if lacuna in {
            "identidade_nao_disponivel",
            "componentes_nao_disponiveis",
            "capacidades_nao_disponiveis",
        }:
            return "media"

        return "baixa"

    # ============================================================
    # BARRA DE AÇÃO
    # ============================================================

    def executar_necessidade(
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
                "Esta camada registra necessidades; ela não "
                "executa ações para resolvê-las."
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
                "Esta camada é somente de leitura sobre o "
                "diagnóstico."
            ),
        }


def main() -> None:
    necessidades = NecessidadesInternasNixal()

    print("=" * 60)
    print("NIXAL — NECESSIDADES INTERNAS 56.4.9")
    print("=" * 60)
    print()
    print(necessidades.analisar())


if __name__ == "__main__":
    main()
