import struct


# ============================================================
# MICROETAPA 36
# CRISTAL PERSISTENTE INCREMENTAL
#
# Objetivo:
#
# 1. Criar um dicionário base.
# 2. Criar conhecimento base.
# 3. Adicionar deltas incrementais.
# 4. Serializar tudo em um único bloco binário.
# 5. Ler esse bloco novamente.
# 6. Reconstruir todo o conhecimento.
# 7. Verificar igualdade exata.
#
# A ideia é simular uma memória que cresce sem
# reescrever todo o conhecimento anterior.
# ============================================================


# ============================================================
# DICIONÁRIO BASE
# ============================================================

CONCEITOS = {
    "hipótese": 0,
    "observação": 1,
    "experimento": 2,
    "evidência": 3,
    "resultado": 4,
    "pergunta": 5,
    "investigação": 6,
    "dado": 7,
    "padrão": 8,
    "incerteza": 9,
    "conclusão": 10,
    "teoria": 11,
    "explicação": 12,
    "erro": 13,
    "previsão": 14,
    "nova": 15,
    "correta": 16,
    "incorreta": 17,
    "provisória": 18,
}


RELACOES = {
    "nasce_de": 0,
    "pode_ser_testada_por": 1,
    "pode_receber": 2,
    "pode_ser_modificada_por": 3,
    "pode_estar": 4,
    "pode_gerar": 5,
    "pode_testar": 6,
    "pode_modificar": 7,
    "continua_sendo": 8,
    "precisa_lidar_com": 9,
    "tem_caracteristica": 10,
    "pode_ser_apoiada_por": 11,
    "pode_ser_contradita_por": 12,
    "pode_orientar": 13,
    "pode_ser_revisada_por": 14,
    "pode_conter": 15,
    "pode_reduzir": 16,
    "pode_explicar": 17,
    "pode_gerar_previsao": 18,
    "pode_conter_erro": 19,
}


# ============================================================
# CONHECIMENTO BASE
# ============================================================

BASE = [
    (
        "hipótese",
        "nasce_de",
        "observação",
    ),
    (
        "hipótese",
        "pode_ser_testada_por",
        "experimento",
    ),
    (
        "hipótese",
        "pode_receber",
        "evidência",
    ),
    (
        "hipótese",
        "pode_ser_modificada_por",
        "evidência",
    ),
    (
        "hipótese",
        "pode_estar",
        "correta",
    ),
    (
        "hipótese",
        "pode_estar",
        "incorreta",
    ),
]


# ============================================================
# DELTA 1
# ============================================================

DELTA_1 = [
    (
        "observação",
        "pode_gerar",
        "hipótese",
    ),
    (
        "experimento",
        "pode_testar",
        "hipótese",
    ),
    (
        "evidência",
        "pode_modificar",
        "hipótese",
    ),
]


# ============================================================
# DELTA 2
# ============================================================

DELTA_2 = [
    (
        "hipótese",
        "continua_sendo",
        "provisória",
    ),
    (
        "hipótese",
        "precisa_lidar_com",
        "incerteza",
    ),
    (
        "observação",
        "pode_gerar",
        "dado",
    ),
]


# ============================================================
# DELTA 3
# ============================================================

DELTA_3 = [
    (
        "dado",
        "pode_gerar",
        "padrão",
    ),
    (
        "padrão",
        "pode_gerar",
        "hipótese",
    ),
    (
        "hipótese",
        "pode_ser_apoiada_por",
        "resultado",
    ),
]


# ============================================================
# DELTA 4
# ============================================================

DELTA_4 = [
    (
        "hipótese",
        "pode_ser_contradita_por",
        "resultado",
    ),
    (
        "pergunta",
        "pode_orientar",
        "investigação",
    ),
    (
        "investigação",
        "pode_gerar",
        "dado",
    ),
]


# ============================================================
# CONVERSÃO PARA IDs
# ============================================================

def converter_para_ids(
    experiencias,
    conceitos,
    relacoes,
):
    resultado = []

    for sujeito, relacao, objeto in experiencias:
        if sujeito not in conceitos:
            raise ValueError(
                f"Conceito desconhecido: {sujeito}"
            )

        if objeto not in conceitos:
            raise ValueError(
                f"Conceito desconhecido: {objeto}"
            )

        if relacao not in relacoes:
            raise ValueError(
                f"Relação desconhecida: {relacao}"
            )

        resultado.append(
            (
                conceitos[sujeito],
                relacoes[relacao],
                conceitos[objeto],
            )
        )

    return resultado


# ============================================================
# CODIFICAÇÃO DE UM BLOCO DE TRIPLAS
#
# Cada tripla = 3 bytes.
# ============================================================

def codificar_triplas(triplas):
    dados = bytearray()

    if len(triplas) > 255:
        raise ValueError(
            "Mais de 255 triplas no mesmo bloco."
        )

    dados.append(len(triplas))

    for sujeito, relacao, objeto in triplas:
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
# DECODIFICAÇÃO DE UM BLOCO DE TRIPLAS
# ============================================================

def decodificar_triplas(dados, posicao):
    if posicao >= len(dados):
        raise ValueError(
            "Bloco de triplas ausente."
        )

    quantidade = dados[posicao]
    posicao += 1

    triplas = []

    for _ in range(quantidade):
        if posicao + 3 > len(dados):
            raise ValueError(
                "Bloco de triplas incompleto."
            )

        sujeito = dados[posicao]
        relacao = dados[posicao + 1]
        objeto = dados[posicao + 2]

        posicao += 3

        triplas.append(
            (
                sujeito,
                relacao,
                objeto,
            )
        )

    return triplas, posicao


# ============================================================
# FORMATO DO ARQUIVO
#
# CABEÇALHO
#
# NXCP = assinatura
# 01   = versão
#
# depois:
#
# quantidade de blocos
#
# bloco base
# delta 1
# delta 2
# delta 3
# delta 4
#
# O dicionário é compartilhado.
# ============================================================

def construir_arquivo():
    base_ids = converter_para_ids(
        BASE,
        CONCEITOS,
        RELACOES,
    )

    delta_1_ids = converter_para_ids(
        DELTA_1,
        CONCEITOS,
        RELACOES,
    )

    delta_2_ids = converter_para_ids(
        DELTA_2,
        CONCEITOS,
        RELACOES,
    )

    delta_3_ids = converter_para_ids(
        DELTA_3,
        CONCEITOS,
        RELACOES,
    )

    delta_4_ids = converter_para_ids(
        DELTA_4,
        CONCEITOS,
        RELACOES,
    )

    blocos = [
        base_ids,
        delta_1_ids,
        delta_2_ids,
        delta_3_ids,
        delta_4_ids,
    ]

    dados = bytearray()

    # Cabeçalho
    dados.extend(b"NXCP")
    dados.append(1)

    # Quantidade de blocos
    dados.append(len(blocos))

    # Blocos
    for bloco in blocos:
        dados.extend(
            codificar_triplas(bloco)
        )

    return bytes(dados), blocos


# ============================================================
# LEITURA DO ARQUIVO
# ============================================================

def ler_arquivo(dados):
    if len(dados) < 6:
        raise ValueError(
            "Arquivo pequeno demais."
        )

    if dados[0:4] != b"NXCP":
        raise ValueError(
            "Assinatura inválida."
        )

    versao = dados[4]

    if versao != 1:
        raise ValueError(
            f"Versão não suportada: {versao}"
        )

    quantidade_blocos = dados[5]

    posicao = 6

    blocos = []

    for _ in range(quantidade_blocos):
        bloco, posicao = decodificar_triplas(
            dados,
            posicao,
        )

        blocos.append(bloco)

    if posicao != len(dados):
        raise ValueError(
            "Existem bytes extras no arquivo."
        )

    return blocos


# ============================================================
# VOLTAR DE IDs PARA NOMES
# ============================================================

def reconstruir_semantica(
    blocos,
    conceitos,
    relacoes,
):
    conceitos_invertidos = {
        indice: nome
        for nome, indice
        in conceitos.items()
    }

    relacoes_invertidas = {
        indice: nome
        for nome, indice
        in relacoes.items()
    }

    resultado = []

    for bloco in blocos:
        for sujeito_id, relacao_id, objeto_id in bloco:
            resultado.append(
                (
                    conceitos_invertidos[sujeito_id],
                    relacoes_invertidas[relacao_id],
                    conceitos_invertidos[objeto_id],
                )
            )

    return resultado


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print(
        "=== MICROETAPA 36 ==="
    )

    print(
        "CRISTAL PERSISTENTE INCREMENTAL"
    )

    print()

    # --------------------------------------------------------
    # CONHECIMENTO ORIGINAL
    # --------------------------------------------------------

    conhecimento_original = (
        BASE
        + DELTA_1
        + DELTA_2
        + DELTA_3
        + DELTA_4
    )

    print("=== CONHECIMENTO ===")

    print(
        f"Triplas originais: "
        f"{len(conhecimento_original)}"
    )

    print()

    # --------------------------------------------------------
    # CONSTRUIR
    # --------------------------------------------------------

    arquivo, blocos_originais = (
        construir_arquivo()
    )

    print("=== ARQUIVO CRISTAL ===")

    print(
        f"Tamanho total: "
        f"{len(arquivo)} bytes"
    )

    print(
        f"Blocos: "
        f"{len(blocos_originais)}"
    )

    print()

    # --------------------------------------------------------
    # LER
    # --------------------------------------------------------

    blocos_reconstruidos = ler_arquivo(
        arquivo
    )

    print("=== RECONSTRUÇÃO DOS BLOCOS ===")

    if blocos_reconstruidos == blocos_originais:
        print(
            "PASSOU: todos os blocos foram "
            "reconstruídos exatamente."
        )
    else:
        print(
            "FALHOU: os blocos reconstruídos "
            "são diferentes."
        )

    print()

    # --------------------------------------------------------
    # RECONSTRUIR SEMÂNTICA
    # --------------------------------------------------------

    conhecimento_reconstruido = (
        reconstruir_semantica(
            blocos_reconstruidos,
            CONCEITOS,
            RELACOES,
        )
    )

    print("=== INTEGRIDADE SEMÂNTICA ===")

    if (
        conhecimento_reconstruido
        == conhecimento_original
    ):
        print(
            "PASSOU: o conhecimento inteiro "
            "foi reconstruído exatamente."
        )
    else:
        print(
            "FALHOU: o conhecimento reconstruído "
            "não é idêntico ao original."
        )

    print()

    # --------------------------------------------------------
    # CADA BLOCO
    # --------------------------------------------------------

    print("=== CRESCIMENTO POR BLOCO ===")

    for indice, bloco in enumerate(
        blocos_originais,
        start=1,
    ):
        tamanho = len(
            codificar_triplas(bloco)
        )

        print(
            f"Bloco {indice}: "
            f"{len(bloco)} triplas | "
            f"{tamanho} bytes"
        )

    print()

    # --------------------------------------------------------
    # ESTATÍSTICAS
    # --------------------------------------------------------

    print("=== ESTATÍSTICAS ===")

    print(
        f"Conceitos: "
        f"{len(CONCEITOS)}"
    )

    print(
        f"Relações: "
        f"{len(RELACOES)}"
    )

    print(
        f"Blocos: "
        f"{len(blocos_originais)}"
    )

    print(
        f"Triplas: "
        f"{len(conhecimento_original)}"
    )


if __name__ == "__main__":
    main()
