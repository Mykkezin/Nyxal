#!/usr/bin/env python3

"""
NIXAL — TESTE DA EXECUÇÃO CONTROLADA DA AVALIAÇÃO

Microetapa 56.4.33
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_avaliacao_hipotese import (
    AvaliacaoHipoteseNixal,
)
from nixal_execucao_avaliacao_hipotese import (
    ExecucaoAvaliacaoHipoteseNixal,
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
        "estado": "teste_integrado_no_ciclo",
        "origem": "integracao_teste_ciclo_hipotese_nixal",
        "valor": {
            "hipotese": {
                "hipotese": (
                    "É possível que existam dependências entre componentes."
                ),
                "necessidade": "conhecer_dependencias_arquiteturais",
                "pergunta": "Quais relações de dependência existem?",
                "estado": "provisoria",
                "confirmada": False,
                "testada": True,
            },
            "ciclo": {
                "hipotese": (
                    "É possível que existam dependências entre componentes."
                ),
                "necessidade": "conhecer_dependencias_arquiteturais",
                "pergunta": "Quais relações de dependência existem?",
                "estado_atual": "testada",
                "historico": [
                    {
                        "de": None,
                        "para": "provisoria",
                        "evento": "hipotese_criada",
                    },
                    {
                        "de": "provisoria",
                        "para": "testada",
                        "evento": "teste_registrado",
                        "indice_teste": 1,
                    },
                ],
                "testes": [
                    {
                        "indice": 1,
                        "estado_anterior": "provisoria",
                        "resultado": {
                            "estado": "teste_concluido",
                            "resultado": {
                                "sucesso": True,
                                "estado": "observacao_realizada",
                            },
                        },
                    }
                ],
                "avaliacoes": [],
                "conhecimento_permanente": False,
            },
            "resultado_teste": {
                "sucesso": True,
                "estado": "observacao_realizada",
                "suporte": True,
                "contraria": False,
                "inconclusivo": False,
                "evidencias": [
                    {
                        "fonte": "teste_deterministico",
                        "descricao": "Uma relação foi observada.",
                    }
                ],
            },
            "teste_executado": True,
            "teste_integrado": True,
            "ciclo_atualizado": True,
            "hipotese_testada": True,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


class AvaliadorFalso(AvaliacaoHipoteseNixal):
    def __init__(self, resultado: dict[str, Any]) -> None:
        self._resultado = deepcopy(resultado)
        self.chamadas: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def avaliar(
        self,
        hipotese: dict[str, Any],
        resultado_teste: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas.append(
            (
                deepcopy(hipotese),
                deepcopy(resultado_teste),
            )
        )
        return deepcopy(self._resultado)


def resultado_avaliacao_valido() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "suportada",
        "origem": "avaliacao_hipotese_nixal",
        "valor": {
            "hipotese": (
                "É possível que existam dependências entre componentes."
            ),
            "estado_anterior": "provisoria",
            "estado_teste": "teste_concluido",
            "evidencias": [
                {
                    "fonte": "teste_deterministico",
                }
            ],
            "motivo": "Evidência favorável observada.",
            "conhecimento_permanente": False,
        },
    }


def main() -> None:
    avaliador = AvaliadorFalso(
        resultado_avaliacao_valido()
    )

    executor = ExecucaoAvaliacaoHipoteseNixal(
        avaliador=avaliador
    )

    entrada = entrada_valida()
    original = deepcopy(entrada)

    resultado = executor.executar(
        entrada
    )

    valor = resultado.get(
        "valor",
        {},
    )

    check(
        resultado.get("sucesso") is True,
        "1. avaliação retorna sucesso",
    )

    check(
        resultado.get("estado") == "hipotese_avaliada",
        "2. estado registra hipótese avaliada",
    )

    check(
        valor.get("hipotese_avaliada") is True,
        "3. hipótese é marcada como avaliada",
    )

    check(
        valor.get("estado_avaliacao") == "suportada",
        "4. classificação da avaliação é encaminhada",
    )

    check(
        valor.get("conhecimento_permanente") is False,
        "5. conhecimento permanente continua falso",
    )

    check(
        valor.get("arquitetura_modificada") is False,
        "6. arquitetura permanece sem modificação",
    )

    check(
        len(avaliador.chamadas) == 1,
        "7. avaliador é acionado uma vez",
    )

    hipotese_recebida, teste_recebido = avaliador.chamadas[0]

    check(
        hipotese_recebida
        == original["valor"]["hipotese"],
        "8. hipótese é encaminhada ao avaliador",
    )

    check(
        teste_recebido["suporte"] is True
        and teste_recebido["contraria"] is False
        and teste_recebido["inconclusivo"] is False,
        "9. classificação explícita é encaminhada",
    )

    check(
        teste_recebido["evidencias"]
        == original["valor"]["resultado_teste"]["evidencias"],
        "10. evidências são encaminhadas sem perda",
    )

    check(
        valor["resultado_avaliacao"]
        == resultado_avaliacao_valido(),
        "11. resultado da avaliação é preservado",
    )

    entrada["valor"]["ciclo"]["estado_atual"] = "alterado"

    check(
        valor["ciclo"]["estado_atual"] == "testada",
        "12. ciclo retornado permanece isolado",
    )

    entrada_invalida = deepcopy(original)
    entrada_invalida[
        "estado"
    ] = "entrada_teste_preparada"

    resultado_invalido = executor.executar(
        entrada_invalida
    )

    check(
        resultado_invalido.get("sucesso") is False,
        "13. estado de entrada incorreto é recusado",
    )

    entrada_sem_integracao = deepcopy(original)
    entrada_sem_integracao[
        "valor"
    ]["teste_integrado"] = False

    resultado_sem_integracao = executor.executar(
        entrada_sem_integracao
    )

    check(
        resultado_sem_integracao.get("sucesso") is False,
        "14. teste não integrado é recusado",
    )

    entrada_ja_avaliada = deepcopy(original)
    entrada_ja_avaliada[
        "valor"
    ]["hipotese_avaliada"] = True

    resultado_ja_avaliada = executor.executar(
        entrada_ja_avaliada
    )

    check(
        resultado_ja_avaliada.get("sucesso") is False,
        "15. hipótese já avaliada é recusada",
    )

    entrada_ciclo_incorreto = deepcopy(original)
    entrada_ciclo_incorreto[
        "valor"
    ]["ciclo"]["estado_atual"] = "provisoria"

    resultado_ciclo_incorreto = executor.executar(
        entrada_ciclo_incorreto
    )

    check(
        resultado_ciclo_incorreto.get("sucesso") is False,
        "16. ciclo que não está testado é recusado",
    )

    entrada_flags_incompletas = deepcopy(original)
    entrada_flags_incompletas[
        "valor"
    ]["resultado_teste"]["contraria"] = None

    resultado_flags_incompletas = executor.executar(
        entrada_flags_incompletas
    )

    check(
        resultado_flags_incompletas.get("sucesso") is False,
        "17. flags de classificação incompletas são recusadas",
    )

    entrada_flags_ambigua = deepcopy(original)

    entrada_flags_ambigua[
        "valor"
    ]["resultado_teste"]["contraria"] = True

    resultado_flags_ambigua = executor.executar(
        entrada_flags_ambigua
    )

    check(
        resultado_flags_ambigua.get("sucesso") is False,
        "18. múltiplas classificações simultâneas são recusadas",
    )

    entrada_sem_evidencias = deepcopy(original)
    entrada_sem_evidencias[
        "valor"
    ]["resultado_teste"]["evidencias"] = None

    resultado_sem_evidencias = executor.executar(
        entrada_sem_evidencias
    )

    check(
        resultado_sem_evidencias.get("sucesso") is False,
        "19. ausência de lista de evidências é recusada",
    )

    avaliador_falhou = AvaliadorFalso(
        {
            "sucesso": False,
            "estado": "negado",
            "valor": None,
        }
    )

    executor_falhou = ExecucaoAvaliacaoHipoteseNixal(
        avaliador=avaliador_falhou
    )

    resultado_falha = executor_falhou.executar(
        original
    )

    check(
        resultado_falha.get("sucesso") is False
        and resultado_falha.get("estado")
        == "avaliacao_nao_concluida",
        "20. falha do avaliador não vira sucesso artificial",
    )

    avaliador_estado_incorreto = AvaliadorFalso(
        {
            "sucesso": True,
            "estado": "desconhecido",
            "valor": None,
        }
    )

    executor_estado_incorreto = ExecucaoAvaliacaoHipoteseNixal(
        avaliador=avaliador_estado_incorreto
    )

    resultado_estado = executor_estado_incorreto.executar(
        original
    )

    check(
        resultado_estado.get("sucesso") is True
        and resultado_estado.get("estado")
        == "avaliacao_nao_concluida",
        "21. estado de avaliação desconhecido não é promovido",
    )

    try:
        executor.promover_conhecimento()
        bloqueou_promocao = False
    except PermissionError:
        bloqueou_promocao = True

    check(
        bloqueou_promocao,
        "22. promoção de conhecimento continua bloqueada",
    )

    try:
        executor.modificar_arquitetura()
        bloqueou_arquitetura = False
    except PermissionError:
        bloqueou_arquitetura = True

    check(
        bloqueou_arquitetura,
        "23. modificação de arquitetura continua bloqueada",
    )

    try:
        executor.executar_capacidade()
        bloqueou_capacidade = False
    except PermissionError:
        bloqueou_capacidade = True

    check(
        bloqueou_capacidade,
        "24. execução de capacidades continua bloqueada",
    )

    check(
        original == entrada_valida(),
        "25. fábrica de entrada continua determinística",
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
