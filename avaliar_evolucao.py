import json
import ollama

MODELO = "qwen2:7b"

CRISTAL_A = {
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

CRISTAL_B = {
    "conceito": "Hipótese",
    "essencia": (
        "uma ideia provisória para explicação e investigação baseada em "
        "observação, nascida de padrões e fruto de experiência, "
        "aberta a experimentação"
    ),
    "relacoes": [
        "surgimento de uma possibilidade ainda não investigada",
        "submissão a novas observações",
        "efeito de novas evidências"
    ],
    "incerteza": "carrega ideia, relações, limites e incerteza"
}

REQUISITOS = [
    {
        "id": 1,
        "texto": "A hipótese é uma ideia provisória.",
        "componentes": [
            "é uma ideia",
            "é provisória"
        ]
    },
    {
        "id": 2,
        "texto": (
            "A hipótese pode ser usada para explicar um fenômeno "
            "ou orientar uma investigação."
        ),
        "componentes": [
            "pode ser usada para explicar um fenômeno",
            "pode orientar uma investigação"
        ]
    },
    {
        "id": 3,
        "texto": "A hipótese não precisa estar correta.",
        "componentes": [
            "a hipótese pode estar incorreta",
            "a hipótese não precisa estar correta"
        ]
    },
    {
        "id": 4,
        "texto": "Uma hipótese pode surgir de uma observação.",
        "componentes": [
            "pode surgir de observação"
        ]
    },
    {
        "id": 5,
        "texto": "Uma hipótese pode surgir de padrões encontrados em dados.",
        "componentes": [
            "pode surgir de padrões",
            "os padrões podem estar em dados"
        ]
    },
    {
        "id": 6,
        "texto": "Uma hipótese pode surgir de uma experiência anterior.",
        "componentes": [
            "pode surgir de experiência anterior"
        ]
    },
    {
        "id": 7,
        "texto": (
            "Uma hipótese pode surgir de uma possibilidade "
            "que ainda não foi investigada."
        ),
        "componentes": [
            "pode surgir de uma possibilidade",
            "a possibilidade ainda não foi investigada"
        ]
    },
    {
        "id": 8,
        "texto": "Uma hipótese pode ser submetida a experimentos.",
        "componentes": [
            "pode ser submetida a experimentos"
        ]
    },
    {
        "id": 9,
        "texto": "Uma hipótese pode ser submetida a novas observações.",
        "componentes": [
            "pode ser submetida a novas observações"
        ]
    },
    {
        "id": 10,
        "texto": "Resultados compatíveis podem dar suporte à hipótese.",
        "componentes": [
            "resultados podem ser compatíveis",
            "resultados compatíveis podem dar suporte à hipótese"
        ]
    },
    {
        "id": 11,
        "texto": (
            "Suporte não transforma necessariamente a hipótese "
            "em verdade absoluta."
        ),
        "componentes": [
            "receber suporte não garante verdade absoluta"
        ]
    },
    {
        "id": 12,
        "texto": (
            "Novas evidências podem modificar "
            "a interpretação anterior."
        ),
        "componentes": [
            "novas evidências podem aparecer",
            "novas evidências podem modificar a interpretação anterior"
        ]
    },
    {
        "id": 13,
        "texto": (
            "Novas evidências podem contradizer "
            "a interpretação anterior."
        ),
        "componentes": [
            "novas evidências podem contradizer a interpretação anterior"
        ]
    },
    {
        "id": 14,
        "texto": (
            "A representação deve preservar relações, limitações "
            "e o grau de incerteza."
        ),
        "componentes": [
            "preserva relações",
            "preserva limitações",
            "preserva o grau de incerteza"
        ]
    }
]


def tamanho_bytes(objeto):
    texto = json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return len(texto.encode("utf-8"))


def extrair_evidencias(objeto, caminho="raiz"):
    """
    Converte o cristal em uma lista de evidências concretas.

    Cada evidência possui:
    - índice
    - caminho
    - conteúdo
    """

    evidencias = []

    if isinstance(objeto, dict):

        for chave, valor in objeto.items():

            novo_caminho = f"{caminho}.{chave}"

            evidencias.extend(
                extrair_evidencias(
                    valor,
                    novo_caminho
                )
            )

    elif isinstance(objeto, list):

        # Mantemos a lista inteira como evidência,
        # porque uma relação pode depender do conjunto.
        evidencias.append({
            "caminho": caminho,
            "valor": objeto
        })

        for indice, valor in enumerate(objeto):

            novo_caminho = (
                f"{caminho}[{indice}]"
            )

            evidencias.extend(
                extrair_evidencias(
                    valor,
                    novo_caminho
                )
            )

    else:

        evidencias.append({
            "caminho": caminho,
            "valor": objeto
        })

    for indice, evidencia in enumerate(
        evidencias
    ):

        evidencia["indice"] = indice

    return evidencias


def chamar_json(prompt, limite=80):
    """
    Faz uma chamada curta ao Qwen.
    Tenta novamente se o Ollama abortar.
    """

    try:

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
                "temperature": 0,
                "num_predict": limite
            }
        )

    except Exception:

        resposta = ollama.chat(
            model=MODELO,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Responda somente JSON válido. "
                        + prompt
                    )
                }
            ],
            format="json",
            options={
                "temperature": 0,
                "num_predict": 40
            }
        )

    texto = (
        resposta[
            "message"
        ]["content"].strip()
    )

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if (
        inicio == -1
        or fim == -1
    ):
        raise ValueError(
            "O modelo não retornou JSON válido."
        )

    return json.loads(
        texto[
            inicio:fim + 1
        ]
    )


def selecionar_evidencias(
    evidencias,
    componente
):
    """
    Primeira etapa:
    o Qwen recebe somente as evidências reais
    extraídas do cristal e escolhe quais podem
    sustentar o componente.
    """

    lista = []

    for evidencia in evidencias:

        lista.append({
            "indice": evidencia["indice"],
            "conteudo": evidencia["valor"]
        })

    prompt = f"""
Você deve localizar evidências para uma afirmação.

AFIRMAÇÃO:
{componente}

EVIDÊNCIAS DISPONÍVEIS:
{json.dumps(lista, ensure_ascii=False)}

Escolha somente os índices das evidências cujo CONTEÚDO
realmente possa sustentar a afirmação.

Não invente evidências.
Não use conhecimento externo.
Não use o nome do campo ou caminho como argumento.

Se nenhuma evidência for suficiente, retorne lista vazia.

Responda SOMENTE:

{{"indices":[]}}
"""

    try:

        resultado = chamar_json(
            prompt,
            limite=60
        )

    except Exception:

        return []

    indices = resultado.get(
        "indices",
        []
    )

    if not isinstance(
        indices,
        list
    ):
        return []

    indices_validos = []

    indices_existentes = {
        evidencia["indice"]
        for evidencia in evidencias
    }

    for indice in indices:

        if (
            isinstance(indice, int)
            and
            indice in indices_existentes
        ):
            if indice not in indices_validos:
                indices_validos.append(
                    indice
                )

    return indices_validos


def verificar_evidencias(
    componente,
    evidencias_selecionadas
):
    """
    Segunda etapa:
    o Qwen só recebe o componente e as
    evidências escolhidas.

    Ele não recebe o cristal inteiro.
    """

    if not evidencias_selecionadas:

        return False

    prompt = f"""
Determine se as evidências abaixo sustentam
o significado COMPLETO da afirmação.

AFIRMAÇÃO:
{componente}

EVIDÊNCIAS:
{json.dumps(evidencias_selecionadas, ensure_ascii=False)}

Regras:

1. Use somente essas evidências.
2. Não use conhecimento externo.
3. Não complete lacunas.
4. Uma evidência vaga não é suficiente.
5. Se faltar uma parte essencial da afirmação,
   responda false.

Responda SOMENTE:

{{"preservado":true}}

ou:

{{"preservado":false}}
"""

    try:

        resultado = chamar_json(
            prompt,
            limite=40
        )

    except Exception:

        return False

    return bool(
        resultado.get(
            "preservado",
            False
        )
    )


def analisar_componente(
    cristal,
    componente
):
    """
    Analisa um componente em duas etapas.
    """

    evidencias = extrair_evidencias(
        cristal
    )

    indices = selecionar_evidencias(
        evidencias,
        componente
    )

    selecionadas = []

    for indice in indices:

        for evidencia in evidencias:

            if (
                evidencia["indice"]
                == indice
            ):
                selecionadas.append(
                    evidencia
                )
                break

    preservado = verificar_evidencias(
        componente,
        [
            {
                "caminho": evidencia[
                    "caminho"
                ],
                "valor": evidencia[
                    "valor"
                ]
            }
            for evidencia in selecionadas
        ]
    )

    return {
        "presente": preservado,
        "evidencias": selecionadas
    }


def avaliar_requisito(
    cristal,
    requisito
):
    componentes = []

    for componente in requisito[
        "componentes"
    ]:

        resultado = analisar_componente(
            cristal,
            componente
        )

        componentes.append({
            "texto": componente,
            "presente": resultado[
                "presente"
            ],
            "evidencias": resultado[
                "evidencias"
            ]
        })

    presentes = sum(
        1
        for componente in componentes
        if componente["presente"]
    )

    total = len(componentes)

    if presentes == total:

        status = "PRESERVADO"

    elif presentes > 0:

        status = "PARCIAL"

    else:

        status = "NÃO PRESERVADO"

    return {
        "status": status,
        "componentes": componentes
    }


def avaliar(
    cristal,
    nome
):
    print(
        f"\n=== {nome} ==="
    )

    tamanho = tamanho_bytes(
        cristal
    )

    preservados = 0
    parciais = 0
    perdidos = 0

    for requisito in REQUISITOS:

        resultado = avaliar_requisito(
            cristal,
            requisito
        )

        status = resultado[
            "status"
        ]

        if status == "PRESERVADO":

            preservados += 1

        elif status == "PARCIAL":

            parciais += 1

        else:

            perdidos += 1

        print(
            f"\n{requisito['id']:02d}. "
            f"{status} | "
            f"{requisito['texto']}"
        )

        for componente in resultado[
            "componentes"
        ]:

            simbolo = (
                "✓"
                if componente["presente"]
                else "✗"
            )

            print(
                f"    {simbolo} "
                f"{componente['texto']}"
            )

            for evidencia in componente[
                "evidencias"
            ]:

                print(
                    "        "
                    f"{evidencia['caminho']} = "
                    f"{evidencia['valor']}"
                )

    total = len(REQUISITOS)

    pontuacao = (
        preservados +
        (parciais * 0.5)
    ) / total * 100

    print("\n--- RESUMO ---")

    print(
        f"Tamanho: "
        f"{tamanho} bytes"
    )

    print(
        f"Preservados: "
        f"{preservados}/{total}"
    )

    print(
        f"Parciais: "
        f"{parciais}/{total}"
    )

    print(
        f"Não preservados: "
        f"{perdidos}/{total}"
    )

    print(
        f"Cobertura diagnóstica: "
        f"{pontuacao:.2f}%"
    )

    return {
        "tamanho": tamanho,
        "preservados": preservados,
        "parciais": parciais,
        "perdidos": perdidos,
        "pontuacao": pontuacao
    }


print(
    "=== AVALIADOR EM DUAS CAMADAS ==="
)

resultado_a = avaliar(
    CRISTAL_A,
    "CRISTAL A"
)

resultado_b = avaliar(
    CRISTAL_B,
    "CRISTAL B"
)

print(
    "\n=== DECISÃO EXPERIMENTAL ==="
)

if (
    resultado_b["preservados"]
    >= resultado_a["preservados"]
    and
    resultado_b["parciais"]
    >= resultado_a["parciais"]
    and
    resultado_b["tamanho"]
    <= resultado_a["tamanho"]
):

    print(
        "ACEITAR CRISTAL B"
    )

else:

    print(
        "REJEITAR CRISTAL B"
    )
