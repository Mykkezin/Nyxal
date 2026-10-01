import json


# ============================================================
# MICROETAPA 32
# CURVA COMPLETA + DICIONÁRIO MÍNIMO
#
# Objetivos:
# 1. Medir todas as quantidades de 1 até 49 experiências.
# 2. Encontrar o primeiro ponto exato de economia positiva.
# 3. Construir automaticamente um dicionário mínimo.
# 4. Remover redundâncias.
# 5. Verificar integridade semântica das triplas.
#
# IMPORTANTE:
# A representação continua sendo MANUAL.
# Este teste mede eficiência da estrutura,
# não descoberta autônoma de conhecimento.
# ============================================================


# ============================================================
# CONCEITOS
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
# RELAÇÕES
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
# UTILITÁRIOS
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
    texto = "\n".join(
        item["texto"]
        for item in itens
    )

    return bytes_utf8(texto)


# ============================================================
# CONSTRÓI DICIONÁRIO MÍNIMO
# ============================================================

def construir_dicionario_minimo():
    conceitos_usados = set()
    relacoes_usadas = set()

    for item in EXPERIENCIAS:
        for sujeito_id, relacao_id, objeto_id in item["relacoes"]:
            conceitos_usados.add(sujeito_id)
            conceitos_usados.add(objeto_id)

            nome_relacao = RELACOES[relacao_id]
            relacoes_usadas.add(nome_relacao)

    conceitos_ordenados = sorted(conceitos_usados)

    nomes_relacoes_ordenados = sorted(
        relacoes_usadas
    )

    novos_conceitos = {
        novo_id: CONCEITOS[antigo_id]
        for novo_id, antigo_id
        in enumerate(conceitos_ordenados)
    }

    mapa_conceitos = {
        antigo_id: novo_id
        for novo_id, antigo_id
        in enumerate(conceitos_ordenados)
    }

    novos_relacoes = {
        novo_id: nome
        for novo_id, nome
        in enumerate(nomes_relacoes_ordenados)
    }

    mapa_relacoes = {
        nome: novo_id
        for novo_id, nome
        in enumerate(nomes_relacoes_ordenados)
    }

    return (
        novos_conceitos,
        novos_relacoes,
        mapa_conceitos,
        mapa_relacoes,
    )


# ============================================================
# REMAPEAMENTO
# ============================================================

def remapear_experiencias(
    experiencias,
    mapa_conceitos,
    mapa_relacoes,
):
    resultado = []

    for item in experiencias:
        novas_relacoes = []

        for sujeito_id, relacao_id, objeto_id in item["relacoes"]:
            novo_sujeito = mapa_conceitos[sujeito_id]

            nome_relacao = RELACOES[relacao_id]

            novo_relacao = mapa_relacoes[nome_relacao]

            novo_objeto = mapa_conceitos[objeto_id]

            novas_relacoes.append(
                [
                    novo_sujeito,
                    novo_relacao,
                    novo_objeto,
                ]
            )

        resultado.append(
            {
                "texto": item["texto"],
                "relacoes": novas_relacoes,
            }
        )

    return resultado


# ============================================================
# ASSINATURA SEMÂNTICA
#
# Converte IDs em:
#
# conceito -> relação -> conceito
#
# Isso permite comparar a representação original
# com a representação remapeada sem depender dos números.
# ============================================================

def assinatura_semantica(
    experiencias,
    conceitos,
    relacoes,
):
    resultado = []

    for item in experiencias:
        assinatura_item = []

        for sujeito_id, relacao_id, objeto_id in item["relacoes"]:
            sujeito = conceitos[sujeito_id]
            relacao = relacoes[relacao_id]
            objeto = conceitos[objeto_id]

            assinatura_item.append(
                (
                    sujeito,
                    relacao,
                    objeto,
                )
            )

        resultado.append(
            assinatura_item
        )

    return resultado


# ============================================================
# MEDIÇÃO
# ============================================================

def medir(
    quantidade,
    experiencias_minimas,
    conceitos_minimos,
    relacoes_minimas,
):
    itens = experiencias_minimas[:quantidade]

    original = tamanho_original(itens)

    dicionario = (
        json_bytes(conceitos_minimos)
        + json_bytes(relacoes_minimas)
    )

    representacoes = [
        item["relacoes"]
        for item in itens
    ]

    representacao = json_bytes(
        representacoes
    )

    total = dicionario + representacao

    if original == 0:
        economia = 0.0
    else:
        economia = (
            (original - total)
            / original
        ) * 100

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
    print("=== MICROETAPA 32 ===")
    print("CURVA COMPLETA + DICIONÁRIO MÍNIMO")
    print()

    print(
        f"Experiências disponíveis: "
        f"{len(EXPERIENCIAS)}"
    )

    print(
        f"Conceitos no dicionário original: "
        f"{len(CONCEITOS)}"
    )

    print(
        f"Relações no dicionário original: "
        f"{len(RELACOES)}"
    )

    print()

    # --------------------------------------------------------
    # DICIONÁRIO MÍNIMO
    # --------------------------------------------------------

    (
        conceitos_minimos,
        relacoes_minimas,
        mapa_conceitos,
        mapa_relacoes,
    ) = construir_dicionario_minimo()

    experiencias_minimas = remapear_experiencias(
        EXPERIENCIAS,
        mapa_conceitos,
        mapa_relacoes,
    )

    print("=== DICIONÁRIO MÍNIMO ===")

    print(
        f"Conceitos utilizados: "
        f"{len(conceitos_minimos)}"
    )

    print(
        f"Relações utilizadas: "
        f"{len(relacoes_minimas)}"
    )

    print(
        f"Conceitos originais: "
        f"{len(CONCEITOS)}"
    )

    print(
        f"Relações originais: "
        f"{len(RELACOES)}"
    )

    print()

    # --------------------------------------------------------
    # TAMANHO DOS DICIONÁRIOS
    # --------------------------------------------------------

    dicionario_original = (
        json_bytes(CONCEITOS)
        + json_bytes(RELACOES)
    )

    dicionario_minimo = (
        json_bytes(conceitos_minimos)
        + json_bytes(relacoes_minimas)
    )

    print("=== CUSTO FIXO ===")

    print(
        f"Dicionário original: "
        f"{dicionario_original} bytes"
    )

    print(
        f"Dicionário mínimo: "
        f"{dicionario_minimo} bytes"
    )

    diferenca = (
        dicionario_original
        - dicionario_minimo
    )

    print(
        f"Economia do dicionário: "
        f"{diferenca} bytes"
    )

    print()

    # --------------------------------------------------------
    # VERIFICAÇÃO SEMÂNTICA
    # --------------------------------------------------------

    assinatura_original = assinatura_semantica(
        EXPERIENCIAS,
        CONCEITOS,
        RELACOES,
    )

    assinatura_remapeada = assinatura_semantica(
        experiencias_minimas,
        conceitos_minimos,
        relacoes_minimas,
    )

    print("=== INTEGRIDADE SEMÂNTICA ===")

    if assinatura_original == assinatura_remapeada:
        print(
            "PASSOU: o remapeamento preservou "
            "todas as triplas semânticas."
        )
    else:
        print(
            "FALHOU: alguma relação semântica "
            "foi alterada."
        )

    print()

    # --------------------------------------------------------
    # CURVA COMPLETA
    # --------------------------------------------------------

    print("=== CURVA COMPLETA ===")
    print()

    resultados = []

    for quantidade in range(
        1,
        len(experiencias_minimas) + 1,
    ):
        resultado = medir(
            quantidade,
            experiencias_minimas,
            conceitos_minimos,
            relacoes_minimas,
        )

        resultados.append(resultado)

        print(
            f"{quantidade:02d} experiências | "
            f"original: {resultado['original']:4d} B | "
            f"repr.: {resultado['representacao']:4d} B | "
            f"total: {resultado['total']:4d} B | "
            f"economia: {resultado['economia']:7.2f}%"
        )

    print()

    # --------------------------------------------------------
    # PRIMEIRO PONTO POSITIVO
    # --------------------------------------------------------

    positivos = [
        resultado
        for resultado in resultados
        if resultado["economia"] > 0
    ]

    print("=== PONTO DE EQUILÍBRIO ===")

    if positivos:
        primeiro = positivos[0]

        print(
            f"Primeiro ponto positivo: "
            f"{primeiro['quantidade']} experiências"
        )

        print(
            f"Original: "
            f"{primeiro['original']} bytes"
        )

        print(
            f"Total cristalizado: "
            f"{primeiro['total']} bytes"
        )

        print(
            f"Economia: "
            f"{primeiro['economia']:.2f}%"
        )

    else:
        print(
            "Nenhum ponto positivo foi encontrado."
        )

    print()

    # --------------------------------------------------------
    # MELHOR RESULTADO
    # --------------------------------------------------------

    melhor = max(
        resultados,
        key=lambda resultado: resultado["economia"],
    )

    print("=== MELHOR RESULTADO ===")

    print(
        f"Experiências: "
        f"{melhor['quantidade']}"
    )

    print(
        f"Original: "
        f"{melhor['original']} bytes"
    )

    print(
        f"Total cristalizado: "
        f"{melhor['total']} bytes"
    )

    print(
        f"Economia: "
        f"{melhor['economia']:.2f}%"
    )

    print()

    # --------------------------------------------------------
    # ÚLTIMO ESTADO
    # --------------------------------------------------------

    ultimo = resultados[-1]

    print("=== ESTADO FINAL DO CORPUS ===")

    print(
        f"Experiências: "
        f"{ultimo['quantidade']}"
    )

    print(
        f"Texto original: "
        f"{ultimo['original']} bytes"
    )

    print(
        f"Representação estrutural: "
        f"{ultimo['representacao']} bytes"
    )

    print(
        f"Representação total: "
        f"{ultimo['total']} bytes"
    )

    print(
        f"Economia final: "
        f"{ultimo['economia']:.2f}%"
    )


if __name__ == "__main__":
    main()
