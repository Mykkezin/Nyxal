from pathlib import Path
import struct


# ============================================================
# MICROETAPA 37
# CRISTAL APPEND-ONLY
#
# Objetivo:
#
# 1. Criar um cristal inicial.
# 2. Fechar o arquivo.
# 3. Reabrir o arquivo.
# 4. Acrescentar um novo bloco no final.
# 5. Fechar novamente.
# 6. Reabrir e verificar o conhecimento acumulado.
#
# O arquivo nunca é reconstruído do zero.
#
# FORMATO:
#
# NXAP
# versão
# bloco 1
# bloco 2
# bloco 3
# ...
#
# Cada bloco:
#
# 1 byte  -> quantidade de triplas
# 3 bytes -> cada tripla
#
# Como não armazenamos a quantidade total de blocos
# no cabeçalho, novos blocos podem ser simplesmente
# acrescentados ao final do arquivo.
# ============================================================


ARQUIVO = Path(
    "experimentos/cristal_nyxal.bin"
)


# ============================================================
# DICIONÁRIO
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
# BLOCOS DE CONHECIMENTO
# ============================================================

BLOCOS = [
    [
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
    ],

    [
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
    ],

    [
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
    ],

    [
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
    ],

    [
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
    ],
]


# ============================================================
# CABEÇALHO
# ============================================================

CABECALHO = b"NXAP" + bytes([1])


# ============================================================
# CONVERTE UMA TRIPLA PARA IDs
# ============================================================

def tripla_para_ids(sujeito, relacao, objeto):
    if sujeito not in CONCEITOS:
        raise ValueError(
            f"Conceito desconhecido: {sujeito}"
        )

    if objeto not in CONCEITOS:
        raise ValueError(
            f"Conceito desconhecido: {objeto}"
        )

    if relacao not in RELACOES:
        raise ValueError(
            f"Relação desconhecida: {relacao}"
        )

    return (
        CONCEITOS[sujeito],
        RELACOES[relacao],
        CONCEITOS[objeto],
    )


# ============================================================
# CODIFICA UM BLOCO
# ============================================================

def codificar_bloco(bloco):
    if len(bloco) > 255:
        raise ValueError(
            "Um bloco não pode possuir mais de 255 triplas."
        )

    dados = bytearray()

    # Quantidade de triplas
    dados.append(len(bloco))

    for sujeito, relacao, objeto in bloco:
        sujeito_id, relacao_id, objeto_id = (
            tripla_para_ids(
                sujeito,
                relacao,
                objeto,
            )
        )

        dados.extend(
            struct.pack(
                "BBB",
                sujeito_id,
                relacao_id,
                objeto_id,
            )
        )

    return bytes(dados)


# ============================================================
# DECODIFICA TODOS OS BLOCOS
# ============================================================

def decodificar_arquivo(dados):
    if len(dados) < len(CABECALHO):
        raise ValueError(
            "Arquivo pequeno demais."
        )

    if dados[:4] != b"NXAP":
        raise ValueError(
            "Assinatura inválida."
        )

    versao = dados[4]

    if versao != 1:
        raise ValueError(
            f"Versão inválida: {versao}"
        )

    posicao = len(CABECALHO)

    blocos = []

    while posicao < len(dados):
        quantidade = dados[posicao]

        posicao += 1

        bloco = []

        for _ in range(quantidade):
            if posicao + 3 > len(dados):
                raise ValueError(
                    "Bloco incompleto."
                )

            sujeito_id = dados[posicao]
            relacao_id = dados[posicao + 1]
            objeto_id = dados[posicao + 2]

            posicao += 3

            bloco.append(
                (
                    sujeito_id,
                    relacao_id,
                    objeto_id,
                )
            )

        blocos.append(bloco)

    return blocos


# ============================================================
# CONVERTE IDs PARA NOMES
# ============================================================

def reconstruir_conhecimento(blocos):
    conceitos_invertidos = {
        indice: nome
        for nome, indice in CONCEITOS.items()
    }

    relacoes_invertidas = {
        indice: nome
        for nome, indice in RELACOES.items()
    }

    conhecimento = []

    for bloco in blocos:
        for sujeito_id, relacao_id, objeto_id in bloco:
            conhecimento.append(
                (
                    conceitos_invertidos[sujeito_id],
                    relacoes_invertidas[relacao_id],
                    conceitos_invertidos[objeto_id],
                )
            )

    return conhecimento


# ============================================================
# CONHECIMENTO ORIGINAL ACUMULADO
# ============================================================

def conhecimento_esperado(quantidade_blocos):
    resultado = []

    for bloco in BLOCOS[:quantidade_blocos]:
        resultado.extend(bloco)

    return resultado


# ============================================================
# VERIFICAÇÃO
# ============================================================

def verificar(quantidade_blocos):
    dados = ARQUIVO.read_bytes()

    blocos = decodificar_arquivo(dados)

    conhecimento = reconstruir_conhecimento(
        blocos
    )

    esperado = conhecimento_esperado(
        quantidade_blocos
    )

    return (
        len(blocos) == quantidade_blocos
        and conhecimento == esperado
    )


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=== MICROETAPA 37 ===")
    print("CRISTAL APPEND-ONLY")
    print()

    ARQUIVO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # LIMPA O EXPERIMENTO ANTERIOR
    # --------------------------------------------------------

    if ARQUIVO.exists():
        ARQUIVO.unlink()

    print(
        f"Arquivo: {ARQUIVO}"
    )

    print()

    # --------------------------------------------------------
    # CRIA O CABEÇALHO
    # --------------------------------------------------------

    with open(
        ARQUIVO,
        "wb",
    ) as arquivo:
        arquivo.write(
            CABECALHO
        )

    print(
        "Cabeçalho criado."
    )

    print()

    # --------------------------------------------------------
    # ADICIONA CADA BLOCO SEPARADAMENTE
    # --------------------------------------------------------

    for indice, bloco in enumerate(
        BLOCOS,
        start=1,
    ):
        dados_bloco = codificar_bloco(
            bloco
        )

        tamanho_antes = ARQUIVO.stat().st_size

        # IMPORTANTE:
        #
        # modo "ab" = append.
        #
        # O conteúdo anterior não é reescrito.
        #
        with open(
            ARQUIVO,
            "ab",
        ) as arquivo:
            arquivo.write(
                dados_bloco
            )

        tamanho_depois = ARQUIVO.stat().st_size

        crescimento = (
            tamanho_depois
            - tamanho_antes
        )

        passou = verificar(
            indice
        )

        print(
            f"Bloco {indice}: "
            f"{len(bloco)} triplas | "
            f"+{crescimento} bytes | "
            f"arquivo: {tamanho_depois} bytes"
        )

        if passou:
            print(
                "  PASSOU: conhecimento acumulado "
                "reconstruído corretamente."
            )
        else:
            print(
                "  FALHOU: conhecimento acumulado "
                "não corresponde ao esperado."
            )

        print()

    # --------------------------------------------------------
    # VERIFICAÇÃO FINAL
    # --------------------------------------------------------

    print("=== VERIFICAÇÃO FINAL ===")

    dados_finais = ARQUIVO.read_bytes()

    blocos_finais = decodificar_arquivo(
        dados_finais
    )

    conhecimento_final = (
        reconstruir_conhecimento(
            blocos_finais
        )
    )

    conhecimento_original = []

    for bloco in BLOCOS:
        conhecimento_original.extend(
            bloco
        )

    if (
        conhecimento_final
        == conhecimento_original
    ):
        print(
            "PASSOU: o cristal persistente "
            "foi reconstruído exatamente."
        )
    else:
        print(
            "FALHOU: o cristal persistente "
            "não corresponde ao original."
        )

    print()

    # --------------------------------------------------------
    # ESTATÍSTICAS
    # --------------------------------------------------------

    tamanho_final = ARQUIVO.stat().st_size

    print("=== ESTATÍSTICAS ===")

    print(
        f"Tamanho final: "
        f"{tamanho_final} bytes"
    )

    print(
        f"Blocos: "
        f"{len(blocos_finais)}"
    )

    print(
        f"Triplas: "
        f"{len(conhecimento_final)}"
    )

    print(
        f"Arquivo existe: "
        f"{ARQUIVO.exists()}"
    )


if __name__ == "__main__":
    main()
