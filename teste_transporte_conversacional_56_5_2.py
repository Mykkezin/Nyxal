#!/usr/bin/env python3

"""
NIXAL — TESTE DO TRANSPORTE CONVERSACIONAL

Microetapa 56.5.2
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_interface import (
    InterfaceConversacionalNixal,
)
from nixal_transporte_conversacional import (
    TransporteConversacionalNixal,
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


class NucleoFalso:
    """
    Núcleo determinístico usado somente para validar o transporte.
    """

    def __init__(self) -> None:
        self.chamadas = 0
        self.entradas: list[dict[str, Any]] = []
        self.respostas: list[dict[str, Any]] = []

    def processar(
        self,
        entrada: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1

        entrada_isolada = deepcopy(
            entrada
        )

        self.entradas.append(
            entrada_isolada
        )

        texto = (
            entrada["valor"]["texto"]
        )

        sessao = (
            entrada["valor"]["sessao"]
        )

        interface = InterfaceConversacionalNixal()

        resposta = interface.criar_resposta(
            f"Recebi: {texto}",
            sessao=sessao,
        )

        # A resposta real produzida pelo núcleo fica registrada
        # separadamente da cópia que o transporte devolverá.
        self.respostas.append(
            resposta
        )

        return resposta


class NucleoRespostaInvalida:
    def processar(
        self,
        _entrada: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "resposta_pronta",
            "origem": "nucleo_invalido",
            "resposta": "",
            "valor": {},
            "versao_interface": "56.5.1",
        }


class NucleoTipoInvalido:
    def processar(
        self,
        _entrada: dict[str, Any],
    ) -> str:
        return "resposta inválida"


class NucleoComFalha:
    def processar(
        self,
        _entrada: dict[str, Any],
    ) -> dict[str, Any]:
        raise RuntimeError(
            "falha controlada"
        )


def main() -> None:
    interface = InterfaceConversacionalNixal()

    transporte = TransporteConversacionalNixal(
        interface
    )

    nucleo = NucleoFalso()

    resultado = transporte.processar_mensagem(
        "Olá, Nixal.",
        nucleo,
        sessao="sessao_1",
    )

    check(
        resultado.get("sucesso") is True,
        "1. processamento conversacional retorna sucesso",
    )

    check(
        resultado.get("estado")
        == "mensagem_processada",
        "2. estado registra mensagem processada",
    )

    check(
        resultado.get("origem")
        == "transporte_conversacional_nixal",
        "3. origem identifica o transporte",
    )

    check(
        resultado["valor"].get(
            "mensagem_processada"
        ) is True,
        "4. mensagem fica marcada como processada",
    )

    check(
        resultado["valor"].get(
            "conhecimento_permanente"
        ) is False,
        "5. conhecimento permanente permanece falso",
    )

    check(
        resultado["valor"].get(
            "arquitetura_modificada"
        ) is False,
        "6. arquitetura permanece sem modificação",
    )

    check(
        nucleo.chamadas == 1,
        "7. núcleo é acionado uma vez",
    )

    entrada = resultado["valor"].get(
        "entrada"
    )

    check(
        isinstance(
            entrada,
            dict,
        ),
        "8. entrada encaminhada é preservada",
    )

    check(
        entrada["valor"]["texto"]
        == "Olá, Nixal.",
        "9. texto chega intacto ao transporte",
    )

    check(
        entrada["valor"]["sessao"]
        == "sessao_1",
        "10. sessão chega intacta ao núcleo",
    )

    resposta = resultado["valor"].get(
        "resposta"
    )

    check(
        isinstance(
            resposta,
            dict,
        ),
        "11. resposta do núcleo é preservada",
    )

    check(
        interface.validar_resposta(
            resposta
        ),
        "12. resposta do núcleo atende ao contrato da interface",
    )

    check(
        resposta["resposta"]
        == "Recebi: Olá, Nixal.",
        "13. conteúdo da resposta é preservado",
    )

    check(
        resultado.get("resposta")
        == resposta,
        "14. resposta também é exposta no nível de transporte",
    )

    check(
        nucleo.entradas[0]
        == entrada,
        "15. núcleo recebeu a entrada estruturada correta",
    )

    entrada_original = deepcopy(
        resultado["valor"]["entrada"]
    )

    nucleo.entradas[0]["valor"]["texto"] = (
        "alterado externamente"
    )

    check(
        resultado["valor"]["entrada"]["valor"]["texto"]
        == "Olá, Nixal.",
        "16. entrada entregue ao núcleo permanece isolada da saída",
    )

    check(
        entrada_original["valor"]["texto"]
        == "Olá, Nixal.",
        "17. cópia de referência da entrada permanece preservada",
    )

    resposta_original = deepcopy(
        resultado["valor"]["resposta"]
    )

    nucleo.respostas[0]["resposta"] = (
        "alterada externamente"
    )

    check(
        resultado["valor"]["resposta"]["resposta"]
        == "Recebi: Olá, Nixal.",
        "18. resposta produzida pelo núcleo permanece isolada da saída",
    )

    check(
        resposta_original["resposta"]
        == "Recebi: Olá, Nixal.",
        "19. cópia de referência da resposta permanece preservada",
    )

    entrada_direta = interface.criar_entrada(
        "Mensagem direta",
        sessao="sessao_2",
    )

    resultado_direto = transporte.enviar_entrada(
        entrada_direta,
        nucleo,
    )

    check(
        resultado_direto.get("sucesso") is True,
        "20. envio de entrada estruturada retorna sucesso",
    )

    check(
        resultado_direto["valor"]["entrada"]
        == entrada_direta,
        "21. entrada estruturada direta é preservada",
    )

    check(
        resultado_direto["valor"]["resposta"]["resposta"]
        == "Recebi: Mensagem direta",
        "22. núcleo responde à entrada estruturada direta",
    )

    entrada_direta["valor"]["texto"] = (
        "modificada"
    )

    check(
        resultado_direto["valor"]["entrada"]["valor"]["texto"]
        == "Mensagem direta",
        "23. entrada direta original permanece isolada",
    )

    resultado_texto_vazio = (
        transporte.processar_mensagem(
            "",
            nucleo,
        )
    )

    check(
        resultado_texto_vazio.get("sucesso")
        is False,
        "24. texto vazio é recusado pela fronteira",
    )

    resultado_nucleo_invalido = (
        transporte.processar_mensagem(
            "teste",
            object(),
        )
    )

    check(
        resultado_nucleo_invalido.get("sucesso")
        is False,
        "25. núcleo sem método processar é recusado",
    )

    resultado_resposta_invalida = (
        transporte.processar_mensagem(
            "teste",
            NucleoRespostaInvalida(),
        )
    )

    check(
        resultado_resposta_invalida.get("sucesso")
        is False,
        "26. resposta estruturalmente inválida é recusada",
    )

    check(
        resultado_resposta_invalida.get("estado")
        == "resposta_nucleo_invalida",
        "27. estado identifica resposta inválida do núcleo",
    )

    resultado_tipo_invalido = (
        transporte.processar_mensagem(
            "teste",
            NucleoTipoInvalido(),
        )
    )

    check(
        resultado_tipo_invalido.get("sucesso")
        is False,
        "28. resposta não-dicionário é recusada",
    )

    resultado_falha = (
        transporte.processar_mensagem(
            "teste",
            NucleoComFalha(),
        )
    )

    check(
        resultado_falha.get("sucesso")
        is False,
        "29. falha do núcleo não vira sucesso artificial",
    )

    check(
        resultado_falha.get("estado")
        == "nucleo_nao_respondeu",
        "30. falha do núcleo possui estado explícito",
    )

    bloqueios = [
        (
            "interpretar",
            "31. interpretação permanece bloqueada",
        ),
        (
            "executar_capacidade",
            "32. execução de capacidade permanece bloqueada",
        ),
        (
            "acessar_memoria",
            "33. acesso direto à memória permanece bloqueado",
        ),
        (
            "acessar_corpo",
            "34. acesso direto ao corpo permanece bloqueado",
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
        (
            "promover_conhecimento",
            "39. promoção de conhecimento permanece bloqueada",
        ),
        (
            "modificar_arquitetura",
            "40. modificação arquitetural permanece bloqueada",
        ),
    ]

    for nome_metodo, mensagem in bloqueios:
        try:
            getattr(
                transporte,
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
