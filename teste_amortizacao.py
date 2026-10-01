import json


# ============================================================
# MICROETAPA 31
# AMORTIZAÇÃO DA CRISTALIZAÇÃO
#
# Objetivo:
# medir quando uma estrutura compartilhada de conceitos +
# relações começa a compensar o custo inicial do dicionário.
#
# A representação continua sendo MANUAL.
# Ainda não é descoberta autônoma pela Nixal.
# ============================================================


# ============================================================
# CONCEITOS REUTILIZÁVEIS
# ============================================================

CONCEITOS = {
    0: "hipótese",
    1: "observação",
    2: "experimento",
    3: "evidência",
    4: "resultado",
    5: "pergunta",
    6: "investigação",
    7: "dado",
    8: "padrão",
    9: "incerteza",
    10: "conclusão",
    11: "teoria",
    12: "explicação",
    13: "erro",
    14: "previsão",
    15: "nova",
    16: "correta",
    17: "incorreta",
    18: "provisória",
}


# ============================================================
# RELAÇÕES REUTILIZÁVEIS
# ============================================================

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
    11: "pode_ser_apoiada_por",
    12: "pode_ser_contradita_por",
    13: "pode_orientar",
    14: "nasce_de",
    15: "pode_conter",
    16: "pode_reduzir",
    17: "pode_explicar",
    18: "pode_gerar_previsao",
    19: "pode_conter_erro",
    20: "pode_ser_revisada_por",
}


# ============================================================
# CORPUS
#
# Cada item possui:
#
# texto original
# representação estrutural
#
# A estrutura usa:
#
# [sujeito_id, relacao_id, objeto_id]
#
# ============================================================

EXPERIENCIAS = [
    {
        "texto": "Uma hipótese nasce de uma observação.",
        "relacoes": [
            [0, 0, 1],
        ],
    },
    {
        "texto": "Uma hipótese pode ser testada por experimento.",
        "relacoes": [
            [0, 1, 2],
        ],
    },
    {
        "texto": "Uma hipótese pode receber evidência.",
        "relacoes": [
            [0, 2, 3],
        ],
    },
    {
        "texto": "Uma hipótese pode ser modificada por evidência.",
        "relacoes": [
            [0, 3, 3],
        ],
    },
    {
        "texto": "Uma hipótese pode estar correta.",
        "relacoes": [
            [0, 4, 16],
        ],
    },
    {
        "texto": "Uma hipótese pode estar incorreta.",
        "relacoes": [
            [0, 4, 17],
        ],
    },
    {
        "texto": "Uma observação pode gerar uma hipótese.",
        "relacoes": [
            [1, 5, 0],
        ],
    },
    {
        "texto": "Um experimento pode testar uma hipótese.",
        "relacoes": [
            [2, 6, 0],
        ],
    },
    {
        "texto": "Uma evidência pode modificar uma hipótese.",
        "relacoes": [
            [3, 7, 0],
        ],
    },
    {
        "texto": "Uma hipótese continua sendo provisória.",
        "relacoes": [
            [0, 8, 18],
        ],
    },
    {
        "texto": "Uma hipótese precisa lidar com incerteza.",
        "relacoes": [
            [0, 9, 9],
        ],
    },
    {
        "texto": "Uma observação pode gerar um dado.",
        "relacoes": [
            [1, 5, 7],
        ],
    },
    {
        "texto": "Um dado pode revelar um padrão.",
        "relacoes": [
            [7, 5, 8],
        ],
    },
    {
        "texto": "Um padrão pode gerar uma hipótese.",
        "relacoes": [
            [8, 5, 0],
        ],
    },
    {
        "texto": "Uma hipótese pode ser apoiada por um resultado.",
        "relacoes": [
            [0, 11, 4],
        ],
    },
    {
        "texto": "Uma hipótese pode ser contradita por um resultado.",
        "relacoes": [
            [0, 12, 4],
        ],
    },
    {
        "texto": "Uma pergunta pode orientar uma investigação.",
        "relacoes": [
            [5, 13, 6],
        ],
    },
    {
        "texto": "Uma investigação pode gerar dados.",
        "relacoes": [
            [6, 5, 7],
        ],
    },
    {
        "texto": "Uma investigação pode gerar resultados.",
        "relacoes": [
            [6, 5, 4],
        ],
    },
    {
        "texto": "Uma evidência nova pode modificar uma hipótese.",
        "relacoes": [
            [3, 10, 15],
            [0, 3, 3],
        ],
    },
    {
        "texto": "Uma observação nova pode gerar uma hipótese.",
        "relacoes": [
            [1, 10, 15],
            [1, 5, 0],
        ],
    },
    {
        "texto": "Um resultado pode modificar uma conclusão.",
        "relacoes": [
            [4, 7, 10],
        ],
    },
    {
        "texto": "Uma conclusão pode orientar uma investigação.",
        "relacoes": [
            [10, 13, 6],
        ],
    },
    {
        "texto": "Uma investigação pode modificar uma conclusão.",
        "relacoes": [
            [6, 7, 10],
        ],
    },
    {
        "texto": "Uma teoria pode explicar um fenômeno.",
        "relacoes": [
            [11, 17, 12],
        ],
    },
    {
        "texto": "Uma hipótese pode explicar um fenômeno.",
        "relacoes": [
            [0, 17, 12],
        ],
    },
    {
        "texto": "Uma hipótese pode gerar uma previsão.",
        "relacoes": [
            [0, 18, 14],
        ],
    },
    {
        "texto": "Uma previsão pode ser testada por experimento.",
        "relacoes": [
            [14, 1, 2],
        ],
    },
    {
        "texto": "Um experimento pode revelar um erro.",
        "relacoes": [
            [2, 5, 13],
        ],
    },
    {
        "texto": "Um erro pode modificar uma conclusão.",
        "relacoes": [
            [13, 7, 10],
        ],
    },
    {
        "texto": "Uma conclusão pode ser revisada por nova evidência.",
        "relacoes": [
            [10, 20, 3],
            [3, 10, 15],
        ],
    },
    {
        "texto": "Uma nova evidência pode reduzir uma incerteza.",
        "relacoes": [
            [3, 10, 15],
            [3, 16, 9],
        ],
    },
    {
        "texto": "Um resultado pode apoiar uma teoria.",
        "relacoes": [
            [4, 11, 11],
        ],
    },
    {
        "texto": "Um resultado pode contradizer uma teoria.",
        "relacoes": [
            [4, 12, 11],
        ],
    },
    {
        "texto": "Uma teoria pode gerar uma previsão.",
        "relacoes": [
            [11, 18, 14],
        ],
    },
    {
        "texto": "Uma observação pode ser uma evidência.",
        "relacoes": [
            [1, 10, 3],
        ],
    },
    {
        "texto": "Um dado pode ser uma evidência.",
        "relacoes": [
            [7, 10, 3],
        ],
    },
    {
        "texto": "Um resultado pode ser uma evidência.",
        "relacoes": [
            [4, 10, 3],
        ],
    },
    {
        "texto": "Uma hipótese pode conter um erro.",
        "relacoes": [
            [0, 19, 13],
        ],
    },
    {
        "texto": "Uma teoria pode conter uma hipótese.",
        "relacoes": [
            [11, 15, 0],
        ],
    },
    {
        "texto": "Uma explicação pode gerar uma hipótese.",
        "relacoes": [
            [12, 5, 0],
        ],
    },
    {
        "texto": "Uma explicação pode orientar uma investigação.",
        "relacoes": [
            [12, 13, 6],
        ],
    },
    {
        "texto": "Uma hipótese pode gerar uma explicação.",
        "relacoes": [
            [0, 17, 12],
        ],
    },
    {
        "texto": "Uma investigação pode reduzir uma incerteza.",
        "relacoes": [
            [6, 16, 9],
        ],
    },
    {
        "texto": "Um experimento pode gerar uma evidência.",
        "relacoes": [
            [2, 5, 3],
        ],
    },
    {
        "texto": "Uma observação pode modificar uma hipótese.",
        "relacoes": [
            [1, 7, 0],
        ],
    },
    {
        "texto": "Uma nova observação pode contradizer uma hipótese.",
        "relacoes": [
            [1, 10, 15],
            [1, 12, 0],
        ],
    },
    {
        "texto": "Uma nova observação pode apoiar uma hipótese.",
        "relacoes": [
            [1, 10, 15],
            [1, 11, 0],
        ],
    },
    {
        "texto": "Uma nova evidência pode apoiar uma hipótese.",
        "relacoes": [
            [3, 10, 15],
            [3, 11, 0],
        ],
    },
]


# ============================================================
# FUNÇÕES
# ============================================================

def bytes_utf8(texto):
    return len(texto.encode("utf-8"))


def json_bytes(objeto):
    texto = json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return bytes_utf8(texto)


def tamanho_original(itens):
    texto = "\n".join(item["texto"] for item in itens)
    return bytes_utf8(texto)


def tamanho_representacao(itens):
    estruturas = [
        item["relacoes"]
        for item in itens
    ]

    return json_bytes(estruturas)


def tamanho_dicionario():
    conceitos = json_bytes(CONCEITOS)
    relacoes = json_bytes(RELACOES)

    return conceitos + relacoes


def porcentagem_economia(original, representacao):
    if original == 0:
        return 0.0

    return ((original - representacao) / original) * 100


def medir(quantidade):
    itens = EXPERIENCIAS[:quantidade]

    original = tamanho_original(itens)

    dicionario = tamanho_dicionario()

    representacao = tamanho_representacao(itens)

    total = dicionario + representacao

    economia = porcentagem_economia(
        original,
        total,
    )

    return {
        "quantidade": quantidade,
        "original": original,
        "dicionario": dicionario,
        "representacao": representacao,
        "total": total,
        "economia": economia,
    }


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=== TESTE DE AMORTIZAÇÃO DA CRISTALIZAÇÃO ===")
    print()

    print(f"Experiências disponíveis: {len(EXPERIENCIAS)}")
    print(
        f"Conceitos compartilhados: {len(CONCEITOS)}"
    )
    print(
        f"Relações compartilhadas: {len(RELACOES)}"
    )
    print()

    print("=== CUSTO FIXO DA ESTRUTURA ===")

    conceitos_bytes = json_bytes(CONCEITOS)
    relacoes_bytes = json_bytes(RELACOES)
    dicionario_bytes = tamanho_dicionario()

    print(
        f"Conceitos: {conceitos_bytes} bytes"
    )
    print(
        f"Relações: {relacoes_bytes} bytes"
    )
    print(
        f"Total fixo: {dicionario_bytes} bytes"
    )
    print()

    print("=== EVOLUÇÃO ===")
    print()

    quantidades = [
        5,
        10,
        15,
        20,
        25,
        30,
        35,
        40,
        45,
        50,
    ]

    resultados = []

    for quantidade in quantidades:
        if quantidade > len(EXPERIENCIAS):
            continue

        resultado = medir(quantidade)
        resultados.append(resultado)

        print(
            f"{quantidade:02d} experiências | "
            f"original: {resultado['original']:4d} B | "
            f"representação: {resultado['representacao']:4d} B | "
            f"total: {resultado['total']:4d} B | "
            f"economia: {resultado['economia']:7.2f}%"
        )

    print()

    # ========================================================
    # PONTO DE EQUILÍBRIO
    # ========================================================

    ponto_equilibrio = None

    for resultado in resultados:
        if resultado["total"] < resultado["original"]:
            ponto_equilibrio = resultado
            break

    print("=== PONTO DE EQUILÍBRIO ===")

    if ponto_equilibrio is None:
        print(
            "O ponto de equilíbrio não foi atingido "
            "dentro deste corpus."
        )
    else:
        print(
            f"Primeiro ponto abaixo do texto original: "
            f"{ponto_equilibrio['quantidade']} experiências"
        )

        print(
            f"Original: "
            f"{ponto_equilibrio['original']} bytes"
        )

        print(
            f"Representação total: "
            f"{ponto_equilibrio['total']} bytes"
        )

        print(
            f"Economia: "
            f"{ponto_equilibrio['economia']:.2f}%"
        )

    print()

    # ========================================================
    # MELHOR RESULTADO DO CORPUS
    # ========================================================

    melhor = min(
        resultados,
        key=lambda resultado: resultado["total"]
        - resultado["original"],
    )

    print("=== MELHOR RESULTADO DO CORPUS ===")

    print(
        f"Experiências: {melhor['quantidade']}"
    )

    print(
        f"Original: {melhor['original']} bytes"
    )

    print(
        f"Representação total: {melhor['total']} bytes"
    )

    print(
        f"Economia: {melhor['economia']:.2f}%"
    )

    print()

    # ========================================================
    # INTEGRIDADE ESTRUTURAL
    # ========================================================

    integridade = True

    for item in EXPERIENCIAS:
        for relacao in item["relacoes"]:
            if len(relacao) != 3:
                integridade = False
                break

            sujeito_id = relacao[0]
            relacao_id = relacao[1]
            objeto_id = relacao[2]

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

    if integridade:
        print(
            "PASSOU: todos os IDs utilizados "
            "apontam para conceitos e relações válidos."
        )
    else:
        print(
            "FALHOU: existe pelo menos uma "
            "relação com ID inválido."
        )

    print()

    # ========================================================
    # CONCLUSÃO AUTOMÁTICA
    # ========================================================

    print("=== CONCLUSÃO DO EXPERIMENTO ===")

    if ponto_equilibrio is not None:
        print(
            "A estrutura compartilhada atingiu "
            "economia positiva dentro deste corpus."
        )
    else:
        print(
            "A estrutura compartilhada ainda não "
            "atingiu economia positiva neste corpus."
        )

    print(
        "A integridade estrutural foi medida "
        "separadamente da economia."
    )


if __name__ == "__main__":
    main()
