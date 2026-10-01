import json
import ollama

MODELO = "qwen2:7b"

cristal_atual = {
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

problemas = {
    "fidelidade_atual": 80,
    "informacoes_perdidas": [
        "a hipótese pode surgir de uma possibilidade ainda não investigada",
        "a hipótese pode ser submetida a novas observações",
        "novas evidências podem contradizer a interpretação anterior"
    ]
}

prompt = f"""
Você está examinando sua própria representação de conhecimento.

CRISTAL ATUAL:
{json.dumps(cristal_atual, ensure_ascii=False, indent=2)}

PROBLEMAS IDENTIFICADOS:
{json.dumps(problemas, ensure_ascii=False, indent=2)}

OBJETIVO:
Crie uma versão melhor do cristal.

REGRAS:
1. Preserve o conhecimento já presente.
2. Tente recuperar os pontos identificados como perdidos.
3. Não aumente o cristal desnecessariamente.
4. Remova redundâncias.
5. Mantenha a incerteza explícita.
6. Não invente fatos.
7. A nova versão deve ser menor ou mais informativa que a anterior.

Responda SOMENTE com JSON válido:

{{
  "conceito": "",
  "essencia": "",
  "relacoes": [],
  "incerteza": ""
}}
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

texto = resposta["message"]["content"].strip()

inicio = texto.find("{")
fim = texto.rfind("}")

if inicio == -1 or fim == -1:
    raise ValueError("O modelo não retornou JSON válido.")

novo_cristal = json.loads(texto[inicio:fim + 1])

print("=== CRISTAL ANTERIOR ===")
print(json.dumps(cristal_atual, ensure_ascii=False, indent=2))

print("\n=== NOVO CRISTAL ===")
print(json.dumps(novo_cristal, ensure_ascii=False, indent=2))
