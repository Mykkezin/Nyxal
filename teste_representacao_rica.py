import json
import re

import ollama


# ============================================================
# MICROETAPA 49
# REPRESENTAÇÃO SEMÂNTICA RICA — V4
#
# Objetivo:
#
# Separar:
#
# 1. PROPOSIÇÃO BASE
# 2. MODALIDADE
#
# Regras centrais:
#
# - modalidade não altera a proposição;
# - negação não transforma "correta" em "incorreta";
# - "não precisa" e "não é necessário" devem convergir
#   para "não_necessidade";
# - "não está" deve preservar a proposição-base "estar"
#   e colocar a força lógica em "negação";
# - a linguagem natural pode variar, mas a representação
#   interna deve ser canônica.
#
# Este experimento NÃO altera:
#
# - pipeline_integrado.py
# - teste_consenso_qwen.py
# - teste_gate_relacional.py
# - gerenciador_cristal.py
# - qualquer cristal binário
# ============================================================


MODELO = "qwen2:7b"

TEMPERATURAS = [
    0.0,
    0.3,
    0.7,
]


MODALIDADES_PERMITIDAS = {
    "possibilidade",
    "necessidade",
    "não_necessidade",
    "negação",
}


TESTES = [
    {
        "id": 1,
        "texto": "Uma hipótese pode estar correta.",
        "proposicao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
        },
        "modalidade": "possibilidade",
    },

    {
        "id": 2,
        "texto": "Uma hipótese não precisa estar correta.",
        "proposicao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
        },
        "modalidade": "não_necessidade",
    },

    {
        "id": 3,
        "texto": "Uma hipótese pode estar incorreta.",
        "proposicao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "incorreta",
        },
        "modalidade": "possibilidade",
    },

    {
        "id": 4,
        "texto": "Não é necessário que uma hipótese esteja correta.",
        "proposicao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
        },
        "modalidade": "não_necessidade",
    },

    {
        "id": 5,
        "texto": "Uma hipótese precisa estar correta.",
        "proposicao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
        },
        "modalidade": "necessidade",
    },

    {
        "id": 6,
        "texto": "Uma hipótese não está correta.",
        "proposicao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
        },
        "modalidade": "negação",
    },
]


# ============================================================
# NORMALIZAÇÃO DE CONCEITO
# ============================================================

def normalizar_conceito(valor):
    if not isinstance(valor, str):
        return valor

    valor = valor.strip()

    artigos = (
        "um ",
        "uma ",
        "o ",
        "a ",
        "os ",
        "as ",
    )

    for artigo in artigos:
        if valor.lower().startswith(artigo):
            valor = valor[len(artigo):]
            break

    return valor.strip()


# ============================================================
# NORMALIZAÇÃO DA RELAÇÃO BASE
#
# A relação representa somente a proposição.
#
# A força modal NÃO deve ficar dentro da relação.
# ============================================================

def normalizar_relacao_base(valor):
    if not isinstance(valor, str):
        return valor

    valor = valor.strip().lower()

    equivalencias = {
        "estar": "estar",
        "pode_estar": "estar",
        "pode estar": "estar",
        "precisa estar": "estar",
        "não precisa estar": "estar",
        "nao precisa estar": "estar",
        "é possível estar": "estar",
        "e possível estar": "estar",
        "não é necessário estar": "estar",
        "nao é necessário estar": "estar",
        "nao e necessario estar": "estar",

        # Negação pertence à modalidade.
        "não está": "estar",
        "nao esta": "estar",
        "não estar": "estar",
        "nao estar": "estar",
    }

    return equivalencias.get(
        valor,
        valor,
    )


# ============================================================
# NORMALIZAÇÃO DETERMINÍSTICA DA PROPOSIÇÃO
#
# O estado explícito da frase tem prioridade.
#
# Isso impede que:
#
# "não precisa estar correta"
#
# seja transformado em:
#
# "estar incorreta"
# ============================================================

def extrair_estado_explicito(texto):
    texto_normalizado = (
        texto
        .strip()
        .lower()
    )

    if re.search(
        r"\bincorreta\b",
        texto_normalizado,
    ):
        return "incorreta"

    if re.search(
        r"\bcorreta\b",
        texto_normalizado,
    ):
        return "correta"

    return None


# ============================================================
# MODALIDADE POR EXPRESSÃO
#
# Camada determinística para equivalências linguísticas
# conhecidas.
#
# A saída do Qwen continua sendo registrada.
# ============================================================

def detectar_modalidade_explicita(texto):
    texto_normalizado = (
        texto
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # NÃO NECESSIDADE
    #
    # Deve ser testada antes de NECESSIDADE.
    # --------------------------------------------------------

    expressoes_nao_necessidade = [
        "não precisa",
        "nao precisa",
        "não é necessário",
        "não é necessaria",
        "nao é necessario",
        "nao e necessario",
    ]

    for expressao in expressoes_nao_necessidade:
        if expressao in texto_normalizado:
            return "não_necessidade"

    # --------------------------------------------------------
    # NECESSIDADE
    # --------------------------------------------------------

    expressoes_necessidade = [
        "precisa",
        "é necessário",
        "é necessaria",
        "e necessario",
        "e necessaria",
    ]

    for expressao in expressoes_necessidade:
        if expressao in texto_normalizado:
            return "necessidade"

    # --------------------------------------------------------
    # POSSIBILIDADE
    # --------------------------------------------------------

    expressoes_possibilidade = [
        "pode",
        "é possível",
        "e possivel",
    ]

    for expressao in expressoes_possibilidade:
        if expressao in texto_normalizado:
            return "possibilidade"

    # --------------------------------------------------------
    # NEGAÇÃO
    #
    # Vem depois das formas de não_necessidade.
    # --------------------------------------------------------

    expressoes_negacao = [
        "não está",
        "nao esta",
        "não é",
        "nao e",
    ]

    for expressao in expressoes_negacao:
        if expressao in texto_normalizado:
            return "negação"

    return None


# ============================================================
# PASSAGEM A — PROPOSIÇÃO BASE
# ============================================================

def extrair_proposicao(
    texto,
    temperatura,
):
    prompt = f"""
Extraia somente a PROPOSIÇÃO BASE da frase.

A proposição-base representa o estado ou relação principal,
independentemente da modalidade.

A modalidade NÃO deve ser incorporada à proposição.

REGRAS:

1. Remova artigos dos conceitos.
2. Para frases sobre o estado de uma hipótese:
   sujeito = hipótese
   relação = estar
3. O objeto representa o estado explicitamente mencionado.
4. Se a frase disser "correta", preserve "correta".
5. Se a frase disser "incorreta", preserve "incorreta".
6. Nunca transforme "correta" em "incorreta"
   por causa de negação ou não_necessidade.
7. Nunca coloque "pode", "precisa", "não precisa",
   "é possível", "não é necessário", "não está"
   ou formas equivalentes dentro da relação.
8. Responda somente JSON válido.

Formato:

{{
  "sujeito": "...",
  "relacao": "...",
  "objeto": "..."
}}

FRASE:

{texto}
""".strip()

    resposta = ollama.chat(
        model=MODELO,
        format="json",
        options={
            "temperature": temperatura,
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "Você extrai a proposição-base "
                    "sem incorporar modalidade."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    bruto = (
        resposta["message"]["content"]
        .strip()
    )

    try:
        candidato = json.loads(
            bruto
        )

    except json.JSONDecodeError:
        return {
            "status": "ERRO_JSON",
            "bruto": bruto,
        }

    if not isinstance(
        candidato,
        dict,
    ):
        return {
            "status": "ERRO_ESTRUTURA",
            "bruto": bruto,
        }

    sujeito = normalizar_conceito(
        candidato.get(
            "sujeito"
        )
    )

    relacao = normalizar_relacao_base(
        candidato.get(
            "relacao"
        )
    )

    objeto_qwen = normalizar_conceito(
        candidato.get(
            "objeto"
        )
    )

    objeto_explicito = (
        extrair_estado_explicito(
            texto
        )
    )

    objeto_final = (
        objeto_explicito
        if objeto_explicito is not None
        else objeto_qwen
    )

    proposicao = {
        "sujeito": sujeito,
        "relacao": relacao,
        "objeto": objeto_final,
    }

    if relacao != "estar":
        return {
            "status": "RELACAO_BASE_INVALIDA",
            "proposicao": proposicao,
            "bruto": bruto,
        }

    return {
        "status": "OK",
        "proposicao": proposicao,
        "objeto_qwen": objeto_qwen,
        "objeto_explicito": objeto_explicito,
        "bruto": bruto,
    }


# ============================================================
# PASSAGEM B — MODALIDADE
# ============================================================

def extrair_modalidade(
    texto,
    temperatura,
):
    prompt = f"""
Classifique somente a modalidade lógica da frase.

Modalidades permitidas:

- possibilidade
- necessidade
- não_necessidade
- negação

REGRAS:

1. "pode" ou "é possível" indica possibilidade.
2. "precisa" ou "é necessário" indica necessidade.
3. "não precisa" ou "não é necessário" indica
   não_necessidade.
4. "não está" ou uma negação direta do estado indica
   negação.
5. "não precisa" NÃO é possibilidade.
6. "não é necessário" NÃO é necessidade.
7. "não está" NÃO é não_necessidade.
8. Responda somente JSON válido.
9. Use exatamente a chave "modalidade".

Formato:

{{
  "modalidade": "..."
}}

FRASE:

{texto}
""".strip()

    resposta = ollama.chat(
        model=MODELO,
        format="json",
        options={
            "temperature": temperatura,
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um classificador rigoroso "
                    "de modalidade lógica."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    bruto = (
        resposta["message"]["content"]
        .strip()
    )

    try:
        candidato = json.loads(
            bruto
        )

    except json.JSONDecodeError:
        return {
            "status": "ERRO_JSON",
            "bruto": bruto,
        }

    modalidade_qwen = candidato.get(
        "modalidade"
    )

    modalidade_explicita = (
        detectar_modalidade_explicita(
            texto
        )
    )

    if modalidade_qwen not in MODALIDADES_PERMITIDAS:
        if modalidade_explicita is None:
            return {
                "status": "MODALIDADE_INVALIDA",
                "modalidade_qwen": modalidade_qwen,
                "bruto": bruto,
            }

        modalidade_final = (
            modalidade_explicita
        )

        ajustada = True

    elif (
        modalidade_explicita is not None
        and modalidade_qwen
        != modalidade_explicita
    ):
        modalidade_final = (
            modalidade_explicita
        )

        ajustada = True

    else:
        modalidade_final = modalidade_qwen
        ajustada = False

    return {
        "status": "OK",
        "modalidade": modalidade_final,
        "modalidade_qwen": modalidade_qwen,
        "modalidade_explicita": modalidade_explicita,
        "ajustada": ajustada,
        "bruto": bruto,
    }


# ============================================================
# EXECUTAR TESTE
# ============================================================

def executar_teste(teste):
    print()
    print("=" * 70)
    print(
        f"TESTE {teste['id']}"
    )
    print("=" * 70)

    print(
        f"Frase: {teste['texto']}"
    )

    esperado_rico = {
        **teste["proposicao"],
        "modalidade": teste[
            "modalidade"
        ],
    }

    print()
    print("ESPERADO:")
    print(
        json.dumps(
            esperado_rico,
            ensure_ascii=False,
            indent=2,
        )
    )

    representacoes = []

    for temperatura in TEMPERATURAS:
        proposicao = extrair_proposicao(
            teste["texto"],
            temperatura,
        )

        modalidade = extrair_modalidade(
            teste["texto"],
            temperatura,
        )

        print()
        print(
            f"TEMPERATURA {temperatura:.1f}"
        )

        print()
        print("PROPOSIÇÃO:")
        print(
            json.dumps(
                proposicao,
                ensure_ascii=False,
                indent=2,
            )
        )

        print()
        print("MODALIDADE:")
        print(
            json.dumps(
                modalidade,
                ensure_ascii=False,
                indent=2,
            )
        )

        if (
            proposicao["status"] == "OK"
            and modalidade["status"] == "OK"
        ):
            representacao = {
                **proposicao["proposicao"],
                "modalidade": modalidade[
                    "modalidade"
                ],
            }

            representacoes.append(
                representacao
            )

            print()
            print("REPRESENTAÇÃO RICA:")
            print(
                json.dumps(
                    representacao,
                    ensure_ascii=False,
                    indent=2,
                )
            )

    if len(representacoes) != len(
        TEMPERATURAS
    ):
        print()
        print("CONSENSO RICO: NÃO")
        print("BENCHMARK RICO: FALHOU")

        return {
            "consenso": False,
            "correto": False,
        }

    primeiro = representacoes[0]

    consenso = all(
        representacao == primeiro
        for representacao in representacoes
    )

    correto = all(
        representacao == esperado_rico
        for representacao in representacoes
    )

    print()
    print(
        "CONSENSO RICO: "
        + (
            "SIM"
            if consenso
            else "NÃO"
        )
    )

    print(
        "BENCHMARK RICO: "
        + (
            "PASSOU"
            if correto
            else "FALHOU"
        )
    )

    return {
        "consenso": consenso,
        "correto": correto,
    }


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print(
        "=== MICROETAPA 49 ==="
    )

    print(
        "REPRESENTAÇÃO SEMÂNTICA RICA — V4"
    )

    total = len(
        TESTES
    )

    consensos = 0
    corretos = 0
    aprovados = 0

    for teste in TESTES:
        resultado = executar_teste(
            teste
        )

        if resultado["consenso"]:
            consensos += 1

        if resultado["correto"]:
            corretos += 1

        if (
            resultado["consenso"]
            and resultado["correto"]
        ):
            aprovados += 1

    print()
    print("=" * 70)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 70)

    print(
        f"Testes: {total}"
    )

    print(
        f"Consenso rico: "
        f"{consensos}/{total} "
        f"({consensos / total * 100:.2f}%)"
    )

    print(
        f"Benchmark rico: "
        f"{corretos}/{total} "
        f"({corretos / total * 100:.2f}%)"
    )

    print(
        f"Consenso + benchmark: "
        f"{aprovados}/{total} "
        f"({aprovados / total * 100:.2f}%)"
    )


if __name__ == "__main__":
    main()
