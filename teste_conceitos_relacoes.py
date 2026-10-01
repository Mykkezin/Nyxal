import json


EXPERIENCIAS = [
    "Uma hipótese nasce de uma observação.",
    "Uma hipótese pode ser testada por experimento.",
    "Uma hipótese pode receber novas evidências.",
    "Uma hipótese pode ser modificada por novas evidências.",
    "Uma hipótese pode estar correta ou incorreta.",
    "Uma observação pode gerar uma hipótese.",
    "Um experimento pode testar uma hipótese.",
    "Novas evidências podem modificar uma hipótese.",
    "Uma hipótese continua sendo provisória.",
    "Uma hipótese precisa lidar com incerteza.",
]


# Conceitos reutilizáveis.
CONCEITOS = {
    0: "hipótese",
    1: "observação",
    2: "experimento",
    3: "evidência",
    4: "nova",
    5: "correta",
    6: "incorreta",
    7: "provisória",
    8: "incerteza",
}


# Relações reutilizáveis.
RELACOES = {
    0: "nasce_de",
    1: "pode_ser_testada_por",
    2: "pode_receber",
    3: "pode_ser_modificada_por",
    4: "pode_estar",
    5: "pode_gerar",
    6: "pode_testar",
    7: "pode_modificar",
    8: "continua_sendo",
    9: "precisa_lidar_com",
    10: "tem_caracteristica",
}


# Cada experiência vira uma ou mais relações:
#
# [sujeito, relação, objeto]
#
# Exemplo:
# hipótese -> nasce_de -> observação
#
REPRESENTACOES = [
    [
        [0, 0, 1]
    ],
    [
        [0, 1, 2]
    ],
    [
        [0, 2, 3],
        [3, 10, 4]
    ],
    [
        [0, 3, 3],
        [3, 10, 4]
    ],
    [
        [0, 4, 5],
        [0, 4, 6]
    ],
    [
        [1, 5, 0]
    ],
    [
        [2, 6, 0]
    ],
    [
        [3, 7, 0]
    ],
    [
        [0, 8, 7]
    ],
    [
        [0, 9, 8]
    ],
]


# Reconstrução canônica.
#
# Observação:
# não estamos tentando reproduzir a frase original palavra por palavra.
# Estamos reconstruindo a estrutura de conhecimento representada.
def reconstruir_relacao(relacao):
    sujeito_id, relacao_id, objeto_id = relacao

    sujeito = CONCEITOS[sujeito_id]
    nome_relacao = RELACOES[relacao_id]
    objeto = CONCEITOS[objeto_id]

    return {
        "sujeito": sujeito,
        "relacao": nome_relacao,
        "objeto": objeto,
    }


def reconstruir_experiencia(representacao):
    return [
        reconstruir_relacao(relacao)
        for relacao in representacao
    ]


def gerar_conhecimento_total():
    return [
        reconstruir_experiencia(representacao)
        for representacao in REPRESENTACOES
    ]


def json_bytes(objeto):
    texto = json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":")
    )
    return len(texto.encode("utf-8"))


def texto_bytes(texto):
    return len(texto.encode("utf-8"))


def main():
    print("=== TESTE DE CONCEITOS + RELAÇÕES ===")
    print()

    # --------------------------------------------------
    # TAMANHO ORIGINAL
    # --------------------------------------------------

    original_texto = "\n".join(EXPERIENCIAS)
    tamanho_original = texto_bytes(original_texto)

    # --------------------------------------------------
    # DICIONÁRIOS
    # --------------------------------------------------

    tamanho_conceitos = json_bytes(CONCEITOS)
    tamanho_relacoes = json_bytes(RELACOES)

    # --------------------------------------------------
    # REPRESENTAÇÃO
    # --------------------------------------------------

    tamanho_representacoes = json_bytes(REPRESENTACOES)

    tamanho_total = (
        tamanho_conceitos
        + tamanho_relacoes
        + tamanho_representacoes
    )

    economia = (
        (tamanho_original - tamanho_total)
        / tamanho_original
    ) * 100

    print("=== TAMANHOS ===")
    print(f"Texto original: {tamanho_original} bytes")
    print(f"Dicionário de conceitos: {tamanho_conceitos} bytes")
    print(f"Dicionário de relações: {tamanho_relacoes} bytes")
    print(f"Representações: {tamanho_representacoes} bytes")
    print(f"Representação total: {tamanho_total} bytes")
    print(f"Economia total: {economia:.2f}%")
    print()

    # --------------------------------------------------
    # CONCEITOS
    # --------------------------------------------------

    print("=== CONCEITOS ===")

    for codigo, conceito in CONCEITOS.items():
        print(f"{codigo}: {conceito}")

    print()

    # --------------------------------------------------
    # RELAÇÕES
    # --------------------------------------------------

    print("=== RELAÇÕES ===")

    for codigo, relacao in RELACOES.items():
        print(f"{codigo}: {relacao}")

    print()

    # --------------------------------------------------
    # RECONSTRUÇÃO
    # --------------------------------------------------

    print("=== RECONSTRUÇÃO ===")

    conhecimento = gerar_conhecimento_total()

    for indice, experiencia in enumerate(conhecimento, start=1):
        print(f"{indice:02d}:")

        for relacao in experiencia:
            print(
                f"    {relacao['sujeito']} "
                f"--{relacao['relacao']}--> "
                f"{relacao['objeto']}"
            )

    print()

    # --------------------------------------------------
    # INTEGRIDADE
    # --------------------------------------------------

    reconstruido = gerar_conhecimento_total()

    # Como a representação é construída diretamente
    # pelos IDs, verificamos se todos os IDs utilizados
    # apontam para conceitos e relações existentes.
    integridade = True

    for experiencia in REPRESENTACOES:
        for relacao in experiencia:
            if len(relacao) != 3:
                integridade = False
                break

            sujeito_id, relacao_id, objeto_id = relacao

            if sujeito_id not in CONCEITOS:
                integridade = False
                break

            if relacao_id not in RELACOES:
                integridade = False
                break

            if objeto_id not in CONCEITOS:
                integridade = False
                break

        if not integridade:
            break

    print("=== INTEGRIDADE ===")

    if integridade and len(reconstruido) == len(EXPERIENCIAS):
        print("PASSOU: todas as relações foram reconstruídas.")
    else:
        print("FALHOU: a representação possui inconsistências.")

    print()

    # --------------------------------------------------
    # COMPARAÇÃO CONCEITUAL
    # --------------------------------------------------

    total_relacoes = sum(
        len(experiencia)
        for experiencia in REPRESENTACOES
    )

    print("=== ESTRUTURA ===")
    print(f"Experiências originais: {len(EXPERIENCIAS)}")
    print(f"Relações armazenadas: {total_relacoes}")
    print(f"Conceitos reutilizáveis: {len(CONCEITOS)}")
    print(f"Relações reutilizáveis: {len(RELACOES)}")


if __name__ == "__main__":
    main()
