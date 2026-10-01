# ============================================================
# ASSINATURAS CANÔNICAS
# ============================================================

ASSINATURAS = {
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

    # --------------------------------------------------------
    # CORREÇÃO IMPORTANTE
    #
    # O cristal já contém:
    #
    # experimento -> pode_testar -> hipótese
    #
    # Portanto essa é a orientação canônica.
    # --------------------------------------------------------

    "pode_testar": {
        "sujeitos": {
            "experimento",
        },
        "objetos": {
            "hipótese",
        },
    },

    "pode_gerar": {
        "sujeitos": {
            "hipótese",
        },
        "objetos": {
            "previsão",
        },
    },

    "apoia": {
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

    "revisa": {
        "sujeitos": {
            "evidência",
            "resultado",
            "investigação",
        },
        "objetos": {
            "hipótese",
            "conclusão",
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
}


# ============================================================
# RELAÇÕES INVERSAS
# ============================================================

RELACOES_INVERSAS = {
    "pode_ser_modificada_por": "pode_modificar",
    "pode_ser_testada_por": "pode_testar",
    "pode_ser_apoiada_por": "apoia",
    "pode_ser_contradita_por": "contradiz",
    "pode_ser_revisada_por": "revisa",
}


# ============================================================
# VARIANTES SEMÂNTICAS
# ============================================================

RELACOES_VARIANTES = {
    "pode_ser_modificar": "pode_modificar",
}


# ============================================================
# RELAÇÕES ESPECIALIZADAS
# ============================================================

RELACOES_ESPECIALIZADAS = {
    "pode_gerar_previsao": "pode_gerar",
}


# ============================================================
# VALIDAÇÃO DE ASSINATURA
# ============================================================

def assinatura_valida(
    sujeito,
    relacao,
    objeto,
):
    assinatura = ASSINATURAS.get(
        relacao
    )

    if assinatura is None:
        return False

    return (
        sujeito in assinatura["sujeitos"]
        and objeto in assinatura["objetos"]
    )


# ============================================================
# NORMALIZAÇÃO SEMÂNTICA
# ============================================================

def normalizar_trinca(
    sujeito,
    relacao,
    objeto,
):
    original = [
        sujeito,
        relacao,
        objeto,
    ]

    # --------------------------------------------------------
    # 1. INVERSÃO
    # --------------------------------------------------------

    if relacao in RELACOES_INVERSAS:
        relacao_canonica = (
            RELACOES_INVERSAS[
                relacao
            ]
        )

        novo_sujeito = objeto
        novo_objeto = sujeito

        if assinatura_valida(
            novo_sujeito,
            relacao_canonica,
            novo_objeto,
        ):
            return {
                "status": "NORMALIZADO",
                "tipo": "INVERSAO",
                "original": original,
                "resultado": [
                    novo_sujeito,
                    relacao_canonica,
                    novo_objeto,
                ],
            }

        return {
            "status": "REJEITAR",
            "motivo": (
                "A inversão produziria "
                "uma assinatura inválida."
            ),
            "original": original,
        }

    # --------------------------------------------------------
    # 2. VARIANTE SEMÂNTICA
    # --------------------------------------------------------

    if relacao in RELACOES_VARIANTES:
        relacao_canonica = (
            RELACOES_VARIANTES[
                relacao
            ]
        )

        if assinatura_valida(
            sujeito,
            relacao_canonica,
            objeto,
        ):
            return {
                "status": "NORMALIZADO",
                "tipo": "VARIANTE_SEMANTICA",
                "original": original,
                "resultado": [
                    sujeito,
                    relacao_canonica,
                    objeto,
                ],
            }

        return {
            "status": "REJEITAR",
            "motivo": (
                "A variante produziria "
                "uma assinatura inválida."
            ),
            "original": original,
        }

    # --------------------------------------------------------
    # 3. ESPECIALIZAÇÃO
    # --------------------------------------------------------

    if relacao in RELACOES_ESPECIALIZADAS:
        relacao_canonica = (
            RELACOES_ESPECIALIZADAS[
                relacao
            ]
        )

        if assinatura_valida(
            sujeito,
            relacao_canonica,
            objeto,
        ):
            return {
                "status": "NORMALIZADO",
                "tipo": "ESPECIALIZACAO",
                "original": original,
                "resultado": [
                    sujeito,
                    relacao_canonica,
                    objeto,
                ],
            }

        return {
            "status": "REJEITAR",
            "motivo": (
                "A especialização produziria "
                "uma assinatura inválida."
            ),
            "original": original,
        }

    # --------------------------------------------------------
    # 4. RELAÇÃO CANÔNICA
    # --------------------------------------------------------

    if relacao in ASSINATURAS:
        if assinatura_valida(
            sujeito,
            relacao,
            objeto,
        ):
            return {
                "status": "CANONICO",
                "original": original,
                "resultado": original.copy(),
            }

        return {
            "status": "REJEITAR",
            "motivo": (
                "A assinatura da relação "
                "é inválida."
            ),
            "original": original,
        }

    # --------------------------------------------------------
    # 5. RELAÇÃO DESCONHECIDA
    # --------------------------------------------------------

    return {
        "status": "REJEITAR",
        "motivo": "Relação desconhecida.",
        "original": original,
    }


# ============================================================
# TESTES
# ============================================================

TESTES = [
    {
        "nome": "CANÔNICO",
        "entrada": {
            "sujeito": "evidência",
            "relacao": "pode_modificar",
            "objeto": "hipótese",
        },
        "esperado": "CANONICO",
    },

    {
        "nome": "INVERSÃO",
        "entrada": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_modificada_por",
            "objeto": "evidência",
        },
        "esperado": "NORMALIZADO",
        "resultado_esperado": [
            "evidência",
            "pode_modificar",
            "hipótese",
        ],
    },

    {
        "nome": "ESPECIALIZAÇÃO",
        "entrada": {
            "sujeito": "hipótese",
            "relacao": "pode_gerar_previsao",
            "objeto": "previsão",
        },
        "esperado": "NORMALIZADO",
        "resultado_esperado": [
            "hipótese",
            "pode_gerar",
            "previsão",
        ],
    },

    # --------------------------------------------------------
    # CORRIGIDO
    #
    # "Uma hipótese pode ser testada por um experimento."
    #
    # forma invertida:
    #
    # hipótese -> pode_ser_testada_por -> experimento
    #
    # forma canônica:
    #
    # experimento -> pode_testar -> hipótese
    # --------------------------------------------------------

    {
        "nome": "TESTE INVERSO",
        "entrada": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_testada_por",
            "objeto": "experimento",
        },
        "esperado": "NORMALIZADO",
        "resultado_esperado": [
            "experimento",
            "pode_testar",
            "hipótese",
        ],
    },

    {
        "nome": "VARIANTE SEMÂNTICA",
        "entrada": {
            "sujeito": "evidência",
            "relacao": "pode_ser_modificar",
            "objeto": "hipótese",
        },
        "esperado": "NORMALIZADO",
        "resultado_esperado": [
            "evidência",
            "pode_modificar",
            "hipótese",
        ],
    },

    {
        "nome": "INVERSÃO INVÁLIDA",
        "entrada": {
            "sujeito": "hipótese",
            "relacao": "pode_ser_modificada_por",
            "objeto": "incorreta",
        },
        "esperado": "REJEITAR",
    },

    {
        "nome": "RELAÇÃO DESCONHECIDA",
        "entrada": {
            "sujeito": "hipótese",
            "relacao": "pode_ser",
            "objeto": "correta",
        },
        "esperado": "REJEITAR",
    },
]


# ============================================================
# EXECUÇÃO
# ============================================================

def executar_testes():
    passaram = 0

    print()
    print("NORMALIZAÇÃO SEMÂNTICA")
    print()

    for indice, teste in enumerate(
        TESTES,
        start=1,
    ):
        print(
            f"=== TESTE {indice} ==="
        )

        print(
            f"Nome: {teste['nome']}"
        )

        entrada = teste["entrada"]

        print("Entrada:")
        print("{")
        print(
            f'  "sujeito": '
            f'"{entrada["sujeito"]}",'
        )
        print(
            f'  "relacao": '
            f'"{entrada["relacao"]}",'
        )
        print(
            f'  "objeto": '
            f'"{entrada["objeto"]}"'
        )
        print("}")

        resultado = normalizar_trinca(
            entrada["sujeito"],
            entrada["relacao"],
            entrada["objeto"],
        )

        print()
        print("Resultado:")
        print(resultado)

        passou = (
            resultado["status"]
            == teste["esperado"]
        )

        if "resultado_esperado" in teste:
            passou = (
                passou
                and resultado.get(
                    "resultado"
                )
                == teste[
                    "resultado_esperado"
                ]
            )

        print()

        if passou:
            print("TESTE: PASSOU")
            passaram += 1
        else:
            print("TESTE: FALHOU")

        print()

    total = len(TESTES)

    fidelidade = (
        passaram / total
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
        f"Falharam: {total - passaram}"
    )

    print(
        f"Fidelidade do normalizador: "
        f"{fidelidade:.2f}%"
    )

    if passaram == total:
        print(
            "TODAS AS REGRAS PASSARAM."
        )
    else:
        print(
            "ATENÇÃO: alguma regra "
            "ainda precisa ser revisada."
        )


if __name__ == "__main__":
    executar_testes()
