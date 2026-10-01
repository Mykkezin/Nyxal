import json


CRISTAL_C = {
    "conceito": "Hipótese"
}


ATOMOS = {
    "H1": "Hipótese",
    "H2": "ideia",
    "H3": "provisória",
    "H4": "explicação",
    "H5": "investigação",
    "H6": "incorreta",
    "H7": "observação",
    "H8": "padrões",
    "H9": "dados",
    "H10": "experiência",
    "H11": "possibilidade",
    "H12": "não investigada",
    "H13": "experimentos",
    "H14": "novas observações",
    "H15": "resultados compatíveis",
    "H16": "suporte",
    "H17": "verdade absoluta",
    "H18": "novas evidências",
    "H19": "modificar",
    "H20": "contradizer",
    "H21": "relações",
    "H22": "limitações",
    "H23": "incerteza"
}


REQUISITOS = [
    {
        "id": 1,
        "texto": "A hipótese é uma ideia provisória.",
        "atomos": [
            "H1",
            "H2",
            "H3"
        ]
    },
    {
        "id": 2,
        "texto": (
            "A hipótese pode ser usada para explicar um fenômeno "
            "ou orientar uma investigação."
        ),
        "atomos": [
            "H1",
            "H4",
            "H5"
        ]
    },
    {
        "id": 3,
        "texto": (
            "A hipótese não precisa estar correta."
        ),
        "atomos": [
            "H1",
            "H6"
        ]
    },
    {
        "id": 4,
        "texto": (
            "Uma hipótese pode surgir de uma observação."
        ),
        "atomos": [
            "H1",
            "H7"
        ]
    },
    {
        "id": 5,
        "texto": (
            "Uma hipótese pode surgir de padrões encontrados em dados."
        ),
        "atomos": [
            "H1",
            "H8",
            "H9"
        ]
    },
    {
        "id": 6,
        "texto": (
            "Uma hipótese pode surgir de uma experiência anterior."
        ),
        "atomos": [
            "H1",
            "H10"
        ]
    },
    {
        "id": 7,
        "texto": (
            "Uma hipótese pode surgir de uma possibilidade "
            "que ainda não foi investigada."
        ),
        "atomos": [
            "H1",
            "H11",
            "H12"
        ]
    },
    {
        "id": 8,
        "texto": (
            "Uma hipótese pode ser submetida a experimentos."
        ),
        "atomos": [
            "H1",
            "H13"
        ]
    },
    {
        "id": 9,
        "texto": (
            "Uma hipótese pode ser submetida a novas observações."
        ),
        "atomos": [
            "H1",
            "H14"
        ]
    },
    {
        "id": 10,
        "texto": (
            "Resultados compatíveis podem dar suporte à hipótese."
        ),
        "atomos": [
            "H1",
            "H15",
            "H16"
        ]
    },
    {
        "id": 11,
        "texto": (
            "Suporte não transforma necessariamente a hipótese "
            "em verdade absoluta."
        ),
        "atomos": [
            "H1",
            "H16",
            "H17"
        ]
    },
    {
        "id": 12,
        "texto": (
            "Novas evidências podem modificar "
            "a interpretação anterior."
        ),
        "atomos": [
            "H1",
            "H18",
            "H19"
        ]
    },
    {
        "id": 13,
        "texto": (
            "Novas evidências podem contradizer "
            "a interpretação anterior."
        ),
        "atomos": [
            "H1",
            "H18",
            "H20"
        ]
    },
    {
        "id": 14,
        "texto": (
            "A representação deve preservar relações, limitações "
            "e o grau de incerteza."
        ),
        "atomos": [
            "H21",
            "H22",
            "H23"
        ]
    }
]


def extrair_texto(cristal):
    partes = []

    def percorrer(valor):
        if isinstance(valor, dict):
            for chave, conteudo in valor.items():
                partes.append(str(chave))
                percorrer(conteudo)

        elif isinstance(valor, list):
            for item in valor:
                percorrer(item)

        else:
            partes.append(str(valor))

    percorrer(cristal)

    return " ".join(partes).lower()


def encontrar_atomos(texto):
    encontrados = set()

    texto = texto.lower()

    for codigo, palavra in ATOMOS.items():
        if palavra.lower() in texto:
            encontrados.add(codigo)

    return encontrados


print("=== TESTE DE SANIDADE ATÔMICO ===")

print("\nCRISTAL:")
print(
    json.dumps(
        CRISTAL_C,
        ensure_ascii=False,
        indent=2
    )
)

texto_cristal = extrair_texto(
    CRISTAL_C
)

atomos_encontrados = encontrar_atomos(
    texto_cristal
)

print("\n=== ÁTOMOS ENCONTRADOS ===")

if atomos_encontrados:
    for atomo in sorted(atomos_encontrados):
        print(
            f"{atomo}: {ATOMOS[atomo]}"
        )
else:
    print("Nenhum.")

preservados = 0

print("\n=== RESULTADOS ===")

for requisito in REQUISITOS:

    atomos_necessarios = set(
        requisito["atomos"]
    )

    faltantes = (
        atomos_necessarios
        - atomos_encontrados
    )

    completo = (
        len(faltantes) == 0
    )

    if completo:
        preservados += 1

    status = (
        "SIM"
        if completo
        else "NÃO"
    )

    print(
        f"{requisito['id']:02d}. "
        f"{status} | "
        f"{requisito['texto']}"
    )

    if faltantes:
        print(
            "    Faltam: "
            + ", ".join(
                sorted(faltantes)
            )
        )


total = len(REQUISITOS)

percentual = (
    preservados / total
) * 100

print("\n=== RESUMO ===")

print(
    f"Preservados: "
    f"{preservados}/{total}"
)

print(
    f"Cobertura atômica: "
    f"{percentual:.2f}%"
)

print("\n=== DIAGNÓSTICO ===")

if preservados == 0:
    print(
        "PASSOU: o avaliador reconheceu que "
        "o cristal contém apenas o conceito "
        "e não contém os demais conhecimentos."
    )
else:
    print(
        "FALHOU: ainda existe conhecimento "
        "sendo considerado presente sem estar "
        "explicitamente representado."
    )
