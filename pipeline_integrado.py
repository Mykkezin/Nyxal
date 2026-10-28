import json

from experiencia_qwen import (
    normalizar_candidato,
)

from teste_consenso_qwen import (
    interpretar,
    TEMPERATURAS,
)

from teste_normalizacao_semantica import (
    normalizar_trinca,
)

from teste_gate_relacional import (
    validar_assinatura,
)

from gerenciador_cristal import (
    abrir_ou_criar_cristal,
    registrar_experiencia,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

GRAVAR_NO_CRISTAL = True


# ============================================================
# VALIDAÇÃO BÁSICA
# ============================================================

def validar_formato_basico(candidato):
    if not isinstance(candidato, dict):
        return False, "Candidato não é objeto JSON."

    chaves_esperadas = {
        "sujeito",
        "relacao",
        "objeto",
    }

    if set(candidato.keys()) != chaves_esperadas:
        return (
            False,
            "As chaves do candidato estão incorretas.",
        )

    if not isinstance(candidato["sujeito"], str):
        return False, "Sujeito não é texto."

    if not isinstance(candidato["relacao"], str):
        return False, "Relação não é texto."

    if not isinstance(candidato["objeto"], str):
        return False, "Objeto não é texto."

    return True, "Formato básico válido."


# ============================================================
# PREPARAR CANDIDATO
# ============================================================

def preparar_candidato(candidato):
    candidato_normalizado = normalizar_candidato(
        candidato
    )

    valido, motivo = validar_formato_basico(
        candidato_normalizado
    )

    if not valido:
        return {
            "status": "REJEITAR",
            "etapa": "FORMATO",
            "motivo": motivo,
            "candidato": candidato_normalizado,
        }

    sujeito = candidato_normalizado["sujeito"]
    relacao = candidato_normalizado["relacao"]
    objeto = candidato_normalizado["objeto"]

    resultado_semantico = normalizar_trinca(
        sujeito,
        relacao,
        objeto,
    )

    if resultado_semantico["status"] == "REJEITAR":
        return {
            "status": "REJEITAR",
            "etapa": "NORMALIZACAO_SEMANTICA",
            "motivo": resultado_semantico.get(
                "motivo",
                "Trinca rejeitada.",
            ),
            "original": [
                sujeito,
                relacao,
                objeto,
            ],
            "resultado_semantico": (
                resultado_semantico
            ),
        }

    trinca = resultado_semantico["resultado"]

    trinca_dict = {
        "sujeito": trinca[0],
        "relacao": trinca[1],
        "objeto": trinca[2],
    }

    return {
        "status": "PRONTO",
        "candidato_original": candidato,
        "candidato_normalizado": candidato_normalizado,
        "resultado_semantico": resultado_semantico,
        "candidato_canonico": trinca_dict,
    }


# ============================================================
# PROCESSAR UMA TEMPERATURA
# ============================================================

def processar_temperatura(texto, temperatura):
    candidato = interpretar(
        texto,
        temperatura,
    )

    resultado = preparar_candidato(
        candidato
    )

    return {
        "temperatura": temperatura,
        "candidato": candidato,
        "processamento": resultado,
    }


# ============================================================
# CONSENSO CANÔNICO
# ============================================================

def verificar_consenso(resultados):
    candidatos_prontos = []

    for resultado in resultados:
        processamento = resultado["processamento"]

        if processamento["status"] != "PRONTO":
            return {
                "consenso": False,
                "motivo": (
                    "Pelo menos um candidato foi "
                    "rejeitado antes do consenso."
                ),
                "resultado": None,
            }

        candidatos_prontos.append(
            processamento["candidato_canonico"]
        )

    primeiro = candidatos_prontos[0]

    consenso = all(
        candidato == primeiro
        for candidato in candidatos_prontos
    )

    if not consenso:
        return {
            "consenso": False,
            "motivo": (
                "Os candidatos não convergiram "
                "para a mesma representação canônica."
            ),
            "resultado": None,
        }

    return {
        "consenso": True,
        "motivo": (
            "Os três candidatos convergiram "
            "para a mesma representação canônica."
        ),
        "resultado": primeiro,
    }


# ============================================================
# GATE RELACIONAL
# ============================================================

def executar_gate(candidato):
    valido, motivo = validar_assinatura(
        candidato
    )

    return {
        "passou": valido,
        "motivo": motivo,
    }


# ============================================================
# PIPELINE COMPLETO
# ============================================================

def executar_pipeline(texto):
    print()
    print("=" * 70)
    print("PIPELINE INTEGRADO — A NIXAL")
    print("=" * 70)

    print()
    print("ENTRADA:")
    print(texto)

    print()
    print("-" * 70)
    print("ETAPA 1 — QWEN")
    print("-" * 70)

    resultados = []

    for temperatura in TEMPERATURAS:
        try:
            resultado = processar_temperatura(
                texto,
                temperatura,
            )

        except Exception as erro:
            print(
                f"\nTemperatura {temperatura:.1f}: ERRO"
            )

            print(
                f"Motivo: {erro}"
            )

            return {
                "status": "ABSTENCAO",
                "etapa": "QWEN",
                "motivo": str(erro),
            }

        resultados.append(
            resultado
        )

        print(
            f"\nTemperatura {temperatura:.1f}"
        )

        print(
            "Candidato bruto:"
        )

        print(
            json.dumps(
                resultado["candidato"],
                ensure_ascii=False,
                indent=2,
            )
        )

        print(
            "Processamento:"
        )

        print(
            json.dumps(
                resultado["processamento"],
                ensure_ascii=False,
                indent=2,
            )
        )

    print()
    print("-" * 70)
    print("ETAPA 2 — CONSENSO")
    print("-" * 70)

    consenso = verificar_consenso(
        resultados
    )

    print(
        "CONSENSO:",
        "SIM" if consenso["consenso"] else "NÃO",
    )

    print(
        "MOTIVO:",
        consenso["motivo"],
    )

    if not consenso["consenso"]:
        print()
        print("DECISÃO FINAL: ABSTENÇÃO")

        return {
            "status": "ABSTENCAO",
            "etapa": "CONSENSO",
            "motivo": consenso["motivo"],
            "resultados": resultados,
        }

    candidato_final = (
        consenso["resultado"]
    )

    print()
    print("REPRESENTAÇÃO CANÔNICA:")
    print(
        json.dumps(
            candidato_final,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("-" * 70)
    print("ETAPA 3 — GATE RELACIONAL")
    print("-" * 70)

    gate = executar_gate(
        candidato_final
    )

    print(
        "GATE:",
        "PASSOU" if gate["passou"] else "FALHOU",
    )

    print(
        "MOTIVO:",
        gate["motivo"],
    )

    if not gate["passou"]:
        print()
        print("DECISÃO FINAL: ABSTENÇÃO")

        return {
            "status": "ABSTENCAO",
            "etapa": "GATE_RELACIONAL",
            "motivo": gate["motivo"],
            "candidato": candidato_final,
        }

    tripla = (
        candidato_final["sujeito"],
        candidato_final["relacao"],
        candidato_final["objeto"],
    )

    print()
    print("-" * 70)
    print("ETAPA 4 — CRISTAL")
    print("-" * 70)

    print("TRIPLA APROVADA:")
    print(tripla)

    if not GRAVAR_NO_CRISTAL:
        print()
        print(
            "MODO SEGURO: "
            "não gravaremos no cristal nesta etapa."
        )

        print()
        print("DECISÃO FINAL: ACEITAR")

        return {
            "status": "ACEITAR",
            "etapa": "MODO_SEGURO",
            "tripla": tripla,
            "gravado": False,
        }

    resultado_cristal = registrar_experiencia(
        *tripla
    )

    print()
    print("RESULTADO DO CRISTAL:")

    print(
        json.dumps(
            resultado_cristal,
            ensure_ascii=False,
            indent=2,
        )
    )

    passou = resultado_cristal.get(
        "passou",
        False,
    )

    print()

    if passou:
        print(
            "DECISÃO FINAL: "
            "CRISTALIZADO"
        )

        return {
            "status": "CRISTALIZADO",
            "tripla": tripla,
            "gravado": True,
            "resultado_cristal": (
                resultado_cristal
            ),
        }

    print(
        "DECISÃO FINAL: "
        "FALHA NA VERIFICAÇÃO DO CRISTAL"
    )

    return {
        "status": "FALHA_CRISTAL",
        "tripla": tripla,
        "gravado": True,
        "resultado_cristal": (
            resultado_cristal
        ),
    }


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    # Prepara o cristal pelo ponto de entrada único antes de
    # processar qualquer coisa. Não destrutivo: se já existe,
    # o conhecimento anterior continua lá.
    (
        conceitos,
        relacoes,
        blocos,
    ) = abrir_ou_criar_cristal()

    print()
    print(
        f"CRISTAL ABERTO: {len(conceitos)} conceitos, "
        f"{len(relacoes)} relações, {len(blocos)} blocos."
    )

    texto = input(
        "Digite uma experiência para a Nixal:\n> "
    ).strip()

    if not texto:
        print(
            "Nenhum texto foi informado."
        )
        return

    executar_pipeline(
        texto
    )


if __name__ == "__main__":
    main()
