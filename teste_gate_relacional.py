import json

import ollama


# ============================================================
# MICROETAPA 47
# GATE RELACIONAL
#
# Objetivo:
#
# combinar:
#
# 1. interpretação do Qwen
# 2. consenso
# 3. validação estrutural
# 4. assinatura sujeito/relação/objeto
#
# O benchmark externo continua sendo usado apenas
# para medir o desempenho do gate.
# ============================================================


MODELO = "qwen2:7b"

TEMPERATURAS = [
    0.0,
    0.3,
    0.7,
]


# ============================================================
# CONCEITOS
# ============================================================

CONCEITOS = {
    "hipótese",
    "observação",
    "experimento",
    "evidência",
    "resultado",
    "pergunta",
    "investigação",
    "dado",
    "padrão",
    "incerteza",
    "conclusão",
    "teoria",
    "explicação",
    "erro",
    "previsão",
    "nova",
    "correta",
    "incorreta",
    "provisória",
}


# ============================================================
# ASSINATURAS DAS RELAÇÕES
#
# Esta é uma regra determinística.
#
# Formato:
#
# relação:
#     sujeitos permitidos
#     objetos permitidos
#
# Não é um julgamento do Qwen.
# ============================================================

ASSINATURAS = {
    "pode_gerar": {
        "sujeitos": {
            "observação",
            "padrão",
            "investigação",
            "hipótese",
            "explicação",
            "experimento",
        },
        "objetos": {
            "hipótese",
            "dado",
            "resultado",
            "previsão",
            "explicação",
        },
    },

    "pode_gerar_previsao": {
        "sujeitos": {
            "hipótese",
            "teoria",
        },
        "objetos": {
            "previsão",
        },
    },

    "pode_testar": {
        "sujeitos": {
            "experimento",
        },
        "objetos": {
            "hipótese",
            "previsão",
        },
    },

    "pode_ser_testada_por": {
        "sujeitos": {
            "hipótese",
            "previsão",
        },
        "objetos": {
            "experimento",
        },
    },

    "pode_receber": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "evidência",
        },
    },

    "pode_modificar": {
        "sujeitos": {
            "evidência",
            "resultado",
            "erro",
            "observação",
            "investigação",
        },
        "objetos": {
            "hipótese",
            "conclusão",
        },
    },

    "pode_ser_modificada_por": {
        "sujeitos": {
            "hipótese",
            "conclusão",
        },
        "objetos": {
            "evidência",
            "resultado",
        },
    },

    "pode_estar": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "correta",
            "incorreta",
        },
    },

    "continua_sendo": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "provisória",
        },
    },

    "precisa_lidar_com": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "incerteza",
        },
    },

    "pode_ser_apoiada_por": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "resultado",
        },
    },

    "pode_ser_contradita_por": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "resultado",
        },
    },

    "contradiz": {
        "sujeitos": {
            "evidência",
            "resultado",
            "observação",
        },
        "objetos": {
            "hipótese",
            "conclusão",
        },
    },

    "pode_explicar": {
        "sujeitos": {
            "hipótese",
            "teoria",
        },
        "objetos": {
            "explicação",
        },
    },

    "pode_conter": {
        "sujeitos": {
            "teoria",
        },
        "objetos": {
            "hipótese",
        },
    },

    "pode_conter_erro": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "erro",
        },
    },

    "pode_reduzir": {
        "sujeitos": {
            "investigação",
        },
        "objetos": {
            "incerteza",
        },
    },
}


# ============================================================
# PROMPT
# ============================================================

def criar_prompt(texto):
    relacoes = []

    for nome, assinatura in ASSINATURAS.items():
        relacoes.append(
            f"{nome}: "
            f"sujeitos={sorted(assinatura['sujeitos'])}; "
            f"objetos={sorted(assinatura['objetos'])}"
        )

    return f"""
Transforme a frase em uma única tripla estrutural.

Responda somente com JSON válido:

{{
  "sujeito": "...",
  "relacao": "...",
  "objeto": "..."
}}

CONCEITOS PERMITIDOS:
{sorted(CONCEITOS)}

RELAÇÕES E ASSINATURAS:
{chr(10).join(relacoes)}

REGRAS:
1. Não invente conceitos.
2. Não invente relações.
3. Não troque sujeito e objeto.
4. Respeite a direção da relação.
5. Escolha a relação de acordo com seu significado.
6. Responda somente JSON.

FRASE:
{texto}
""".strip()


# ============================================================
# QWEN
# ============================================================

def interpretar(texto, temperatura):
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
                    "Você é um interpretador estrutural "
                    "rigoroso."
                ),
            },
            {
                "role": "user",
                "content": criar_prompt(texto),
            },
        ],
    )

    conteudo = (
        resposta["message"]["content"]
        .strip()
    )

    candidato = json.loads(
        conteudo
    )

    return normalizar(candidato)


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_conceito(valor):
    if not isinstance(valor, str):
        return valor

    valor = valor.strip()

    for artigo in (
        "um ",
        "uma ",
        "o ",
        "a ",
        "os ",
        "as ",
    ):
        if valor.lower().startswith(artigo):
            valor = valor[len(artigo):]
            break

    return valor.strip()


def normalizar_relacao(valor):
    if not isinstance(valor, str):
        return valor

    return (
        valor
        .strip()
        .replace(" ", "_")
    )


def normalizar(candidato):
    if not isinstance(candidato, dict):
        return candidato

    resultado = dict(candidato)

    if "sujeito" in resultado:
        resultado["sujeito"] = (
            normalizar_conceito(
                resultado["sujeito"]
            )
        )

    if "relacao" in resultado:
        resultado["relacao"] = (
            normalizar_relacao(
                resultado["relacao"]
            )
        )

    if "objeto" in resultado:
        resultado["objeto"] = (
            normalizar_conceito(
                resultado["objeto"]
            )
        )

    return resultado


# ============================================================
# VALIDAÇÃO ESTRUTURAL
# ============================================================

def validar_estrutura(candidato):
    if not isinstance(
        candidato,
        dict,
    ):
        return False

    if set(candidato.keys()) != {
        "sujeito",
        "relacao",
        "objeto",
    }:
        return False

    if candidato["sujeito"] not in CONCEITOS:
        return False

    if candidato["objeto"] not in CONCEITOS:
        return False

    if candidato["relacao"] not in ASSINATURAS:
        return False

    return True


# ============================================================
# GATE RELACIONAL
# ============================================================

def validar_assinatura(candidato):
    if not validar_estrutura(candidato):
        return False, "estrutura inválida"

    relacao = candidato["relacao"]

    assinatura = ASSINATURAS[relacao]

    sujeito = candidato["sujeito"]
    objeto = candidato["objeto"]

    if sujeito not in assinatura["sujeitos"]:
        return (
            False,
            (
                f"sujeito '{sujeito}' não é permitido "
                f"na relação '{relacao}'"
            ),
        )

    if objeto not in assinatura["objetos"]:
        return (
            False,
            (
                f"objeto '{objeto}' não é permitido "
                f"na relação '{relacao}'"
            ),
        )

    return True, "assinatura válida"


# ============================================================
# BENCHMARK
# ============================================================

TESTES = [
    {
        "texto": "Uma observação pode gerar uma hipótese.",
        "esperado": {
            "sujeito": "observação",
            "relacao": "pode_gerar",
            "objeto": "hipótese",
        },
    },

    {
        "texto": "Um experimento pode testar uma hipótese.",
        "esperado": {
            "sujeito": "experimento",
            "relacao": "pode_testar",
            "objeto": "hipótese",
        },
    },

    {
        "texto": "Uma hipótese pode gerar uma previsão.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_gerar",
            "objeto": "previsão",
        },
    },

    {
        "texto": "Uma hipótese pode receber uma evidência.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_receber",
            "objeto": "evidência",
        },
    },

    {
        "texto": "Uma evidência pode modificar uma hipótese.",
        "esperado": {
            "sujeito": "evidência",
            "relacao": "pode_modificar",
            "objeto": "hipótese",
        },
    },

    {
        "texto": "Uma hipótese pode estar correta.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "correta",
        },
    },

    {
        "texto": "Uma hipótese pode estar incorreta.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "incorreta",
        },
    },

    {
        "texto": "Uma hipótese continua sendo provisória.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "continua_sendo",
            "objeto": "provisória",
        },
    },

    {
        "texto": "Uma hipótese precisa lidar com incerteza.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "precisa_lidar_com",
            "objeto": "incerteza",
        },
    },

    {
        "texto": "Uma hipótese pode ser apoiada por um resultado.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_apoiada_por",
            "objeto": "resultado",
        },
    },

    {
        "texto": "Uma hipótese pode ser contradita por um resultado.",
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_contradita_por",
            "objeto": "resultado",
        },
    },
]


# ============================================================
# FIDELIDADE SEMÂNTICA
#
# Benchmark externo.
# ============================================================

def avaliar_benchmark(candidato, teste):
    return candidato == teste["esperado"]


# ============================================================
# EXECUTAR UM TESTE
# ============================================================

def executar_teste(numero, teste):
    print(
        f"=== TESTE {numero} ==="
    )

    print(
        f"Texto: {teste['texto']}"
    )

    candidatos = []

    for temperatura in TEMPERATURAS:
        try:
            candidato = interpretar(
                teste["texto"],
                temperatura,
            )
        except Exception as erro:
            print(
                f"Temperatura {temperatura:.1f}: ERRO"
            )
            print(
                f"Motivo: {erro}"
            )
            print()

            return {
                "consenso": False,
                "assinatura": False,
                "benchmark": False,
                "aceito": False,
            }

        candidatos.append(candidato)

        print(
            f"Temperatura {temperatura:.1f}:"
        )

        print(
            json.dumps(
                candidato,
                ensure_ascii=False,
                indent=2,
            )
        )

        print()

    # --------------------------------------------------------
    # CONSENSO
    # --------------------------------------------------------

    consenso = all(
        candidato == candidatos[0]
        for candidato in candidatos
    )

    print(
        "CONSENSO: "
        + (
            "SIM"
            if consenso
            else "NÃO"
        )
    )

    # --------------------------------------------------------
    # ASSINATURA
    # --------------------------------------------------------

    assinaturas = []

    for candidato in candidatos:
        valido, motivo = (
            validar_assinatura(
                candidato
            )
        )

        assinaturas.append(
            valido
        )

        print(
            f"Assinatura: "
            f"{'PASSOU' if valido else 'FALHOU'} "
            f"({motivo})"
        )

    todas_assinaturas_validas = all(
        assinaturas
    )

    # --------------------------------------------------------
    # BENCHMARK
    # --------------------------------------------------------

    benchmark = all(
        avaliar_benchmark(
            candidato,
            teste,
        )
        for candidato in candidatos
    )

    print(
        "BENCHMARK: "
        + (
            "PASSOU"
            if benchmark
            else "FALHOU"
        )
    )

    # --------------------------------------------------------
    # GATE
    #
    # Neste experimento:
    #
    # consenso + assinatura válida
    #
    # O benchmark NÃO participa da decisão.
    # Ele só mede depois se o gate acertou.
    # --------------------------------------------------------

    aceito = (
        consenso
        and todas_assinaturas_validas
    )

    print(
        "DECISÃO DO GATE: "
        + (
            "ACEITAR"
            if aceito
            else "ABSTER-SE"
        )
    )

    print()

    return {
        "consenso": consenso,
        "assinatura": todas_assinaturas_validas,
        "benchmark": benchmark,
        "aceito": aceito,
    }


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print(
        "=== MICROETAPA 47 ==="
    )

    print(
        "GATE RELACIONAL"
    )

    print()

    total = len(TESTES)

    consensos = 0
    assinaturas = 0
    benchmarks = 0
    aceitos = 0
    abstencoes = 0

    for numero, teste in enumerate(
        TESTES,
        start=1,
    ):
        resultado = executar_teste(
            numero,
            teste,
        )

        if resultado["consenso"]:
            consensos += 1

        if resultado["assinatura"]:
            assinaturas += 1

        if resultado["benchmark"]:
            benchmarks += 1

        if resultado["aceito"]:
            aceitos += 1
        else:
            abstencoes += 1

    def percentual(valor):
        return (
            valor / total
        ) * 100

    print(
        "=== RESULTADO FINAL ==="
    )

    print(
        f"Testes: {total}"
    )

    print(
        f"Consenso: "
        f"{consensos}/{total} "
        f"({percentual(consensos):.2f}%)"
    )

    print(
        f"Assinaturas válidas: "
        f"{assinaturas}/{total} "
        f"({percentual(assinaturas):.2f}%)"
    )

    print(
        f"Benchmark correto: "
        f"{benchmarks}/{total} "
        f"({percentual(benchmarks):.2f}%)"
    )

    print(
        f"Aceitos pelo gate: "
        f"{aceitos}/{total} "
        f"({percentual(aceitos):.2f}%)"
    )

    print(
        f"Abstenções: "
        f"{abstencoes}/{total} "
        f"({percentual(abstencoes):.2f}%)"
    )


if __name__ == "__main__":
    main()
