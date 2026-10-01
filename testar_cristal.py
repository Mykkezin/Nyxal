import ollama

MODELO = "qwen2:7b"

cristal = {
    "conceito": "Hipótese",
    "essencia": "ideia provisória para explicação e investigação",
    "relacoes": [
        "baseada em observação",
        "nascida de padrões",
        "fruto de experiência",
        "aberta a experimentação"
    ],
    "incerteza": "carrega ideia, relações, limites e incerteza"
}

prompt = f"""
Você recebeu APENAS este cristal:

{cristal}

Reconstrua o conhecimento que ele representa.

Regras:
1. Não invente informações.
2. Não acrescente fatos que não estejam sustentados pelo cristal.
3. Separe claramente o que está explícito do que é apenas inferência.
4. Diga quais informações provavelmente foram perdidas.

Responda em português.
"""

resposta = ollama.chat(
    model=MODELO,
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)

print("=== RECONSTRUÇÃO DO CRISTAL ===")
print(resposta["message"]["content"])
