#!/usr/bin/env python3

"""
NIXAL — TESTE DA EXECUÇÃO CONTROLADA DA FORMULAÇÃO DE HIPÓTESE

Microetapa 56.4.28
"""

from __future__ import annotations

from copy import deepcopy

from nixal_execucao_formulacao_hipotese import (
    ExecucaoFormulacaoHipoteseNixal,
)


class FormuladorFalso:
    """Formulador determinístico para testar a camada de controle."""

    def __init__(
        self,
        resultado: dict,
    ) -> None:
        self.resultado = deepcopy(
            resultado
        )
        self.chamadas: list[dict] = []

    def formular(
        self,
        investigacao: dict,
    ) -> dict:
        self.chamadas.append(
            deepcopy(
                investigacao
            )
        )
        return deepcopy(
            self.resultado
        )


def assert_true(
    condicao: bool,
    mensagem: str,
) -> None:
    if not condicao:
        raise AssertionError(
            mensagem
        )


def verificar(
    numero: int,
    descricao: str,
    funcao,
) -> tuple[int, int]:
    try:
        funcao()
        print(
            f"[PASS] {numero}. {descricao}"
        )
        return 0, 1
    except Exception as erro:
        print(
            f"[FAIL] {numero}. {descricao}: {erro}"
        )
        return 1, 1


def esperar_erro(
    funcao,
    tipo_erro,
) -> None:
    try:
        funcao()
    except tipo_erro:
        return

    raise AssertionError(
        f"era esperado {tipo_erro.__name__}"
    )


def executar() -> None:
    falhas = 0
    testes = 0

    resultado_formulador = {
        "sucesso": True,
        "estado": "hipotese_provisoria",
        "origem": "formulacao_hipoteses_nixal",
        "valor": {
            "hipotese": (
                "É possível que existam dependências entre "
                "os componentes ainda não registradas."
            ),
            "necessidade": (
                "conhecer_dependencias_arquiteturais"
            ),
            "pergunta": (
                "Quais relações de dependência existem "
                "entre os componentes?"
            ),
            "estado": "provisoria",
            "tipo": "explicacao_candidata",
            "razao": (
                "Interpretação provisória das evidências."
            ),
            "evidencias_de_suporte": [
                {
                    "id": "evidencia_1",
                    "fonte": "ler_arquivo",
                }
            ],
            "evidencias_contrarias_conhecidas": [],
            "contrarias_avaliadas": False,
            "confianca": "indeterminada",
            "confirmada": False,
            "testada": False,
        },
    }

    formulador = FormuladorFalso(
        resultado_formulador
    )

    executor = ExecucaoFormulacaoHipoteseNixal(
        formulador=formulador
    )

    entrada = {
        "sucesso": True,
        "estado": "entrada_formulacao_preparada",
        "origem": "preparacao_formulacao_hipotese_nixal",
        "valor": {
            "entrada_formulacao": {
                "necessidade": (
                    "conhecer_dependencias_arquiteturais"
                ),
                "pergunta": (
                    "Quais relações de dependência existem "
                    "entre os componentes?"
                ),
                "tipo_investigacao": (
                    "mapeamento_arquitetural"
                ),
                "valor": {
                    "evidencias": [
                        {
                            "fonte": "ler_arquivo",
                            "sucesso": True,
                            "estado": "evidencia_disponivel",
                            "argumentos": {
                                "arquivo": "corpo_nixal.py"
                            },
                        }
                    ]
                },
            },
            "pode_formular_hipotese": True,
            "hipotese_formulada": False,
            "hipotese_avaliada": False,
            "conhecimento_permanente": False,
        },
    }

    entrada_antes = deepcopy(
        entrada
    )

    resultado = executor.executar(
        entrada
    )

    erro, total = verificar(
        1,
        "execução retorna sucesso",
        lambda: assert_true(
            resultado.get("sucesso") is True,
            "execução não retornou sucesso",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        2,
        "estado registra hipótese provisória criada",
        lambda: assert_true(
            resultado.get("estado")
            == "hipotese_provisoria_criada",
            "estado incorreto",
        ),
    )
    falhas += erro
    testes += total

    valor = resultado.get(
        "valor",
        {}
    )

    erro, total = verificar(
        3,
        "hipótese é marcada como formulada",
        lambda: assert_true(
            valor[
                "hipotese_formulada"
            ] is True,
            "hipótese não foi marcada como formulada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        4,
        "hipótese permanece provisória",
        lambda: assert_true(
            valor["hipotese"][
                "estado"
            ] == "provisoria",
            "hipótese deixou de ser provisória",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        5,
        "hipótese não é marcada como confirmada",
        lambda: assert_true(
            valor["hipotese"][
                "confirmada"
            ] is False,
            "hipótese foi marcada como confirmada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        6,
        "hipótese ainda não foi testada",
        lambda: assert_true(
            valor["hipotese"][
                "testada"
            ] is False,
            "hipótese foi marcada como testada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        7,
        "hipótese ainda não foi avaliada",
        lambda: assert_true(
            valor[
                "hipotese_avaliada"
            ] is False,
            "hipótese foi marcada como avaliada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        8,
        "conhecimento permanente continua falso",
        lambda: assert_true(
            valor[
                "conhecimento_permanente"
            ] is False,
            "conhecimento permanente foi promovido",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        9,
        "arquitetura permanece sem modificação",
        lambda: assert_true(
            valor[
                "arquitetura_modificada"
            ] is False,
            "arquitetura foi modificada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        10,
        "entrada é encaminhada sem perder pergunta",
        lambda: assert_true(
            formulador.chamadas[0][
                "pergunta"
            ]
            == entrada["valor"][
                "entrada_formulacao"
            ]["pergunta"],
            "pergunta não foi encaminhada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        11,
        "entrada é encaminhada sem perder evidências",
        lambda: assert_true(
            len(
                formulador.chamadas[0][
                    "valor"
                ]["evidencias"]
            )
            == 1,
            "evidências não foram encaminhadas",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        12,
        "entrada de formulação permanece inalterada",
        lambda: assert_true(
            entrada
            == entrada_antes,
            "entrada foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        13,
        "hipótese retornada é uma cópia isolada",
        lambda: (
            lambda dados: (
                dados["valor"]["hipotese"].update(
                    {
                        "alterado": True
                    }
                ),
                assert_true(
                    "alterado"
                    not in executor.executar(
                        entrada
                    )["valor"]["hipotese"],
                    "referência interna vazou",
                ),
            )
        )(
            executor.executar(
                entrada
            )
        ),
    )
    falhas += erro
    testes += total

    resultado_falha = {
        "sucesso": False,
        "estado": "desconhecido",
        "origem": "formulacao_hipoteses_nixal",
        "valor": None,
        "motivo": "sem evidência suficiente",
    }

    executor_falha = ExecucaoFormulacaoHipoteseNixal(
        formulador=FormuladorFalso(
            resultado_falha
        )
    )

    erro, total = verificar(
        14,
        "resultado sem hipótese não é promovido artificialmente",
        lambda: assert_true(
            executor_falha.executar(
                entrada
            )["sucesso"]
            is False,
            "falha foi mascarada",
        ),
    )
    falhas += erro
    testes += total

    resultado_desconhecido = {
        "sucesso": True,
        "estado": "desconhecido",
        "origem": "formulacao_hipoteses_nixal",
        "valor": None,
        "motivo": (
            "Não existem evidências suficientes para formular "
            "uma hipótese."
        ),
    }

    executor_desconhecido = ExecucaoFormulacaoHipoteseNixal(
        formulador=FormuladorFalso(
            resultado_desconhecido
        )
    )

    erro, total = verificar(
        15,
        "estado desconhecido não vira hipótese provisória",
        lambda: assert_true(
            executor_desconhecido.executar(
                entrada
            )["estado"]
            == "formulacao_nao_concluida",
            "estado desconhecido foi promovido",
        ),
    )
    falhas += erro
    testes += total

    entrada_estado_incorreto = deepcopy(
        entrada
    )
    entrada_estado_incorreto[
        "estado"
    ] = "sem_evidencia_consolidada"

    erro, total = verificar(
        16,
        "estado de entrada incorreto é recusado",
        lambda: assert_true(
            executor.executar(
                entrada_estado_incorreto
            )["sucesso"]
            is False,
            "estado incorreto foi aceito",
        ),
    )
    falhas += erro
    testes += total

    entrada_sem_permissao = deepcopy(
        entrada
    )
    entrada_sem_permissao[
        "valor"
    ]["pode_formular_hipotese"] = False

    erro, total = verificar(
        17,
        "entrada sem permissão explícita é recusada",
        lambda: assert_true(
            executor.executar(
                entrada_sem_permissao
            )["sucesso"]
            is False,
            "permissão ausente foi ignorada",
        ),
    )
    falhas += erro
    testes += total

    entrada_sem_formulacao = deepcopy(
        entrada
    )
    entrada_sem_formulacao[
        "valor"
    ].pop(
        "entrada_formulacao"
    )

    erro, total = verificar(
        18,
        "entrada interna ausente é recusada",
        lambda: assert_true(
            executor.executar(
                entrada_sem_formulacao
            )["sucesso"]
            is False,
            "entrada interna ausente foi aceita",
        ),
    )
    falhas += erro
    testes += total

    resultado_hipotese_invalida = {
        "sucesso": True,
        "estado": "hipotese_provisoria",
        "origem": "formulacao_hipoteses_nixal",
        "valor": {
            "hipotese": "hipótese",
            "estado": "confirmada",
            "confirmada": True,
            "testada": False,
        },
    }

    executor_hipotese_invalida = ExecucaoFormulacaoHipoteseNixal(
        formulador=FormuladorFalso(
            resultado_hipotese_invalida
        )
    )

    erro, total = verificar(
        19,
        "hipótese não provisória é recusada",
        lambda: assert_true(
            executor_hipotese_invalida.executar(
                entrada
            )["sucesso"]
            is False,
            "hipótese inválida foi aceita",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        20,
        "avaliação continua bloqueada nesta camada",
        lambda: esperar_erro(
            executor.avaliar_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        21,
        "teste continua bloqueado nesta camada",
        lambda: esperar_erro(
            executor.testar_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        22,
        "promoção de conhecimento continua bloqueada",
        lambda: esperar_erro(
            executor.promover_conhecimento,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        23,
        "modificação de arquitetura continua bloqueada",
        lambda: esperar_erro(
            executor.modificar_arquitetura,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        24,
        "execução de capacidades continua bloqueada",
        lambda: esperar_erro(
            executor.executar_capacidade,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    print("\n" + "=" * 64)
    print(
        f"TESTES EXECUTADOS: {testes}"
    )
    print(
        f"FALHAS: {falhas}"
    )
    print(
        f"PASSOU: {falhas == 0}"
    )
    print("=" * 64)

    if falhas != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    executar()
