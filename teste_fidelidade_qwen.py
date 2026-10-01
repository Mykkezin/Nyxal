import json

from experiencia_qwen import (
    interpretar,
    normalizar_candidato,
    validar_candidato,
)


# ============================================================
# MICROETAPA 43
# FIDELIDADE ESTRUTURAL DO QWEN
#
# O objetivo é medir:
#
#       frase
#         ↓
#       Qwen
#         ↓
#    normalização
#         ↓
# estrutura candidata
#         ↓
# comparação exata
#
# O Qwen NÃO avalia a própria resposta.
#
# As respostas esperadas são definidas externamente
# neste teste.
# ============================================================


TESTES = [
    {
        "texto": "Uma observação pode gerar uma hipótese.",
        "esperado": {
            "sujeito": "observação",
            "relacao": "pode_gerar",
            "objeto": "hipótese",
        },
    },
    {
        "texto": "Um experimento pode testar uma hipótese.",
        "esperado": {
            "sujeito": "experimento",
            "relacao": "pode_testar",
            "objeto": "hipótese",
        },
    },
    {
        "texto": "Uma hipótese pode gerar uma previsão.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_gerar",
            "objeto": "previsão",
        },
    },
    {
        "texto": "Uma hipótese pode receber uma evidência.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_receber",
            "objeto": "evidência",
        },
    },
    {
        "texto": "Uma evidência pode modificar uma hipótese.",
        "esperado": {
            "sujeito": "evidência",
            "relacao": "pode_modificar",
            "objeto": "hipótese",
        },
    },
    {
        "texto": "Uma hipótese pode estar correta.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "correta",
        },
    },
    {
        "texto": "Uma hipótese pode estar incorreta.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "incorreta",
        },
    },
    {
        "texto": "Uma hipótese continua sendo provisória.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "continua_sendo",
            "objeto": "provisória",
        },
    },
    {
        "texto": "Uma hipótese precisa lidar com incerteza.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "precisa_lidar_com",
            "objeto": "incerteza",
        },
    },
    {
        "texto": "Uma hipótese pode ser apoiada por um resultado.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_apoiada_por",
            "objeto": "resultado",
        },
    },
    {
        "texto": "Uma hipótese pode ser contradita por um resultado.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_contradita_por",
            "objeto": "resultado",
        },
    },
]


def executar_teste(numero, teste):
    texto = teste["texto"]
    esperado = teste["esperado"]

    print(f"=== TESTE {numero} ===")
    print(f"Texto: {texto}")
    print()

    try:
        bruto = interpretar(texto)
    except Exception as erro:
        print("RESULTADO: FALHOU")
        print(f"Erro no Qwen: {erro}")
        print()

        return False

    normalizado = normalizar_candidato(
        bruto
    )

    print("Candidato normalizado:")

    print(
        json.dumps(
            normalizado,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()

    valido, motivo = validar_candidato(
        normalizado
    )

    if not valido:
        print("RESULTADO: FALHOU")
        print(
            f"Verificador estrutural: {motivo}"
        )
        print()

        return False

    passou = (
        normalizado == esperado
    )

    if passou:
        print("RESULTADO: PASSOU")
    else:
        print("RESULTADO: FALHOU")

        print()
        print("Esperado:")

        print(
            json.dumps(
                esperado,
                ensure_ascii=False,
                indent=2,
            )
        )

    print()

    return passou


def main():
    print(
        "=== MICROETAPA 43 ==="
    )

    print(
        "FIDELIDADE ESTRUTURAL DO QWEN"
    )

    print()

    total = len(TESTES)
    passaram = 0

    for numero, teste in enumerate(
        TESTES,
        start=1,
    ):
        if executar_teste(
            numero,
            teste,
        ):
            passaram += 1

    falharam = (
        total - passaram
    )

    cobertura = (
        passaram / total
    ) * 100

    print(
        "=== RESULTADO FINAL ==="
    )

    print(
        f"Testes: {total}"
    )

    print(
        f"Passaram: {passaram}"
    )

    print(
        f"Falharam: {falharam}"
    )

    print(
        f"Fidelidade estrutural: "
        f"{cobertura:.2f}%"
    )

    if falharam == 0:
        print(
            "PASSOU: todas as estruturas "
            "coincidiram exatamente com o esperado."
        )
    else:
        print(
            "ATENÇÃO: existem interpretações "
            "que precisam ser analisadas."
        )


if __name__ == "__main__":
    main()
