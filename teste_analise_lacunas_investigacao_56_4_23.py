#!/usr/bin/env python3

"""
NIXAL — TESTE DA ANÁLISE DE LACUNAS DA INVESTIGAÇÃO

Microetapa 56.4.23
"""

from __future__ import annotations

import copy


from nixal_analise_lacunas_investigacao import (
    AnaliseLacunasInvestigacaoNixal,
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

    analise = AnaliseLacunasInvestigacaoNixal()

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
        "evidencia_necessaria": (
            "Relações explicitamente observadas "
            "ou declaradas entre componentes."
        ),
        "contexto_historico_relevante": [
            {
                "origem_historica": {
                    "id": "historico-001",
                    "versao": "56.4.18",
                },
                "status_epistemico": {
                    "tipo": "investigacao_historica",
                    "nao_equivale_a_verdade": True,
                    "conhecimento_permanente": False,
                },
            }
        ],
        "historico_consultado": True,
        "historico_encontrado": True,
    }

    copia_antes = copy.deepcopy(
        investigacao
    )

    resultado = analise.analisar(
        investigacao
    )

    erro, total = verificar(
        1,
        "análise retorna sucesso",
        lambda: assert_true(
            resultado.get("sucesso") is True,
            "análise não retornou sucesso",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        2,
        "estado identifica lacunas",
        lambda: assert_true(
            resultado.get("estado")
            == "lacunas_identificadas",
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
        "investigação permanece aberta",
        lambda: assert_true(
            valor[
                "investigacao_permanece_aberta"
            ]
            is True,
            "investigação foi encerrada indevidamente",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        4,
        "investigação ainda é marcada como necessária",
        lambda: assert_true(
            valor[
                "investigacao_necessaria"
            ]
            is True,
            "necessidade de investigar foi perdida",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        5,
        "pergunta original é preservada",
        lambda: assert_true(
            valor["pergunta"]
            == investigacao["pergunta"],
            "pergunta alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        6,
        "necessidade original é preservada",
        lambda: assert_true(
            valor["necessidade"]
            == investigacao["necessidade"],
            "necessidade alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        7,
        "evidência necessária é preservada",
        lambda: assert_true(
            valor["evidencia_necessaria"]
            == investigacao["evidencia_necessaria"],
            "requisito de evidência alterado",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        8,
        "existe ao menos uma lacuna aberta",
        lambda: assert_true(
            len(
                valor["lacunas_abertas"]
            )
            >= 1,
            "nenhuma lacuna foi identificada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        9,
        "lacuna principal é de evidência necessária",
        lambda: assert_true(
            valor["lacunas_abertas"][0][
                "tipo"
            ]
            == "evidencia_necessaria",
            "tipo da lacuna incorreto",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        10,
        "lacuna permanece aberta",
        lambda: assert_true(
            valor["lacunas_abertas"][0][
                "estado"
            ]
            == "aberta",
            "lacuna foi considerada fechada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        11,
        "histórico encontrado é reconhecido",
        lambda: assert_true(
            valor[
                "historico_encontrado"
            ]
            is True,
            "histórico não foi reconhecido",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        12,
        "histórico disponível não fecha a lacuna",
        lambda: assert_true(
            valor[
                "historico_nao_fecha_lacunas"
            ]
            is True,
            "histórico foi tratado como prova suficiente",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        13,
        "contexto histórico disponível é reconhecido",
        lambda: assert_true(
            valor[
                "contexto_historico_disponivel"
            ]
            is True,
            "contexto histórico não foi reconhecido",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        14,
        "investigação original é retornada isoladamente",
        lambda: assert_true(
            valor[
                "investigacao_original"
            ]
            == copia_antes,
            "cópia original não foi preservada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        15,
        "análise não altera investigação de entrada",
        lambda: assert_true(
            investigacao
            == copia_antes,
            "investigação de entrada foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        16,
        "resultado possui cópia isolada da investigação original",
        lambda: (
            lambda dados: (
                dados["valor"][
                    "investigacao_original"
                ].update(
                    {
                        "alterado": True
                    }
                ),
                assert_true(
                    "alterado"
                    not in analise.analisar(
                        investigacao
                    )["valor"][
                        "investigacao_original"
                    ],
                    "referência interna vazou",
                ),
            )
        )(
            analise.analisar(
                investigacao
            )
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        17,
        "investigação não é executada nesta camada",
        lambda: esperar_erro(
            analise.executar_investigacao,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        18,
        "capacidades não são executadas nesta camada",
        lambda: esperar_erro(
            lambda: analise.executar_capacidade(
                "ler_arquivo"
            ),
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        19,
        "hipóteses não são formuladas nesta camada",
        lambda: esperar_erro(
            lambda: analise.formular_hipotese(
                "hipotese"
            ),
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        20,
        "arquitetura não é modificada nesta camada",
        lambda: esperar_erro(
            lambda: analise.modificar_arquitetura(
                "planta_nixal"
            ),
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        21,
        "conhecimento permanente não é promovido",
        lambda: esperar_erro(
            analise.promover_conhecimento,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        22,
        "pergunta ausente é recusada",
        lambda: assert_true(
            analise.analisar(
                {
                    "evidencia_necessaria": (
                        "alguma evidência"
                    )
                }
            )["sucesso"]
            is False,
            "pergunta ausente não foi recusada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        23,
        "evidência necessária ausente é recusada",
        lambda: assert_true(
            analise.analisar(
                {
                    "pergunta": (
                        "O que ainda precisa ser descoberto?"
                    )
                }
            )["sucesso"]
            is False,
            "evidência necessária ausente não foi recusada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        24,
        "contexto histórico inválido é recusado",
        lambda: assert_true(
            analise.analisar(
                {
                    "pergunta": (
                        "Quais relações existem?"
                    ),
                    "evidencia_necessaria": (
                        "Relações explicitamente observadas."
                    ),
                    "contexto_historico_relevante": {},
                }
            )["sucesso"]
            is False,
            "contexto inválido não foi recusado",
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
