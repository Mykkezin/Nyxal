#!/usr/bin/env python3

"""
NIXAL — TESTE DA INTEGRAÇÃO FORMULAÇÃO → CICLO

Microetapa 56.4.29

Valida:
    - encaminhamento da saída da 56.4.28;
    - início do ciclo em "provisoria";
    - isolamento das entradas;
    - persistência coordenada pelo ciclo-memória;
    - ausência de teste/avaliação/promoção;
    - recusa de entradas inválidas.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_execucao_formulacao_hipotese import (
    ExecucaoFormulacaoHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_integracao_formulacao_ciclo_hipotese import (
    IntegracaoFormulacaoCicloHipoteseNixal,
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


class ExecutorFalso(ExecucaoFormulacaoHipoteseNixal):
    def __init__(self, resultado: dict[str, Any]) -> None:
        self._resultado = deepcopy(resultado)
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
    ) -> None:
        self._resultado = deepcopy(resultado)
        self.chamadas = 0
        self.hipotese_recebida = None

    def iniciar(
        self,
        hipotese: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1
        self.hipotese_recebida = deepcopy(
            hipotese
        )
        return deepcopy(
            self._resultado
        )


def resultado_formulacao_valido() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "hipotese_provisoria_criada",
        "origem": "execucao_formulacao_hipotese_nixal",
        "valor": {
            "entrada_preparada": {
                "sucesso": True,
                "estado": "entrada_formulacao_preparada",
            },
            "hipotese": {
                "hipotese": (
                    "É possível que existam dependências entre componentes."
                ),
                "necessidade": "conhecer_dependencias_arquiteturais",
                "pergunta": (
                    "Quais relações de dependência existem?"
                ),
                "estado": "provisoria",
                "confirmada": False,
                "testada": False,
                "evidencias_de_suporte": [
                    {
                        "id": "evidencia_1",
                        "fonte": "ler_arquivo",
                    }
                ],
            },
            "hipotese_formulada": True,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


def ciclo_valido() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "provisoria",
        "origem": "ciclo_memoria_hipotese_nixal",
        "valor": {
            "hipotese": (
                "É possível que existam dependências entre componentes."
            ),
            "necessidade": "conhecer_dependencias_arquiteturais",
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
        "persistencia": {
            "sucesso": True,
            "estado": "persistido",
        },
    }


def criar_integracao() -> tuple[
    IntegracaoFormulacaoCicloHipoteseNixal,
    ExecutorFalso,
    CicloMemoriaFalso,
]:
    executor = ExecutorFalso(
        resultado_formulacao_valido()
    )

    ciclo_memoria = CicloMemoriaFalso(
        ciclo_valido()
    )

    integracao = IntegracaoFormulacaoCicloHipoteseNixal(
        executor,
        ciclo_memoria,
    )

    return (
        integracao,
        executor,
        ciclo_memoria,
    )


def main() -> None:
    entrada = {
        "sucesso": True,
        "estado": "entrada_formulacao_preparada",
        "valor": {
            "entrada_formulacao": {
                "necessidade": "conhecer_dependencias_arquiteturais",
                "pergunta": (
                    "Quais relações de dependência existem?"
                ),
                "valor": {
                    "evidencias": [
                        {
                            "fonte": "ler_arquivo",
                            "sucesso": True,
                            "estado": "evidencia_disponivel",
                        }
                    ]
                },
            }
        },
    }

    entrada_original = deepcopy(
        entrada
    )

    (
        integracao,
        executor,
        ciclo_memoria,
    ) = criar_integracao()

    resultado = integracao.executar(
        entrada
    )

    check(
        resultado.get("sucesso") is True,
        "1. integração retorna sucesso",
    )

    check(
        resultado.get("estado")
        == "hipotese_integrada_no_ciclo",
        "2. estado registra integração no ciclo",
    )

    valor = resultado.get("valor", {})

    check(
        valor.get("hipotese_formulada") is True,
        "3. hipótese permanece marcada como formulada",
    )

    check(
        valor.get("ciclo_iniciado") is True,
        "4. ciclo é iniciado",
    )

    check(
        valor.get("hipotese_integrada") is True,
        "5. hipótese é marcada como integrada",
    )

    check(
        valor.get("hipotese_testada") is False,
        "6. hipótese ainda não foi testada",
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
        "10. execução da formulação ocorre uma vez",
    )

    check(
        ciclo_memoria.chamadas == 1,
        "11. ciclo-memória recebe uma vez a hipótese",
    )

    check(
        executor.entrada_recebida == entrada_original,
        "12. entrada é encaminhada sem alteração",
    )

    check(
        ciclo_memoria.hipotese_recebida
        == valor.get("hipotese"),
        "13. hipótese formulada é encaminhada ao ciclo",
    )

    ciclo = valor.get(
        "ciclo",
        {},
    )

    check(
        ciclo.get("estado_atual") == "provisoria",
        "14. ciclo inicia no estado provisório",
    )

    check(
        ciclo.get("conhecimento_permanente") is False,
        "15. ciclo não promove conhecimento permanente",
    )

    entrada["valor"]["entrada_formulacao"]["pergunta"] = "alterada"

    check(
        valor["entrada_preparada"]
        == entrada_original,
        "16. resultado mantém cópia isolada da entrada",
    )

    entrada_invalida = deepcopy(
        entrada_original
    )
    entrada_invalida["estado"] = "hipotese_provisoria_criada"

    resultado_invalido = integracao.executar(
        entrada_invalida
    )

    check(
        resultado_invalido.get("sucesso") is False,
        "17. estado de entrada incorreto é recusado",
    )

    resultado_formulacao_desconhecida = {
        "sucesso": True,
        "estado": "desconhecido",
        "origem": "execucao_formulacao_hipotese_nixal",
        "valor": None,
    }

    integracao_desconhecida = IntegracaoFormulacaoCicloHipoteseNixal(
        ExecutorFalso(
            resultado_formulacao_desconhecida
        ),
        CicloMemoriaFalso(
            ciclo_valido()
        ),
    )

    resultado_desconhecido = (
        integracao_desconhecida.executar(
            entrada_original
        )
    )

    check(
        resultado_desconhecido.get("sucesso") is True
        and resultado_desconhecido.get("estado")
        == "formulacao_nao_integrada",
        "18. estado desconhecido não inicia ciclo",
    )

    integracao_falha = IntegracaoFormulacaoCicloHipoteseNixal(
        ExecutorFalso(
            {
                "sucesso": False,
                "estado": "falha_formulacao",
                "valor": None,
            }
        ),
        CicloMemoriaFalso(
            ciclo_valido()
        ),
    )

    resultado_falha = integracao_falha.executar(
        entrada_original
    )

    check(
        resultado_falha.get("sucesso") is False
        and resultado_falha.get("estado")
        == "formulacao_nao_integrada",
        "19. falha de formulação não inicia ciclo",
    )

    hipotese_invalida = resultado_formulacao_valido()
    hipotese_invalida["valor"]["hipotese"]["estado"] = "testada"

    integracao_hipotese_invalida = (
        IntegracaoFormulacaoCicloHipoteseNixal(
            ExecutorFalso(
                hipotese_invalida
            ),
            CicloMemoriaFalso(
                ciclo_valido()
            ),
        )
    )

    resultado_hipotese_invalida = (
        integracao_hipotese_invalida.executar(
            entrada_original
        )
    )

    check(
        resultado_hipotese_invalida.get("sucesso") is False,
        "20. hipótese não provisória é recusada",
    )

    ciclo_final_invalido = ciclo_valido()
    ciclo_final_invalido["valor"]["estado_atual"] = "suportada"

    integracao_ciclo_invalido = (
        IntegracaoFormulacaoCicloHipoteseNixal(
            ExecutorFalso(
                resultado_formulacao_valido()
            ),
            CicloMemoriaFalso(
                ciclo_final_invalido
            ),
        )
    )

    resultado_ciclo_invalido = (
        integracao_ciclo_invalido.executar(
            entrada_original
        )
    )

    check(
        resultado_ciclo_invalido.get("sucesso") is False,
        "21. ciclo que não inicia como provisório é recusado",
    )

    try:
        integracao.testar_hipotese()
        bloqueou_teste = False
    except PermissionError:
        bloqueou_teste = True

    check(
        bloqueou_teste,
        "22. teste continua bloqueado nesta camada",
    )

    try:
        integracao.avaliar_hipotese()
        bloqueou_avaliacao = False
    except PermissionError:
        bloqueou_avaliacao = True

    check(
        bloqueou_avaliacao,
        "23. avaliação continua bloqueada nesta camada",
    )

    try:
        integracao.promover_conhecimento()
        bloqueou_promocao = False
    except PermissionError:
        bloqueou_promocao = True

    check(
        bloqueou_promocao,
        "24. promoção de conhecimento continua bloqueada",
    )

    try:
        integracao.modificar_arquitetura()
        bloqueou_arquitetura = False
    except PermissionError:
        bloqueou_arquitetura = True

    check(
        bloqueou_arquitetura,
        "25. modificação de arquitetura continua bloqueada",
    )

    try:
        integracao.executar_capacidade()
        bloqueou_capacidade = False
    except PermissionError:
        bloqueou_capacidade = True

    check(
        bloqueou_capacidade,
        "26. execução de capacidades continua bloqueada",
    )

    print()
    print("=" * 64)
    print(
        "TESTES EXECUTADOS:",
        TOTAL,
    )
    print(
        "FALHAS:",
        FALHAS,
    )
    print(
        "PASSOU:",
        FALHAS == 0,
    )
    print("=" * 64)


if __name__ == "__main__":
    main()
