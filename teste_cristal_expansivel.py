from pathlib import Path
import struct


# ============================================================
# MICROETAPA 38
# CRISTAL EXPANSÍVEL
#
# Objetivo:
#
# 1. Criar um dicionário inicial.
# 2. Criar conhecimento inicial.
# 3. Reutilizar conhecimento existente.
# 4. Adicionar um conceito novo.
# 5. Adicionar uma relação nova.
# 6. Adicionar conceito + relação novos.
# 7. Nunca alterar os IDs antigos.
# 8. Persistir tudo por APPEND.
# 9. Fechar e reabrir o arquivo após cada etapa.
# 10. Reconstruir todo o conhecimento no final.
#
# Este é um teste de expansão do "cristal", não de
# descoberta autônoma.
# ============================================================


ARQUIVO = Path(
    "experimentos/cristal_nyxal_expansivel.bin"
)


# ============================================================
# ESTADO INICIAL
# ============================================================

CONCEITOS_BASE = [
    "hipótese",
    "observação",
    "experimento",
    "evidência",
    "resultado",
    "pergunta",
    "investigação",
    "dado",
    "padrão",
    "incerteza",
    "conclusão",
    "teoria",
    "explicação",
    "erro",
    "previsão",
    "nova",
    "correta",
    "incorreta",
    "provisória",
]


RELACOES_BASE = [
    "nasce_de",
    "pode_ser_testada_por",
    "pode_receber",
    "pode_ser_modificada_por",
    "pode_estar",
    "pode_gerar",
    "pode_testar",
    "pode_modificar",
    "continua_sendo",
    "precisa_lidar_com",
    "tem_caracteristica",
    "pode_ser_apoiada_por",
    "pode_ser_contradita_por",
    "pode_orientar",
    "pode_ser_revisada_por",
    "pode_conter",
    "pode_reduzir",
    "pode_explicar",
    "pode_gerar_previsao",
    "pode_conter_erro",
]


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
]


# ============================================================
# ETAPA 1
#
# Tudo já conhecido.
# Nenhum conceito ou relação novo.
# ============================================================

REUTILIZACAO = [
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
# ETAPA 2
#
# Conceito novo:
#
# modelo
#
# Relação já existente:
#
# pode_gerar_previsao
# ============================================================

NOVO_CONCEITO = [
    (
        "modelo",
        "pode_gerar_previsao",
        "previsão",
    ),
]


# ============================================================
# ETAPA 3
#
# Relação nova:
#
# depende_de
#
# Os dois conceitos já existem.
# ============================================================

NOVA_RELACAO = [
    (
        "evidência",
        "depende_de",
        "observação",
    ),
]


# ============================================================
# ETAPA 4
#
# Conceito novo:
#
# simulação
#
# Relação nova:
#
# representa
# ============================================================

NOVO_CONCEITO_E_RELACAO = [
    (
        "simulação",
        "representa",
        "modelo",
    ),
]


# ============================================================
# FORMATO DO ARQUIVO
#
# CABEÇALHO:
#
# NXEX
# versão
#
# Depois existem registros.
#
# Registro 1 = conceito
# Registro 2 = relação
# Registro 3 = bloco de conhecimento
#
# CONCEITO:
#
# 1 byte  -> tipo = 1
# 1 byte  -> tamanho
# N bytes -> UTF-8
#
# RELAÇÃO:
#
# 1 byte  -> tipo = 2
# 1 byte  -> tamanho
# N bytes -> UTF-8
#
# BLOCO:
#
# 1 byte -> tipo = 3
# 1 byte -> quantidade de triplas
# 3 bytes por tripla
#
# Os IDs são determinados pela ordem em que conceitos e
# relações foram adicionados.
#
# Portanto:
#
# ID antigo nunca muda.
# ============================================================


MAGIC = b"NXEX"
VERSAO = 1

TIPO_CONCEITO = 1
TIPO_RELACAO = 2
TIPO_BLOCO = 3


# ============================================================
# ESTADO EM MEMÓRIA
# ============================================================

def criar_estado():
    conceitos = {
        nome: indice
        for indice, nome
        in enumerate(CONCEITOS_BASE)
    }

    relacoes = {
        nome: indice
        for indice, nome
        in enumerate(RELACOES_BASE)
    }

    return conceitos, relacoes


# ============================================================
# REGISTRO DE CONCEITO
# ============================================================

def codificar_conceito(nome):
    dados = nome.encode("utf-8")

    if len(dados) > 255:
        raise ValueError(
            "Conceito maior que 255 bytes."
        )

    return (
        bytes([TIPO_CONCEITO])
        + bytes([len(dados)])
        + dados
    )


# ============================================================
# REGISTRO DE RELAÇÃO
# ============================================================

def codificar_relacao(nome):
    dados = nome.encode("utf-8")

    if len(dados) > 255:
        raise ValueError(
            "Relação maior que 255 bytes."
        )

    return (
        bytes([TIPO_RELACAO])
        + bytes([len(dados)])
        + dados
    )


# ============================================================
# CONVERTER TRIPLA PARA IDs
# ============================================================

def tripla_para_ids(
    tripla,
    conceitos,
    relacoes,
):
    sujeito, relacao, objeto = tripla

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

    return (
        conceitos[sujeito],
        relacoes[relacao],
        conceitos[objeto],
    )


# ============================================================
# REGISTRO DE BLOCO
# ============================================================

def codificar_bloco(
    bloco,
    conceitos,
    relacoes,
):
    if len(bloco) > 255:
        raise ValueError(
            "Bloco maior que 255 triplas."
        )

    dados = bytearray()

    dados.append(TIPO_BLOCO)
    dados.append(len(bloco))

    for tripla in bloco:
        sujeito_id, relacao_id, objeto_id = (
            tripla_para_ids(
                tripla,
                conceitos,
                relacoes,
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
# ADICIONAR CONCEITO
# ============================================================

def adicionar_conceito(
    nome,
    conceitos,
):
    if nome in conceitos:
        return False

    proximo_id = len(conceitos)

    if proximo_id > 255:
        raise ValueError(
            "Limite de conceitos atingido."
        )

    conceitos[nome] = proximo_id

    return True


# ============================================================
# ADICIONAR RELAÇÃO
# ============================================================

def adicionar_relacao(
    nome,
    relacoes,
):
    if nome in relacoes:
        return False

    proximo_id = len(relacoes)

    if proximo_id > 255:
        raise ValueError(
            "Limite de relações atingido."
        )

    relacoes[nome] = proximo_id

    return True


# ============================================================
# LER UMA STRING
# ============================================================

def ler_string(
    dados,
    posicao,
):
    if posicao >= len(dados):
        raise ValueError(
            "String ausente."
        )

    tamanho = dados[posicao]
    posicao += 1

    fim = posicao + tamanho

    if fim > len(dados):
        raise ValueError(
            "String incompleta."
        )

    texto = dados[posicao:fim].decode(
        "utf-8"
    )

    return texto, fim


# ============================================================
# LER ARQUIVO COMPLETO
# ============================================================

def ler_arquivo(dados):
    if len(dados) < 5:
        raise ValueError(
            "Arquivo pequeno demais."
        )

    if dados[:4] != MAGIC:
        raise ValueError(
            "MAGIC inválido."
        )

    if dados[4] != VERSAO:
        raise ValueError(
            "Versão inválida."
        )

    posicao = 5

    conceitos = {}
    relacoes = {}

    blocos = []

    while posicao < len(dados):
        tipo = dados[posicao]
        posicao += 1

        # --------------------------------------------
        # CONCEITO
        # --------------------------------------------

        if tipo == TIPO_CONCEITO:
            nome, posicao = ler_string(
                dados,
                posicao,
            )

            if nome in conceitos:
                raise ValueError(
                    f"Conceito duplicado: {nome}"
                )

            conceitos[nome] = len(conceitos)

        # --------------------------------------------
        # RELAÇÃO
        # --------------------------------------------

        elif tipo == TIPO_RELACAO:
            nome, posicao = ler_string(
                dados,
                posicao,
            )

            if nome in relacoes:
                raise ValueError(
                    f"Relação duplicada: {nome}"
                )

            relacoes[nome] = len(relacoes)

        # --------------------------------------------
        # BLOCO
        # --------------------------------------------

        elif tipo == TIPO_BLOCO:
            if posicao >= len(dados):
                raise ValueError(
                    "Quantidade do bloco ausente."
                )

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

        else:
            raise ValueError(
                f"Tipo de registro desconhecido: {tipo}"
            )

    return (
        conceitos,
        relacoes,
        blocos,
    )


# ============================================================
# RECONSTRUIR CONHECIMENTO
# ============================================================

def reconstruir_conhecimento(
    conceitos,
    relacoes,
    blocos,
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
# ABRIR ESTADO ATUAL
# ============================================================

def estado_atual():
    dados = ARQUIVO.read_bytes()

    return ler_arquivo(dados)


# ============================================================
# VERIFICAR CONHECIMENTO
# ============================================================

def verificar(
    esperado,
):
    conceitos, relacoes, blocos = (
        estado_atual()
    )

    reconstruido = reconstruir_conhecimento(
        conceitos,
        relacoes,
        blocos,
    )

    return reconstruido == esperado


# ============================================================
# VERIFICAR IDS ANTIGOS
# ============================================================

def verificar_ids_antigos(
    conceitos_antes,
    relacoes_antes,
):
    conceitos, relacoes, _ = (
        estado_atual()
    )

    for nome, indice in conceitos_antes.items():
        if nome not in conceitos:
            return False

        if conceitos[nome] != indice:
            return False

    for nome, indice in relacoes_antes.items():
        if nome not in relacoes:
            return False

        if relacoes[nome] != indice:
            return False

    return True


# ============================================================
# APPEND DE UM REGISTRO
# ============================================================

def append_registro(
    dados,
):
    with open(
        ARQUIVO,
        "ab",
    ) as arquivo:
        arquivo.write(dados)


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=== MICROETAPA 38 ===")
    print("CRISTAL EXPANSÍVEL")
    print()

    ARQUIVO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if ARQUIVO.exists():
        ARQUIVO.unlink()

    # --------------------------------------------------------
    # ESTADO BASE
    # --------------------------------------------------------

    conceitos, relacoes = criar_estado()

    conhecimento_esperado = []

    print("=== CRIAÇÃO DO CRISTAL BASE ===")

    with open(
        ARQUIVO,
        "wb",
    ) as arquivo:
        arquivo.write(
            MAGIC + bytes([VERSAO])
        )

        for nome in CONCEITOS_BASE:
            arquivo.write(
                codificar_conceito(nome)
            )

        for nome in RELACOES_BASE:
            arquivo.write(
                codificar_relacao(nome)
            )

    # --------------------------------------------------------
    # BASE DE CONHECIMENTO
    # --------------------------------------------------------

    dados_bloco = codificar_bloco(
        BASE,
        conceitos,
        relacoes,
    )

    append_registro(
        dados_bloco
    )

    conhecimento_esperado.extend(
        BASE
    )

    print(
        f"Conceitos: {len(conceitos)}"
    )

    print(
        f"Relações: {len(relacoes)}"
    )

    print(
        f"Tamanho: "
        f"{ARQUIVO.stat().st_size} bytes"
    )

    if verificar(
        conhecimento_esperado
    ):
        print(
            "PASSOU: cristal base reconstruído."
        )
    else:
        print(
            "FALHOU: cristal base."
        )

    print()

    # --------------------------------------------------------
    # ETAPA 1
    # --------------------------------------------------------

    print("=== ETAPA 1 — REUTILIZAÇÃO ===")

    tamanho_antes = ARQUIVO.stat().st_size

    append_registro(
        codificar_bloco(
            REUTILIZACAO,
            conceitos,
            relacoes,
        )
    )

    conhecimento_esperado.extend(
        REUTILIZACAO
    )

    tamanho_depois = ARQUIVO.stat().st_size

    if verificar(
        conhecimento_esperado
    ):
        print(
            "PASSOU: conhecimento acumulado."
        )
    else:
        print(
            "FALHOU: reutilização."
        )

    print(
        f"Crescimento: "
        f"{tamanho_depois - tamanho_antes} bytes"
    )

    print()

    # --------------------------------------------------------
    # ETAPA 2
    # --------------------------------------------------------

    print("=== ETAPA 2 — CONCEITO NOVO ===")

    conceitos_antes = dict(
        conceitos
    )

    nome_conceito = "modelo"

    adicionou = adicionar_conceito(
        nome_conceito,
        conceitos,
    )

    if not adicionou:
        raise ValueError(
            "O conceito deveria ser novo."
        )

    append_registro(
        codificar_conceito(
            nome_conceito
        )
    )

    tamanho_antes = ARQUIVO.stat().st_size

    append_registro(
        codificar_bloco(
            NOVO_CONCEITO,
            conceitos,
            relacoes,
        )
    )

    conhecimento_esperado.extend(
        NOVO_CONCEITO
    )

    tamanho_depois = ARQUIVO.stat().st_size

    ids_ok = verificar_ids_antigos(
        conceitos_antes,
        relacoes,
    )

    conhecimento_ok = verificar(
        conhecimento_esperado
    )

    print(
        f"Novo conceito: "
        f"{nome_conceito}"
    )

    print(
        f"ID novo: "
        f"{conceitos[nome_conceito]}"
    )

    print(
        f"Crescimento total da etapa: "
        f"{tamanho_depois - tamanho_antes} bytes"
    )

    if ids_ok:
        print(
            "PASSOU: IDs antigos permaneceram intactos."
        )
    else:
        print(
            "FALHOU: algum ID antigo mudou."
        )

    if conhecimento_ok:
        print(
            "PASSOU: conhecimento reconstruído."
        )
    else:
        print(
            "FALHOU: conhecimento reconstruído."
        )

    print()

    # --------------------------------------------------------
    # ETAPA 3
    # --------------------------------------------------------

    print("=== ETAPA 3 — RELAÇÃO NOVA ===")

    relacoes_antes = dict(
        relacoes
    )

    nome_relacao = "depende_de"

    adicionou = adicionar_relacao(
        nome_relacao,
        relacoes,
    )

    if not adicionou:
        raise ValueError(
            "A relação deveria ser nova."
        )

    append_registro(
        codificar_relacao(
            nome_relacao
        )
    )

    tamanho_antes = ARQUIVO.stat().st_size

    append_registro(
        codificar_bloco(
            NOVA_RELACAO,
            conceitos,
            relacoes,
        )
    )

    conhecimento_esperado.extend(
        NOVA_RELACAO
    )

    tamanho_depois = ARQUIVO.stat().st_size

    ids_ok = verificar_ids_antigos(
        conceitos,
        relacoes_antes,
    )

    conhecimento_ok = verificar(
        conhecimento_esperado
    )

    print(
        f"Nova relação: "
        f"{nome_relacao}"
    )

    print(
        f"ID novo: "
        f"{relacoes[nome_relacao]}"
    )

    print(
        f"Crescimento total da etapa: "
        f"{tamanho_depois - tamanho_antes} bytes"
    )

    if ids_ok:
        print(
            "PASSOU: IDs antigos permaneceram intactos."
        )
    else:
        print(
            "FALHOU: algum ID antigo mudou."
        )

    if conhecimento_ok:
        print(
            "PASSOU: conhecimento reconstruído."
        )
    else:
        print(
            "FALHOU: conhecimento reconstruído."
        )

    print()

    # --------------------------------------------------------
    # ETAPA 4
    # --------------------------------------------------------

    print(
        "=== ETAPA 4 — CONCEITO + RELAÇÃO NOVOS ==="
    )

    conceitos_antes = dict(
        conceitos
    )

    relacoes_antes = dict(
        relacoes
    )

    novo_conceito = "simulação"
    nova_relacao = "representa"

    adicionar_conceito(
        novo_conceito,
        conceitos,
    )

    adicionar_relacao(
        nova_relacao,
        relacoes,
    )

    append_registro(
        codificar_conceito(
            novo_conceito
        )
    )

    append_registro(
        codificar_relacao(
            nova_relacao
        )
    )

    tamanho_antes = ARQUIVO.stat().st_size

    append_registro(
        codificar_bloco(
            NOVO_CONCEITO_E_RELACAO,
            conceitos,
            relacoes,
        )
    )

    conhecimento_esperado.extend(
        NOVO_CONCEITO_E_RELACAO
    )

    tamanho_depois = ARQUIVO.stat().st_size

    ids_ok = verificar_ids_antigos(
        conceitos_antes,
        relacoes_antes,
    )

    conhecimento_ok = verificar(
        conhecimento_esperado
    )

    print(
        f"Novo conceito: "
        f"{novo_conceito}"
    )

    print(
        f"ID do conceito: "
        f"{conceitos[novo_conceito]}"
    )

    print(
        f"Nova relação: "
        f"{nova_relacao}"
    )

    print(
        f"ID da relação: "
        f"{relacoes[nova_relacao]}"
    )

    print(
        f"Crescimento total da etapa: "
        f"{tamanho_depois - tamanho_antes} bytes"
    )

    if ids_ok:
        print(
            "PASSOU: IDs antigos permaneceram intactos."
        )
    else:
        print(
            "FALHOU: algum ID antigo mudou."
        )

    if conhecimento_ok:
        print(
            "PASSOU: conhecimento reconstruído."
        )
    else:
        print(
            "FALHOU: conhecimento reconstruído."
        )

    print()

    # --------------------------------------------------------
    # VERIFICAÇÃO FINAL
    # --------------------------------------------------------

    print("=== VERIFICAÇÃO FINAL ===")

    conceitos_finais, relacoes_finais, blocos_finais = (
        estado_atual()
    )

    conhecimento_final = reconstruir_conhecimento(
        conceitos_finais,
        relacoes_finais,
        blocos_finais,
    )

    if conhecimento_final == conhecimento_esperado:
        print(
            "PASSOU: todo o conhecimento "
            "foi reconstruído exatamente."
        )
    else:
        print(
            "FALHOU: conhecimento final divergente."
        )

    print()

    # --------------------------------------------------------
    # ESTATÍSTICAS
    # --------------------------------------------------------

    print("=== ESTADO FINAL ===")

    print(
        f"Conceitos: "
        f"{len(conceitos_finais)}"
    )

    print(
        f"Relações: "
        f"{len(relacoes_finais)}"
    )

    print(
        f"Triplas: "
        f"{len(conhecimento_final)}"
    )

    print(
        f"Tamanho do arquivo: "
        f"{ARQUIVO.stat().st_size} bytes"
    )

    print(
        f"Arquivo existe: "
        f"{ARQUIVO.exists()}"
    )


if __name__ == "__main__":
    main()
