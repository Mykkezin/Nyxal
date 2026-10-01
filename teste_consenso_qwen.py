import json

import ollama


# ============================================================
# MICROETAPA 46
# CONSENSO + ABSTINÊNCIA
#
# Objetivo:
#
# 1. Fazer múltiplas interpretações da mesma frase.
# 2. Verificar se existe consenso entre elas.
# 3. Medir fidelidade semântica contra um benchmark externo.
# 4. Medir fidelidade canônica.
# 5. Se não houver consenso ou se o consenso estiver errado,
#    o sistema se ABSTÉM.
#
# IMPORTANTE:
#
# Consenso NÃO significa verdade.
# Ele mede somente estabilidade entre interpretações.
#
# O benchmark externo continua sendo o juiz do experimento.
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

CONCEITOS = [
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
]


# ============================================================
# RELAÇÕES
# ============================================================

RELACOES = {
    "nasce_de": {
        "definicao": (
            "O sujeito surge ou se origina do objeto."
        ),
        "exemplo": (
            "hipótese --nasce_de--> observação"
        ),
    },

    "pode_ser_testada_por": {
        "definicao": (
            "O sujeito pode ser testado pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_testada_por--> "
            "experimento"
        ),
    },

    "pode_receber": {
        "definicao": (
            "O sujeito pode receber o objeto."
        ),
        "exemplo": (
            "hipótese --pode_receber--> evidência"
        ),
    },

    "pode_ser_modificada_por": {
        "definicao": (
            "O sujeito pode ser modificado pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_modificada_por--> "
            "evidência"
        ),
    },

    "pode_estar": {
        "definicao": (
            "O sujeito pode estar no estado indicado "
            "pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_estar--> correta"
        ),
    },

    "pode_gerar": {
        "definicao": (
            "O sujeito pode gerar ou produzir o objeto."
        ),
        "exemplo": (
            "observação --pode_gerar--> hipótese"
        ),
    },

    "pode_testar": {
        "definicao": (
            "O sujeito pode testar o objeto."
        ),
        "exemplo": (
            "experimento --pode_testar--> hipótese"
        ),
    },

    "pode_modificar": {
        "definicao": (
            "O sujeito pode modificar o objeto."
        ),
        "exemplo": (
            "evidência --pode_modificar--> hipótese"
        ),
    },

    "continua_sendo": {
        "definicao": (
            "O sujeito continua apresentando "
            "a condição indicada pelo objeto."
        ),
        "exemplo": (
            "hipótese --continua_sendo--> provisória"
        ),
    },

    "precisa_lidar_com": {
        "definicao": (
            "O sujeito precisa lidar com o objeto."
        ),
        "exemplo": (
            "hipótese --precisa_lidar_com--> "
            "incerteza"
        ),
    },

    "tem_caracteristica": {
        "definicao": (
            "O sujeito possui a característica indicada "
            "pelo objeto."
        ),
        "exemplo": (
            "hipótese --tem_caracteristica--> "
            "incerteza"
        ),
    },

    "pode_ser_apoiada_por": {
        "definicao": (
            "O sujeito pode receber suporte do objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_apoiada_por--> "
            "resultado"
        ),
    },

    "pode_ser_contradita_por": {
        "definicao": (
            "O sujeito pode ser contradito pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_contradita_por--> "
            "resultado"
        ),
    },

    "pode_orientar": {
        "definicao": (
            "O sujeito pode orientar o objeto."
        ),
        "exemplo": (
            "pergunta --pode_orientar--> investigação"
        ),
    },

    "pode_ser_revisada_por": {
        "definicao": (
            "O sujeito pode ser revisado pelo objeto."
        ),
        "exemplo": (
            "conclusão --pode_ser_revisada_por--> "
            "evidência"
        ),
    },

    "pode_conter": {
        "definicao": (
            "O sujeito pode conter o objeto."
        ),
        "exemplo": (
            "teoria --pode_conter--> hipótese"
        ),
    },

    "pode_reduzir": {
        "definicao": (
            "O sujeito pode reduzir o objeto."
        ),
        "exemplo": (
            "investigação --pode_reduzir--> "
            "incerteza"
        ),
    },

    "pode_explicar": {
        "definicao": (
            "O sujeito pode explicar o objeto."
        ),
        "exemplo": (
            "hipótese --pode_explicar--> "
            "explicação"
        ),
    },

    "pode_gerar_previsao": {
        "definicao": (
            "O sujeito pode gerar uma previsão."
        ),
        "exemplo": (
            "hipótese --pode_gerar_previsao--> "
            "previsão"
        ),
    },

    "pode_conter_erro": {
        "definicao": (
            "O sujeito pode conter um erro."
        ),
        "exemplo": (
            "hipótese --pode_conter_erro--> erro"
        ),
    },
}


# ============================================================
# BENCHMARK
#
# "relacoes_semanticamente_aceitas" permite distinguir:
#
# CANÔNICO:
# uma única forma preferencial.
#
# SEMANTICAMENTE ACEITO:
# mais de uma representação pode preservar o sentido.
# ============================================================

TESTES = [
    {
        "texto": "Uma observação pode gerar uma hipótese.",

        "esperado": {
            "sujeito": "observação",
            "relacao": "pode_gerar",
            "objeto": "hipótese",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_gerar",
        ],
    },

    {
        "texto": "Um experimento pode testar uma hipótese.",

        "esperado": {
            "sujeito": "experimento",
            "relacao": "pode_testar",
            "objeto": "hipótese",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_testar",
        ],
    },

    {
        "texto": "Uma hipótese pode gerar uma previsão.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_gerar",
            "objeto": "previsão",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_gerar",
            "pode_gerar_previsao",
        ],
    },

    {
        "texto": "Uma hipótese pode receber uma evidência.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_receber",
            "objeto": "evidência",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_receber",
        ],
    },

    {
        "texto": "Uma evidência pode modificar uma hipótese.",

        "esperado": {
            "sujeito": "evidência",
            "relacao": "pode_modificar",
            "objeto": "hipótese",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_modificar",
        ],
    },

    {
        "texto": "Uma hipótese pode estar correta.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "correta",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_estar",
        ],
    },

    {
        "texto": "Uma hipótese pode estar incorreta.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_estar",
            "objeto": "incorreta",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_estar",
        ],
    },

    {
        "texto": "Uma hipótese continua sendo provisória.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "continua_sendo",
            "objeto": "provisória",
        },

        "relacoes_semanticamente_aceitas": [
            "continua_sendo",
        ],
    },

    {
        "texto": "Uma hipótese precisa lidar com incerteza.",

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "precisa_lidar_com",
            "objeto": "incerteza",
        },

        "relacoes_semanticamente_aceitas": [
            "precisa_lidar_com",
        ],
    },

    {
        "texto": (
            "Uma hipótese pode ser apoiada "
            "por um resultado."
        ),

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_apoiada_por",
            "objeto": "resultado",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_ser_apoiada_por",
        ],
    },

    {
        "texto": (
            "Uma hipótese pode ser contradita "
            "por um resultado."
        ),

        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_contradita_por",
            "objeto": "resultado",
        },

        "relacoes_semanticamente_aceitas": [
            "pode_ser_contradita_por",
        ],
    },
]


# ============================================================
# PROMPT
# ============================================================

def criar_prompt(texto):
    lista_conceitos = ", ".join(
        CONCEITOS
    )

    lista_relacoes = []

    for nome, dados in RELACOES.items():
        lista_relacoes.append(
            f"- {nome}: "
            f"{dados['definicao']} "
            f"Exemplo: {dados['exemplo']}"
        )

    relacoes_texto = "\n".join(
        lista_relacoes
    )

    return f"""
Transforme a frase abaixo em exatamente uma relação
estrutural.

Responda somente com JSON válido:

{{
  "sujeito": "...",
  "relacao": "...",
  "objeto": "..."
}}

CONCEITOS PERMITIDOS:

{lista_conceitos}

RELAÇÕES PERMITIDAS:

{relacoes_texto}

REGRAS:

1. Use somente conceitos da lista.
2. Use somente relações da lista.
3. Não invente relações.
4. Não use artigos nos conceitos.
5. Preserve a direção da relação.
6. O sujeito é o elemento que realiza, possui,
   recebe ou sofre a ação de acordo com a
   definição da relação.
7. O objeto é o elemento relacionado ao sujeito.
8. Não troque sujeito e objeto.
9. Escolha a relação pela definição semântica.
10. Responda somente o JSON.

FRASE:

{texto}
""".strip()


# ============================================================
# QWEN
# ============================================================

def interpretar(
    texto,
    temperatura,
):
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

    return normalizar_candidato(
        candidato
    )


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_conceito(valor):
    if not isinstance(
        valor,
        str,
    ):
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
        if valor.lower().startswith(
            artigo
        ):
            valor = valor[
                len(artigo):
            ]
            break

    return valor.strip()


def normalizar_relacao(valor):
    if not isinstance(
        valor,
        str,
    ):
        return valor

    return (
        valor
        .strip()
        .replace(
            " ",
            "_",
        )
    )


def normalizar_candidato(
    candidato,
):
    if not isinstance(
        candidato,
        dict,
    ):
        return candidato

    resultado = dict(
        candidato
    )

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

def validar_estrutura(
    candidato,
):
    if not isinstance(
        candidato,
        dict,
    ):
        return False

    chaves = {
        "sujeito",
        "relacao",
        "objeto",
    }

    if set(candidato.keys()) != chaves:
        return False

    if candidato["sujeito"] not in CONCEITOS:
        return False

    if candidato["objeto"] not in CONCEITOS:
        return False

    if candidato["relacao"] not in RELACOES:
        return False

    return True


# ============================================================
# AVALIAÇÃO SEMÂNTICA
# ============================================================

def avaliar_semantica(
    candidato,
    teste,
):
    if not validar_estrutura(
        candidato
    ):
        return False

    esperado = teste["esperado"]

    if (
        candidato["sujeito"]
        != esperado["sujeito"]
    ):
        return False

    if (
        candidato["objeto"]
        != esperado["objeto"]
    ):
        return False

    if (
        candidato["relacao"]
        not in teste[
            "relacoes_semanticamente_aceitas"
        ]
    ):
        return False

    return True


# ============================================================
# AVALIAÇÃO CANÔNICA
# ============================================================

def avaliar_canonica(
    candidato,
    teste,
):
    return (
        candidato
        == teste["esperado"]
    )


# ============================================================
# EXECUTAR TESTE
# ============================================================

def executar_teste(
    numero,
    teste,
):
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
                f"Temperatura "
                f"{temperatura:.1f}: ERRO"
            )

            print(
                f"Motivo: {erro}"
            )

            print()

            return {
                "consenso": False,
                "semantica": False,
                "canonica": False,
                "aceitar": False,
                "abstencao": True,
            }

        candidatos.append(
            candidato
        )

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
    # CORREÇÃO SEMÂNTICA
    # --------------------------------------------------------

    semanticamente_corretos = [
        avaliar_semantica(
            candidato,
            teste,
        )
        for candidato in candidatos
    ]

    todos_semanticamente_corretos = all(
        semanticamente_corretos
    )

    # --------------------------------------------------------
    # CORREÇÃO CANÔNICA
    # --------------------------------------------------------

    resultados_canonicos = [
        avaliar_canonica(
            candidato,
            teste,
        )
        for candidato in candidatos
    ]

    todos_canonicos = all(
        resultados_canonicos
    )

    # --------------------------------------------------------
    # GATE
    #
    # Aceitar somente quando:
    #
    # 1. existe consenso
    # 2. todos os candidatos consensuais são
    #    semanticamente corretos
    #
    # Caso contrário:
    #
    # ABSTENÇÃO
    # --------------------------------------------------------

    aceitar = (
        consenso
        and todos_semanticamente_corretos
    )

    abstencao = not aceitar

    print(
        "SEMÂNTICA DOS 3: "
        + (
            "PASSOU"
            if todos_semanticamente_corretos
            else "FALHOU"
        )
    )

    print(
        "CANÔNICA DOS 3: "
        + (
            "PASSOU"
            if todos_canonicos
            else "FALHOU"
        )
    )

    print(
        "DECISÃO DO GATE: "
        + (
            "ACEITAR"
            if aceitar
            else "ABSTER-SE"
        )
    )

    print()

    return {
        "consenso": consenso,
        "semantica": (
            todos_semanticamente_corretos
        ),
        "canonica": todos_canonicos,
        "aceitar": aceitar,
        "abstencao": abstencao,
    }


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print(
        "=== MICROETAPA 46 ==="
    )

    print(
        "CONSENSO + ABSTINÊNCIA"
    )

    print()

    total = len(TESTES)

    consensos = 0
    semanticos = 0
    canonicos = 0
    aceitos = 0
    abstincoes = 0

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

        if resultado["semantica"]:
            semanticos += 1

        if resultado["canonica"]:
            canonicos += 1

        if resultado["aceitar"]:
            aceitos += 1

        if resultado["abstencao"]:
            abstincoes += 1

    # --------------------------------------------------------
    # PERCENTUAIS
    # --------------------------------------------------------

    percentual_consenso = (
        consensos / total
    ) * 100

    percentual_semantica = (
        semanticos / total
    ) * 100

    percentual_canonica = (
        canonicos / total
    ) * 100

    percentual_aceitos = (
        aceitos / total
    ) * 100

    percentual_abstencao = (
        abstincoes / total
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
        f"({percentual_consenso:.2f}%)"
    )

    print(
        f"Consenso semanticamente correto: "
        f"{semanticos}/{total} "
        f"({percentual_semantica:.2f}%)"
    )

    print(
        f"Consenso canônico: "
        f"{canonicos}/{total} "
        f"({percentual_canonica:.2f}%)"
    )

    print(
        f"Aceitos pelo gate: "
        f"{aceitos}/{total} "
        f"({percentual_aceitos:.2f}%)"
    )

    print(
        f"Abstenções: "
        f"{abstincoes}/{total} "
        f"({percentual_abstencao:.2f}%)"
    )

    print()

    print(
        "=== INTERPRETAÇÃO ==="
    )

    print(
        "Consenso mede estabilidade "
        "entre as interpretações."
    )

    print(
        "Fidelidade mede correção "
        "contra o benchmark externo."
    )

    print(
        "Abstenção impede que uma "
        "interpretação instável ou "
        "incorreta seja aceita pelo gate."
    )


if __name__ == "__main__":
    main()
