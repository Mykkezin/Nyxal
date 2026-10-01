import json
import ollama

MODELO = "qwen2:7b"

experiencia = """
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

prompt = f"""
Transforme a experiência abaixo em uma representação extremamente compacta.

EXPERIÊNCIA:
{experiencia}

Responda SOMENTE com JSON válido:

{{
  "conceito": "nome curto",
  "essencia": "ideia central",
  "relacoes": ["relação 1", "relação 2", "relação 3"],
  "incerteza": "incerteza principal"
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

cristal = json.loads(texto[inicio:fim + 1])

cristal_texto = json.dumps(
    cristal,
    ensure_ascii=False,
    separators=(",", ":")
)

original_bytes = len(experiencia.encode("utf-8"))
cristal_bytes = len(cristal_texto.encode("utf-8"))

print("=== EXPERIÊNCIA ===")
print(f"{original_bytes} bytes")

print("\n=== CRISTAL ===")
print(cristal_texto)
print(f"{cristal_bytes} bytes")

reducao = 100 - (cristal_bytes / original_bytes * 100)

print("\n=== RESULTADO ===")
print(f"Redução: {reducao:.2f}%")
