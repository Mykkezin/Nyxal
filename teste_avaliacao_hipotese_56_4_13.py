#!/usr/bin/env python3

"""
NIXAL — TESTE DA AVALIAÇÃO DE HIPÓTESES

Microetapa 56.4.13
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_avaliacao_hipotese import (
    ESTADO_ENFRAQUECIDA,
    ESTADO_INCONCLUSIVA,
    ESTADO_REFUTADA,
    ESTADO_SUPORTADA,
    AvaliacaoHipoteseNixal,
)


ARQUIVO_PLANTA = (
    Path(__file__).resolve().parent
    / "planta_nixal"
    / "planta.json"
)


def hash_planta() -> str:
    return hashlib.sha256(
        ARQUIVO_PLANTA.read_bytes()
    ).hexdigest()


def assert_passou(
    nome: str,
    condicao: bool,
) -> bool:
    print(
        f"[{'PASS' if condicao else 'FAIL'}] {nome}"
    )
    return condicao


def hipotese_base() -> dict[str, object]:
    return {
        "hipotese": (
            "É possível que existam dependências entre componentes."
        ),
        "estado": "provisoria",
    }


def resultado(
    *,
    suporte: bool,
    contraria: bool,
    inconclusivo: bool,
) -> dict[str, object]:
    return {
        "estado": "teste_concluido",
        "suporte": suporte,
        "contraria": contraria,
        "inconclusivo": inconclusivo,
        "evidencias": [
            {
                "fonte": "teste_controlado",
                "descricao": "Evidência fornecida explicitamente.",
            }
        ],
    }


def main() -> None:
    avaliador = AvaliacaoHipoteseNixal()

    resultados: list[bool] = []
    hash_antes = hash_planta()

    suportada = avaliador.avaliar(
        hipotese_base(),
        resultado(
            suporte=True,
            contraria=False,
            inconclusivo=False,
        ),
    )

    resultados.append(
        assert_passou(
            "1. evidência favorável produz hipótese suportada",
            suportada.get("estado")
            == ESTADO_SUPORTADA,
        )
    )

    refutada = avaliador.avaliar(
        hipotese_base(),
        resultado(
            suporte=False,
            contraria=True,
            inconclusivo=False,
        ),
    )

    resultados.append(
        assert_passou(
            "2. evidência contrária produz hipótese refutada",
            refutada.get("estado")
            == ESTADO_REFUTADA,
        )
    )

    inconclusiva = avaliador.avaliar(
        hipotese_base(),
        resultado(
            suporte=False,
            contraria=False,
            inconclusivo=True,
        ),
    )

    resultados.append(
        assert_passou(
            "3. resultado inconclusivo permanece inconclusivo",
            inconclusiva.get("estado")
            == ESTADO_INCONCLUSIVA,
        )
    )

    sem_evidencia = avaliador.avaliar(
        hipotese_base(),
        {
            "estado": "teste_concluido",
            "suporte": True,
            "contraria": False,
            "inconclusivo": False,
            "evidencias": [],
        },
    )

    resultados.append(
        assert_passou(
            "4. ausência de evidência produz resultado inconclusivo",
            sem_evidencia.get("estado")
            == ESTADO_INCONCLUSIVA,
        )
    )

    resultados.append(
        assert_passou(
            "5. hipótese original é preservada",
            suportada.get(
                "valor",
                {},
            ).get("hipotese")
            == hipotese_base()["hipotese"],
        )
    )

    resultados.append(
        assert_passou(
            "6. estado anterior registrado como provisório",
            suportada.get(
                "valor",
                {},
            ).get("estado_anterior")
            == "provisoria",
        )
    )

    resultados.append(
        assert_passou(
            "7. avaliação não cria conhecimento permanente",
            suportada.get(
                "valor",
                {},
            ).get("conhecimento_permanente")
            is False,
        )
    )

    resultados.append(
        assert_passou(
            "8. evidência é preservada",
            len(
                suportada.get(
                    "valor",
                    {},
                ).get(
                    "evidencias",
                    [],
                )
            )
            == 1,
        )
    )

    hipótese_enfraquecida = {
        "hipotese": "Hipótese de teste.",
        "estado": "provisoria",
    }

    # O estado "enfraquecida" será usado quando uma futura camada
    # de comparação indicar redução de suporte sem refutação.
    _ = ESTADO_ENFRAQUECIDA

    entrada_invalida = avaliador.avaliar(
        hipótese_enfraquecida,
        {
            "estado": "teste_concluido",
            "suporte": True,
            "contraria": True,
            "inconclusivo": False,
            "evidencias": [
                {"fonte": "teste"}
            ],
        },
    )

    resultados.append(
        assert_passou(
            "9. resultado com classificações conflitantes é negado",
            entrada_invalida.get("estado")
            == "negado",
        )
    )

    hipotese_confirmada = {
        "hipotese": "Hipótese já confirmada.",
        "estado": "confirmada",
    }

    resultados.append(
        assert_passou(
            "10. hipótese não provisória não é avaliada",
            avaliador.avaliar(
                hipotese_confirmada,
                resultado(
                    suporte=True,
                    contraria=False,
                    inconclusivo=False,
                ),
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "11. execução do teste é bloqueada",
            avaliador.executar_teste(
                hipotese_base()
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "12. promoção para conhecimento é bloqueada",
            avaliador.promover_para_conhecimento(
                hipotese_base()
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "13. modificação da arquitetura é bloqueada",
            avaliador.modificar(
                hipotese_base()
            ).get("estado")
            == "negado",
        )
    )

    resultados.append(
        assert_passou(
            "14. avaliação não acessa a planta diretamente",
            not hasattr(
                avaliador,
                "caminho_planta",
            ),
        )
    )

    resultados.append(
        assert_passou(
            "15. avaliação não executa capacidades",
            not hasattr(
                avaliador,
                "executar_capacidade",
            ),
        )
    )

    resultado_negado = avaliador.avaliar(
        "hipótese inválida",
        resultado(
            suporte=True,
            contraria=False,
            inconclusivo=False,
        ),
    )

    resultados.append(
        assert_passou(
            "16. hipótese inválida é rejeitada",
            resultado_negado.get("estado")
            == "negado",
        )
    )

    resultado_malformado = avaliador.avaliar(
        hipotese_base(),
        {
            "estado": "teste_concluido",
            "suporte": "sim",
            "contraria": False,
            "inconclusivo": False,
            "evidencias": [
                {"fonte": "teste"}
            ],
        },
    )

    resultados.append(
        assert_passou(
            "17. resultado de teste malformado é rejeitado",
            resultado_malformado.get("estado")
            == "negado",
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "18. avaliação não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    primeira = avaliador.avaliar(
        hipotese_base(),
        resultado(
            suporte=True,
            contraria=False,
            inconclusivo=False,
        ),
    )

    segunda = avaliador.avaliar(
        hipotese_base(),
        resultado(
            suporte=True,
            contraria=False,
            inconclusivo=False,
        ),
    )

    resultados.append(
        assert_passou(
            "19. avaliação é determinística",
            primeira == segunda,
        )
    )

    print()
    print("=" * 60)
    print(
        f"TESTES EXECUTADOS: {len(resultados)}"
    )
    print(
        f"FALHAS: {sum(not resultado for resultado in resultados)}"
    )
    print(
        f"PASSOU: {all(resultados)}"
    )
    print("=" * 60)

    if not all(resultados):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
