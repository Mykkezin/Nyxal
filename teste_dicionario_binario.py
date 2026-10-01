import json
import struct


# ============================================================
# MICROETAPA 34
# DICIONÁRIO BINÁRIO
#
# Objetivo:
# transformar o dicionário de conceitos e relações
# em uma estrutura binária compacta.
#
# Precisamos provar:
#
# 1. dicionário binário é menor que JSON
# 2. cristal binário continua íntegro
# 3. dicionário binário pode ser reconstruído exatamente
# 4. conceitos e relações continuam semanticamente iguais
# 5. tamanho total da representação diminui
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
# CRISTAL BINÁRIO
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
# FUNÇÕES BÁSICAS
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
    return bytes_utf8(
        "\n".join(TEXTOS)
    )


def serializar_dicionario_json():
    objeto = {
        "conceitos": CONCEITOS,
        "relacoes": RELACOES,
    }

    texto = json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return texto.encode("utf-8")


# ============================================================
# DICIONÁRIO BINÁRIO
#
# FORMATO:
#
# 2 bytes  -> assinatura "NX"
# 1 byte   -> versão
# 1 byte   -> quantidade de conceitos
#
# Para cada conceito:
# 1 byte   -> tamanho da string
# N bytes  -> UTF-8
#
# Depois:
# 1 byte   -> quantidade de relações
#
# Para cada relação:
# 1 byte   -> tamanho da string
# N bytes  -> UTF-8
#
# Os IDs não precisam ser armazenados porque
# a posição define o ID.
# ============================================================

def codificar_dicionario_binario(conceitos, relacoes):
    dados = bytearray()

    # Assinatura
    dados.extend(b"NX")

    # Versão
    dados.append(1)

    # Quantidade de conceitos
    if len(conceitos) > 255:
        raise ValueError(
            "Quantidade de conceitos excede 255."
        )

    dados.append(len(conceitos))

    # Conceitos
    for indice in range(len(conceitos)):
        palavra = conceitos[indice]
        bytes_palavra = palavra.encode("utf-8")

        if len(bytes_palavra) > 255:
            raise ValueError(
                "Um conceito excede 255 bytes."
            )

        dados.append(len(bytes_palavra))
        dados.extend(bytes_palavra)

    # Quantidade de relações
    if len(relacoes) > 255:
        raise ValueError(
            "Quantidade de relações excede 255."
        )

    dados.append(len(relacoes))

    # Relações
    for indice in range(len(relacoes)):
        palavra = relacoes[indice]
        bytes_palavra = palavra.encode("utf-8")

        if len(bytes_palavra) > 255:
            raise ValueError(
                "Uma relação excede 255 bytes."
            )

        dados.append(len(bytes_palavra))
        dados.extend(bytes_palavra)

    return bytes(dados)


# ============================================================
# DECODIFICAÇÃO DO DICIONÁRIO
# ============================================================

def ler_tamanho_e_string(dados, posicao):
    if posicao >= len(dados):
        raise ValueError(
            "Dicionário binário incompleto."
        )

    tamanho = dados[posicao]
    posicao += 1

    fim = posicao + tamanho

    if fim > len(dados):
        raise ValueError(
            "String incompleta no dicionário."
        )

    texto = dados[posicao:fim].decode("utf-8")

    return texto, fim


def decodificar_dicionario_binario(dados):
    if len(dados) < 4:
        raise ValueError(
            "Dicionário binário pequeno demais."
        )

    posicao = 0

    # Assinatura
    if dados[0:2] != b"NX":
        raise ValueError(
            "Assinatura do dicionário inválida."
        )

    posicao = 2

    # Versão
    versao = dados[posicao]
    posicao += 1

    if versao != 1:
        raise ValueError(
            f"Versão não suportada: {versao}"
        )

    # Conceitos
    quantidade_conceitos = dados[posicao]
    posicao += 1

    conceitos = {}

    for indice in range(quantidade_conceitos):
        texto, posicao = ler_tamanho_e_string(
            dados,
            posicao,
        )

        conceitos[indice] = texto

    # Quantidade de relações
    if posicao >= len(dados):
        raise ValueError(
            "Quantidade de relações ausente."
        )

    quantidade_relacoes = dados[posicao]
    posicao += 1

    relacoes = {}

    for indice in range(quantidade_relacoes):
        texto, posicao = ler_tamanho_e_string(
            dados,
            posicao,
        )

        relacoes[indice] = texto

    if posicao != len(dados):
        raise ValueError(
            "Existem bytes extras no dicionário."
        )

    return conceitos, relacoes


# ============================================================
# CRISTAL BINÁRIO
# ============================================================

def codificar_cristal_binario(experiencias):
    dados = bytearray()

    for experiencia in experiencias:
        quantidade = len(experiencia)

        if quantidade > 255:
            raise ValueError(
                "Uma experiência excede 255 relações."
            )

        dados.append(quantidade)

        for sujeito, relacao, objeto in experiencia:
            if not 0 <= sujeito <= 255:
                raise ValueError(
                    f"ID de sujeito inválido: {sujeito}"
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
# RECONSTRUÇÃO DO CRISTAL
# ============================================================

def decodificar_cristal_binario(dados):
    posicao = 0
    experiencias = []

    while posicao < len(dados):
        quantidade = dados[posicao]
        posicao += 1

        experiencia = []

        for _ in range(quantidade):
            if posicao + 3 > len(dados):
                raise ValueError(
                    "Cristal binário incompleto."
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
# ASSINATURA SEMÂNTICA
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
    print("=== MICROETAPA 34 ===")
    print("DICIONÁRIO BINÁRIO")
    print()

    tamanho_original = tamanho_texto_original()

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    dicionario_json = (
        serializar_dicionario_json()
    )

    cristal_json = json.dumps(
        EXPERIENCIAS,
        separators=(",", ":"),
    ).encode("utf-8")

    tamanho_dicionario_json = len(
        dicionario_json
    )

    tamanho_cristal_json = len(
        cristal_json
    )

    total_json = (
        tamanho_dicionario_json
        + tamanho_cristal_json
    )

    economia_json = (
        (tamanho_original - total_json)
        / tamanho_original
    ) * 100

    # --------------------------------------------------------
    # BINÁRIO
    # --------------------------------------------------------

    dicionario_binario = (
        codificar_dicionario_binario(
            CONCEITOS,
            RELACOES,
        )
    )

    cristal_binario = (
        codificar_cristal_binario(
            EXPERIENCIAS
        )
    )

    tamanho_dicionario_binario = len(
        dicionario_binario
    )

    tamanho_cristal_binario = len(
        cristal_binario
    )

    total_binario = (
        tamanho_dicionario_binario
        + tamanho_cristal_binario
    )

    economia_binaria = (
        (tamanho_original - total_binario)
        / tamanho_original
    ) * 100

    # --------------------------------------------------------
    # TAMANHOS
    # --------------------------------------------------------

    print("=== TAMANHOS ===")

    print(
        f"Texto original: "
        f"{tamanho_original} bytes"
    )

    print()

    print("JSON:")

    print(
        f"Dicionário JSON: "
        f"{tamanho_dicionario_json} bytes"
    )

    print(
        f"Cristal JSON: "
        f"{tamanho_cristal_json} bytes"
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

    print("BINÁRIO:")

    print(
        f"Dicionário binário: "
        f"{tamanho_dicionario_binario} bytes"
    )

    print(
        f"Cristal binário: "
        f"{tamanho_cristal_binario} bytes"
    )

    print(
        f"Total binário: "
        f"{total_binario} bytes"
    )

    print(
        f"Economia binária: "
        f"{economia_binaria:.2f}%"
    )

    print()

    # --------------------------------------------------------
    # REDUÇÃO
    # --------------------------------------------------------

    print("=== REDUÇÃO ===")

    reducao_dicionario = (
        (
            tamanho_dicionario_json
            - tamanho_dicionario_binario
        )
        / tamanho_dicionario_json
    ) * 100

    reducao_total = (
        (
            total_json
            - total_binario
        )
        / total_json
    ) * 100

    print(
        f"Redução do dicionário: "
        f"{reducao_dicionario:.2f}%"
    )

    print(
        f"Redução da representação total: "
        f"{reducao_total:.2f}%"
    )

    print()

    # --------------------------------------------------------
    # RECONSTRUÇÃO DO DICIONÁRIO
    # --------------------------------------------------------

    print("=== INTEGRIDADE DO DICIONÁRIO ===")

    (
        conceitos_reconstruidos,
        relacoes_reconstruidas,
    ) = decodificar_dicionario_binario(
        dicionario_binario
    )

    if (
        conceitos_reconstruidos == CONCEITOS
        and relacoes_reconstruidas == RELACOES
    ):
        print(
            "PASSOU: o dicionário binário "
            "foi reconstruído exatamente."
        )
    else:
        print(
            "FALHOU: o dicionário binário "
            "foi alterado durante a reconstrução."
        )

    print()

    # --------------------------------------------------------
    # RECONSTRUÇÃO DO CRISTAL
    # --------------------------------------------------------

    print("=== INTEGRIDADE DO CRISTAL ===")

    cristal_reconstruido = (
        decodificar_cristal_binario(
            cristal_binario
        )
    )

    if cristal_reconstruido == EXPERIENCIAS:
        print(
            "PASSOU: o cristal binário "
            "foi reconstruído exatamente."
        )
    else:
        print(
            "FALHOU: o cristal binário "
            "não foi reconstruído exatamente."
        )

    print()

    # --------------------------------------------------------
    # INTEGRIDADE SEMÂNTICA
    # --------------------------------------------------------

    print("=== INTEGRIDADE SEMÂNTICA ===")

    original_semantico = assinatura_semantica(
        EXPERIENCIAS,
        CONCEITOS,
        RELACOES,
    )

    reconstruido_semantico = assinatura_semantica(
        cristal_reconstruido,
        conceitos_reconstruidos,
        relacoes_reconstruidas,
    )

    if original_semantico == reconstruido_semantico:
        print(
            "PASSOU: todas as relações semânticas "
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


if __name__ == "__main__":
    main()
