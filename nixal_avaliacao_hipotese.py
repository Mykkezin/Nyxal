#!/usr/bin/env python3

"""
NIXAL — AVALIAÇÃO DE HIPÓTESES

Microetapa 56.4.13

Responsabilidade:
    Receber uma hipótese provisória e um resultado de teste
    explicitamente fornecido, comparar evidências de suporte e
    evidências contrárias e classificar o resultado.

Classificações possíveis:

    suportada
        As evidências do teste favorecem a hipótese.

    enfraquecida
        O teste apresentou evidência que reduz o suporte à hipótese,
        mas não é suficiente para classificá-la como refutada.

    refutada
        O teste apresenta evidência contrária suficiente para negar
        a hipótese no contexto do teste realizado.

    inconclusiva
        O resultado não permite decidir entre suporte e refutação.

Princípios:
1. A hipótese precisa estar explicitamente marcada como provisória.
2. O resultado do teste precisa ser fornecido externamente.
3. A camada não executa testes.
4. A camada não inventa evidências.
5. A camada não transforma resultado em conhecimento permanente.
6. A camada não modifica a arquitetura.
7. Uma classificação depende do resultado observado e de seus
   critérios explícitos.
"""

from __future__ import annotations

from typing import Any


ESTADO_SUPORTADA = "suportada"
ESTADO_ENFRAQUECIDA = "enfraquecida"
ESTADO_REFUTADA = "refutada"
ESTADO_INCONCLUSIVA = "inconclusiva"


class AvaliacaoHipoteseNixal:
    """Avalia hipóteses com base em resultados de teste fornecidos."""

    FONTE = "avaliacao_hipotese_nixal"

    def avaliar(
        self,
        hipotese: dict[str, Any],
        resultado_teste: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(
            hipotese,
            dict,
        ):
            return self._negado(
                "Hipótese inválida."
            )

        if not isinstance(
            resultado_teste,
            dict,
        ):
            return self._negado(
                "Resultado de teste inválido."
            )

        texto_hipotese = hipotese.get(
            "hipotese"
        )

        estado_hipotese = hipotese.get(
            "estado"
        )

        if not isinstance(
            texto_hipotese,
            str,
        ) or not texto_hipotese.strip():
            return self._negado(
                "A hipótese não possui texto válido."
            )

        if estado_hipotese != "provisoria":
            return self._negado(
                "Somente hipóteses explicitamente provisórias "
                "podem ser avaliadas nesta camada."
            )

        estado_teste = resultado_teste.get(
            "estado"
        )

        suporte = resultado_teste.get(
            "suporte"
        )

        contraria = resultado_teste.get(
            "contraria"
        )

        inconclusivo = resultado_teste.get(
            "inconclusivo"
        )

        evidencias = resultado_teste.get(
            "evidencias"
        )

        if not isinstance(
            suporte,
            bool,
        ) or not isinstance(
            contraria,
            bool,
        ) or not isinstance(
            inconclusivo,
            bool,
        ):
            return self._negado(
                "O resultado precisa declarar suporte, contraria "
                "e inconclusivo como booleanos."
            )

        if not isinstance(
            evidencias,
            list,
        ):
            return self._negado(
                "O resultado precisa fornecer uma lista de evidências."
            )

        flags_ativas = sum(
            [
                suporte,
                contraria,
                inconclusivo,
            ]
        )

        if flags_ativas != 1:
            return self._negado(
                "O resultado precisa escolher exatamente uma "
                "classificação de teste."
            )

        evidencias_validas = [
            item
            for item in evidencias
            if isinstance(
                item,
                dict,
            )
        ]

        if not evidencias_validas:
            return {
                "sucesso": True,
                "estado": ESTADO_INCONCLUSIVA,
                "origem": self.FONTE,
                "valor": {
                    "hipotese": texto_hipotese,
                    "estado_anterior": "provisoria",
                    "estado_teste": estado_teste,
                    "evidencias": [],
                    "motivo": (
                        "Nenhuma evidência estruturada foi fornecida; "
                        "o teste permanece inconclusivo."
                    ),
                    "conhecimento_permanente": False,
                },
            }

        if inconclusivo:
            estado_final = ESTADO_INCONCLUSIVA
            motivo = (
                "As evidências não permitem decidir se a hipótese "
                "é suportada ou refutada."
            )

        elif contraria:
            estado_final = ESTADO_REFUTADA
            motivo = (
                "O resultado do teste contém evidência contrária "
                "explícita à hipótese."
            )

        else:
            estado_final = ESTADO_SUPORTADA
            motivo = (
                "O resultado do teste contém evidência que favorece "
                "explicitamente a hipótese."
            )

        return {
            "sucesso": True,
            "estado": estado_final,
            "origem": self.FONTE,
            "valor": {
                "hipotese": texto_hipotese,
                "estado_anterior": "provisoria",
                "estado_teste": estado_teste,
                "evidencias": list(evidencias_validas),
                "motivo": motivo,
                "conhecimento_permanente": False,
            },
        }

    def promover_para_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "Avaliação de hipótese não promove conhecimento permanente."
        )

    def executar_teste(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "Esta camada avalia resultados; ela não executa testes."
        )

    def modificar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A avaliação de hipótese não modifica a arquitetura."
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "avaliacao_hipotese_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    avaliador = AvaliacaoHipoteseNixal()

    hipotese = {
        "hipotese": (
            "É possível que existam dependências entre componentes "
            "ainda não registradas formalmente."
        ),
        "estado": "provisoria",
    }

    resultado_teste = {
        "estado": "teste_concluido",
        "suporte": True,
        "contraria": False,
        "inconclusivo": False,
        "evidencias": [
            {
                "fonte": "teste_arquitetural",
                "descricao": (
                    "Uma relação de uso entre componentes foi "
                    "observada."
                ),
            }
        ],
    }

    print("=" * 60)
    print("NIXAL — AVALIAÇÃO DE HIPÓTESES 56.4.13")
    print("=" * 60)
    print()
    print(
        avaliador.avaliar(
            hipotese,
            resultado_teste,
        )
    )


if __name__ == "__main__":
    main()
