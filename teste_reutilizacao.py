import re


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
    "Uma hipótese precisa lidar com incerteza."
]


def tamanho_bytes(texto):
    return len(
        texto.encode("utf-8")
    )


def tokenizar(texto):
    """
    Mantém palavras e pontuação separadas.
    Isso permite reconstruir o texto original.
    """

    return re.findall(
        r"[A-Za-zÀ-ÿ]+|[.,!?;:]|\s+",
        texto
    )


def criar_vocabulario(textos):
    vocabulario = []
    vistos = set()

    for texto in textos:

        for token in tokenizar(texto):

            if token not in vistos:

                vistos.add(token)
                vocabulario.append(token)

    return vocabulario


def criar_mapa(vocabulario):
    return {
        token: indice
        for indice, token
        in enumerate(vocabulario)
    }


def codificar(texto, mapa):
    tokens = tokenizar(texto)

    ids = []

    for token in tokens:
        ids.append(
            str(mapa[token])
        )

    return " ".join(ids)


def decodificar(codificado, vocabulario):
    if not codificado.strip():
        return ""

    ids = codificado.split()

    tokens = [
        vocabulario[int(indice)]
        for indice in ids
    ]

    return "".join(tokens)


def tamanho_lista(textos):
    return tamanho_bytes(
        "\n".join(textos)
    )


print(
    "=== TESTE DE REUTILIZAÇÃO LOSSLESS ==="
)

# --------------------------------------------------
# ORIGINAL
# --------------------------------------------------

tamanho_original = tamanho_lista(
    EXPERIENCIAS
)

# --------------------------------------------------
# VOCABULÁRIO COMPARTILHADO
# --------------------------------------------------

vocabulario = criar_vocabulario(
    EXPERIENCIAS
)

mapa = criar_mapa(
    vocabulario
)

tamanho_vocabulario = tamanho_bytes(
    "\n".join(vocabulario)
)

# --------------------------------------------------
# CODIFICAÇÃO
# --------------------------------------------------

codificados = []

for experiencia in EXPERIENCIAS:

    codificado = codificar(
        experiencia,
        mapa
    )

    codificados.append(
        codificado
    )

# --------------------------------------------------
# TAMANHO DOS IDS
# --------------------------------------------------

tamanho_ids = tamanho_lista(
    codificados
)

tamanho_total = (
    tamanho_vocabulario
    + tamanho_ids
)

# --------------------------------------------------
# RECONSTRUÇÃO
# --------------------------------------------------

reconstruidos = []

for codificado in codificados:

    reconstruido = decodificar(
        codificado,
        vocabulario
    )

    reconstruidos.append(
        reconstruido
    )

# --------------------------------------------------
# INTEGRIDADE
# --------------------------------------------------

integridade = (
    reconstruidos
    == EXPERIENCIAS
)

# --------------------------------------------------
# RESULTADOS
# --------------------------------------------------

print()
print("=== TAMANHOS ===")

print(
    f"Texto original: "
    f"{tamanho_original} bytes"
)

print(
    f"Vocabulário compartilhado: "
    f"{tamanho_vocabulario} bytes"
)

print(
    f"Representações codificadas: "
    f"{tamanho_ids} bytes"
)

print(
    f"Representação total: "
    f"{tamanho_total} bytes"
)

if tamanho_original > 0:

    economia = (
        100
        - (
            tamanho_total
            / tamanho_original
            * 100
        )
    )

    print(
        f"Economia total: "
        f"{economia:.2f}%"
    )

print()
print("=== VOCABULÁRIO ===")

print(
    f"Tokens únicos: "
    f"{len(vocabulario)}"
)

print()

for indice, token in enumerate(
    vocabulario
):

    print(
        f"{indice}: {repr(token)}"
    )

print()
print("=== RECONSTRUÇÃO ===")

for indice, reconstruido in enumerate(
    reconstruidos,
    start=1
):

    print(
        f"{indice:02d}: "
        f"{reconstruido}"
    )

print()
print("=== INTEGRIDADE ===")

if integridade:

    print(
        "PASSOU: todos os textos foram "
        "reconstruídos exatamente."
    )

else:

    print(
        "FALHOU: houve perda durante "
        "a reconstrução."
    )

    for indice, (
        original,
        reconstruido
    ) in enumerate(
        zip(
            EXPERIENCIAS,
            reconstruidos
        ),
        start=1
    ):

        if original != reconstruido:

            print()
            print(
                f"Experiência {indice}:"
            )

            print(
                f"Original:     {repr(original)}"
            )

            print(
                f"Reconstruída: {repr(reconstruido)}"
            )
