import json

import ollama


# ============================================================
# MICROETAPA 48
# TESTE ISOLADO DE MODALIDADE
# ============================================================

MODELO = "qwen2:7b"

TEMPERATURAS = [
    0.0,
    0.3,
    0.7,
]

MODALIDADES_PERMITIDAS = {
    "possibilidade",
    "necessidade",
    "não_necessidade",
    "negação",
}


TESTES = [
    {
        "id": 1,
        "texto": "Uma hipótese pode estar correta.",
        "esperado": "possibilidade",
    },
    {
        "id": 2,
        "texto": "É possível que uma hipótese esteja correta.",
        "esperado": "possibilidade",
    },
    {
        "id": 3,
        "texto": "Uma hipótese não precisa estar correta.",
        "esperado": "não_necessidade",
    },
    {
        "id": 4,
        "texto": "Não é necessário que uma hipótese esteja correta.",
        "esperado": "não_necessidade",
    },
    {
        "id": 5,
        "texto": "Uma hipótese pode estar incorreta.",
        "esperado": "possibilidade",
    },
    {
        "id": 6,
        "texto": "Uma hipótese precisa lidar com incerteza.",
        "esperado": "necessidade",
    },
    {
        "id": 7,
        "texto": "Uma hipótese não está correta.",
        "esperado": "negação",
    },
]


def criar_prompt(texto):
    return f"""
Classifique somente a modalidade lógica da frase abaixo.

Modalidades permitidas:
- possibilidade
- necessidade
- não_necessidade
- negação

Definições:

possibilidade:
A frase apresenta algo como possível, podendo ocorrer ou ser verdadeiro.

necessidade:
A frase apresenta algo como necessário, obrigatório ou que deve ocorrer.

não_necessidade:
A frase afirma que algo não é necessário ou não precisa ocorrer.

negação:
A frase afirma diretamente que algo não ocorre, não é ou não está em determinado estado.

Regras:
1. Responda somente com JSON válido.
2. Use exatamente a chave "modalidade".
3. O valor deve ser exatamente uma modalidade permitida.
4. Não explique.
5. Não invente informação.
6. Não transforme não_necessidade em possibilidade.

Formato:

{{
  "modalidade": "..."
}}

Frase:

{texto}
""".strip()


def interpretar(texto, temperatura):
    resposta = ollama.chat(
        model=MODELO,
        format="json",
        options={
            "temperature": temperatura,
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um classificador rigoroso "
                    "de modalidade lógica."
                ),
            },
            {
                "role": "user",
                "content": criar_prompt(texto),
            },
        ],
    )

    bruto = resposta["message"]["content"].strip()

    try:
        candidato = json.loads(bruto)
    except json.JSONDecodeError:
        return {
            "status": "ERRO_JSON",
            "bruto": bruto,
        }

    if not isinstance(candidato, dict):
        return {
            "status": "ERRO_ESTRUTURA",
            "bruto": bruto,
        }

    modalidade = candidato.get("modalidade")

    if modalidade not in MODALIDADES_PERMITIDAS:
        return {
            "status": "MODALIDADE_INVALIDA",
            "modalidade": modalidade,
            "bruto": bruto,
        }

    return {
        "status": "OK",
        "modalidade": modalidade,
        "bruto": bruto,
    }


def executar_teste(teste):
    print()
    print("=" * 70)
    print(f"TESTE {teste['id']}")
    print("=" * 70)

    print(f"Frase: {teste['texto']}")
    print(f"Esperado: {teste['esperado']}")

    resultados = []

    for temperatura in TEMPERATURAS:
        resultado = interpretar(
            teste["texto"],
            temperatura,
        )

        resultados.append(resultado)

        print()
        print(f"Temperatura {temperatura:.1f}")

        print(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
            )
        )

    if any(
        resultado["status"] != "OK"
        for resultado in resultados
    ):
        print()
        print("CONSENSO: NÃO")
        print("BENCHMARK: FALHOU")

        return {
            "consenso": False,
            "correto": False,
        }

    modalidades = [
        resultado["modalidade"]
        for resultado in resultados
    ]

    consenso = all(
        modalidade == modalidades[0]
        for modalidade in modalidades
    )

    correto = all(
        modalidade == teste["esperado"]
        for modalidade in modalidades
    )

    print()
    print(
        "CONSENSO:",
        "SIM" if consenso else "NÃO",
    )

    print(
        "MODALIDADES:",
        ", ".join(modalidades),
    )

    print(
        "BENCHMARK:",
        "PASSOU" if correto else "FALHOU",
    )

    return {
        "consenso": consenso,
        "correto": correto,
    }


def main():
    print("=== MICROETAPA 48 ===")
    print("TESTE ISOLADO DE MODALIDADE")

    total = len(TESTES)

    consensos = 0
    corretos = 0
    aprovados = 0

    for teste in TESTES:
        resultado = executar_teste(teste)

        if resultado["consenso"]:
            consensos += 1

        if resultado["correto"]:
            corretos += 1

        if (
            resultado["consenso"]
            and resultado["correto"]
        ):
            aprovados += 1

    print()
    print("=" * 70)
    print("RESULTADO FINAL")
    print("=" * 70)

    print(f"Testes: {total}")

    print(
        f"Consenso: {consensos}/{total} "
        f"({consensos / total * 100:.2f}%)"
    )

    print(
        f"Benchmark correto: {corretos}/{total} "
        f"({corretos / total * 100:.2f}%)"
    )

    print(
        f"Consenso + benchmark: {aprovados}/{total} "
        f"({aprovados / total * 100:.2f}%)"
    )


if __name__ == "__main__":
    main()
