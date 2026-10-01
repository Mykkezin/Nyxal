#!/usr/bin/env python3

"""
NIXAL — TESTE DA INTEGRAÇÃO DO RESULTADO DO TESTE AO CICLO

Microetapa 56.4.32
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_execucao_teste_hipotese import (
    ExecucaoTesteHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_integracao_teste_ciclo_hipotese import (
    IntegracaoTesteCicloHipoteseNixal,
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


def entrada_preparada_valida() -> dict[str, Any]:
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
                    "necessidade": "conhecer_dependencias_arquiteturais",
                    "pergunta": "Quais relações de dependência existem?",
                    "estado": "provisoria",
                    "confirmada": False,
                    "testada": False,
                },
                "necessidade": "conhecer_dependencias_arquiteturais",
                "pergunta": "Quais relações de dependência existem?",
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
            "ciclo": {
                "hipotese": (
                    "É possível que existam dependências entre componentes."
                ),
                "necessidade": "conhecer_dependencias_arquiteturais",
                "pergunta": "Quais relações de dependência existem?",
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
            "teste_preparado": True,
            "teste_executado": False,
            "resultado_teste_disponivel": False,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


def resultado_teste_valido() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "teste_concluido",
        "origem": "execucao_teste_hipotese_nixal",
        "valor": {
            "entrada_preparada": {},
            "entrada_teste": {},
            "resultado_teste": {
                "estado": "observacao_realizada",
                "evidencias": [
                    {
                        "fonte": "teste_deterministico",
                        "descricao": "Uma relação foi observada.",
                    }
                ],
            },
            "registro_teste": {
                "estado": "teste_concluido",
                "resultado": {
                    "estado": "observacao_realizada",
                    "evidencias": [
                        {
                            "fonte": "teste_deterministico",
                            "descricao": "Uma relação foi observada.",
                        }
                    ],
                },
            },
            "teste_preparado": True,
            "teste_executado": True,
            "resultado_teste_disponivel": True,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


class ExecutorTesteFalso(ExecucaoTesteHipoteseNixal):
    def __init__(
        self,
        resultado: dict[str, Any],
    ) -> None:
        self._resultado = deepcopy(
            resultado
        )
        self.chamadas = 0
        self.entrada_recebida = None

    def executar(
        self,
        entrada_preparada: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1
        self.entrada_recebida = deepcopy(
            entrada_preparada
        )
        return deepcopy(
            self._resultado
        )


class CicloMemoriaFalso(CicloMemoriaHipoteseNixal):
    def __init__(
        self,
        resultado: dict[str, Any],
        ciclo_atual: dict[str, Any],
    ) -> None:
        self._resultado = deepcopy(
            resultado
        )
        self._ciclo_atual = deepcopy(
            ciclo_atual
        )
        self.chamadas = 0
        self.resultado_recebido = None

    def obter_ciclo(
        self,
    ) -> dict[str, Any] | None:
        return deepcopy(
            self._ciclo_atual
        )

    def registrar_teste(
        self,
        resultado_teste: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1
        self.resultado_recebido = deepcopy(
            resultado_teste
        )
        return deepcopy(
            self._resultado
        )


def ciclo_valido() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "testada",
        "origem": "ciclo_memoria_hipotese_nixal",
        "valor": {
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
    }


def criar_integracao() -> tuple[
    IntegracaoTesteCicloHipoteseNixal,
    ExecutorTesteFalso,
    CicloMemoriaFalso,
]:
    executor = ExecutorTesteFalso(
        resultado_teste_valido()
    )

    ciclo = CicloMemoriaFalso(
        ciclo_valido(),
        entrada_preparada_valida()["valor"]["ciclo"],
    )

    integracao = IntegracaoTesteCicloHipoteseNixal(
        executor,
        ciclo,
    )

    return integracao, executor, ciclo


def main() -> None:
    entrada = entrada_preparada_valida()
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
        == "teste_integrado_no_ciclo",
        "2. estado registra integração do teste no ciclo",
    )

    check(
        valor.get("teste_executado") is True,
        "3. teste permanece marcado como executado",
    )

    check(
        valor.get("teste_integrado") is True,
        "4. teste é marcado como integrado",
    )

    check(
        valor.get("ciclo_atualizado") is True,
        "5. ciclo é marcado como atualizado",
    )

    check(
        valor.get("hipotese_testada") is True,
        "6. hipótese passa a ser marcada como testada",
    )

    check(
        valor.get("hipotese_avaliada") is False,
        "7. hipótese ainda não foi avaliada",
    )

    check(
        valor.get("conhecimento_permanente") is False,
        "8. conhecimento permanente continua falso",
    )

    check(
        valor.get("arquitetura_modificada") is False,
        "9. arquitetura permanece sem modificação",
    )

    check(
        executor.chamadas == 1,
        "10. executor do teste é acionado uma vez",
    )

    check(
        ciclo_memoria.chamadas == 1,
        "11. ciclo-memória registra o teste uma vez",
    )

    check(
        ciclo_memoria.resultado_recebido
        == {
            "estado": "teste_concluido",
            "resultado": resultado_teste_valido()["valor"]["resultado_teste"],
        },
        "12. resultado observado é encaminhado sem classificação",
    )

    check(
        ciclo_resultado.get("estado_atual")
        == "testada",
        "13. ciclo atualizado fica no estado testada",
    )

    check(
        len(
            ciclo_resultado.get("testes", [])
        )
        == 1,
        "14. ciclo contém um registro de teste",
    )

    check(
        ciclo_resultado.get("avaliacoes")
        == [],
        "15. nenhuma avaliação é criada nesta camada",
    )

    check(
        ciclo_resultado.get("conhecimento_permanente")
        is False,
        "16. ciclo não promove conhecimento permanente",
    )

    entrada["valor"]["ciclo"]["estado_atual"] = "alterado"

    check(
        valor["ciclo_anterior"]["estado_atual"]
        == "provisoria",
        "17. ciclo anterior retornado permanece isolado",
    )

    resultado["valor"]["ciclo"]["estado_atual"] = "alterado"

    check(
        ciclo_resultado["estado_atual"] == "alterado",
        "18. cópia do ciclo pode ser modificada sem erro",
    )

    check(
        executor.entrada_recebida == original,
        "19. entrada encaminhada ao executor permanece isolada",
    )

    check(
        entrada == {
            **original,
            "valor": {
                **original["valor"],
                "ciclo": {
                    **original["valor"]["ciclo"],
                    "estado_atual": "alterado",
                },
            },
        },
        "20. mutação local da entrada do teste não afeta outras cópias",
    )

    entrada_invalida = deepcopy(original)
    entrada_invalida["estado"] = "teste_concluido"

    resultado_invalido = integracao.executar(
        entrada_invalida
    )

    check(
        resultado_invalido.get("sucesso") is False,
        "21. estado de entrada incorreto é recusado",
    )

    integracao_falha = IntegracaoTesteCicloHipoteseNixal(
        ExecutorTesteFalso(
            {
                "sucesso": False,
                "estado": "teste_nao_concluido",
                "valor": None,
            }
        ),
        CicloMemoriaFalso(
            ciclo_valido(),
            original["valor"]["ciclo"],
        ),
    )

    resultado_falha = integracao_falha.executar(
        deepcopy(original)
    )

    check(
        resultado_falha.get("sucesso") is False
        and resultado_falha.get("estado")
        == "teste_nao_integrado",
        "22. falha de execução não é integrada ao ciclo",
    )

    integracao_estado = IntegracaoTesteCicloHipoteseNixal(
        ExecutorTesteFalso(
            {
                "sucesso": True,
                "estado": "observacao_realizada",
                "valor": {},
            }
        ),
        CicloMemoriaFalso(
            ciclo_valido(),
            original["valor"]["ciclo"],
        ),
    )

    resultado_estado = integracao_estado.executar(
        deepcopy(original)
    )

    check(
        resultado_estado.get("sucesso") is True
        and resultado_estado.get("estado")
        == "teste_nao_integrado",
        "23. estado sem teste concluído não é integrado",
    )

    ciclo_divergente = deepcopy(
        original["valor"]["ciclo"]
    )
    ciclo_divergente["hipotese"] = "ciclo diferente"

    integracao_divergente = IntegracaoTesteCicloHipoteseNixal(
        ExecutorTesteFalso(
            resultado_teste_valido()
        ),
        CicloMemoriaFalso(
            ciclo_valido(),
            ciclo_divergente,
        ),
    )

    resultado_divergente = integracao_divergente.executar(
        deepcopy(original)
    )

    check(
        resultado_divergente.get("sucesso") is False,
        "24. ciclo divergente do ciclo interno é recusado",
    )

    integracao_knowledge = IntegracaoTesteCicloHipoteseNixal(
        ExecutorTesteFalso(
            resultado_teste_valido()
        ),
        CicloMemoriaFalso(
            {
                "sucesso": True,
                "estado": "testada",
                "origem": "ciclo_memoria_hipotese_nixal",
                "valor": {
                    **ciclo_valido()["valor"],
                    "conhecimento_permanente": True,
                },
            },
            {
                **original["valor"]["ciclo"],
            },
        ),
    )

    resultado_knowledge = integracao_knowledge.executar(
        deepcopy(original)
    )

    check(
        resultado_knowledge.get("sucesso") is False,
        "25. ciclo atualizado com conhecimento permanente é recusado",
    )

    try:
        integracao.avaliar_hipotese()
        bloqueou_avaliacao = False
    except PermissionError:
        bloqueou_avaliacao = True

    check(
        bloqueou_avaliacao,
        "26. avaliação continua bloqueada nesta camada",
    )

    try:
        integracao.promover_conhecimento()
        bloqueou_promocao = False
    except PermissionError:
        bloqueou_promocao = True

    check(
        bloqueou_promocao,
        "27. promoção de conhecimento continua bloqueada",
    )

    try:
        integracao.modificar_arquitetura()
        bloqueou_arquitetura = False
    except PermissionError:
        bloqueou_arquitetura = True

    check(
        bloqueou_arquitetura,
        "28. modificação de arquitetura continua bloqueada",
    )

    try:
        integracao.executar_capacidade()
        bloqueou_capacidade = False
    except PermissionError:
        bloqueou_capacidade = True

    check(
        bloqueou_capacidade,
        "29. execução de capacidades continua bloqueada",
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
