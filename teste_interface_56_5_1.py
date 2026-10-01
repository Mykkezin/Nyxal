#!/usr/bin/env python3

"""
NIXAL — TESTE DO CONTRATO DA INTERFACE CONVERSACIONAL

Microetapa 56.5.1
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_interface import (
    InterfaceConversacionalNixal,
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
        print(
            f"[PASS] {TOTAL}. {mensagem}"
        )
    else:
        FALHAS += 1
        print(
            f"[FAIL] {TOTAL}. {mensagem}"
        )


def main() -> None:
    interface = InterfaceConversacionalNixal()

    entrada = interface.criar_entrada(
        "Olá, Nixal.",
        sessao="sessao_teste",
    )

    check(
        interface.validar_entrada(
            entrada
        ),
        "1. entrada criada possui contrato válido",
    )

    check(
        entrada.get("estado")
        == "entrada_recebida",
        "2. entrada possui estado correto",
    )

    check(
        entrada.get("origem")
        == "interface_conversacional_nixal",
        "3. origem da entrada é a interface",
    )

    check(
        entrada.get("versao_interface")
        == "56.5.1",
        "4. versão da interface é registrada",
    )

    check(
        entrada["valor"].get("texto")
        == "Olá, Nixal.",
        "5. texto original é preservado",
    )

    check(
        entrada["valor"].get("sessao")
        == "sessao_teste",
        "6. sessão é preservada",
    )

    check(
        entrada["valor"].get("origem_mensagem")
        == "usuario",
        "7. origem da mensagem é registrada",
    )

    check(
        entrada["valor"].get("interpretado")
        is False,
        "8. interface não interpreta a mensagem",
    )

    check(
        entrada["valor"].get("processado")
        is False,
        "9. interface não processa a mensagem",
    )

    check(
        entrada["valor"].get("capacidade_executada")
        is False,
        "10. nenhuma capacidade é executada",
    )

    check(
        entrada["valor"].get("conhecimento_permanente")
        is False,
        "11. conhecimento permanente permanece falso",
    )

    check(
        entrada["valor"].get("arquitetura_modificada")
        is False,
        "12. arquitetura permanece sem modificação",
    )

    original_entrada = deepcopy(
        entrada
    )

    entrada["valor"]["texto"] = (
        "texto alterado externamente"
    )

    check(
        original_entrada["valor"]["texto"]
        == "Olá, Nixal.",
        "13. cópia externa não altera o contrato original",
    )

    resposta = interface.criar_resposta(
        "Olá. Estou aqui.",
        sessao="sessao_teste",
    )

    check(
        interface.validar_resposta(
            resposta
        ),
        "14. resposta criada possui contrato válido",
    )

    check(
        resposta.get("estado")
        == "resposta_pronta",
        "15. resposta possui estado correto",
    )

    check(
        resposta.get("resposta")
        == "Olá. Estou aqui.",
        "16. texto da resposta é preservado",
    )

    check(
        resposta.get("sessao")
        == "sessao_teste",
        "17. sessão da resposta é preservada",
    )

    check(
        resposta["valor"].get("interpretado")
        is False,
        "18. interface não interpreta a própria resposta",
    )

    check(
        resposta["valor"].get("capacidade_executada")
        is False,
        "19. resposta não executa capacidade",
    )

    check(
        resposta["valor"].get("conhecimento_permanente")
        is False,
        "20. resposta não promove conhecimento",
    )

    check(
        resposta["valor"].get("arquitetura_modificada")
        is False,
        "21. resposta não modifica arquitetura",
    )

    resposta_original = deepcopy(
        resposta
    )

    resposta["resposta"] = (
        "alterada externamente"
    )

    check(
        resposta_original["resposta"]
        == "Olá. Estou aqui.",
        "22. cópia externa não altera resposta isolada",
    )

    entradas_invalidas: list[dict[str, Any]] = [
        {},
        {
            "sucesso": False,
            "estado": "entrada_recebida",
            "origem": interface.FONTE,
            "valor": {},
            "versao_interface": interface.VERSAO,
        },
        {
            "sucesso": True,
            "estado": "estado_invalido",
            "origem": interface.FONTE,
            "valor": {},
            "versao_interface": interface.VERSAO,
        },
    ]

    for indice, entrada_invalida in enumerate(
        entradas_invalidas,
        start=23,
    ):
        check(
            interface.validar_entrada(
                entrada_invalida
            )
            is False,
            f"{indice}. entrada inválida é recusada",
        )

    respostas_invalidas: list[dict[str, Any]] = [
        {},
        {
            "sucesso": False,
            "estado": "resposta_pronta",
            "origem": interface.FONTE,
            "resposta": "Olá.",
            "valor": {
                "texto": "Olá.",
                "interpretado": False,
                "capacidade_executada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "versao_interface": interface.VERSAO,
        },
        {
            "sucesso": True,
            "estado": "resposta_pronta",
            "origem": interface.FONTE,
            "resposta": "",
            "valor": {
                "texto": "",
                "interpretado": False,
                "capacidade_executada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "versao_interface": interface.VERSAO,
        },
    ]

    for indice, resposta_invalida in enumerate(
        respostas_invalidas,
        start=26,
    ):
        check(
            interface.validar_resposta(
                resposta_invalida
            )
            is False,
            f"{indice}. resposta inválida é recusada",
        )

    try:
        interface.criar_entrada("")
        bloqueou_texto_vazio = False
    except ValueError:
        bloqueou_texto_vazio = True

    check(
        bloqueou_texto_vazio,
        "29. texto de entrada vazio é recusado",
    )

    try:
        interface.criar_resposta("")
        bloqueou_resposta_vazia = False
    except ValueError:
        bloqueou_resposta_vazia = True

    check(
        bloqueou_resposta_vazia,
        "30. resposta vazia é recusada",
    )

    bloqueios = [
        (
            "executar_capacidade",
            "31. execução de capacidade permanece bloqueada",
        ),
        (
            "interpretar",
            "32. interpretação permanece bloqueada",
        ),
        (
            "modificar_arquitetura",
            "33. modificação arquitetural permanece bloqueada",
        ),
        (
            "promover_conhecimento",
            "34. promoção de conhecimento permanece bloqueada",
        ),
        (
            "investigar",
            "35. investigação permanece bloqueada",
        ),
        (
            "formular_hipotese",
            "36. formulação de hipótese permanece bloqueada",
        ),
        (
            "executar_teste",
            "37. execução de teste permanece bloqueada",
        ),
        (
            "avaliar_hipotese",
            "38. avaliação de hipótese permanece bloqueada",
        ),
    ]

    for nome_metodo, mensagem in bloqueios:
        try:
            getattr(
                interface,
                nome_metodo,
            )()
            bloqueou = False
        except PermissionError:
            bloqueou = True

        check(
            bloqueou,
            mensagem,
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
