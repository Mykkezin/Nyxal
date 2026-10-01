import json
from pathlib import Path


ARQUIVO_BASE = Path("conhecimento_base.json")


def carregar_base():
    with open(
        ARQUIVO_BASE,
        "r",
        encoding="utf-8"
    ) as arquivo:
        return json.load(arquivo)


def reconstruir(ids, base):
    conhecimento = []

    for identificador in ids:
        if identificador in base:
            conhecimento.append(
                base[identificador]
            )

    return conhecimento


def bytes_texto(texto):
    return len(
        texto.encode("utf-8")
    )


def bytes_json(objeto):
    texto = json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return bytes_texto(texto)


def criar_texto_original(base):
    partes = []

    for item in base.values():
        partes.append(
            item["texto"]
        )

    return "\n".join(partes)


if __name__ == "__main__":

    base = carregar_base()

    cristal = list(
        base.keys()
    )

    texto_original = criar_texto_original(
        base
    )

    tamanho_original = bytes_texto(
        texto_original
    )

    tamanho_ids = bytes_texto(
        "|".join(cristal)
    )

    tamanho_base = bytes_json(
        base
    )

    tamanho_atomo_total = (
        tamanho_ids
        + tamanho_base
    )

    conhecimento = reconstruir(
        cristal,
        base
    )

    reconstruido = "\n".join(
        item["texto"]
        for item in conhecimento
    )

    reconstruido_exato = (
        reconstruido
        == texto_original
    )

    print(
        "=== CRISTAL ATÔMICO ==="
    )

    print(
        f"Átomos armazenados: "
        f"{len(cristal)}"
    )

    print()

    print(
        "=== TAMANHOS ==="
    )

    print(
        f"Conhecimento original: "
        f"{tamanho_original} bytes"
    )

    print(
        f"IDs do cristal: "
        f"{tamanho_ids} bytes"
    )

    print(
        f"Base de conhecimento: "
        f"{tamanho_base} bytes"
    )

    print(
        f"Representação atômica total: "
        f"{tamanho_atomo_total} bytes"
    )

    if tamanho_original > 0:

        economia = (
            100
            - (
                tamanho_atomo_total
                / tamanho_original
                * 100
            )
        )

        print(
            f"Economia total: "
            f"{economia:.2f}%"
        )

    print()

    print(
        "=== RECONSTRUÇÃO ==="
    )

    for identificador, item in zip(
        cristal,
        conhecimento
    ):
        print(
            f"{identificador}: "
            f"{item['texto']}"
        )

    print()

    print(
        "=== INTEGRIDADE ==="
    )

    if reconstruido_exato:
        print(
            "PASSOU: a reconstrução "
            "é exatamente igual ao "
            "conhecimento original."
        )
    else:
        print(
            "FALHOU: a reconstrução "
            "não é idêntica ao original."
        )
