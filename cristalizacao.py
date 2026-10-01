import json
from pathlib import Path
import ollama

ARQUIVO = Path("memoria/cristalizacao.json")
MODELO = "qwen2:7b"


def carregar():
    if ARQUIVO.exists():
        with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    return {"conceitos": {}}


def salvar(dados):
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)

    with open(ARQUIVO, "w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2
        )


def cristalizar(experiencia):
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


def reconstruir(cristal):
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


if __name__ == "__main__":

    experiencia = (
        "Uma hipótese é uma ideia provisória que pode ser testada "
        "por observação ou experimento. Ela pode estar correta ou "
        "errada e precisa de evidências para ser confirmada."
    )

    cristal = cristalizar(experiencia)

    dados = carregar()
    dados["conceitos"][cristal["conceito"]] = cristal
    salvar(dados)

    print("\n=== EXPERIÊNCIA ORIGINAL ===")
    print(experiencia)

    print("\n=== CRISTAL ===")
    print(json.dumps(cristal, ensure_ascii=False, indent=2))

    print("\n=== RECONSTRUÇÃO ===")
    reconstruida = reconstruir(cristal)
    print(reconstruida)
