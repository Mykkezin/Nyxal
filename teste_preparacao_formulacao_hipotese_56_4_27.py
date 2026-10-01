#!/usr/bin/env python3

"""
NIXAL — TESTE DA PREPARAÇÃO PARA FORMULAÇÃO DE HIPÓTESE

Microetapa 56.4.27
"""

from __future__ import annotations

from copy import deepcopy

from nixal_preparacao_formulacao_hipotese import (
    PreparacaoFormulacaoHipoteseNixal,
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

    preparacao = PreparacaoFormulacaoHipoteseNixal()

    investigacao = {
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
        "contexto_historico_relevante": [],
        "historico_consultado": True,
        "historico_encontrado": False,
    }

    consolidacao = {
        "sucesso": True,
        "estado": "evidencias_consolidadas",
        "origem": "consolidacao_evidencias_nixal",
        "valor": {
            "evidencia_consolidada": True,
            "evidencias": [
                {
                    "fonte": "listar_arquivos",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "resultado": [
                        "planta_nixal",
                        "nixal_composicao.py",
                    ],
                    "indice_consolidacao": 1,
                },
                {
                    "fonte": "ler_arquivo",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "resultado": (
                        "conteúdo estrutural observado"
                    ),
                    "indice_consolidacao": 2,
                },
            ],
            "quantidade_evidencias": 2,
            "conhecimento_permanente": False,
        },
    }

    investigacao_antes = deepcopy(
        investigacao
    )
    consolidacao_antes = deepcopy(
        consolidacao
    )

    resultado = preparacao.preparar(
        investigacao,
        consolidacao,
    )

    erro, total = verificar(
        1,
        "preparação retorna sucesso",
        lambda: assert_true(
            resultado.get("sucesso") is True,
            "preparação falhou",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        2,
        "estado indica entrada preparada",
        lambda: assert_true(
            resultado.get("estado")
            == "entrada_formulacao_preparada",
            "estado incorreto",
        ),
    )
    falhas += erro
    testes += total

    valor = resultado.get(
        "valor",
        {}
    )

    entrada = valor.get(
        "entrada_formulacao",
        {}
    )

    erro, total = verificar(
        3,
        "entrada preserva a necessidade",
        lambda: assert_true(
            entrada["necessidade"]
            == investigacao["necessidade"],
            "necessidade não preservada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        4,
        "entrada preserva a pergunta",
        lambda: assert_true(
            entrada["pergunta"]
            == investigacao["pergunta"],
            "pergunta não preservada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        5,
        "entrada preserva o tipo da investigação",
        lambda: assert_true(
            entrada["tipo_investigacao"]
            == investigacao["tipo_investigacao"],
            "tipo não preservado",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        6,
        "entrada segue o contrato da formulação de hipóteses",
        lambda: assert_true(
            isinstance(
                entrada.get("valor"),
                dict,
            )
            and isinstance(
                entrada["valor"].get(
                    "evidencias"
                ),
                list,
            ),
            "estrutura da entrada não segue o contrato esperado",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        7,
        "duas evidências consolidadas são encaminhadas",
        lambda: assert_true(
            len(
                entrada["valor"]["evidencias"]
            )
            == 2,
            "evidências não foram encaminhadas",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        8,
        "fontes das evidências são preservadas",
        lambda: assert_true(
            [
                evidencia["fonte"]
                for evidencia
                in entrada["valor"]["evidencias"]
            ]
            == [
                "listar_arquivos",
                "ler_arquivo",
            ],
            "fontes foram alteradas",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        9,
        "origem da evidência é explicitamente consolidada",
        lambda: assert_true(
            entrada["valor"][
                "origem_evidencias"
            ]
            == "consolidacao_evidencias_nixal",
            "origem incorreta",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        10,
        "hipótese ainda não foi formulada",
        lambda: assert_true(
            valor[
                "hipotese_formulada"
            ]
            is False,
            "hipótese foi formulada indevidamente",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        11,
        "hipótese pode ser formulada na próxima camada",
        lambda: assert_true(
            valor[
                "pode_formular_hipotese"
            ]
            is True,
            "ponte não liberou a próxima camada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        12,
        "conhecimento permanente continua falso",
        lambda: assert_true(
            valor[
                "conhecimento_permanente"
            ]
            is False,
            "conhecimento permanente foi marcado",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        13,
        "histórico continua separado da verdade",
        lambda: assert_true(
            entrada[
                "historico_nao_equivale_a_verdade"
            ]
            is True,
            "separação histórica foi perdida",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        14,
        "evidências não são tratadas como conhecimento permanente",
        lambda: assert_true(
            entrada[
                "evidencias_nao_equivalem_a_conhecimento_permanente"
            ]
            is True,
            "separação epistemológica foi perdida",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        15,
        "investigação de entrada permanece inalterada",
        lambda: assert_true(
            investigacao
            == investigacao_antes,
            "investigação foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        16,
        "consolidação de entrada permanece inalterada",
        lambda: assert_true(
            consolidacao
            == consolidacao_antes,
            "consolidação foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        17,
        "resultado retornado é isolado",
        lambda: (
            lambda dados: (
                dados["valor"][
                    "entrada_formulacao"
                ]["valor"]["evidencias"][0].update(
                    {
                        "alterado": True
                    }
                ),
                assert_true(
                    "alterado"
                    not in preparacao.preparar(
                        investigacao,
                        consolidacao,
                    )["valor"][
                        "entrada_formulacao"
                    ]["valor"]["evidencias"][0],
                    "referência interna vazou",
                ),
            )
        )(
            preparacao.preparar(
                investigacao,
                consolidacao,
            )
        ),
    )
    falhas += erro
    testes += total

    consolidacao_nao_consolidada = deepcopy(
        consolidacao
    )
    consolidacao_nao_consolidada[
        "estado"
    ] = "sem_evidencia_consolidada"

    erro, total = verificar(
        18,
        "consolidação não consolidada é recusada",
        lambda: assert_true(
            preparacao.preparar(
                investigacao,
                consolidacao_nao_consolidada,
            )["sucesso"]
            is False,
            "consolidação inadequada foi aceita",
        ),
    )
    falhas += erro
    testes += total

    consolidacao_sem_evidencias = deepcopy(
        consolidacao
    )
    consolidacao_sem_evidencias[
        "valor"
    ]["evidencias"] = []

    erro, total = verificar(
        19,
        "ausência de evidências é recusada",
        lambda: assert_true(
            preparacao.preparar(
                investigacao,
                consolidacao_sem_evidencias,
            )["sucesso"]
            is False,
            "ausência de evidências foi aceita",
        ),
    )
    falhas += erro
    testes += total

    investigacao_sem_pergunta = deepcopy(
        investigacao
    )
    investigacao_sem_pergunta[
        "pergunta"
    ] = ""

    erro, total = verificar(
        20,
        "pergunta ausente é recusada",
        lambda: assert_true(
            preparacao.preparar(
                investigacao_sem_pergunta,
                consolidacao,
            )["sucesso"]
            is False,
            "pergunta ausente foi aceita",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        21,
        "hipótese permanece bloqueada nesta camada",
        lambda: esperar_erro(
            preparacao.formular_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        22,
        "avaliação de hipótese permanece bloqueada",
        lambda: esperar_erro(
            preparacao.avaliar_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        23,
        "capacidades permanecem bloqueadas",
        lambda: esperar_erro(
            lambda: preparacao.executar_capacidade(
                "ler_arquivo"
            ),
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        24,
        "arquitetura permanece protegida",
        lambda: esperar_erro(
            lambda: preparacao.modificar_arquitetura(
                "planta_nixal"
            ),
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        25,
        "conhecimento permanente permanece bloqueado",
        lambda: esperar_erro(
            preparacao.promover_conhecimento,
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
