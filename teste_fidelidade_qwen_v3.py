import json

from teste_fidelidade_qwen_v2 import (
    interpretar,
    normalizar_candidato,
)


# ============================================================
# MICROETAPA 45
# FIDELIDADE SEMÂNTICA + FIDELIDADE CANÔNICA
#
# Agora separamos duas métricas:
#
# 1. FIDELIDADE SEMÂNTICA
#    O candidato preserva o significado estrutural?
#
# 2. FIDELIDADE CANÔNICA
#    O candidato escolheu exatamente a forma preferencial?
#
# Isso evita tratar uma relação mais específica como
# erro semântico quando ela ainda representa corretamente
# o conhecimento.
#
# O Qwen continua sem ser o juiz.
# ============================================================


TESTES = [
    {
        "texto": "Uma observação pode gerar uma hipótese.",

        "esperado": {
            "sujeito": "observação",
            "relacao": "pode_gerar",
            "objeto": "hipótese",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_gerar",
        ],
    },

    {
        "texto": "Um experimento pode testar uma hipótese.",

        "esperado": {
            "sujeito": "experimento",
            "relacao": "pode_testar",
            "objeto": "hipótese",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_testar",
        ],
    },

    {
        "texto": "Uma hipótese pode gerar uma previsão.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_gerar",
            "objeto": "previsão",
        },

        # As duas representam a mesma direção estrutural:
        #
        # hipótese -> gerar -> previsão
        #
        # "pode_gerar_previsao" é uma forma mais específica.
        "relacoes_semanticamente_aceitas": [
            "pode_gerar",
            "pode_gerar_previsao",
        ],
    },

    {
        "texto": "Uma hipótese pode receber uma evidência.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_receber",
            "objeto": "evidência",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_receber",
        ],
    },

    {
        "texto": "Uma evidência pode modificar uma hipótese.",

        "esperado": {
            "sujeito": "evidência",
            "relacao": "pode_modificar",
            "objeto": "hipótese",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_modificar",
        ],
    },

    {
        "texto": "Uma hipótese pode estar correta.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "correta",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_estar",
        ],
    },

    {
        "texto": "Uma hipótese pode estar incorreta.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "incorreta",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_estar",
        ],
    },

    {
        "texto": "Uma hipótese continua sendo provisória.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "continua_sendo",
            "objeto": "provisória",
        },

        "relacoes_semanticamente_aceitas": [
            "continua_sendo",
        ],
    },

    {
        "texto": "Uma hipótese precisa lidar com incerteza.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "precisa_lidar_com",
            "objeto": "incerteza",
        },

        "relacoes_semanticamente_aceitas": [
            "precisa_lidar_com",
        ],
    },

    {
        "texto": "Uma hipótese pode ser apoiada por um resultado.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_apoiada_por",
            "objeto": "resultado",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_ser_apoiada_por",
        ],
    },

    {
        "texto": "Uma hipótese pode ser contradita por um resultado.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_contradita_por",
            "objeto": "resultado",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_ser_contradita_por",
        ],
    },
]


def avaliar_semantica(
    candidato,
    esperado,
    relacoes_aceitas,
):
    if not isinstance(
        candidato,
        dict,
    ):
        return False

    if (
        candidato.get("sujeito")
        != esperado["sujeito"]
    ):
        return False

    if (
        candidato.get("objeto")
        != esperado["objeto"]
    ):
        return False

    if (
        candidato.get("relacao")
        not in relacoes_aceitas
    ):
        return False

    return True


def executar_teste(
    numero,
    teste,
):
    print(
        f"=== TESTE {numero} ==="
    )

    print(
        f"Texto: {teste['texto']}"
    )

    try:
        bruto = interpretar(
            teste["texto"]
        )

        candidato = normalizar_candidato(
            bruto
        )

    except Exception as erro:
        print(
            "QWEN: FALHOU"
        )

        print(
            f"Erro: {erro}"
        )

        print()

        return False, False

    print(
        "Candidato normalizado:"
    )

    print(
        json.dumps(
            candidato,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()

    # --------------------------------------------------------
    # FIDELIDADE SEMÂNTICA
    # --------------------------------------------------------

    semantica = avaliar_semantica(
        candidato,
        teste["esperado"],
        teste[
            "relacoes_semanticamente_aceitas"
        ],
    )

    if semantica:
        print(
            "FIDELIDADE SEMÂNTICA: PASSOU"
        )
    else:
        print(
            "FIDELIDADE SEMÂNTICA: FALHOU"
        )

    # --------------------------------------------------------
    # FIDELIDADE CANÔNICA
    # --------------------------------------------------------

    canonica = (
        candidato
        == teste["esperado"]
    )

    if canonica:
        print(
            "FIDELIDADE CANÔNICA: PASSOU"
        )
    else:
        print(
            "FIDELIDADE CANÔNICA: FALHOU"
        )

        print()
        print(
            "Canônico esperado:"
        )

        print(
            json.dumps(
                teste["esperado"],
                ensure_ascii=False,
                indent=2,
            )
        )

    print()

    return semantica, canonica


def main():
    print(
        "=== MICROETAPA 45 ==="
    )

    print(
        "FIDELIDADE SEMÂNTICA + CANÔNICA"
    )

    print()

    total = len(TESTES)

    semanticos = 0
    canonicos = 0

    for numero, teste in enumerate(
        TESTES,
        start=1,
    ):
        semantica, canonica = (
            executar_teste(
                numero,
                teste,
            )
        )

        if semantica:
            semanticos += 1

        if canonica:
            canonicos += 1

    semantica_percentual = (
        semanticos / total
    ) * 100

    canonica_percentual = (
        canonicos / total
    ) * 100

    print(
        "=== RESULTADO FINAL ==="
    )

    print(
        f"Testes: {total}"
    )

    print(
        f"Fidelidade semântica: "
        f"{semanticos}/{total} "
        f"({semantica_percentual:.2f}%)"
    )

    print(
        f"Fidelidade canônica: "
        f"{canonicos}/{total} "
        f"({canonica_percentual:.2f}%)"
    )

    print()

    if semanticos == total:
        print(
            "SEMÂNTICA: PASSOU"
        )
    else:
        print(
            "SEMÂNTICA: ainda existem "
            "interpretações incorretas."
        )

    if canonicos == total:
        print(
            "CANÔNICA: PASSOU"
        )
    else:
        print(
            "CANÔNICA: existem formas "
            "estruturalmente equivalentes "
            "ou diferentes do padrão preferencial."
        )


if __name__ == "__main__":
    main()
