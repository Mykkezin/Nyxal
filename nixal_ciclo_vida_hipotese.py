#!/usr/bin/env python3

"""
NIXAL — CICLO DE VIDA DA HIPÓTESE

Microetapa 56.4.14

Responsabilidade:
    Representar as transições formais do estado de uma hipótese
    durante investigação e avaliação.

Estados:
    provisoria
    testada
    suportada
    enfraquecida
    refutada
    inconclusiva

Princípios:
1. A hipótese nasce como provisória.
2. Um teste registrado marca que ela foi testada.
3. A avaliação define o resultado interpretado do teste.
4. O histórico nunca é apagado pela transição seguinte.
5. Uma hipótese avaliada não vira conhecimento permanente.
6. Esta camada não executa testes.
7. Esta camada não modifica a arquitetura.
8. Não inventar evidências ou avaliações ausentes.
"""

from __future__ import annotations

from typing import Any


ESTADO_PROVISORIA = "provisoria"
ESTADO_TESTADA = "testada"
ESTADO_SUPORTADA = "suportada"
ESTADO_ENFRAQUECIDA = "enfraquecida"
ESTADO_REFUTADA = "refutada"
ESTADO_INCONCLUSIVA = "inconclusiva"


class CicloVidaHipoteseNixal:
    """Gerencia somente o estado formal e histórico de uma hipótese."""

    FONTE = "ciclo_vida_hipotese_nixal"

    ESTADOS_FINAIS = {
        ESTADO_SUPORTADA,
        ESTADO_ENFRAQUECIDA,
        ESTADO_REFUTADA,
        ESTADO_INCONCLUSIVA,
    }

    def iniciar(
        self,
        hipotese: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            hipotese,
            dict,
        ):
            return self._negado(
                "Hipótese inválida."
            )

        texto = hipotese.get("hipotese")

        if not isinstance(
            texto,
            str,
        ) or not texto.strip():
            return self._negado(
                "A hipótese precisa possuir texto válido."
            )

        estado_original = hipotese.get(
            "estado",
            ESTADO_PROVISORIA,
        )

        if estado_original != ESTADO_PROVISORIA:
            return self._negado(
                "Somente hipóteses provisórias podem iniciar o ciclo."
            )

        estado = {
            "hipotese": texto,
            "necessidade": hipotese.get(
                "necessidade"
            ),
            "pergunta": hipotese.get(
                "pergunta"
            ),
            "estado_atual": ESTADO_PROVISORIA,
            "historico": [
                {
                    "de": None,
                    "para": ESTADO_PROVISORIA,
                    "evento": "hipotese_criada",
                }
            ],
            "testes": [],
            "avaliacoes": [],
            "conhecimento_permanente": False,
        }

        return {
            "sucesso": True,
            "estado": ESTADO_PROVISORIA,
            "origem": self.FONTE,
            "valor": estado,
        }

    def registrar_teste(
        self,
        ciclo: dict[str, Any],
        resultado_teste: dict[str, Any],
    ) -> dict[str, Any]:
        estado_atual = self._estado_atual(
            ciclo
        )

        if estado_atual is None:
            return self._negado(
                "Ciclo de hipótese inválido."
            )

        if estado_atual in self.ESTADOS_FINAIS:
            return self._negado(
                "Uma hipótese já avaliada não pode receber outro "
                "teste nesta camada."
            )

        if not isinstance(
            resultado_teste,
            dict,
        ):
            return self._negado(
                "Resultado de teste inválido."
            )

        teste = dict(resultado_teste)

        registro = {
            "indice": len(
                ciclo.get(
                    "testes",
                    [],
                )
            ) + 1,
            "estado_anterior": estado_atual,
            "resultado": teste,
        }

        novo_ciclo = self._copiar_ciclo(ciclo)

        novo_ciclo.setdefault(
            "testes",
            [],
        ).append(
            registro
        )

        novo_ciclo.setdefault(
            "historico",
            [],
        ).append(
            {
                "de": estado_atual,
                "para": ESTADO_TESTADA,
                "evento": "teste_registrado",
                "indice_teste": registro["indice"],
            }
        )

        novo_ciclo["estado_atual"] = ESTADO_TESTADA

        return {
            "sucesso": True,
            "estado": ESTADO_TESTADA,
            "origem": self.FONTE,
            "valor": novo_ciclo,
        }

    def registrar_avaliacao(
        self,
        ciclo: dict[str, Any],
        avaliacao: dict[str, Any],
    ) -> dict[str, Any]:
        estado_atual = self._estado_atual(
            ciclo
        )

        if estado_atual not in {
            ESTADO_TESTADA,
        }:
            return self._negado(
                "A avaliação precisa ser registrada após um teste."
            )

        if not isinstance(
            avaliacao,
            dict,
        ):
            return self._negado(
                "Avaliação inválida."
            )

        estado_avaliacao = avaliacao.get(
            "estado"
        )

        estados_permitidos = {
            ESTADO_SUPORTADA,
            ESTADO_ENFRAQUECIDA,
            ESTADO_REFUTADA,
            ESTADO_INCONCLUSIVA,
        }

        if estado_avaliacao not in estados_permitidos:
            return self._negado(
                "Estado de avaliação não reconhecido."
            )

        novo_ciclo = self._copiar_ciclo(ciclo)

        registro = {
            "indice": len(
                novo_ciclo.get(
                    "avaliacoes",
                    [],
                )
            ) + 1,
            "estado_anterior": estado_atual,
            "resultado": dict(avaliacao),
        }

        novo_ciclo.setdefault(
            "avaliacoes",
            [],
        ).append(
            registro
        )

        novo_ciclo.setdefault(
            "historico",
            [],
        ).append(
            {
                "de": estado_atual,
                "para": estado_avaliacao,
                "evento": "hipotese_avaliada",
                "indice_avaliacao": registro["indice"],
            }
        )

        novo_ciclo["estado_atual"] = estado_avaliacao

        return {
            "sucesso": True,
            "estado": estado_avaliacao,
            "origem": self.FONTE,
            "valor": novo_ciclo,
        }

    def reabrir(
        self,
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        estado_atual = self._estado_atual(
            ciclo
        )

        if estado_atual not in self.ESTADOS_FINAIS:
            return self._negado(
                "Somente hipóteses avaliadas podem ser reabertas."
            )

        novo_ciclo = self._copiar_ciclo(ciclo)

        novo_ciclo.setdefault(
            "historico",
            [],
        ).append(
            {
                "de": estado_atual,
                "para": ESTADO_PROVISORIA,
                "evento": "hipotese_reaberta",
            }
        )

        novo_ciclo["estado_atual"] = ESTADO_PROVISORIA

        return {
            "sucesso": True,
            "estado": ESTADO_PROVISORIA,
            "origem": self.FONTE,
            "valor": novo_ciclo,
        }

    def promover_para_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "O ciclo da hipótese não promove conhecimento permanente."
        )

    def executar_teste(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "Esta camada registra testes; não os executa."
        )

    def modificar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "Esta camada não modifica a arquitetura."
        )

    @staticmethod
    def _estado_atual(
        ciclo: dict[str, Any],
    ) -> str | None:
        if not isinstance(
            ciclo,
            dict,
        ):
            return None

        estado = ciclo.get(
            "estado_atual"
        )

        if not isinstance(
            estado,
            str,
        ):
            return None

        return estado

    @staticmethod
    def _copiar_ciclo(
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        import copy

        return copy.deepcopy(ciclo)

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "ciclo_vida_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    ciclo = CicloVidaHipoteseNixal()

    hipotese = {
        "hipotese": (
            "É possível que existam dependências entre componentes."
        ),
        "estado": ESTADO_PROVISORIA,
        "necessidade": "conhecer_dependencias_arquiteturais",
    }

    iniciado = ciclo.iniciar(
        hipotese
    )

    testado = ciclo.registrar_teste(
        iniciado["valor"],
        {
            "estado": "teste_concluido",
            "suporte": True,
        },
    )

    avaliado = ciclo.registrar_avaliacao(
        testado["valor"],
        {
            "estado": ESTADO_SUPORTADA,
            "motivo": "Resultado favorável.",
        },
    )

    print("=" * 60)
    print("NIXAL — CICLO DE VIDA DA HIPÓTESE 56.4.14")
    print("=" * 60)
    print()
    print(avaliado)


if __name__ == "__main__":
    main()
