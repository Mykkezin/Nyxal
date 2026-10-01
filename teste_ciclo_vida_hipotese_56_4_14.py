#!/usr/bin/env python3

"""
NIXAL — TESTE DO CICLO DE VIDA DA HIPÓTESE

Microetapa 56.4.14
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from nixal_ciclo_vida_hipotese import (
    ESTADO_ENFRAQUECIDA,
    ESTADO_INCONCLUSIVA,
    ESTADO_PROVISORIA,
    ESTADO_REFUTADA,
    ESTADO_SUPORTADA,
    ESTADO_TESTADA,
    CicloVidaHipoteseNixal,
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


def hipotese() -> dict[str, object]:
    return {
        "hipotese": (
            "É possível que existam dependências entre componentes."
        ),
        "estado": ESTADO_PROVISORIA,
        "necessidade": "conhecer_dependencias_arquiteturais",
        "pergunta": (
            "Quais relações de dependência existem?"
        ),
    }


def main() -> None:
    ciclo = CicloVidaHipoteseNixal()

    resultados: list[bool] = []

    hash_antes = hash_planta()

    iniciado = ciclo.iniciar(
        hipotese()
    )

    resultados.append(
        assert_passou(
            "1. hipótese inicia como provisória",
            iniciado.get("estado")
            == ESTADO_PROVISORIA,
        )
    )

    valor_iniciado = iniciado.get(
        "valor",
        {},
    )

    resultados.append(
        assert_passou(
            "2. histórico registra criação",
            len(
                valor_iniciado.get(
                    "historico",
                    [],
                )
            )
            == 1
            and valor_iniciado.get(
                "historico",
                [],
            )[0].get("evento")
            == "hipotese_criada",
        )
    )

    testado = ciclo.registrar_teste(
        valor_iniciado,
        {
            "estado": "teste_concluido",
            "suporte": True,
            "contraria": False,
            "inconclusivo": False,
            "evidencias": [
                {
                    "fonte": "teste_controlado"
                }
            ],
        },
    )

    resultados.append(
        assert_passou(
            "3. registro de teste produz estado testado",
            testado.get("estado")
            == ESTADO_TESTADA,
        )
    )

    valor_testado = testado.get(
        "valor",
        {},
    )

    resultados.append(
        assert_passou(
            "4. histórico preserva o teste",
            len(
                valor_testado.get(
                    "testes",
                    [],
                )
            )
            == 1
            and len(
                valor_testado.get(
                    "historico",
                    [],
                )
            )
            == 2,
        )
    )

    avaliada = ciclo.registrar_avaliacao(
        valor_testado,
        {
            "estado": ESTADO_SUPORTADA,
            "motivo": "Evidência favorável.",
        },
    )

    resultados.append(
        assert_passou(
            "5. avaliação suportada produz estado suportada",
            avaliada.get("estado")
            == ESTADO_SUPORTADA,
        )
    )

    valor_avaliado = avaliada.get(
        "valor",
        {},
    )

    resultados.append(
        assert_passou(
            "6. histórico preserva avaliação",
            len(
                valor_avaliado.get(
                    "avaliacoes",
                    [],
                )
            )
            == 1
            and len(
                valor_avaliado.get(
                    "historico",
                    [],
                )
            )
            == 3,
        )
    )

    resultados.append(
        assert_passou(
            "7. conhecimento permanente continua falso",
            valor_avaliado.get(
                "conhecimento_permanente"
            )
            is False,
        )
    )

    reaberta = ciclo.reabrir(
        valor_avaliado
    )

    resultados.append(
        assert_passou(
            "8. hipótese avaliada pode voltar a provisória",
            reaberta.get("estado")
            == ESTADO_PROVISORIA,
        )
    )

    valor_reaberta = reaberta.get(
        "valor",
        {},
    )

    resultados.append(
        assert_passou(
            "9. reabertura preserva histórico anterior",
            len(
                valor_reaberta.get(
                    "historico",
                    [],
                )
            )
            == 4
            and valor_reaberta.get(
                "historico",
                [],
            )[-1].get("evento")
            == "hipotese_reaberta",
        )
    )

    avaliada_refutada = ciclo.registrar_avaliacao(
        ciclo.registrar_teste(
            valor_reaberta,
            {
                "estado": "teste_concluido_2",
                "suporte": False,
                "contraria": True,
                "inconclusivo": False,
                "evidencias": [
                    {
                        "fonte": "teste_controlado_2"
                    }
                ],
            },
        )["valor"],
        {
            "estado": ESTADO_REFUTADA,
            "motivo": "Evidência contrária.",
        },
    )

    resultados.append(
        assert_passou(
            "10. ciclo permite nova avaliação como refutada",
            avaliada_refutada.get("estado")
            == ESTADO_REFUTADA,
        )
    )

    _ = ESTADO_ENFRAQUECIDA
    _ = ESTADO_INCONCLUSIVA

    bloqueado = ciclo.promover_para_conhecimento(
        avaliada_refutada
    )

    resultados.append(
        assert_passou(
            "11. promoção para conhecimento é bloqueada",
            bloqueado.get("estado")
            == "negado",
        )
    )

    executar = ciclo.executar_teste(
        avaliada_refutada
    )

    resultados.append(
        assert_passou(
            "12. execução de teste é bloqueada",
            executar.get("estado")
            == "negado",
        )
    )

    modificar = ciclo.modificar(
        avaliada_refutada
    )

    resultados.append(
        assert_passou(
            "13. modificação da arquitetura é bloqueada",
            modificar.get("estado")
            == "negado",
        )
    )

    invalidar = ciclo.iniciar(
        {
            "hipotese": "Hipótese já suportada.",
            "estado": ESTADO_SUPORTADA,
        }
    )

    resultados.append(
        assert_passou(
            "14. hipótese não provisória não inicia ciclo",
            invalidar.get("estado")
            == "negado",
        )
    )

    avaliar_sem_teste = ciclo.registrar_avaliacao(
        iniciado["valor"],
        {
            "estado": ESTADO_SUPORTADA,
        },
    )

    resultados.append(
        assert_passou(
            "15. avaliação sem teste é bloqueada",
            avaliar_sem_teste.get("estado")
            == "negado",
        )
    )

    testar_estado_final = ciclo.registrar_teste(
        avaliada_refutada["valor"],
        {
            "estado": "teste_extra",
        },
    )

    resultados.append(
        assert_passou(
            "16. novo teste não é aceito após avaliação final",
            testar_estado_final.get("estado")
            == "negado",
        )
    )

    hash_depois = hash_planta()

    resultados.append(
        assert_passou(
            "17. ciclo não modifica a planta",
            hash_antes == hash_depois,
        )
    )

    primeira = ciclo.iniciar(
        hipotese()
    )
    segunda = ciclo.iniciar(
        hipotese()
    )

    resultados.append(
        assert_passou(
            "18. criação inicial é determinística",
            primeira == segunda,
        )
    )

    resultados.append(
        assert_passou(
            "19. sequência de estados termina em estado explícito",
            avaliada_refutada.get("estado")
            in {
                ESTADO_SUPORTADA,
                ESTADO_REFUTADA,
                ESTADO_ENFRAQUECIDA,
                ESTADO_INCONCLUSIVA,
            },
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
