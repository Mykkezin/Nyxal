#!/usr/bin/env python3

"""
NIXAL — DIAGNÓSTICO DA AUTORREPRESENTAÇÃO

Microetapa 56.4.8

Responsabilidade:
    Analisar a coerência e a completude declarada do modelo interno
    da Nixal sem modificar qualquer parte da arquitetura.

Estados possíveis do diagnóstico:

    coerente
        As informações disponíveis não apresentam contradição.

    incompleto
        Existe uma lacuna explícita ou uma parte relevante ainda
        não declarada.

    inconsistente
        Existem informações que se contradizem.

    desconhecido
        Não há dados suficientes para concluir.

Princípios:
1. Ler somente através do estado composto da autorrepresentação.
2. Não acessar a planta diretamente.
3. Não executar capacidades.
4. Não modificar a planta.
5. Não modificar a autorrepresentação.
6. Não inventar componentes ou fatos ausentes.
7. Distinguir incompletude de inconsistência.
"""

from __future__ import annotations

from typing import Any

from nixal_estado_composicao import (
    EstadoCompostoAutorreprentacaoNixal,
)


ESTADO_COERENTE = "coerente"
ESTADO_INCOMPLETO = "incompleto"
ESTADO_INCONSISTENTE = "inconsistente"
ESTADO_DESCONHECIDO = "desconhecido"


class DiagnosticoAutorreprentacaoNixal:
    """Diagnóstico somente leitura da autorrepresentação."""

    FONTE = "diagnostico_autorreprentacao"

    def __init__(
        self,
        estado: EstadoCompostoAutorreprentacaoNixal | None = None,
    ) -> None:
        self.estado = (
            estado
            if estado is not None
            else EstadoCompostoAutorreprentacaoNixal()
        )

    # ============================================================
    # DIAGNÓSTICO PRINCIPAL
    # ============================================================

    def diagnosticar(self) -> dict[str, Any]:
        snapshot = self.estado.construir()

        if snapshot.get("estado") != "conhecido":
            return self._resultado(
                ESTADO_DESCONHECIDO,
                [],
                ["O estado composto não está disponível."],
            )

        valor = snapshot.get("valor")

        if not isinstance(valor, dict):
            return self._resultado(
                ESTADO_DESCONHECIDO,
                [],
                ["O estado composto possui estrutura inválida."],
            )

        achados: list[dict[str, Any]] = []
        inconsistencias: list[str] = []
        lacunas: list[str] = []

        self._verificar_identidade(
            valor,
            inconsistencias,
            lacunas,
            achados,
        )

        self._verificar_estado_arquitetura(
            valor,
            inconsistencias,
            lacunas,
            achados,
        )

        self._verificar_componentes(
            valor,
            inconsistencias,
            lacunas,
            achados,
        )

        self._verificar_capacidades(
            valor,
            inconsistencias,
            lacunas,
            achados,
        )

        self._verificar_limites(
            valor,
            inconsistencias,
            lacunas,
            achados,
        )

        self._verificar_regras(
            valor,
            inconsistencias,
            lacunas,
            achados,
        )

        # Dependências estruturais ainda não estão declaradas
        # explicitamente na planta atual. Isso é uma lacuna,
        # não uma contradição.
        estado_componentes = valor.get(
            "componentes"
        )

        componentes_valor = (
            estado_componentes.get("valor")
            if isinstance(
                estado_componentes,
                dict,
            )
            else None
        )

        if isinstance(componentes_valor, list) and componentes_valor:
            lacunas.append(
                "dependencias_arquiteturais_nao_declaradas"
            )
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "dependencias_arquiteturais",
                    "estado": ESTADO_INCOMPLETO,
                    "motivo": (
                        "A planta atual não declara relações de "
                        "dependência arquitetural."
                    ),
                }
            )

        if inconsistencias:
            estado_final = ESTADO_INCONSISTENTE
        elif lacunas:
            estado_final = ESTADO_INCOMPLETO
        else:
            estado_final = ESTADO_COERENTE

        return {
            "sucesso": True,
            "estado": estado_final,
            "origem": self.FONTE,
            "valor": {
                "inconsistencias": list(inconsistencias),
                "lacunas": list(lacunas),
                "achados": list(achados),
            },
        }

    # ============================================================
    # IDENTIDADE
    # ============================================================

    def _verificar_identidade(
        self,
        valor: dict[str, Any],
        inconsistencias: list[str],
        lacunas: list[str],
        achados: list[dict[str, Any]],
    ) -> None:
        identidade = valor.get("identidade")

        if not isinstance(identidade, dict):
            lacunas.append("identidade_nao_disponivel")
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "identidade",
                    "estado": ESTADO_INCOMPLETO,
                }
            )
            return

        identidade_valor = identidade.get("valor")

        if not isinstance(identidade_valor, dict):
            lacunas.append("identidade_sem_valor")
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "identidade",
                    "estado": ESTADO_INCOMPLETO,
                }
            )
            return

        if not isinstance(
            identidade_valor.get("nome"),
            str,
        ) or not identidade_valor.get("nome", "").strip():
            lacunas.append("nome_nao_declarado")
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "identidade.nome",
                    "estado": ESTADO_INCOMPLETO,
                }
            )

        if not isinstance(
            identidade_valor.get("versao_arquitetura"),
            str,
        ) or not identidade_valor.get(
            "versao_arquitetura",
            "",
        ).strip():
            lacunas.append(
                "versao_arquitetura_nao_declarada"
            )
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "identidade.versao_arquitetura",
                    "estado": ESTADO_INCOMPLETO,
                }
            )

    # ============================================================
    # ESTADO DA ARQUITETURA
    # ============================================================

    def _verificar_estado_arquitetura(
        self,
        valor: dict[str, Any],
        inconsistencias: list[str],
        lacunas: list[str],
        achados: list[dict[str, Any]],
    ) -> None:
        estado = valor.get("estado_arquitetura")

        if not isinstance(estado, dict):
            lacunas.append(
                "estado_arquitetura_nao_disponivel"
            )
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "estado_arquitetura",
                    "estado": ESTADO_INCOMPLETO,
                }
            )
            return

        estado_valor = estado.get("valor")

        if not isinstance(estado_valor, dict):
            lacunas.append(
                "estado_arquitetura_sem_valor"
            )
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "estado_arquitetura",
                    "estado": ESTADO_INCOMPLETO,
                }
            )
            return

        campos_esperados = (
            "fundacao",
            "camada_conversacional",
            "autorrepresentacao",
            "evolucao_autonoma",
        )

        for campo in campos_esperados:
            if campo not in estado_valor:
                lacunas.append(
                    f"estado_arquitetura_sem_{campo}"
                )
                achados.append(
                    {
                        "tipo": "lacuna",
                        "item": f"estado_arquitetura.{campo}",
                        "estado": ESTADO_INCOMPLETO,
                    }
                )

        if (
            estado_valor.get("camada_conversacional")
            == "iniciada"
        ):
            inconsistencias.append(
                "camada_conversacional_contradiz_estado_da_planta"
            )
            achados.append(
                {
                    "tipo": "inconsistencia",
                    "item": "camada_conversacional",
                    "estado": ESTADO_INCONSISTENTE,
                }
            )

    # ============================================================
    # COMPONENTES
    # ============================================================

    def _verificar_componentes(
        self,
        valor: dict[str, Any],
        inconsistencias: list[str],
        lacunas: list[str],
        achados: list[dict[str, Any]],
    ) -> None:
        componentes_estado = valor.get("componentes")

        if not isinstance(
            componentes_estado,
            dict,
        ):
            lacunas.append("componentes_nao_disponiveis")
            return

        componentes = componentes_estado.get("valor")

        if not isinstance(
            componentes,
            list,
        ):
            lacunas.append("componentes_sem_lista")
            return

        ids: list[str] = []

        for componente in componentes:
            if not isinstance(componente, dict):
                inconsistencias.append(
                    "componente_com_estrutura_invalida"
                )
                continue

            componente_id = componente.get("id")

            if (
                not isinstance(
                    componente_id,
                    str,
                )
                or not componente_id.strip()
            ):
                lacunas.append(
                    "componente_sem_id"
                )
            else:
                if componente_id in ids:
                    inconsistencias.append(
                        f"componente_duplicado:{componente_id}"
                    )

                ids.append(componente_id)

            if not isinstance(
                componente.get("arquivo_principal"),
                str,
            ) or not componente.get(
                "arquivo_principal",
                "",
            ).strip():
                lacunas.append(
                    f"componente_sem_arquivo:{componente_id}"
                )

            if not isinstance(
                componente.get("funcao"),
                str,
            ) or not componente.get(
                "funcao",
                "",
            ).strip():
                lacunas.append(
                    f"componente_sem_funcao:{componente_id}"
                )

        if not componentes:
            lacunas.append(
                "nenhum_componente_declarado"
            )
            achados.append(
                {
                    "tipo": "lacuna",
                    "item": "componentes",
                    "estado": ESTADO_INCOMPLETO,
                }
            )

    # ============================================================
    # CAPACIDADES
    # ============================================================

    def _verificar_capacidades(
        self,
        valor: dict[str, Any],
        inconsistencias: list[str],
        lacunas: list[str],
        achados: list[dict[str, Any]],
    ) -> None:
        capacidades_estado = valor.get(
            "capacidades"
        )

        if not isinstance(
            capacidades_estado,
            dict,
        ):
            lacunas.append(
                "capacidades_nao_disponiveis"
            )
            return

        capacidades = capacidades_estado.get(
            "valor"
        )

        if not isinstance(
            capacidades,
            list,
        ):
            lacunas.append(
                "capacidades_sem_lista"
            )
            return

        nomes: list[str] = []

        for capacidade in capacidades:
            if (
                not isinstance(
                    capacidade,
                    str,
                )
                or not capacidade.strip()
            ):
                lacunas.append(
                    "capacidade_com_nome_invalido"
                )
                continue

            if capacidade in nomes:
                inconsistencias.append(
                    f"capacidade_duplicada:{capacidade}"
                )

            nomes.append(capacidade)

        if not capacidades:
            lacunas.append(
                "nenhuma_capacidade_declarada"
            )

    # ============================================================
    # LIMITES
    # ============================================================

    def _verificar_limites(
        self,
        valor: dict[str, Any],
        inconsistencias: list[str],
        lacunas: list[str],
        achados: list[dict[str, Any]],
    ) -> None:
        limites_estado = valor.get("limites")

        if not isinstance(
            limites_estado,
            dict,
        ):
            lacunas.append(
                "limites_nao_disponiveis"
            )
            return

        limites = limites_estado.get(
            "valor"
        )

        if not isinstance(
            limites,
            list,
        ):
            lacunas.append(
                "limites_sem_lista"
            )
            return

        if not limites:
            lacunas.append(
                "nenhuma_limitacao_declarada"
            )

    # ============================================================
    # REGRAS DE MODIFICAÇÃO
    # ============================================================

    def _verificar_regras(
        self,
        valor: dict[str, Any],
        inconsistencias: list[str],
        lacunas: list[str],
        achados: list[dict[str, Any]],
    ) -> None:
        regras_estado = valor.get(
            "regras_modificacao"
        )

        if not isinstance(
            regras_estado,
            dict,
        ):
            lacunas.append(
                "regras_modificacao_nao_disponiveis"
            )
            return

        regras = regras_estado.get(
            "valor"
        )

        if not isinstance(
            regras,
            dict,
        ):
            lacunas.append(
                "regras_modificacao_sem_valor"
            )
            return

        campos_esperados = (
            "planta",
            "arquitetura",
            "codigo_fundacional",
            "evolucoes_experimentais",
        )

        for campo in campos_esperados:
            if campo not in regras:
                lacunas.append(
                    f"regra_ausente:{campo}"
                )

        if regras.get("planta") != "somente_leitura":
            inconsistencias.append(
                "regra_de_modificacao_da_planta_insegura"
            )
            achados.append(
                {
                    "tipo": "inconsistencia",
                    "item": "regras_modificacao.planta",
                    "estado": ESTADO_INCONSISTENTE,
                }
            )

    # ============================================================
    # RESULTADO
    # ============================================================

    def _resultado(
        self,
        estado: str,
        inconsistencias: list[str],
        lacunas: list[str],
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": estado,
            "origem": self.FONTE,
            "valor": {
                "inconsistencias": list(inconsistencias),
                "lacunas": list(lacunas),
                "achados": [],
            },
        }


def main() -> None:
    diagnostico = DiagnosticoAutorreprentacaoNixal()

    print("=" * 60)
    print("NIXAL — DIAGNÓSTICO DA AUTORREPRESENTAÇÃO 56.4.8")
    print("=" * 60)
    print()
    print(diagnostico.diagnosticar())


if __name__ == "__main__":
    main()
