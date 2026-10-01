#!/usr/bin/env python3

"""
NIXAL — TESTE DA PREPARAÇÃO CONTROLADA DO TESTE

Microetapa 56.4.30
"""

from __future__ import annotations

from copy import deepcopy

from nixal_preparacao_teste_hipotese import (
    PreparacaoTesteHipoteseNixal,
)


TOTAL = 0
FALHAS = 0


def check(
    condicao: bool,
    mensagem: str,
) -> None:
    global TOTAL, FALHAS

    TOTAL += 1

    if condicao:
        print(f"[PASS] {TOTAL}. {mensagem}")
    else:
        FALHAS += 1
        print(f"[FAIL] {TOTAL}. {mensagem}")


def integracao_valida() -> dict:
    return {
        "sucesso": True,
        "estado": "hipotese_integrada_no_ciclo",
        "origem": "integracao_formulacao_ciclo_hipotese_nixal",
        "valor": {
            "hipotese": {
                "hipotese": (
                    "É possível que existam dependências entre "
                    "componentes ainda não registradas."
                ),
                "necessidade": (
                    "conhecer_dependencias_arquiteturais"
                ),
                "pergunta": (
                    "Quais relações de dependência existem?"
                ),
                "estado": "provisoria",
                "confirmada": False,
                "testada": False,
            },
            "ciclo": {
                "hipotese": (
                    "É possível que existam dependências entre "
                    "componentes ainda não registradas."
                ),
                "necessidade": (
                    "conhecer_dependencias_arquiteturais"
                ),
                "pergunta": (
                    "Quais relações de dependência existem?"
                ),
                "estado_atual": "provisoria",
                "historico": [
                    {
                        "de": None,
                        "para": "provisoria",
                        "evento": "hipotese_criada",
                    }
                ],
                "testes": [],
                "avaliacoes": [],
                "conhecimento_permanente": False,
            },
            "hipotese_formulada": True,
            "ciclo_iniciado": True,
            "hipotese_integrada": True,
            "hipotese_testada": False,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


def main() -> None:
    preparador = PreparacaoTesteHipoteseNixal()

    entrada = integracao_valida()
    original = deepcopy(entrada)

    resultado = preparador.preparar(
        entrada
    )

    valor = resultado.get(
        "valor",
        {},
    )

    entrada_teste = valor.get(
        "entrada_teste",
        {},
    )

    check(
        resultado.get("sucesso") is True,
        "1. preparação retorna sucesso",
    )

    check(
        resultado.get("estado")
        == "entrada_teste_preparada",
        "2. estado registra entrada de teste preparada",
    )

    check(
        valor.get("teste_preparado") is True,
        "3. teste é marcado como preparado",
    )

    check(
        valor.get("teste_executado") is False,
        "4. teste ainda não foi executado",
    )

    check(
        valor.get("resultado_teste_disponivel") is False,
        "5. resultado do teste ainda não está disponível",
    )

    check(
        valor.get("hipotese_avaliada") is False,
        "6. hipótese ainda não foi avaliada",
    )

    check(
        valor.get("conhecimento_permanente") is False,
        "7. conhecimento permanente continua falso",
    )

    check(
        valor.get("arquitetura_modificada") is False,
        "8. arquitetura permanece sem modificação",
    )

    check(
        entrada_teste.get("estado_hipotese")
        == "provisoria",
        "9. hipótese preparada permanece provisória",
    )

    check(
        entrada_teste.get("estado_teste")
        == "nao_executado",
        "10. estado do teste registra que não foi executado",
    )

    check(
        entrada_teste.get("pode_executar_teste")
        is False,
        "11. esta camada não autoriza execução direta",
    )

    check(
        entrada_teste.get("teste_executado")
        is False,
        "12. entrada de teste permanece não executada",
    )

    check(
        entrada_teste.get("resultado_teste")
        is None,
        "13. nenhum resultado de teste é inventado",
    )

    check(
        entrada_teste.get("evidencias_do_teste")
        == [],
        "14. nenhuma evidência de teste é inventada",
    )

    check(
        entrada_teste.get("suporte")
        is None
        and entrada_teste.get("contraria")
        is None
        and entrada_teste.get("inconclusivo")
        is None,
        "15. classificações do teste permanecem ausentes",
    )

    check(
        entrada_teste.get("pergunta")
        == original["valor"]["hipotese"]["pergunta"],
        "16. pergunta da hipótese é encaminhada",
    )

    check(
        entrada_teste.get("necessidade")
        == original["valor"]["hipotese"]["necessidade"],
        "17. necessidade é encaminhada",
    )

    entrada_teste_copia = deepcopy(
        entrada_teste
    )
    entrada_teste_copia["resultado_teste"] = {
        "inventado": True
    }

    check(
        entrada_teste.get("resultado_teste")
        is None,
        "18. entrada retornada permanece isolada de alterações externas",
    )

    entrada["valor"]["hipotese"]["pergunta"] = "alterada"

    check(
        resultado["valor"]["resultado_integracao"]
        == original,
        "19. resultado preserva cópia isolada da integração",
    )

    entrada_invalida = deepcopy(
        original
    )
    entrada_invalida[
        "estado"
    ] = "hipotese_provisoria_criada"

    resultado_invalido = preparador.preparar(
        entrada_invalida
    )

    check(
        resultado_invalido.get("sucesso") is False,
        "20. estado de entrada incorreto é recusado",
    )

    integracao_nao_provisoria = deepcopy(
        original
    )
    integracao_nao_provisoria[
        "valor"
    ]["ciclo"]["estado_atual"] = "testada"

    resultado_nao_provisoria = preparador.preparar(
        integracao_nao_provisoria
    )

    check(
        resultado_nao_provisoria.get("sucesso") is False,
        "21. ciclo já testado não é preparado novamente",
    )

    integracao_confirmada = deepcopy(
        original
    )
    integracao_confirmada[
        "valor"
    ]["hipotese"]["confirmada"] = True

    resultado_confirmada = preparador.preparar(
        integracao_confirmada
    )

    check(
        resultado_confirmada.get("sucesso") is False,
        "22. hipótese confirmada não é aceita",
    )

    integracao_testada = deepcopy(
        original
    )
    integracao_testada[
        "valor"
    ]["hipotese"]["testada"] = True

    resultado_testada = preparador.preparar(
        integracao_testada
    )

    check(
        resultado_testada.get("sucesso") is False,
        "23. hipótese já testada não é aceita",
    )

    try:
        preparador.executar_teste()
        bloqueou_execucao = False
    except PermissionError:
        bloqueou_execucao = True

    check(
        bloqueou_execucao,
        "24. execução do teste continua bloqueada nesta camada",
    )

    try:
        preparador.avaliar_hipotese()
        bloqueou_avaliacao = False
    except PermissionError:
        bloqueou_avaliacao = True

    check(
        bloqueou_avaliacao,
        "25. avaliação continua bloqueada nesta camada",
    )

    try:
        preparador.promover_conhecimento()
        bloqueou_promocao = False
    except PermissionError:
        bloqueou_promocao = True

    check(
        bloqueou_promocao,
        "26. promoção de conhecimento continua bloqueada",
    )

    try:
        preparador.modificar_arquitetura()
        bloqueou_arquitetura = False
    except PermissionError:
        bloqueou_arquitetura = True

    check(
        bloqueou_arquitetura,
        "27. modificação de arquitetura continua bloqueada",
    )

    try:
        preparador.executar_capacidade()
        bloqueou_capacidade = False
    except PermissionError:
        bloqueou_capacidade = True

    check(
        bloqueou_capacidade,
        "28. execução de capacidades continua bloqueada",
    )

    print()
    print("=" * 64)
    print(
        f"TESTES EXECUTADOS: {TOTAL}"
    )
    print(
        f"FALHAS: {FALHAS}"
    )
    print(
        f"PASSOU: {FALHAS == 0}"
    )
    print("=" * 64)


if __name__ == "__main__":
    main()
