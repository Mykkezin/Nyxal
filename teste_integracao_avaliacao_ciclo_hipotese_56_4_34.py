#!/usr/bin/env python3

"""
NIXAL — TESTE DA INTEGRAÇÃO DA AVALIAÇÃO AO CICLO

Microetapa 56.4.34
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_execucao_avaliacao_hipotese import (
    ExecucaoAvaliacaoHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_integracao_avaliacao_ciclo_hipotese import (
    IntegracaoAvaliacaoCicloHipoteseNixal,
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
                                "estado": "observacao_realizada",
                                "evidencias": [
                                    {
                                        "fonte": "teste_deterministico"
                                    }
                                ],
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


def resultado_avaliacao_valido() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "hipotese_avaliada",
        "origem": "execucao_avaliacao_hipotese_nixal",
        "valor": {
            "resultado_integracao_teste": {},
            "resultado_avaliacao": {
                "sucesso": True,
                "estado": "suportada",
            },
            "hipotese": {
                "hipotese": (
                    "É possível que existam dependências entre componentes."
                )
            },
            "ciclo": {
                "estado_atual": "testada"
            },
            "estado_avaliacao": "suportada",
            "hipotese_avaliada": True,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


class ExecutorAvaliacaoFalso(ExecucaoAvaliacaoHipoteseNixal):
    def __init__(self, resultado: dict[str, Any]) -> None:
        self._resultado = deepcopy(resultado)
        self.chamadas = 0
        self.entrada_recebida = None

    def executar(
        self,
        entrada: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1
        self.entrada_recebida = deepcopy(entrada)
        return deepcopy(self._resultado)


def ciclo_valido() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "suportada",
        "origem": "ciclo_memoria_hipotese_nixal",
        "valor": {
            "hipotese": (
                "É possível que existam dependências entre componentes."
            ),
            "necessidade": "conhecer_dependencias_arquiteturais",
            "pergunta": "Quais relações de dependência existem?",
            "estado_atual": "suportada",
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
                {
                    "de": "testada",
                    "para": "suportada",
                    "evento": "hipotese_avaliada",
                    "indice_avaliacao": 1,
                },
            ],
            "testes": [
                {
                    "indice": 1,
                    "estado_anterior": "provisoria",
                    "resultado": {
                        "estado": "teste_concluido",
                        "resultado": {
                            "estado": "observacao_realizada",
                            "evidencias": [
                                {
                                    "fonte": "teste_deterministico"
                                }
                            ],
                        },
                    },
                }
            ],
            "avaliacoes": [
                {
                    "indice": 1,
                    "estado_anterior": "testada",
                    "resultado": {
                        "estado": "suportada",
                        "resultado": {
                            "hipotese": (
                                "É possível que existam dependências "
                                "entre componentes."
                            ),
                            "estado_anterior": "provisoria",
                            "estado_teste": "teste_concluido",
                            "conhecimento_permanente": False,
                        },
                    },
                }
            ],
            "conhecimento_permanente": False,
        },
    }


class CicloMemoriaFalso(CicloMemoriaHipoteseNixal):
    def __init__(self, resultado: dict[str, Any]) -> None:
        self._resultado = deepcopy(resultado)
        self.chamadas = 0
        self.resultado_recebido = None

    def registrar_avaliacao(
        self,
        avaliacao: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1
        self.resultado_recebido = deepcopy(
            avaliacao
        )
        return deepcopy(
            self._resultado
        )


def criar_integracao() -> tuple[
    IntegracaoAvaliacaoCicloHipoteseNixal,
    ExecutorAvaliacaoFalso,
    CicloMemoriaFalso,
]:
    executor = ExecutorAvaliacaoFalso(
        resultado_avaliacao_valido()
    )

    ciclo = CicloMemoriaFalso(
        ciclo_valido()
    )

    integracao = IntegracaoAvaliacaoCicloHipoteseNixal(
        executor,
        ciclo,
    )

    return integracao, executor, ciclo


def main() -> None:
    entrada = entrada_valida()
    original = deepcopy(entrada)

    integracao, executor, ciclo_memoria = criar_integracao()

    resultado = integracao.executar(
        entrada
    )

    valor = resultado.get(
        "valor",
        {},
    )

    ciclo_resultado = valor.get(
        "ciclo",
        {},
    )

    check(
        resultado.get("sucesso") is True,
        "1. integração retorna sucesso",
    )

    check(
        resultado.get("estado")
        == "avaliacao_integrada_no_ciclo",
        "2. estado registra avaliação integrada",
    )

    check(
        valor.get("avaliacao_integrada") is True,
        "3. avaliação é marcada como integrada",
    )

    check(
        valor.get("ciclo_atualizado") is True,
        "4. ciclo é marcado como atualizado",
    )

    check(
        valor.get("hipotese_avaliada") is True,
        "5. hipótese permanece marcada como avaliada",
    )

    check(
        valor.get("estado_avaliacao") == "suportada",
        "6. classificação avaliada é preservada",
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
        executor.chamadas == 1,
        "9. executor da avaliação é acionado uma vez",
    )

    check(
        executor.entrada_recebida == original,
        "10. resultado do teste é encaminhado sem alteração",
    )

    check(
        ciclo_memoria.chamadas == 1,
        "11. ciclo-memória registra a avaliação uma vez",
    )

    check(
        ciclo_memoria.resultado_recebido
        == {
            "estado": "suportada",
            "resultado": (
                resultado_avaliacao_valido()
                ["valor"]
            ),
        },
        "12. avaliação é encaminhada ao ciclo",
    )

    check(
        ciclo_resultado.get("estado_atual")
        == "suportada",
        "13. ciclo atualizado alcança o estado suportada",
    )

    check(
        len(
            ciclo_resultado.get("avaliacoes", [])
        )
        == 1,
        "14. ciclo contém um registro de avaliação",
    )

    check(
        ciclo_resultado.get("conhecimento_permanente")
        is False,
        "15. ciclo não promove conhecimento permanente",
    )

    entrada_modificada = deepcopy(entrada)
    entrada_modificada["valor"]["ciclo"]["estado_atual"] = "alterado"

    check(
        valor["ciclo_anterior"]["estado_atual"]
        == "testada",
        "16. ciclo anterior retornado permanece isolado",
    )

    resultado["valor"]["ciclo"]["estado_atual"] = "alterado"

    check(
        ciclo_resultado["estado_atual"] == "alterado",
        "17. cópia do ciclo pode ser modificada sem erro",
    )

    entrada_invalida = deepcopy(original)
    entrada_invalida["estado"] = "hipotese_avaliada"

    resultado_invalido = integracao.executar(
        entrada_invalida
    )

    check(
        resultado_invalido.get("sucesso") is False,
        "18. estado de entrada incorreto é recusado",
    )

    entrada_avaliacao_falha = deepcopy(original)

    integracao_falha = IntegracaoAvaliacaoCicloHipoteseNixal(
        ExecutorAvaliacaoFalso(
            {
                "sucesso": False,
                "estado": "avaliacao_nao_concluida",
                "valor": None,
            }
        ),
        CicloMemoriaFalso(
            ciclo_valido()
        ),
    )

    resultado_falha = integracao_falha.executar(
        entrada_avaliacao_falha
    )

    check(
        resultado_falha.get("sucesso") is False
        and resultado_falha.get("estado")
        == "avaliacao_nao_integrada",
        "19. falha de avaliação não é integrada ao ciclo",
    )

    integracao_estado = IntegracaoAvaliacaoCicloHipoteseNixal(
        ExecutorAvaliacaoFalso(
            {
                "sucesso": True,
                "estado": "avaliacao_nao_concluida",
                "valor": None,
            }
        ),
        CicloMemoriaFalso(
            ciclo_valido()
        ),
    )

    resultado_estado = integracao_estado.executar(
        original
    )

    check(
        resultado_estado.get("sucesso") is True
        and resultado_estado.get("estado")
        == "avaliacao_nao_integrada",
        "20. estado sem avaliação concluída não é integrado",
    )

    entrada_classificacao_invalida = deepcopy(original)

    avaliacao_classificacao_invalida = deepcopy(
        resultado_avaliacao_valido()
    )
    avaliacao_classificacao_invalida["valor"][
        "estado_avaliacao"
    ] = "desconhecida"

    integracao_classificacao = IntegracaoAvaliacaoCicloHipoteseNixal(
        ExecutorAvaliacaoFalso(
            avaliacao_classificacao_invalida
        ),
        CicloMemoriaFalso(
            ciclo_valido()
        ),
    )

    resultado_classificacao = integracao_classificacao.executar(
        entrada_classificacao_invalida
    )

    check(
        resultado_classificacao.get("sucesso") is False,
        "21. classificação desconhecida é recusada",
    )

    entrada_ciclo_errado = deepcopy(original)
    entrada_ciclo_errado[
        "valor"
    ]["ciclo"]["estado_atual"] = "provisoria"

    integracao_ciclo_errado = IntegracaoAvaliacaoCicloHipoteseNixal(
        ExecutorAvaliacaoFalso(
            resultado_avaliacao_valido()
        ),
        CicloMemoriaFalso(
            ciclo_valido()
        ),
    )

    resultado_ciclo_errado = integracao_ciclo_errado.executar(
        entrada_ciclo_errado
    )

    check(
        resultado_ciclo_errado.get("sucesso") is False,
        "22. ciclo que não está testado é recusado",
    )

    entrada_knowledge = deepcopy(original)

    avaliacao_com_knowledge = deepcopy(
        resultado_avaliacao_valido()
    )
    avaliacao_com_knowledge["valor"][
        "conhecimento_permanente"
    ] = True

    integracao_knowledge = IntegracaoAvaliacaoCicloHipoteseNixal(
        ExecutorAvaliacaoFalso(
            avaliacao_com_knowledge
        ),
        CicloMemoriaFalso(
            ciclo_valido()
        ),
    )

    resultado_knowledge = integracao_knowledge.executar(
        entrada_knowledge
    )

    check(
        resultado_knowledge.get("sucesso") is False,
        "23. avaliação que promove conhecimento é recusada",
    )

    try:
        integracao.executar_nova_avaliacao()
        bloqueou_nova_avaliacao = False
    except PermissionError:
        bloqueou_nova_avaliacao = True

    check(
        bloqueou_nova_avaliacao,
        "24. nova avaliação continua bloqueada nesta camada",
    )

    try:
        integracao.promover_conhecimento()
        bloqueou_promocao = False
    except PermissionError:
        bloqueou_promocao = True

    check(
        bloqueou_promocao,
        "25. promoção de conhecimento continua bloqueada",
    )

    try:
        integracao.modificar_arquitetura()
        bloqueou_arquitetura = False
    except PermissionError:
        bloqueou_arquitetura = True

    check(
        bloqueou_arquitetura,
        "26. modificação de arquitetura continua bloqueada",
    )

    try:
        integracao.executar_capacidade()
        bloqueou_capacidade = False
    except PermissionError:
        bloqueou_capacidade = True

    check(
        bloqueou_capacidade,
        "27. execução de capacidades continua bloqueada",
    )

    check(
        entrada == original,
        "28. entrada original permanece inalterada",
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
