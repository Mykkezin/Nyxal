import json
import struct


# ============================================================
# MICROETAPA 33
# CRISTAL BINÁRIO
#
# Mantém exatamente a mesma estrutura semântica da
# Microetapa 32, mas troca JSON por bytes compactos.
#
# Objetivos:
# 1. Medir o tamanho dos IDs em binário.
# 2. Reconstruir exatamente as triplas.
# 3. Comparar JSON x binário.
# 4. Medir economia total.
#
# Isto ainda é uma representação manual.
# Não é descoberta autônoma da Nixal.
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
    14: "pode_ser_revisada_por",
    15: "pode_conter",
    16: "pode_reduzir",
    17: "pode_explicar",
    18: "pode_gerar_previsao",
    19: "pode_conter_erro",
}


# ============================================================
# CORPUS ESTRUTURAL
# ============================================================

EXPERIENCIAS = [
    [[0, 0, 1]],
    [[0, 1, 2]],
    [[0, 2, 3]],
    [[0, 3, 3]],
    [[0, 4, 16]],
    [[0, 4, 17]],
    [[1, 5, 0]],
    [[2, 6, 0]],
    [[3, 7, 0]],
    [[0, 8, 18]],
    [[0, 9, 9]],
    [[1, 5, 7]],
    [[7, 5, 8]],
    [[8, 5, 0]],
    [[0, 11, 4]],
    [[0, 12, 4]],
    [[5, 13, 6]],
    [[6, 5, 7]],
    [[6, 5, 4]],
    [[3, 10, 15], [0, 3, 3]],
    [[1, 10, 15], [1, 5, 0]],
    [[4, 7, 10]],
    [[10, 13, 6]],
    [[6, 7, 10]],
    [[11, 17, 12]],
    [[0, 17, 12]],
    [[0, 18, 14]],
    [[14, 1, 2]],
    [[2, 5, 13]],
    [[13, 7, 10]],
    [[10, 14, 3], [3, 10, 15]],
    [[3, 10, 15], [3, 16, 9]],
    [[4, 11, 11]],
    [[4, 12, 11]],
    [[11, 18, 14]],
    [[1, 10, 3]],
    [[7, 10, 3]],
    [[4, 10, 3]],
    [[0, 19, 13]],
    [[11, 15, 0]],
    [[12, 5, 0]],
    [[12, 13, 6]],
    [[0, 17, 12]],
    [[6, 16, 9]],
    [[2, 5, 3]],
    [[1, 7, 0]],
    [[1, 10, 15], [1, 12, 0]],
    [[1, 10, 15], [1, 11, 0]],
    [[3, 10, 15], [3, 11, 0]],
]


# ============================================================
# TEXTOS ORIGINAIS
# ============================================================

TEXTOS = [
    "Uma hipótese nasce de uma observação.",
    "Uma hipótese pode ser testada por experimento.",
    "Uma hipótese pode receber evidência.",
    "Uma hipótese pode ser modificada por evidência.",
    "Uma hipótese pode estar correta.",
    "Uma hipótese pode estar incorreta.",
    "Uma observação pode gerar uma hipótese.",
    "Um experimento pode testar uma hipótese.",
    "Uma evidência pode modificar uma hipótese.",
    "Uma hipótese continua sendo provisória.",
    "Uma hipótese precisa lidar com incerteza.",
    "Uma observação pode gerar um dado.",
    "Um dado pode revelar um padrão.",
    "Um padrão pode gerar uma hipótese.",
    "Uma hipótese pode ser apoiada por um resultado.",
    "Uma hipótese pode ser contradita por um resultado.",
    "Uma pergunta pode orientar uma investigação.",
    "Uma investigação pode gerar dados.",
    "Uma investigação pode gerar resultados.",
    "Uma evidência nova pode modificar uma hipótese.",
    "Uma observação nova pode gerar uma hipótese.",
    "Um resultado pode modificar uma conclusão.",
    "Uma conclusão pode orientar uma investigação.",
    "Uma investigação pode modificar uma conclusão.",
    "Uma teoria pode explicar um fenômeno.",
    "Uma hipótese pode explicar um fenômeno.",
    "Uma hipótese pode gerar uma previsão.",
    "Uma previsão pode ser testada por experimento.",
    "Um experimento pode revelar um erro.",
    "Um erro pode modificar uma conclusão.",
    "Uma conclusão pode ser revisada por nova evidência.",
    "Uma nova evidência pode reduzir uma incerteza.",
    "Um resultado pode apoiar uma teoria.",
    "Um resultado pode contradizer uma teoria.",
    "Uma teoria pode gerar uma previsão.",
    "Uma observação pode ser uma evidência.",
    "Um dado pode ser uma evidência.",
    "Um resultado pode ser uma evidência.",
    "Uma hipótese pode conter um erro.",
    "Uma teoria pode conter uma hipótese.",
    "Uma explicação pode gerar uma hipótese.",
    "Uma explicação pode orientar uma investigação.",
    "Uma hipótese pode gerar uma explicação.",
    "Uma investigação pode reduzir uma incerteza.",
    "Um experimento pode gerar uma evidência.",
    "Uma observação pode modificar uma hipótese.",
    "Uma nova observação pode contradizer uma hipótese.",
    "Uma nova observação pode apoiar uma hipótese.",
    "Uma nova evidência pode apoiar uma hipótese.",
]


# ============================================================
# TAMANHOS
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


def tamanho_texto_original():
    return bytes_utf8("\n".join(TEXTOS))


# ============================================================
# CRISTAL JSON
# ============================================================

def cristal_json():
    return json.dumps(
        EXPERIENCIAS,
        separators=(",", ":"),
    ).encode("utf-8")


# ============================================================
# CRISTAL BINÁRIO
#
# Cada tripla:
#
# sujeito = 1 byte
# relação = 1 byte
# objeto  = 1 byte
#
# Total = 3 bytes
#
# Antes de cada experiência armazenamos 1 byte
# com a quantidade de relações daquela experiência.
# ============================================================

def cristal_binario():
    dados = bytearray()

    for experiencia in EXPERIENCIAS:
        quantidade = len(experiencia)

        if quantidade > 255:
            raise ValueError(
                "Uma experiência possui mais de 255 relações."
            )

        dados.append(quantidade)

        for sujeito, relacao, objeto in experiencia:
            if not 0 <= sujeito <= 255:
                raise ValueError(
                    f"ID de conceito inválido: {sujeito}"
                )

            if not 0 <= relacao <= 255:
                raise ValueError(
                    f"ID de relação inválido: {relacao}"
                )

            if not 0 <= objeto <= 255:
                raise ValueError(
                    f"ID de objeto inválido: {objeto}"
                )

            dados.extend(
                struct.pack(
                    "BBB",
                    sujeito,
                    relacao,
                    objeto,
                )
            )

    return bytes(dados)


# ============================================================
# RECONSTRUÇÃO BINÁRIA
# ============================================================

def reconstruir_binario(dados):
    posicao = 0
    experiencias = []

    while posicao < len(dados):
        quantidade = dados[posicao]
        posicao += 1

        experiencia = []

        for _ in range(quantidade):
            if posicao + 3 > len(dados):
                raise ValueError(
                    "Dados binários incompletos."
                )

            sujeito = dados[posicao]
            relacao = dados[posicao + 1]
            objeto = dados[posicao + 2]

            posicao += 3

            experiencia.append(
                [
                    sujeito,
                    relacao,
                    objeto,
                ]
            )

        experiencias.append(experiencia)

    return experiencias


# ============================================================
# CONVERSÃO PARA SEMÂNTICA
# ============================================================

def assinatura_semantica(
    experiencias,
    conceitos,
    relacoes,
):
    resultado = []

    for experiencia in experiencias:
        item = []

        for sujeito_id, relacao_id, objeto_id in experiencia:
            item.append(
                (
                    conceitos[sujeito_id],
                    relacoes[relacao_id],
                    conceitos[objeto_id],
                )
            )

        resultado.append(item)

    return resultado


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=== MICROETAPA 33 ===")
    print("CRISTAL BINÁRIO")
    print()

    tamanho_original = tamanho_texto_original()

    json_dados = cristal_json()
    binario_dados = cristal_binario()

    tamanho_json = len(json_dados)
    tamanho_binario = len(binario_dados)

    tamanho_dicionario = (
        json_bytes(CONCEITOS)
        + json_bytes(RELACOES)
    )

    total_json = (
        tamanho_dicionario
        + tamanho_json
    )

    total_binario = (
        tamanho_dicionario
        + tamanho_binario
    )

    economia_json = (
        (tamanho_original - total_json)
        / tamanho_original
    ) * 100

    economia_binario = (
        (tamanho_original - total_binario)
        / tamanho_original
    ) * 100

    print("=== TAMANHOS ===")

    print(
        f"Texto original: "
        f"{tamanho_original} bytes"
    )

    print(
        f"Dicionário: "
        f"{tamanho_dicionario} bytes"
    )

    print(
        f"Cristal JSON: "
        f"{tamanho_json} bytes"
    )

    print(
        f"Total JSON: "
        f"{total_json} bytes"
    )

    print(
        f"Economia JSON: "
        f"{economia_json:.2f}%"
    )

    print()

    print(
        f"Cristal binário: "
        f"{tamanho_binario} bytes"
    )

    print(
        f"Total binário: "
        f"{total_binario} bytes"
    )

    print(
        f"Economia binária: "
        f"{economia_binario:.2f}%"
    )

    print()

    # --------------------------------------------------------
    # COMPARAÇÃO
    # --------------------------------------------------------

    print("=== COMPARAÇÃO ===")

    print(
        f"JSON -> binário: "
        f"{tamanho_json - tamanho_binario} bytes "
        f"economizados"
    )

    if tamanho_json > 0:
        reducao = (
            (tamanho_json - tamanho_binario)
            / tamanho_json
        ) * 100
    else:
        reducao = 0.0

    print(
        f"Redução da representação: "
        f"{reducao:.2f}%"
    )

    print()

    # --------------------------------------------------------
    # RECONSTRUÇÃO
    # --------------------------------------------------------

    reconstruido = reconstruir_binario(
        binario_dados
    )

    print("=== INTEGRIDADE ===")

    if reconstruido == EXPERIENCIAS:
        print(
            "PASSOU: o cristal binário foi "
            "reconstruído exatamente."
        )
    else:
        print(
            "FALHOU: a reconstrução binária "
            "não é idêntica."
        )

    print()

    # --------------------------------------------------------
    # INTEGRIDADE SEMÂNTICA
    # --------------------------------------------------------

    original_semantico = assinatura_semantica(
        EXPERIENCIAS,
        CONCEITOS,
        RELACOES,
    )

    reconstruido_semantico = assinatura_semantica(
        reconstruido,
        CONCEITOS,
        RELACOES,
    )

    print("=== INTEGRIDADE SEMÂNTICA ===")

    if original_semantico == reconstruido_semantico:
        print(
            "PASSOU: todas as triplas semânticas "
            "foram preservadas."
        )
    else:
        print(
            "FALHOU: alguma relação semântica "
            "foi alterada."
        )

    print()

    # --------------------------------------------------------
    # ESTATÍSTICAS
    # --------------------------------------------------------

    total_relacoes = sum(
        len(experiencia)
        for experiencia in EXPERIENCIAS
    )

    print("=== ESTATÍSTICAS ===")

    print(
        f"Experiências: "
        f"{len(EXPERIENCIAS)}"
    )

    print(
        f"Relações: "
        f"{total_relacoes}"
    )

    print(
        f"Conceitos: "
        f"{len(CONCEITOS)}"
    )

    print(
        f"Relações disponíveis: "
        f"{len(RELACOES)}"
    )

    print(
        f"Bytes por tripla: 3"
    )


if __name__ == "__main__":
    main()
