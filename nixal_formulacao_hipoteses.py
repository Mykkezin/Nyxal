#!/usr/bin/env python3

"""
NIXAL — FORMULAÇÃO DE HIPÓTESES

Microetapa 56.4.12

Responsabilidade:
    Transformar evidências de uma investigação em hipóteses
    provisórias e explicitamente não confirmadas.

Princípios:
1. A hipótese nasce de evidências já coletadas.
2. Hipótese não é tratada como fato.
3. A camada não executa novas fontes.
4. A camada não valida a própria hipótese.
5. A camada não incorpora conhecimento permanente.
6. A camada não modifica a arquitetura.
7. A camada explicita quando evidências contrárias ainda não foram
   avaliadas.
8. Não inventar evidências.
"""

from __future__ import annotations

from typing import Any


class FormulacaoHipotesesNixal:
    """Formula hipóteses provisórias a partir de uma investigação."""

    FONTE = "formulacao_hipoteses_nixal"

    def formular(
        self,
        investigacao: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            investigacao,
            dict,
        ):
            return self._negado(
                "Investigação inválida."
            )

        pergunta = investigacao.get("pergunta")
        necessidade = investigacao.get("necessidade")

        valor = investigacao.get("valor")

        if isinstance(valor, dict):
            evidencias = valor.get("evidencias")
        else:
            evidencias = investigacao.get(
                "evidencias"
            )

        if not isinstance(
            pergunta,
            str,
        ) or not pergunta.strip():
            return self._desconhecido(
                "A investigação não possui pergunta válida."
            )

        if not isinstance(
            evidencias,
            list,
        ) or not evidencias:
            return self._desconhecido(
                "Não existem evidências suficientes para formular "
                "uma hipótese."
            )

        evidencias_validas = [
            evidencia
            for evidencia in evidencias
            if isinstance(
                evidencia,
                dict,
            )
            and evidencia.get("sucesso") is True
            and evidencia.get("estado")
            == "evidencia_disponivel"
        ]

        if not evidencias_validas:
            return self._desconhecido(
                "As evidências disponíveis não foram confirmadas "
                "como evidência utilizável."
            )

        hipotese = self._construir_hipotese(
            necessidade=necessidade,
            pergunta=pergunta,
            evidencias=evidencias_validas,
        )

        return {
            "sucesso": True,
            "estado": "hipotese_provisoria",
            "origem": self.FONTE,
            "valor": hipotese,
        }

    def _construir_hipotese(
        self,
        necessidade: Any,
        pergunta: str,
        evidencias: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if necessidade == "conhecer_dependencias_arquiteturais":
            texto = (
                "É possível que existam dependências entre os "
                "componentes da arquitetura que ainda não estão "
                "registradas formalmente na planta."
            )

            razao = (
                "Existem componentes com arquivos principais "
                "identificados e seu conteúdo pode conter relações "
                "entre partes da arquitetura, mas essa relação ainda "
                "não foi formalmente validada nesta camada."
            )

        else:
            texto = (
                "É possível que as evidências coletadas revelem "
                "informações relevantes para responder à pergunta "
                "de investigação."
            )

            razao = (
                "A hipótese é uma interpretação provisória das "
                "evidências coletadas e ainda precisa ser testada."
            )

        referencias = [
            self._resumo_evidencia(
                evidencia,
                indice,
            )
            for indice, evidencia in enumerate(
                evidencias,
                start=1,
            )
        ]

        return {
            "hipotese": texto,
            "necessidade": necessidade,
            "pergunta": pergunta,
            "estado": "provisoria",
            "tipo": "explicacao_candidata",
            "razao": razao,
            "evidencias_de_suporte": referencias,
            "evidencias_contrarias_conhecidas": [],
            "contrarias_avaliadas": False,
            "confianca": "indeterminada",
            "confirmada": False,
            "testada": False,
        }

    @staticmethod
    def _resumo_evidencia(
        evidencia: dict[str, Any],
        indice: int,
    ) -> dict[str, Any]:
        return {
            "id": f"evidencia_{indice}",
            "fonte": evidencia.get("fonte"),
            "argumentos": evidencia.get(
                "argumentos",
                {},
            ),
        }

    def testar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A hipótese ainda não é testada nesta camada."
        )

    def confirmar_hipotese(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A hipótese não pode ser confirmada nesta camada."
        )

    def incorporar_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A hipótese não é incorporada como conhecimento "
            "permanente nesta camada."
        )

    def modificar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A formulação de hipóteses não modifica a arquitetura."
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "formulacao_hipoteses_nixal",
            "valor": None,
            "motivo": motivo,
        }

    @staticmethod
    def _desconhecido(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "desconhecido",
            "origem": "formulacao_hipoteses_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    formulador = FormulacaoHipotesesNixal()

    investigacao = {
        "necessidade": "conhecer_dependencias_arquiteturais",
        "pergunta": (
            "Quais relações de dependência existem entre os "
            "componentes da minha arquitetura?"
        ),
        "valor": {
            "evidencias": [
                {
                    "fonte": "listar_arquivos",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "argumentos": {},
                },
                {
                    "fonte": "ler_arquivo",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "argumentos": {
                        "arquivo": "corpo_nixal.py"
                    },
                },
            ]
        },
    }

    print("=" * 60)
    print("NIXAL — FORMULAÇÃO DE HIPÓTESES 56.4.12")
    print("=" * 60)
    print()
    print(formulador.formular(investigacao))


if __name__ == "__main__":
    main()
