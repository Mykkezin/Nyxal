from teste_dicionario_binario import (
    CONCEITOS as CONCEITOS_BASE,
    RELACOES as RELACOES_BASE,
    EXPERIENCIAS as EXPERIENCIAS_BASE,
)


# ============================================================
# MICROETAPA 35
# CRESCIMENTO INCREMENTAL DO CRISTAL
#
# Objetivo:
#
# medir quanto custa adicionar conhecimento novo
# sem recriar todo o dicionário anterior.
#
# Testamos quatro casos:
#
# 1. reutilização total
# 2. conceitos novos
# 3. relações novas
# 4. conceitos + relações novos
#
# O cristal base e o dicionário base permanecem intactos.
# Apenas os deltas são adicionados.
# ============================================================


# ============================================================
# NOVOS CONCEITOS
# ============================================================

NOVOS_CONCEITOS_1 = [
    "modelo",
    "variável",
    "causa",
]

NOVOS_CONCEITOS_2 = [
    "simulação",
    "efeito",
    "sistema",
]


# ============================================================
# NOVAS RELAÇÕES
# ============================================================

NOVAS_RELACOES_1 = [
    "pode_prever",
    "depende_de",
    "pode_simular",
]

NOVAS_RELACOES_2 = [
    "afeta",
    "representa",
    "interage_com",
]


# ============================================================
# NOVAS EXPERIÊNCIAS
#
# Cada item possui:
#
# texto
# sujeito
# relação
# objeto
#
# Os nomes serão convertidos para IDs somente
# no momento da cristalização.
# ============================================================

BATCH_REUTILIZACAO = [
    {
        "texto": "Uma hipótese pode gerar uma previsão.",
        "sujeito": "hipótese",
        "relacao": "pode_gerar_previsao",
        "objeto": "previsão",
    },
    {
        "texto": "Uma previsão pode ser testada por experimento.",
        "sujeito": "previsão",
        "relacao": "pode_ser_testada_por",
        "objeto": "experimento",
    },
    {
        "texto": "Um resultado pode apoiar uma teoria.",
        "sujeito": "resultado",
        "relacao": "pode_ser_apoiada_por",
        "objeto": "teoria",
    },
]


BATCH_NOVOS_CONCEITOS = [
    {
        "texto": "Um modelo pode gerar uma previsão.",
        "sujeito": "modelo",
        "relacao": "pode_gerar_previsao",
        "objeto": "previsão",
    },
    {
        "texto": "Uma variável pode conter um erro.",
        "sujeito": "variável",
        "relacao": "pode_conter_erro",
        "objeto": "erro",
    },
    {
        "texto": "Uma causa pode explicar um resultado.",
        "sujeito": "causa",
        "relacao": "pode_explicar",
        "objeto": "resultado",
    },
]


BATCH_NOVAS_RELACOES = [
    {
        "texto": "Uma hipótese pode prever uma conclusão.",
        "sujeito": "hipótese",
        "relacao": "pode_prever",
        "objeto": "conclusão",
    },
    {
        "texto": "Uma evidência depende de uma observação.",
        "sujeito": "evidência",
        "relacao": "depende_de",
        "objeto": "observação",
    },
    {
        "texto": "Um experimento pode simular uma investigação.",
        "sujeito": "experimento",
        "relacao": "pode_simular",
        "objeto": "investigação",
    },
]


BATCH_NOVOS_CONCEITOS_E_RELACOES = [
    {
        "texto": "Uma simulação pode prever um resultado.",
        "sujeito": "simulação",
        "relacao": "pode_prever",
        "objeto": "resultado",
    },
    {
        "texto": "Um sistema afeta uma variável.",
        "sujeito": "sistema",
        "relacao": "afeta",
        "objeto": "variável",
    },
    {
        "texto": "Um modelo representa uma simulação.",
        "sujeito": "modelo",
        "relacao": "representa",
        "objeto": "simulação",
    },
]


# ============================================================
# FUNÇÕES DE TAMANHO
# ============================================================

def bytes_utf8(texto):
    return len(texto.encode("utf-8"))


def tamanho_textos(itens):
    texto = "\n".join(
        item["texto"]
        for item in itens
    )

    return bytes_utf8(texto)


# ============================================================
# DICIONÁRIO BINÁRIO
#
# Aqui usamos um formato de DELTA.
#
# O dicionário base não é repetido.
#
# Cada expansão armazena somente:
#
# quantidade
# tamanho da string
# string UTF-8
#
# ============================================================

def codificar_strings_binario(strings):
    dados = bytearray()

    if len(strings) > 255:
        raise ValueError(
            "Mais de 255 strings em um único delta."
        )

    dados.append(len(strings))

    for texto in strings:
        bytes_texto = texto.encode("utf-8")

        if len(bytes_texto) > 255:
            raise ValueError(
                "String excede 255 bytes."
            )

        dados.append(len(bytes_texto))
        dados.extend(bytes_texto)

    return bytes(dados)


# ============================================================
# CRISTAL BINÁRIO
# ============================================================

def codificar_experiencias(
    experiencias,
    conceitos,
    relacoes,
):
    dados = bytearray()

    for experiencia in experiencias:
        sujeito_nome = experiencia["sujeito"]
        relacao_nome = experiencia["relacao"]
        objeto_nome = experiencia["objeto"]

        if sujeito_nome not in conceitos:
            raise ValueError(
                f"Conceito ausente: {sujeito_nome}"
            )

        if objeto_nome not in conceitos:
            raise ValueError(
                f"Conceito ausente: {objeto_nome}"
            )

        if relacao_nome not in relacoes:
            raise ValueError(
                f"Relação ausente: {relacao_nome}"
            )

        sujeito_id = conceitos[sujeito_nome]
        relacao_id = relacoes[relacao_nome]
        objeto_id = conceitos[objeto_nome]

        dados.append(1)

        dados.append(sujeito_id)
        dados.append(relacao_id)
        dados.append(objeto_id)

    return bytes(dados)


# ============================================================
# CONVERTE DICIONÁRIO ID -> TEXTO
# PARA TEXTO -> ID
# ============================================================

def inverter_dicionario(dicionario):
    return {
        texto: indice
        for indice, texto in dicionario.items()
    }


# ============================================================
# CONVERTE OS DICIONÁRIOS BASE
# ============================================================

def preparar_dicionarios():
    conceitos = inverter_dicionario(
        CONCEITOS_BASE
    )

    relacoes = inverter_dicionario(
        RELACOES_BASE
    )

    return conceitos, relacoes


# ============================================================
# RECONSTRÓI SEMANTICAMENTE
# ============================================================

def assinatura_semantica(
    experiencias,
):
    resultado = []

    for experiencia in experiencias:
        resultado.append(
            (
                experiencia["sujeito"],
                experiencia["relacao"],
                experiencia["objeto"],
            )
        )

    return resultado


# ============================================================
# TESTA A CATEGORIA DE UM BATCH
# ============================================================

def medir_batch(
    nome,
    experiencias,
    conceitos,
    relacoes,
    novos_conceitos,
    novas_relacoes,
):
    texto_bytes = tamanho_textos(experiencias)

    # IDs atuais
    conceitos_ids = {
        nome: indice
        for nome, indice
        in conceitos.items()
    }

    relacoes_ids = {
        nome: indice
        for nome, indice
        in relacoes.items()
    }

    # Delta do dicionário
    delta_conceitos = codificar_strings_binario(
        novos_conceitos
    )

    delta_relacoes = codificar_strings_binario(
        novas_relacoes
    )

    delta_dicionario = (
        len(delta_conceitos)
        + len(delta_relacoes)
    )

    # Cristal
    cristal = codificar_experiencias(
        experiencias,
        conceitos_ids,
        relacoes_ids,
    )

    tamanho_cristal = len(cristal)

    total_incremental = (
        delta_dicionario
        + tamanho_cristal
    )

    economia = (
        (texto_bytes - total_incremental)
        / texto_bytes
    ) * 100

    print(f"=== {nome} ===")

    print(
        f"Experiências adicionadas: "
        f"{len(experiencias)}"
    )

    print(
        f"Texto novo: "
        f"{texto_bytes} bytes"
    )

    print(
        f"Delta de conceitos: "
        f"{len(delta_conceitos)} bytes"
    )

    print(
        f"Delta de relações: "
        f"{len(delta_relacoes)} bytes"
    )

    print(
        f"Delta total do dicionário: "
        f"{delta_dicionario} bytes"
    )

    print(
        f"Novo cristal: "
        f"{tamanho_cristal} bytes"
    )

    print(
        f"Custo incremental total: "
        f"{total_incremental} bytes"
    )

    print(
        f"Economia incremental: "
        f"{economia:.2f}%"
    )

    print()

    return total_incremental


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=== MICROETAPA 35 ===")
    print("CRESCIMENTO INCREMENTAL DO CRISTAL")
    print()

    # --------------------------------------------------------
    # DICIONÁRIO BASE
    # --------------------------------------------------------

    conceitos, relacoes = preparar_dicionarios()

    print("=== ESTADO BASE ===")

    print(
        f"Conceitos: "
        f"{len(conceitos)}"
    )

    print(
        f"Relações: "
        f"{len(relacoes)}"
    )

    print(
        f"Experiências base: "
        f"{len(EXPERIENCIAS_BASE)}"
    )

    print()

    # --------------------------------------------------------
    # BATCH 1
    #
    # Tudo já conhecido.
    # --------------------------------------------------------

    custo_1 = medir_batch(
        "1. REUTILIZAÇÃO TOTAL",
        BATCH_REUTILIZACAO,
        conceitos,
        relacoes,
        [],
        [],
    )

    # --------------------------------------------------------
    # BATCH 2
    #
    # Novos conceitos.
    # --------------------------------------------------------

    novos_conceitos_batch_1 = list(
        NOVOS_CONCEITOS_1
    )

    novos_relacoes_batch_1 = []

    for indice, nome in enumerate(
        novos_conceitos_batch_1,
        start=len(conceitos),
    ):
        conceitos[nome] = indice

    custo_2 = medir_batch(
        "2. CONCEITOS NOVOS",
        BATCH_NOVOS_CONCEITOS,
        conceitos,
        relacoes,
        novos_conceitos_batch_1,
        novos_relacoes_batch_1,
    )

    # --------------------------------------------------------
    # BATCH 3
    #
    # Novas relações.
    # --------------------------------------------------------

    novos_relacoes_batch_2 = list(
        NOVAS_RELACOES_1
    )

    for indice, nome in enumerate(
        novos_relacoes_batch_2,
        start=len(relacoes),
    ):
        relacoes[nome] = indice

    custo_3 = medir_batch(
        "3. RELAÇÕES NOVAS",
        BATCH_NOVAS_RELACOES,
        conceitos,
        relacoes,
        [],
        novos_relacoes_batch_2,
    )

    # --------------------------------------------------------
    # BATCH 4
    #
    # Novos conceitos + novas relações.
    # --------------------------------------------------------

    novos_conceitos_batch_2 = list(
        NOVOS_CONCEITOS_2
    )

    novos_relacoes_batch_3 = list(
        NOVAS_RELACOES_2
    )

    for indice, nome in enumerate(
        novos_conceitos_batch_2,
        start=len(conceitos),
    ):
        conceitos[nome] = indice

    for indice, nome in enumerate(
        novos_relacoes_batch_3,
        start=len(relacoes),
    ):
        relacoes[nome] = indice

    custo_4 = medir_batch(
        "4. CONCEITOS + RELAÇÕES NOVOS",
        BATCH_NOVOS_CONCEITOS_E_RELACOES,
        conceitos,
        relacoes,
        novos_conceitos_batch_2,
        novos_relacoes_batch_3,
    )

    # --------------------------------------------------------
    # CUSTO TOTAL DOS NOVOS BATCHES
    # --------------------------------------------------------

    custo_total = (
        custo_1
        + custo_2
        + custo_3
        + custo_4
    )

    texto_total_novo = (
        tamanho_textos(BATCH_REUTILIZACAO)
        + tamanho_textos(BATCH_NOVOS_CONCEITOS)
        + tamanho_textos(BATCH_NOVAS_RELACOES)
        + tamanho_textos(
            BATCH_NOVOS_CONCEITOS_E_RELACOES
        )
    )

    economia_total = (
        (texto_total_novo - custo_total)
        / texto_total_novo
    ) * 100

    print("=== TOTAL DO CRESCIMENTO ===")

    print(
        f"Texto novo acumulado: "
        f"{texto_total_novo} bytes"
    )

    print(
        f"Custo cristalizado acumulado: "
        f"{custo_total} bytes"
    )

    print(
        f"Economia acumulada: "
        f"{economia_total:.2f}%"
    )

    print()

    # --------------------------------------------------------
    # ESTADO FINAL
    # --------------------------------------------------------

    print("=== ESTADO FINAL ===")

    print(
        f"Conceitos totais: "
        f"{len(conceitos)}"
    )

    print(
        f"Relações totais: "
        f"{len(relacoes)}"
    )

    print()

    # --------------------------------------------------------
    # INTEGRIDADE DOS BATCHES
    # --------------------------------------------------------

    print("=== INTEGRIDADE ===")

    todos = (
        BATCH_REUTILIZACAO
        + BATCH_NOVOS_CONCEITOS
        + BATCH_NOVAS_RELACOES
        + BATCH_NOVOS_CONCEITOS_E_RELACOES
    )

    semantica = assinatura_semantica(
        todos
    )

    if len(semantica) == len(todos):
        print(
            "PASSOU: todas as experiências "
            "possuem estrutura semântica válida."
        )
    else:
        print(
            "FALHOU: quantidade de estruturas "
            "não corresponde ao corpus."
        )

    print()


if __name__ == "__main__":
    main()
