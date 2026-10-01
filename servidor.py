import json
from pathlib import Path
import ollama

ARQUIVO_MEMORIA = Path("memoria/vida_nyxal.json")
MODELO = "qwen2:7b"


def carregar_memoria():
    if ARQUIVO_MEMORIA.exists():
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    return {
        "nome": "Nixal",
        "fase": "nascimento",
        "memorias": []
    }


def salvar_memoria(vida):
    ARQUIVO_MEMORIA.parent.mkdir(parents=True, exist_ok=True)

    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as arquivo:
        json.dump(
            vida,
            arquivo,
            ensure_ascii=False,
            indent=2
        )


def conversar(texto):
    resposta = ollama.chat(
        model=MODELO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é o núcleo local da Nixal. "
                    "Você está em fase de nascimento. "
                    "Responda em português do Brasil."
                )
            },
            {
                "role": "user",
                "content": texto
            }
        ]
    )

    return resposta["message"]["content"]


vida = carregar_memoria()

print("=" * 50)
print("NIXAL — NÚCLEO 0.3")
print("=" * 50)
print(f"Nome: {vida['nome']}")
print(f"Fase: {vida['fase']}")
print(f"Memórias: {len(vida['memorias'])}")
print()

while True:
    texto = input("Você: ").strip()

    if texto.lower() == "sair":
        salvar_memoria(vida)
        print("Nixal: encerrando.")
        break

    if not texto:
        continue

    resposta = conversar(texto)

    vida["memorias"].append({
        "tipo": "entrada",
        "conteudo": texto
    })

    vida["memorias"].append({
        "tipo": "resposta",
        "conteudo": resposta
    })

    salvar_memoria(vida)

    print()
    print(f"Nixal: {resposta}")
    print()
