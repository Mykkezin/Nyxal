import json

from gerenciador_cristal import (
    caminho_do_projeto,
    carregar_json_com_seguranca,
    salvar_json_atomicamente,
)

ARQUIVO = caminho_do_projeto("memoria", "cristalizacao.json")
MODELO = "qwen2:7b"

CAMPOS_OBRIGATORIOS = ("conceito", "essencia", "relacoes", "incerteza")


def validar_cristal_semantico(dados):
    """Confere o schema do cristal JSON antes de qualquer gravação.

    Um candidato malformado precisa falhar aqui, nunca substituir o
    último estado válido do arquivo.
    """

    if not isinstance(dados, dict):
        raise ValueError("O cristal precisa de um objeto JSON no topo.")

    conceitos = dados.get("conceitos")

    if not isinstance(conceitos, dict):
        raise ValueError("O cristal precisa do campo 'conceitos' como objeto.")

    for nome, cristal in conceitos.items():
        if not isinstance(nome, str) or not nome:
            raise ValueError("Todo conceito precisa de um nome não vazio.")

        if not isinstance(cristal, dict):
            raise ValueError(
                f"O conceito {nome!r} precisa ser um objeto JSON."
            )

        for campo in CAMPOS_OBRIGATORIOS:
            if campo not in cristal:
                raise ValueError(
                    f"O conceito {nome!r} perdeu o campo {campo!r}."
                )

        if cristal["conceito"] != nome:
            raise ValueError(
                f"O conceito {nome!r} declara nome diferente "
                f"({cristal['conceito']!r})."
            )

        for campo in ("essencia", "incerteza"):
            if not isinstance(cristal[campo], str):
                raise ValueError(
                    f"{nome!r}: {campo} precisa ser texto."
                )

        if not isinstance(cristal["relacoes"], list):
            raise ValueError(
                f"{nome!r}: relacoes precisa ser lista."
            )

        for relacao in cristal["relacoes"]:
            if not isinstance(relacao, str):
                raise ValueError(
                    f"{nome!r}: cada relação precisa ser texto."
                )

    return dados


def carregar():
    # Passa pelo gerenciador para ganho persistência atômica e
    # quarentena em caso de JSON corrompido. O formato do arquivo
    # é exatamente o mesmo.
    return validar_cristal_semantico(
        carregar_json_com_seguranca(
            ARQUIVO,
            {"conceitos": {}},
        )
    )


def salvar(dados):
    validar_cristal_semantico(dados)

    return salvar_json_atomicamente(
        dados,
        ARQUIVO,
    )


def cristalizar(experiencia):
    # Dependência opcional: só importa quando o modelo é chamado.
    import ollama

    prompt = f"""
Transforme a experiência abaixo em uma representação compacta.

EXPERIÊNCIA:
{experiencia}

Responda SOMENTE com JSON válido:

{{
  "conceito": "nome curto",
  "essencia": "ideia central em poucas palavras",
  "relacoes": ["relação 1", "relação 2", "relação 3"],
  "incerteza": "o que ainda não foi confirmado"
}}
"""

    resposta = ollama.chat(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}]
    )

    texto = resposta["message"]["content"].strip()

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio == -1 or fim == -1:
        raise ValueError("O modelo não retornou JSON válido.")

    return json.loads(texto[inicio:fim + 1])


def adicionar_conceito(dados, cristal, substituir=False):
    """Acrescenta um cristal sem descartar uma versão mais nova.

    O arquivo inteiro é revalidado antes de voltar, então um candidato
    inválido nunca é gravado por cima do último estado válido.
    """

    anterior = dados["conceitos"].get(cristal["conceito"])

    if anterior is not None and not substituir:
        raise ValueError(
            f"O conceito {cristal['conceito']!r} já existe. "
            "Use substituir=True para alterá-lo."
        )

    dados["conceitos"][cristal["conceito"]] = cristal

    return validar_cristal_semantico(dados)


def reconstruir(cristal):
    # Dependência opcional: só importa quando o modelo é chamado.
    import ollama

    prompt = f"""
Você recebeu somente esta representação cristalizada:

{json.dumps(cristal, ensure_ascii=False)}

Reconstrua o conhecimento que provavelmente originou essa representação.

Não invente informações que não estejam sustentadas pelo cristal.
Explique também qual informação parece ter sido perdida ou ficou incerta.
"""

    resposta = ollama.chat(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}]
    )

    return resposta["message"]["content"]


def main():

    experiencia = (
        "Uma hipótese é uma ideia provisória que pode ser testada "
        "por observação ou experimento. Ela pode estar correta ou "
        "errada e precisa de evidências para ser confirmada."
    )

    cristal = cristalizar(experiencia)

    dados = adicionar_conceito(carregar(), cristal)
    salvar(dados)

    print("\n=== EXPERIÊNCIA ORIGINAL ===")
    print(experiencia)

    print("\n=== CRISTAL ===")
    print(json.dumps(cristal, ensure_ascii=False, indent=2))

    print("\n=== RECONSTRUÇÃO ===")
    reconstruida = reconstruir(cristal)
    print(reconstruida)


if __name__ == "__main__":
    main()
