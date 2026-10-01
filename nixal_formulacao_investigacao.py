#!/usr/bin/env python3

"""
NIXAL — FORMULAÇÃO DE INVESTIGAÇÃO INTERNA

Microetapa 56.4.10

Responsabilidade:
    Transformar necessidades internas já detectadas em perguntas
    de investigação estruturadas.

Esta camada não investiga e não resolve a necessidade.
Ela somente formula o que precisa ser descoberto.

Princípios:
1. A origem é a camada de necessidades internas.
2. Não acessar a planta diretamente.
3. Não executar capacidades.
4. Não alterar a arquitetura.
5. Não inventar fatos.
6. Não transformar hipótese em fato.
7. Uma pergunta de investigação não é uma ação.
"""

from __future__ import annotations

from typing import Any

from nixal_necessidades_internas import (
    NecessidadesInternasNixal,
)


class FormulacaoInvestigacaoNixal:
    """Formula perguntas internas a partir de necessidades detectadas."""

    FONTE = "formulacao_investigacao_nixal"

    _MAPA_PERGUNTAS: dict[str, dict[str, str]] = {
        "conhecer_dependencias_arquiteturais": {
            "pergunta": (
                "Quais relações de dependência existem entre os "
                "componentes da minha arquitetura?"
            ),
            "tipo_investigacao": "mapeamento_arquitetural",
            "evidencia_necessaria": (
                "Relações explicitamente observadas ou declaradas "
                "entre componentes."
            ),
        },
        "recuperar_identidade": {
            "pergunta": (
                "Qual é a identidade arquitetural atualmente "
                "declarada?"
            ),
            "tipo_investigacao": "identidade",
            "evidencia_necessaria": (
                "Informação explícita sobre a identidade."
            ),
        },
        "recuperar_componentes": {
            "pergunta": (
                "Quais componentes da arquitetura estão atualmente "
                "declarados?"
            ),
            "tipo_investigacao": "mapeamento_arquitetural",
            "evidencia_necessaria": (
                "Lista explícita de componentes."
            ),
        },
        "recuperar_capacidades": {
            "pergunta": (
                "Quais capacidades estão atualmente declaradas "
                "como disponíveis?"
            ),
            "tipo_investigacao": "mapeamento_capacidades",
            "evidencia_necessaria": (
                "Lista explícita de capacidades."
            ),
        },
        "recuperar_limites": {
            "pergunta": (
                "Quais limitações estão atualmente declaradas?"
            ),
            "tipo_investigacao": "limites",
            "evidencia_necessaria": (
                "Lista explícita de limitações."
            ),
        },
        "recuperar_regras_modificacao": {
            "pergunta": (
                "Quais regras atualmente controlam modificações "
                "da arquitetura?"
            ),
            "tipo_investigacao": "seguranca_arquitetural",
            "evidencia_necessaria": (
                "Regras explícitas de modificação."
            ),
        },
        "investigar_inconsistencia": {
            "pergunta": (
                "Qual informação está em contradição e quais "
                "evidências permitem identificar a origem da "
                "contradição?"
            ),
            "tipo_investigacao": "integridade",
            "evidencia_necessaria": (
                "As declarações que apresentam a contradição."
            ),
        },
    }

    def __init__(
        self,
        necessidades: NecessidadesInternasNixal | None = None,
    ) -> None:
        self.necessidades = (
            necessidades
            if necessidades is not None
            else NecessidadesInternasNixal()
        )

    def formular(self) -> dict[str, Any]:
        resultado = self.necessidades.analisar()

        if not isinstance(
            resultado,
            dict,
        ):
            return self._desconhecido(
                "Resposta inválida da camada de necessidades."
            )

        valor = resultado.get("valor")

        if not isinstance(
            valor,
            dict,
        ):
            return self._desconhecido(
                "As necessidades não estão disponíveis."
            )

        necessidades = valor.get("necessidades")

        if not isinstance(
            necessidades,
            list,
        ):
            return self._desconhecido(
                "A lista de necessidades não está disponível."
            )

        investigacoes: list[dict[str, Any]] = []

        for necessidade in necessidades:
            if not isinstance(
                necessidade,
                dict,
            ):
                continue

            nome = necessidade.get("necessidade")

            if not isinstance(
                nome,
                str,
            ):
                continue

            investigacao = self._formular_uma(
                necessidade
            )

            investigacoes.append(
                investigacao
            )

        estado = (
            "investigacoes_formuladas"
            if investigacoes
            else "nenhuma_investigacao_formulada"
        )

        return {
            "sucesso": True,
            "estado": estado,
            "origem": self.FONTE,
            "valor": {
                "origem_necessidades": resultado.get(
                    "estado"
                ),
                "investigacoes": investigacoes,
            },
        }

    def _formular_uma(
        self,
        necessidade: dict[str, Any],
    ) -> dict[str, Any]:
        nome = necessidade.get("necessidade")
        dados = self._MAPA_PERGUNTAS.get(nome)

        if dados is None:
            return {
                "origem": "necessidades_internas_nixal",
                "necessidade": nome,
                "problema": necessidade.get(
                    "problema"
                ),
                "pergunta": (
                    "O que preciso descobrir para compreender "
                    "esta necessidade?"
                ),
                "tipo_investigacao": "indeterminado",
                "evidencia_necessaria": (
                    "Evidência suficiente para caracterizar "
                    "a necessidade."
                ),
                "estado": "necessidade_sem_mapeamento",
            }

        return {
            "origem": "necessidades_internas_nixal",
            "necessidade": nome,
            "problema": necessidade.get(
                "problema"
            ),
            "pergunta": dados["pergunta"],
            "tipo_investigacao": dados[
                "tipo_investigacao"
            ],
            "evidencia_necessaria": dados[
                "evidencia_necessaria"
            ],
            "estado": "formulada",
        }

    def executar_investigacao(
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
                "Esta camada formula perguntas; ela não "
                "executa investigações."
            ),
        }

    def gerar_hipotese(
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
                "Hipóteses ainda não são produzidas nesta camada."
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
                "Esta camada é somente de formulação e "
                "não modifica a arquitetura."
            ),
        }

    @staticmethod
    def _desconhecido(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "desconhecido",
            "origem": "formulacao_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    formulacao = FormulacaoInvestigacaoNixal()

    print("=" * 60)
    print("NIXAL — FORMULAÇÃO DE INVESTIGAÇÃO 56.4.10")
    print("=" * 60)
    print()
    print(formulacao.formular())


if __name__ == "__main__":
    main()
