import json

import ollama


# ============================================================
# MICROETAPA 44
# FIDELIDADE DO QWEN V2
#
# Diferença principal:
#
# Cada relação agora possui uma definição explícita
# e exemplos direcionais.
#
# O objetivo é testar se isso reduz:
#
# - inversão de sujeito/objeto
# - confusão entre relações próximas
# - criação de relações fora do vocabulário
#
# O Qwen continua NÃO sendo o juiz.
# A comparação final continua sendo determinística.
# ============================================================


MODELO = "qwen2:7b"


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
# RELAÇÕES COM DEFINIÇÕES
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
            "O sujeito é algo que pode ser testado "
            "pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_testada_por--> "
            "experimento"
        ),
    },

    "pode_receber": {
        "definicao": (
            "O sujeito pode receber ou incorporar "
            "o objeto."
        ),
        "exemplo": (
            "hipótese --pode_receber--> evidência"
        ),
    },

    "pode_ser_modificada_por": {
        "definicao": (
            "O sujeito é alterado ou modificado "
            "pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_modificada_por--> "
            "evidência"
        ),
    },

    "pode_estar": {
        "definicao": (
            "O sujeito pode estar no estado ou "
            "condição indicada pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_estar--> correta"
        ),
    },

    "pode_gerar": {
        "definicao": (
            "O sujeito pode produzir, originar "
            "ou gerar o objeto."
        ),
        "exemplo": (
            "observação --pode_gerar--> hipótese"
        ),
    },

    "pode_testar": {
        "definicao": (
            "O sujeito realiza um teste sobre "
            "o objeto."
        ),
        "exemplo": (
            "experimento --pode_testar--> hipótese"
        ),
    },

    "pode_modificar": {
        "definicao": (
            "O sujeito realiza uma modificação "
            "sobre o objeto."
        ),
        "exemplo": (
            "evidência --pode_modificar--> hipótese"
        ),
    },

    "continua_sendo": {
        "definicao": (
            "O sujeito permanece sendo ou mantendo "
            "a condição indicada pelo objeto."
        ),
        "exemplo": (
            "hipótese --continua_sendo--> provisória"
        ),
    },

    "precisa_lidar_com": {
        "definicao": (
            "O sujeito precisa considerar, enfrentar "
            "ou lidar com o objeto."
        ),
        "exemplo": (
            "hipótese --precisa_lidar_com--> "
            "incerteza"
        ),
    },

    "tem_caracteristica": {
        "definicao": (
            "O sujeito possui a característica "
            "indicada pelo objeto."
        ),
        "exemplo": (
            "hipótese --tem_caracteristica--> "
            "incerteza"
        ),
    },

    "pode_ser_apoiada_por": {
        "definicao": (
            "O sujeito recebe suporte do objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_apoiada_por--> "
            "resultado"
        ),
    },

    "pode_ser_contradita_por": {
        "definicao": (
            "O sujeito pode ser contradito "
            "pelo objeto."
        ),
        "exemplo": (
            "hipótese --pode_ser_contradita_por--> "
            "resultado"
        ),
    },

    "pode_orientar": {
        "definicao": (
            "O sujeito pode orientar ou direcionar "
            "o objeto."
        ),
        "exemplo": (
            "pergunta --pode_orientar--> "
            "investigação"
        ),
    },

    "pode_ser_revisada_por": {
        "definicao": (
            "O sujeito pode ser revisado ou "
            "reavaliado pelo objeto."
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
            "O sujeito pode diminuir o objeto."
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
            "O sujeito pode produzir uma previsão."
        ),
        "exemplo": (
            "hipótese --pode_gerar_previsao--> "
            "previsão"
        ),
    },

    "pode_conter_erro": {
        "definicao": (
            "O sujeito pode conter o objeto "
            "como um erro."
        ),
        "exemplo": (
            "hipótese --pode_conter_erro--> erro"
        ),
    },
}


# ============================================================
# TESTES
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
        "texto": (
            "Uma hipótese pode ser apoiada "
            "por um resultado."
        ),
        "esperado": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_apoiada_por",
            "objeto": "resultado",
        },
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
    },
]


# ============================================================
# CONSTRUIR PROMPT
# ============================================================

def criar_prompt(texto):
    conceitos = ", ".join(CONCEITOS)

    partes_relacoes = []

    for nome, dados in RELACOES.items():
        partes_relacoes.append(
            f"- {nome}: "
            f"{dados['definicao']} "
            f"Exemplo: {dados['exemplo']}"
        )

    relacoes_texto = "\n".join(
        partes_relacoes
    )

    return f"""
Transforme a frase em exatamente uma tripla
estrutural.

Responda somente com JSON válido:

{{
  "sujeito": "...",
  "relacao": "...",
  "objeto": "..."
}}

CONCEITOS PERMITIDOS:

{conceitos}

RELAÇÕES PERMITIDAS:

{relacoes_texto}

REGRAS:

1. Use somente conceitos da lista.
2. Use somente relações da lista.
3. Não invente relações.
4. Não use artigos nos conceitos.
5. Preserve a direção da relação.
6. O sujeito deve ser quem realiza, possui,
   recebe ou sofre a ação descrita conforme
   a definição da relação.
7. O objeto deve ser o elemento relacionado
   ao sujeito.
8. Não troque sujeito e objeto.
9. Escolha a relação pela DEFINIÇÃO, não apenas
   por semelhança das palavras.
10. Responda apenas o JSON.

FRASE:

{texto}
""".strip()


# ============================================================
# QWEN
# ============================================================

def interpretar(texto):
    resposta = ollama.chat(
        model=MODELO,
        format="json",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um interpretador estrutural "
                    "e deve respeitar rigorosamente "
                    "as definições das relações."
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

    return json.loads(
        conteudo
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
    candidato
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
# VALIDAÇÃO
# ============================================================

def validar(candidato):
    esperado = {
        "sujeito",
        "relacao",
        "objeto",
    }

    if set(candidato.keys()) != esperado:
        return False

    if candidato["sujeito"] not in CONCEITOS:
        return False

    if candidato["objeto"] not in CONCEITOS:
        return False

    if candidato["relacao"] not in RELACOES:
        return False

    return True


# ============================================================
# TESTE
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

    try:
        bruto = interpretar(
            teste["texto"]
        )

        normalizado = (
            normalizar_candidato(
                bruto
            )
        )

    except Exception as erro:
        print(
            "RESULTADO: FALHOU"
        )

        print(
            f"Erro: {erro}"
        )

        print()

        return False

    print(
        "Candidato:"
    )

    print(
        json.dumps(
            normalizado,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()

    if not validar(
        normalizado
    ):
        print(
            "RESULTADO: FALHOU"
        )

        print(
            "Motivo: estrutura inválida."
        )

        print()

        return False

    passou = (
        normalizado
        == teste["esperado"]
    )

    if passou:
        print(
            "RESULTADO: PASSOU"
        )

    else:
        print(
            "RESULTADO: FALHOU"
        )

        print()
        print("Esperado:")

        print(
            json.dumps(
                teste["esperado"],
                ensure_ascii=False,
                indent=2,
            )
        )

    print()

    return passou


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print(
        "=== MICROETAPA 44 ==="
    )

    print(
        "RELAÇÕES COM SEMÂNTICA EXPLÍCITA"
    )

    print()

    total = len(TESTES)
    passaram = 0

    for numero, teste in enumerate(
        TESTES,
        start=1,
    ):
        if executar_teste(
            numero,
            teste,
        ):
            passaram += 1

    falharam = (
        total
        - passaram
    )

    fidelidade = (
        passaram
        / total
    ) * 100

    print(
        "=== RESULTADO FINAL ==="
    )

    print(
        f"Testes: {total}"
    )

    print(
        f"Passaram: {passaram}"
    )

    print(
        f"Falharam: {falharam}"
    )

    print(
        f"Fidelidade estrutural: "
        f"{fidelidade:.2f}%"
    )

    if falharam == 0:
        print(
            "PASSOU: todas as estruturas "
            "coincidiram exatamente."
        )
    else:
        print(
            "ATENÇÃO: ainda existem "
            "erros semânticos."
        )


if __name__ == "__main__":
    main()
