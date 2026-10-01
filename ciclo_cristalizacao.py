import json
from pathlib import Path
import ollama

MODELO = "qwen2:7b"

ARQUIVO_CRISTAL = Path("memoria/cristal_atual.json")

ORIGINAL = """
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

CRISTAL_INICIAL = {
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

REQUISITOS = [
    "A hipótese é uma ideia provisória.",
    "A hipótese pode ser usada para explicar um fenômeno ou orientar uma investigação.",
    "A hipótese não precisa estar correta.",
    "Uma hipótese pode surgir de uma observação.",
    "Uma hipótese pode surgir de padrões encontrados em dados.",
    "Uma hipótese pode surgir de uma experiência anterior.",
    "Uma hipótese pode surgir de uma possibilidade ainda não investigada.",
    "Uma hipótese pode ser submetida a experimentos.",
    "Uma hipótese pode ser submetida a novas observações.",
    "Resultados compatíveis podem dar suporte à hipótese.",
    "Suporte não transforma necessariamente a hipótese em verdade absoluta.",
    "Novas evidências podem modificar a interpretação anterior.",
    "Novas evidências podem contradizer a interpretação anterior.",
    "A representação deve preservar relações, limitações e o grau de incerteza."
]


def tamanho_bytes(objeto):
    texto = json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":")
    )
    return len(texto.encode("utf-8"))


def carregar_cristal():
    if ARQUIVO_CRISTAL.exists():
        with open(ARQUIVO_CRISTAL, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    ARQUIVO_CRISTAL.parent.mkdir(parents=True, exist_ok=True)

    with open(ARQUIVO_CRISTAL, "w", encoding="utf-8") as arquivo:
        json.dump(
            CRISTAL_INICIAL,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    return CRISTAL_INICIAL


def gerar_candidato(cristal_atual):
    prompt = f"""
Você está tentando melhorar sua própria representação de conhecimento.

INFORMAÇÃO ORIGINAL:
{ORIGINAL}

REPRESENTAÇÃO ATUAL:
{json.dumps(cristal_atual, ensure_ascii=False)}

OBJETIVO:
Encontre uma representação que use menos espaço que a atual,
mas preserve o máximo possível do conhecimento original.

Você pode reorganizar, combinar ou mudar a estrutura da representação.

Não receba nenhuma fórmula de como fazer isso.
Descubra uma representação que considere eficiente.

REGRAS:
- Não invente conhecimento.
- Não remova uma informação importante apenas para diminuir o tamanho.
- Pode mudar a estrutura do JSON.
- A representação precisa continuar sendo interpretável.
- Retorne SOMENTE JSON válido.
"""

    resposta = ollama.chat(
        model=MODELO,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        format="json",
        options={
            "temperature": 0
        }
    )

    texto = resposta["message"]["content"].strip()

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio == -1 or fim == -1:
        raise ValueError("O modelo não retornou um objeto JSON válido.")

    return json.loads(texto[inicio:fim + 1])


def verificar_requisito(cristal, requisito):
    prompt = f"""
Compare o cristal com o requisito.

INFORMAÇÃO ORIGINAL:
{ORIGINAL}

CRISTAL:
{json.dumps(cristal, ensure_ascii=False)}

REQUISITO:
{requisito}

O significado do requisito está claramente preservado no cristal?

Não use conhecimento externo.
Não complete lacunas com a informação original.
Considere somente o que o cristal realmente representa.

Responda SOMENTE:

{{"preservado": true}}

ou:

{{"preservado": false}}
"""

    resposta = ollama.chat(
        model=MODELO,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        format="json",
        options={
            "temperature": 0
        }
    )

    resultado = json.loads(
        resposta["message"]["content"]
    )

    return bool(resultado.get("preservado", False))


def medir_fidelidade(cristal):
    preservados = 0

    for requisito in REQUISITOS:
        if verificar_requisito(cristal, requisito):
            preservados += 1

    total = len(REQUISITOS)

    return (preservados / total) * 100


def salvar_cristal(cristal):
    ARQUIVO_CRISTAL.parent.mkdir(parents=True, exist_ok=True)

    with open(ARQUIVO_CRISTAL, "w", encoding="utf-8") as arquivo:
        json.dump(
            cristal,
            arquivo,
            ensure_ascii=False,
            indent=2
        )


print("=== CICLO DE CRISTALIZAÇÃO ===")

cristal_atual = carregar_cristal()

tamanho_atual = tamanho_bytes(cristal_atual)
fidelidade_atual = medir_fidelidade(cristal_atual)

print("\n=== ESTADO ATUAL ===")
print(f"Tamanho: {tamanho_atual} bytes")
print(f"Fidelidade estimada: {fidelidade_atual:.2f}%")

print("\nNixal está tentando encontrar uma representação melhor...")

candidato = gerar_candidato(cristal_atual)

tamanho_candidato = tamanho_bytes(candidato)
fidelidade_candidato = medir_fidelidade(candidato)

print("\n=== CANDIDATO ===")
print(json.dumps(candidato, ensure_ascii=False, indent=2))

print("\n=== COMPARAÇÃO ===")
print(
    f"Atual:    {tamanho_atual} bytes | "
    f"{fidelidade_atual:.2f}%"
)

print(
    f"Candidato: {tamanho_candidato} bytes | "
    f"{fidelidade_candidato:.2f}%"
)

print("\n=== DECISÃO ===")

if (
    fidelidade_candidato >= fidelidade_atual
    and tamanho_candidato < tamanho_atual
):
    salvar_cristal(candidato)

    print("ACEITO.")
    print("A nova representação é menor e preservou a fidelidade.")
else:
    print("REJEITADO.")
    print("A representação atual continua sendo a melhor versão.")
