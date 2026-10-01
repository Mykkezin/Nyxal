#!/usr/bin/env python3

"""
NIXAL — TESTE DA EXECUÇÃO CONTROLADA DO TESTE DE HIPÓTESE

Microetapa 56.4.31
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_execucao_teste_hipotese import (
    ExecucaoTesteHipoteseNixal,
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


def entrada_valida() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "entrada_teste_preparada",
        "origem": "preparacao_teste_hipotese_nixal",
        "valor": {
            "entrada_teste": {
                "hipotese": {
                    "hipotese": (
                        "É possível que existam dependências entre componentes."
                    ),
                    "estado": "provisoria",
                    "confirmada": False,
                    "testada": False,
                },
                "necessidade": (
                    "conhecer_dependencias_arquiteturais"
                ),
                "pergunta": (
                    "Quais relações de dependência existem?"
                ),
                "estado_hipotese": "provisoria",
                "estado_teste": "nao_executado",
                "pode_executar_teste": False,
                "teste_executado": False,
                "resultado_teste": None,
                "evidencias_do_teste": [],
                "suporte": None,
                "contraria": None,
                "inconclusivo": None,
                "hipotese_avaliada": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "teste_preparado": True,
            "teste_executado": False,
            "resultado_teste_disponivel": False,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


class TestadorFalso:
    """Executor determinístico para validar a camada de execução."""

    def __init__(
        self,
        resultado: dict[str, Any],
    ) -> None:
        self.resultado = deepcopy(
            resultado
        )
        self.chamadas: list[dict[str, Any]] = []

    def executar(
        self,
        entrada_teste: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas.append(
            deepcopy(
                entrada_teste
            )
        )
        return deepcopy(
            self.resultado
        )


def main() -> None:
    resultado_teste = {
        "sucesso": True,
        "estado": "observacao_realizada",
        "evidencias": [
            {
                "fonte": "teste_deterministico",
                "descricao": (
                    "Uma relação de uso entre componentes foi observada."
                ),
            }
        ],
        "dados_observados": {
            "relacao_encontrada": True
        },
    }

    testador = TestadorFalso(
        resultado_teste
    )

    executor = ExecucaoTesteHipoteseNixal(
        testador
    )

    entrada = entrada_valida()
    original = deepcopy(
        entrada
    )

    resultado = executor.executar(
        entrada
    )

    valor = resultado.get(
        "valor",
        {},
    )

    check(
        resultado.get("sucesso") is True,
        "1. execução do teste retorna sucesso",
    )

    check(
        resultado.get("estado") == "teste_concluido",
        "2. estado registra teste concluído",
    )

    check(
        valor.get("teste_preparado") is True,
        "3. teste permanece marcado como preparado",
    )

    check(
        valor.get("teste_executado") is True,
        "4. teste é marcado como executado",
    )

    check(
        valor.get("resultado_teste_disponivel") is True,
        "5. resultado do teste fica disponível",
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
        testador.chamadas == [original["valor"]["entrada_teste"]],
        "9. executor recebe somente a entrada de teste",
    )

    check(
        valor.get("resultado_teste") == resultado_teste,
        "10. resultado observado é preservado",
    )

    check(
        valor["resultado_teste"] is not resultado_teste,
        "11. resultado retornado é uma cópia isolada",
    )

    check(
        resultado["valor"]["entrada_preparada"] == original,
        "12. entrada preparada é preservada sem alteração",
    )

    entrada["valor"]["entrada_teste"]["pergunta"] = "alterada"

    check(
        resultado["valor"]["entrada_preparada"] == original,
        "13. resultado mantém cópia isolada da entrada externa",
    )

    entrada["valor"]["entrada_teste"]["hipotese"]["alterado"] = True

    check(
        "alterado"
        not in resultado["valor"]["entrada_teste"]["hipotese"],
        "14. entrada de teste retornada também permanece isolada",
    )

    entrada_invalida = deepcopy(
        original
    )
    entrada_invalida[
        "estado"
    ] = "hipotese_integrada_no_ciclo"

    resultado_invalido = executor.executar(
        entrada_invalida
    )

    check(
        resultado_invalido.get("sucesso") is False,
        "15. estado de entrada incorreto é recusado",
    )

    entrada_nao_preparada = deepcopy(
        original
    )
    entrada_nao_preparada[
        "valor"
    ]["teste_preparado"] = False

    resultado_nao_preparada = executor.executar(
        entrada_nao_preparada
    )

    check(
        resultado_nao_preparada.get("sucesso") is False,
        "16. teste não preparado é recusado",
    )

    entrada_ja_executada = deepcopy(
        original
    )
    entrada_ja_executada[
        "valor"
    ]["teste_executado"] = True

    resultado_ja_executada = executor.executar(
        entrada_ja_executada
    )

    check(
        resultado_ja_executada.get("sucesso") is False,
        "17. teste já executado é recusado",
    )

    entrada_resultado_pronto = deepcopy(
        original
    )
    entrada_resultado_pronto[
        "valor"
    ]["resultado_teste_disponivel"] = True

    resultado_pronto = executor.executar(
        entrada_resultado_pronto
    )

    check(
        resultado_pronto.get("sucesso") is False,
        "18. entrada com resultado já disponível é recusada",
    )

    entrada_teste_invalida = deepcopy(
        original
    )
    entrada_teste_invalida[
        "valor"
    ]["entrada_teste"]["estado_hipotese"] = "testada"

    resultado_hipotese = executor.executar(
        entrada_teste_invalida
    )

    check(
        resultado_hipotese.get("sucesso") is False,
        "19. hipótese não provisória é recusada",
    )

    testador_falho = TestadorFalso(
        {
            "sucesso": False,
            "estado": "falha",
            "evidencias": [],
        }
    )

    executor_falho = ExecucaoTesteHipoteseNixal(
        testador_falho
    )

    resultado_falho = executor_falho.executar(
        original
    )

    check(
        resultado_falho.get("sucesso") is False
        and resultado_falho.get("estado")
        == "teste_nao_concluido",
        "20. falha do executor não é promovida para sucesso",
    )

    testador_invalido = TestadorFalso(
        {
            "sucesso": True,
            "estado": "observacao_realizada",
        }
    )

    executor_invalido = ExecucaoTesteHipoteseNixal(
        testador_invalido
    )

    resultado_sem_evidencias = executor_invalido.executar(
        original
    )

    check(
        resultado_sem_evidencias.get("sucesso") is True,
        "21. resultado estruturado sem classificação ainda é aceito",
    )

    check(
        resultado_sem_evidencias["valor"]["hipotese_avaliada"]
        is False,
        "22. ausência de avaliação permanece explícita",
    )

    try:
        executor.avaliar_hipotese()
        bloqueou_avaliacao = False
    except PermissionError:
        bloqueou_avaliacao = True

    check(
        bloqueou_avaliacao,
        "23. avaliação continua bloqueada nesta camada",
    )

    try:
        executor.promover_conhecimento()
        bloqueou_promocao = False
    except PermissionError:
        bloqueou_promocao = True

    check(
        bloqueou_promocao,
        "24. promoção de conhecimento continua bloqueada",
    )

    try:
        executor.modificar_arquitetura()
        bloqueou_arquitetura = False
    except PermissionError:
        bloqueou_arquitetura = True

    check(
        bloqueou_arquitetura,
        "25. modificação de arquitetura continua bloqueada",
    )

    try:
        executor.executar_capacidade()
        bloqueou_capacidade = False
    except PermissionError:
        bloqueou_capacidade = True

    check(
        bloqueou_capacidade,
        "26. execução de capacidades internas continua bloqueada",
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
