import json


# ============================================================
# MICROETAPA 50
# GATE DA REPRESENTAÇÃO SEMÂNTICA RICA
#
# Objetivo:
#
# validar uma representação com:
#
# 1. sujeito
# 2. relação-base
# 3. objeto
# 4. modalidade
#
# O gate é determinístico.
#
# O benchmark mede o comportamento,
# mas NÃO participa da decisão do gate.
#
# Esta etapa é isolada.
#
# NÃO altera:
# - cristal V1
# - gerenciador_cristal.py
# - pipeline_integrado.py
# - gate relacional
# - representação rica V4
# ============================================================


# ============================================================
# CONJUNTOS SEMÂNTICOS
# ============================================================

CONCEITOS = {
    "hipótese",
    "correta",
    "incorreta",
    "incerteza",
    "resultado",
    "experimento",
    "evidência",
    "observação",
}


RELACOES_BASE = {
    "estar",
}


ESTADOS_PARA_ESTAR = {
    "correta",
    "incorreta",
}


MODALIDADES = {
    "possibilidade",
    "necessidade",
    "não_necessidade",
    "negação",
}


# ============================================================
# VALIDAÇÃO ESTRUTURAL
# ============================================================

def validar_estrutura(representacao):
    if not isinstance(
        representacao,
        dict,
    ):
        return (
            False,
            "representação não é um objeto JSON/dict",
        )

    chaves_esperadas = {
        "sujeito",
        "relacao",
        "objeto",
        "modalidade",
    }

    if set(representacao.keys()) != chaves_esperadas:
        return (
            False,
            "estrutura de chaves inválida",
        )

    for chave in chaves_esperadas:
        valor = representacao[chave]

        if not isinstance(
            valor,
            str,
        ):
            return (
                False,
                f"campo '{chave}' não é texto",
            )

        if not valor.strip():
            return (
                False,
                f"campo '{chave}' está vazio",
            )

    return True, "estrutura válida"


# ============================================================
# VALIDAÇÃO DE CONCEITOS
# ============================================================

def validar_conceitos(representacao):
    sujeito = representacao["sujeito"]
    objeto = representacao["objeto"]

    if sujeito not in CONCEITOS:
        return (
            False,
            f"sujeito '{sujeito}' não é permitido",
        )

    if objeto not in CONCEITOS:
        return (
            False,
            f"objeto '{objeto}' não é permitido",
        )

    return True, "conceitos válidos"


# ============================================================
# VALIDAÇÃO DA RELAÇÃO-BASE
# ============================================================

def validar_relacao(representacao):
    relacao = representacao["relacao"]

    if relacao not in RELACOES_BASE:
        return (
            False,
            f"relação-base '{relacao}' não é permitida",
        )

    return True, "relação-base válida"


# ============================================================
# VALIDAÇÃO DA MODALIDADE
# ============================================================

def validar_modalidade(representacao):
    modalidade = representacao["modalidade"]

    if modalidade not in MODALIDADES:
        return (
            False,
            f"modalidade '{modalidade}' não é permitida",
        )

    return True, "modalidade válida"


# ============================================================
# COMPATIBILIDADE SEMÂNTICA
# ============================================================

def validar_compatibilidade(representacao):
    sujeito = representacao["sujeito"]
    relacao = representacao["relacao"]
    objeto = representacao["objeto"]

    # --------------------------------------------------------
    # REGRA 1
    #
    # "estar" no experimento atual é uma relação de estado
    # aplicada a uma hipótese.
    # --------------------------------------------------------

    if relacao == "estar":

        if sujeito != "hipótese":
            return (
                False,
                (
                    "a relação 'estar' neste estágio "
                    "aceita apenas 'hipótese' como sujeito"
                ),
            )

        if objeto not in ESTADOS_PARA_ESTAR:
            return (
                False,
                (
                    "a relação 'estar' exige um estado "
                    "'correta' ou 'incorreta'"
                ),
            )

    return True, "compatibilidade semântica válida"


# ============================================================
# GATE COMPLETO
# ============================================================

def validar_representacao(representacao):
    valido, motivo = validar_estrutura(
        representacao
    )

    if not valido:
        return False, motivo

    valido, motivo = validar_conceitos(
        representacao
    )

    if not valido:
        return False, motivo

    valido, motivo = validar_relacao(
        representacao
    )

    if not valido:
        return False, motivo

    valido, motivo = validar_modalidade(
        representacao
    )

    if not valido:
        return False, motivo

    valido, motivo = validar_compatibilidade(
        representacao
    )

    if not valido:
        return False, motivo

    return True, "representação rica aceita"


# ============================================================
# BENCHMARK
# ============================================================

TESTES = [

    # --------------------------------------------------------
    # REPRESENTAÇÕES VÁLIDAS
    # --------------------------------------------------------

    {
        "nome": "possibilidade + correta",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
            "modalidade": "possibilidade",
        },
        "esperado_gate": True,
    },

    {
        "nome": "não_necessidade + correta",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
            "modalidade": "não_necessidade",
        },
        "esperado_gate": True,
    },

    {
        "nome": "possibilidade + incorreta",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "incorreta",
            "modalidade": "possibilidade",
        },
        "esperado_gate": True,
    },

    {
        "nome": "necessidade + correta",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
            "modalidade": "necessidade",
        },
        "esperado_gate": True,
    },

    {
        "nome": "negação + correta",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
            "modalidade": "negação",
        },
        "esperado_gate": True,
    },

    # --------------------------------------------------------
    # REPRESENTAÇÕES INVÁLIDAS
    # --------------------------------------------------------

    {
        "nome": "estar + objeto incompatível",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "incerteza",
            "modalidade": "possibilidade",
        },
        "esperado_gate": False,
    },

    {
        "nome": "modalidade desconhecida",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
            "modalidade": "talvez",
        },
        "esperado_gate": False,
    },

    {
        "nome": "sujeito incompatível",
        "representacao": {
            "sujeito": "resultado",
            "relacao": "estar",
            "objeto": "correta",
            "modalidade": "possibilidade",
        },
        "esperado_gate": False,
    },

    {
        "nome": "relação desconhecida",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "ser",
            "objeto": "correta",
            "modalidade": "possibilidade",
        },
        "esperado_gate": False,
    },

    {
        "nome": "estrutura incompleta",
        "representacao": {
            "sujeito": "hipótese",
            "relacao": "estar",
            "objeto": "correta",
        },
        "esperado_gate": False,
    },
]


# ============================================================
# EXECUTAR TESTE
# ============================================================

def executar_teste(numero, teste):

    print(
        "=" * 70
    )

    print(
        f"TESTE {numero}"
    )

    print(
        f"Nome: {teste['nome']}"
    )

    print()

    print(
        "REPRESENTAÇÃO:"
    )

    print(
        json.dumps(
            teste["representacao"],
            ensure_ascii=False,
            indent=2,
        )
    )

    print()

    aceito, motivo = validar_representacao(
        teste["representacao"]
    )

    esperado = teste["esperado_gate"]

    correto = (
        aceito == esperado
    )

    print(
        "GATE: "
        + (
            "ACEITAR"
            if aceito
            else "REJEITAR"
        )
    )

    print(
        f"MOTIVO: {motivo}"
    )

    print(
        "ESPERADO: "
        + (
            "ACEITAR"
            if esperado
            else "REJEITAR"
        )
    )

    print(
        "RESULTADO: "
        + (
            "PASSOU"
            if correto
            else "FALHOU"
        )
    )

    print()

    return correto


# ============================================================
# PRINCIPAL
# ============================================================

def main():

    print(
        "=== MICROETAPA 50 ==="
    )

    print(
        "GATE DA REPRESENTAÇÃO SEMÂNTICA RICA"
    )

    print()

    total = len(
        TESTES
    )

    corretos = 0

    aceitos_validos = 0
    rejeitados_invalidos = 0

    validos_totais = 0
    invalidos_totais = 0

    for numero, teste in enumerate(
        TESTES,
        start=1,
    ):

        passou = executar_teste(
            numero,
            teste,
        )

        if passou:
            corretos += 1

        esperado = teste[
            "esperado_gate"
        ]

        if esperado:
            validos_totais += 1

            if passou:
                aceitos_validos += 1

        else:
            invalidos_totais += 1

            if passou:
                rejeitados_invalidos += 1

    print(
        "=" * 70
    )

    print(
        "RESULTADO FINAL"
    )

    print()

    print(
        f"Testes: {total}"
    )

    print(
        f"Gate correto: "
        f"{corretos}/{total} "
        f"({corretos / total * 100:.2f}%)"
    )

    print(
        f"Representações válidas aceitas: "
        f"{aceitos_validos}/{validos_totais}"
    )

    print(
        f"Representações inválidas rejeitadas: "
        f"{rejeitados_invalidos}/{invalidos_totais}"
    )

    print()

    if (
        corretos == total
        and
        aceitos_validos == validos_totais
        and
        rejeitados_invalidos == invalidos_totais
    ):
        print(
            "STATUS: MICROETAPA 50 PASSOU"
        )
    else:
        print(
            "STATUS: MICROETAPA 50 AINDA NÃO PASSOU"
        )


if __name__ == "__main__":
    main()
