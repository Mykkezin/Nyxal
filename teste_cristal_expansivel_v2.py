from pathlib import Path
import struct


# ============================================================
# MICROETAPA 39
# CRISTAL EXPANSÍVEL V2
# CONTABILIDADE CORRETA
#
# Objetivo:
#
# 1. Criar um cristal inicial.
# 2. Adicionar conhecimento reutilizado.
# 3. Adicionar conceito novo.
# 4. Adicionar relação nova.
# 5. Adicionar conceito + relação novos.
# 6. Medir o custo REAL de cada expansão.
# 7. Garantir que o conhecimento anterior permanece intacto.
# 8. Reconstruir tudo no final.
# ============================================================


ARQUIVO = Path(
    "experimentos/cristal_nyxal_expansivel_v2.bin"
)


# ============================================================
# DICIONÁRIO BASE
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
# CONHECIMENTO
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


NOVO_CONCEITO = [
    (
        "modelo",
        "pode_gerar_previsao",
        "previsão",
    ),
]


NOVA_RELACAO = [
    (
        "evidência",
        "depende_de",
        "observação",
    ),
]


NOVO_CONCEITO_E_RELACAO = [
    (
        "simulação",
        "representa",
        "modelo",
    ),
]


# ============================================================
# TIPOS DE REGISTRO
# ============================================================

MAGIC = b"NXEX"
VERSAO = 1

TIPO_CONCEITO = 1
TIPO_RELACAO = 2
TIPO_BLOCO = 3


# ============================================================
# ESTADO
# ============================================================

def criar_estado():
    conceitos = {
        nome: indice
        for indice, nome in enumerate(CONCEITOS_BASE)
    }

    relacoes = {
        nome: indice
        for indice, nome in enumerate(RELACOES_BASE)
    }

    return conceitos, relacoes


# ============================================================
# CODIFICAÇÃO DE CONCEITO
# ============================================================

def codificar_conceito(nome):
    dados = nome.encode("utf-8")

    if len(dados) > 255:
        raise ValueError(
            "Conceito excede 255 bytes."
        )

    return (
        bytes([TIPO_CONCEITO])
        + bytes([len(dados)])
        + dados
    )


# ============================================================
# CODIFICAÇÃO DE RELAÇÃO
# ============================================================

def codificar_relacao(nome):
    dados = nome.encode("utf-8")

    if len(dados) > 255:
        raise ValueError(
            "Relação excede 255 bytes."
        )

    return (
        bytes([TIPO_RELACAO])
        + bytes([len(dados)])
        + dados
    )


# ============================================================
# TRIPLA -> IDS
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
# CODIFICAÇÃO DE BLOCO
# ============================================================

def codificar_bloco(
    bloco,
    conceitos,
    relacoes,
):
    if len(bloco) > 255:
        raise ValueError(
            "Bloco excede 255 triplas."
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
        return None

    novo_id = len(conceitos)

    if novo_id > 255:
        raise ValueError(
            "Limite de conceitos atingido."
        )

    conceitos[nome] = novo_id

    return novo_id


# ============================================================
# ADICIONAR RELAÇÃO
# ============================================================

def adicionar_relacao(
    nome,
    relacoes,
):
    if nome in relacoes:
        return None

    novo_id = len(relacoes)

    if novo_id > 255:
        raise ValueError(
            "Limite de relações atingido."
        )

    relacoes[nome] = novo_id

    return novo_id


# ============================================================
# LEITURA DE STRING
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
# LEITURA DO ARQUIVO
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

        # ----------------------------------------------------
        # CONCEITO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # RELAÇÃO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # BLOCO
        # ----------------------------------------------------

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
                f"Tipo desconhecido: {tipo}"
            )

    return (
        conceitos,
        relacoes,
        blocos,
    )


# ============================================================
# RECONSTRUÇÃO DO CONHECIMENTO
# ============================================================

def reconstruir_conhecimento(
    conceitos,
    relacoes,
    blocos,
):
    conceitos_invertidos = {
        indice: nome
        for nome, indice in conceitos.items()
    }

    relacoes_invertidas = {
        indice: nome
        for nome, indice in relacoes.items()
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
# VERIFICAÇÃO
# ============================================================

def verificar(
    esperado,
):
    dados = ARQUIVO.read_bytes()

    conceitos, relacoes, blocos = (
        ler_arquivo(dados)
    )

    reconstruido = (
        reconstruir_conhecimento(
            conceitos,
            relacoes,
            blocos,
        )
    )

    return reconstruido == esperado


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=== MICROETAPA 39 ===")
    print("CRISTAL EXPANSÍVEL V2")
    print("CONTABILIDADE CORRETA")
    print()

    ARQUIVO.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if ARQUIVO.exists():
        ARQUIVO.unlink()

    conceitos, relacoes = criar_estado()

    conhecimento_esperado = []

    # ========================================================
    # BASE
    # ========================================================

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

    bloco_base = codificar_bloco(
        BASE,
        conceitos,
        relacoes,
    )

    with open(
        ARQUIVO,
        "ab",
    ) as arquivo:
        arquivo.write(
            bloco_base
        )

    conhecimento_esperado.extend(
        BASE
    )

    print("=== BASE ===")

    print(
        f"Tamanho: "
        f"{ARQUIVO.stat().st_size} bytes"
    )

    if verificar(
        conhecimento_esperado
    ):
        print(
            "PASSOU: cristal base."
        )
    else:
        print(
            "FALHOU: cristal base."
        )

    print()

    # ========================================================
    # ETAPA 1 — REUTILIZAÇÃO
    # ========================================================

    print(
        "=== ETAPA 1 — REUTILIZAÇÃO ==="
    )

    tamanho_antes = (
        ARQUIVO.stat().st_size
    )

    bloco = codificar_bloco(
        REUTILIZACAO,
        conceitos,
        relacoes,
    )

    with open(
        ARQUIVO,
        "ab",
    ) as arquivo:
        arquivo.write(
            bloco
        )

    conhecimento_esperado.extend(
        REUTILIZACAO
    )

    crescimento = (
        ARQUIVO.stat().st_size
        - tamanho_antes
    )

    print(
        f"Bloco: "
        f"{len(bloco)} bytes"
    )

    print(
        f"Crescimento real: "
        f"{crescimento} bytes"
    )

    if verificar(
        conhecimento_esperado
    ):
        print(
            "PASSOU: conhecimento acumulado."
        )
    else:
        print(
            "FALHOU: conhecimento acumulado."
        )

    print()

    # ========================================================
    # ETAPA 2 — CONCEITO NOVO
    # ========================================================

    print(
        "=== ETAPA 2 — CONCEITO NOVO ==="
    )

    tamanho_antes = (
        ARQUIVO.stat().st_size
    )

    nome = "modelo"

    novo_id = adicionar_conceito(
        nome,
        conceitos,
    )

    if novo_id is None:
        raise ValueError(
            "Conceito deveria ser novo."
        )

    registro_dicionario = (
        codificar_conceito(nome)
    )

    bloco = codificar_bloco(
        NOVO_CONCEITO,
        conceitos,
        relacoes,
    )

    with open(
        ARQUIVO,
        "ab",
    ) as arquivo:
        arquivo.write(
            registro_dicionario
        )
        arquivo.write(
            bloco
        )

    conhecimento_esperado.extend(
        NOVO_CONCEITO
    )

    crescimento = (
        ARQUIVO.stat().st_size
        - tamanho_antes
    )

    print(
        f"Conceito: "
        f"{nome}"
    )

    print(
        f"ID: "
        f"{novo_id}"
    )

    print(
        f"Dicionário: "
        f"{len(registro_dicionario)} bytes"
    )

    print(
        f"Bloco: "
        f"{len(bloco)} bytes"
    )

    print(
        f"Crescimento real: "
        f"{crescimento} bytes"
    )

    if verificar(
        conhecimento_esperado
    ):
        print(
            "PASSOU: conhecimento."
        )
    else:
        print(
            "FALHOU: conhecimento."
        )

    print()

    # ========================================================
    # ETAPA 3 — RELAÇÃO NOVA
    # ========================================================

    print(
        "=== ETAPA 3 — RELAÇÃO NOVA ==="
    )

    tamanho_antes = (
        ARQUIVO.stat().st_size
    )

    nome = "depende_de"

    novo_id = adicionar_relacao(
        nome,
        relacoes,
    )

    if novo_id is None:
        raise ValueError(
            "Relação deveria ser nova."
        )

    registro_dicionario = (
        codificar_relacao(nome)
    )

    bloco = codificar_bloco(
        NOVA_RELACAO,
        conceitos,
        relacoes,
    )

    with open(
        ARQUIVO,
        "ab",
    ) as arquivo:
        arquivo.write(
            registro_dicionario
        )
        arquivo.write(
            bloco
        )

    conhecimento_esperado.extend(
        NOVA_RELACAO
    )

    crescimento = (
        ARQUIVO.stat().st_size
        - tamanho_antes
    )

    print(
        f"Relação: "
        f"{nome}"
    )

    print(
        f"ID: "
        f"{novo_id}"
    )

    print(
        f"Dicionário: "
        f"{len(registro_dicionario)} bytes"
    )

    print(
        f"Bloco: "
        f"{len(bloco)} bytes"
    )

    print(
        f"Crescimento real: "
        f"{crescimento} bytes"
    )

    if verificar(
        conhecimento_esperado
    ):
        print(
            "PASSOU: conhecimento."
        )
    else:
        print(
            "FALHOU: conhecimento."
        )

    print()

    # ========================================================
    # ETAPA 4 — CONCEITO + RELAÇÃO NOVOS
    # ========================================================

    print(
        "=== ETAPA 4 — CONCEITO + RELAÇÃO ==="
    )

    tamanho_antes = (
        ARQUIVO.stat().st_size
    )

    novo_conceito = "simulação"
    nova_relacao = "representa"

    conceito_id = adicionar_conceito(
        novo_conceito,
        conceitos,
    )

    relacao_id = adicionar_relacao(
        nova_relacao,
        relacoes,
    )

    if conceito_id is None:
        raise ValueError(
            "Conceito deveria ser novo."
        )

    if relacao_id is None:
        raise ValueError(
            "Relação deveria ser nova."
        )

    registro_conceito = (
        codificar_conceito(
            novo_conceito
        )
    )

    registro_relacao = (
        codificar_relacao(
            nova_relacao
        )
    )

    bloco = codificar_bloco(
        NOVO_CONCEITO_E_RELACAO,
        conceitos,
        relacoes,
    )

    with open(
        ARQUIVO,
        "ab",
    ) as arquivo:
        arquivo.write(
            registro_conceito
        )
        arquivo.write(
            registro_relacao
        )
        arquivo.write(
            bloco
        )

    conhecimento_esperado.extend(
        NOVO_CONCEITO_E_RELACAO
    )

    crescimento = (
        ARQUIVO.stat().st_size
        - tamanho_antes
    )

    print(
        f"Conceito: "
        f"{novo_conceito} "
        f"(ID {conceito_id})"
    )

    print(
        f"Relação: "
        f"{nova_relacao} "
        f"(ID {relacao_id})"
    )

    print(
        f"Conceito: "
        f"{len(registro_conceito)} bytes"
    )

    print(
        f"Relação: "
        f"{len(registro_relacao)} bytes"
    )

    print(
        f"Bloco: "
        f"{len(bloco)} bytes"
    )

    print(
        f"Crescimento real: "
        f"{crescimento} bytes"
    )

    if verificar(
        conhecimento_esperado
    ):
        print(
            "PASSOU: conhecimento."
        )
    else:
        print(
            "FALHOU: conhecimento."
        )

    print()

    # ========================================================
    # VERIFICAÇÃO FINAL
    # ========================================================

    print(
        "=== VERIFICAÇÃO FINAL ==="
    )

    dados = ARQUIVO.read_bytes()

    conceitos_finais, relacoes_finais, blocos = (
        ler_arquivo(dados)
    )

    conhecimento_final = (
        reconstruir_conhecimento(
            conceitos_finais,
            relacoes_finais,
            blocos,
        )
    )

    if (
        conhecimento_final
        == conhecimento_esperado
    ):
        print(
            "PASSOU: todo o conhecimento "
            "foi reconstruído exatamente."
        )
    else:
        print(
            "FALHOU: conhecimento divergente."
        )

    print()

    # ========================================================
    # ESTADO FINAL
    # ========================================================

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
        f"Tamanho final: "
        f"{ARQUIVO.stat().st_size} bytes"
    )

    print(
        f"Arquivo existe: "
        f"{ARQUIVO.exists()}"
    )


if __name__ == "__main__":
    main()
