import json
import ollama

MODELO = "qwen2:7b"

original = """
Uma hipótese é uma ideia provisória criada para explicar um fenômeno
ou orientar uma investigação. Ela não precisa estar correta. Seu valor
está em poder ser examinada, testada e comparada com evidências.

Uma hipótese pode nascer de uma observação, de um padrão encontrado
em dados, de uma experiência anterior ou simplesmente de uma possibilidade
que ainda não foi investigada. Depois de formulada, ela pode ser submetida
a experimentos e novas observações.

Se os resultados forem compatíveis com a hipótese, ela ganha suporte,
mas isso não significa necessariamente que se tornou uma verdade absoluta.
Novas evidências podem modificar ou até contradizer a interpretação anterior.

Por isso, uma hipótese precisa carregar não apenas uma ideia central,
mas também suas relações, suas limitações e o grau de incerteza existente.
"""

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
Compare a informação original com o cristal.

INFORMAÇÃO ORIGINAL:
{original}

CRISTAL:
{json.dumps(cristal, ensure_ascii=False)}

Analise somente a preservação da informação.

Responda SOMENTE neste JSON:

{{
  "informacoes_preservadas": [],
  "informacoes_perdidas": [],
  "informacoes_inventadas": [],
  "fidelidade": 0
}}

A fidelidade deve ser um número de 0 a 100.
Não considere palavras diferentes como perda se o significado for equivalente.
Não considere inferências como informação preservada.
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

resultado = json.loads(texto[inicio:fim + 1])

print(json.dumps(resultado, ensure_ascii=False, indent=2))
