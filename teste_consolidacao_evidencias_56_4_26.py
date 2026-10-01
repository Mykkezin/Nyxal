#!/usr/bin/env python3

"""
NIXAL — TESTE DA CONSOLIDAÇÃO DE EVIDÊNCIAS

Microetapa 56.4.26
"""

from __future__ import annotations

from copy import deepcopy

from nixal_consolidacao_evidencias import (
    ConsolidacaoEvidenciasNixal,
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

    consolidacao = ConsolidacaoEvidenciasNixal()

    resultado_execucao = {
        "sucesso": True,
        "estado": "plano_executado",
        "origem": "execucao_plano_investigacao_nixal",
        "valor": {
            "plano": {
                "id": "plano-1",
                "tipo_investigacao": (
                    "mapeamento_arquitetural"
                ),
            },
            "evidencias": [
                {
                    "fonte": "listar_arquivos",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "resultado": [
                        "a.py",
                        "b.py",
                    ],
                },
                {
                    "fonte": "ler_arquivo",
                    "sucesso": True,
                    "estado": "evidencia_disponivel",
                    "resultado": "conteúdo observado",
                },
                {
                    "fonte": "ler_arquivo",
                    "sucesso": False,
                    "estado": "falha_fonte",
                    "erro": "falha de leitura",
                },
            ],
        },
    }

    entrada_antes = deepcopy(
        resultado_execucao
    )

    resultado = consolidacao.consolidar(
        resultado_execucao
    )

    erro, total = verificar(
        1,
        "consolidação retorna sucesso",
        lambda: assert_true(
            resultado.get("sucesso") is True,
            "consolidação não retornou sucesso",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        2,
        "estado indica evidências consolidadas",
        lambda: assert_true(
            resultado.get("estado")
            == "evidencias_consolidadas",
            "estado incorreto",
        ),
    )
    falhas += erro
    testes += total

    valor = resultado.get(
        "valor",
        {}
    )

    evidencias = valor.get(
        "evidencias",
        []
    )

    erro, total = verificar(
        3,
        "somente evidências válidas são consolidadas",
        lambda: assert_true(
            len(evidencias) == 2,
            "quantidade de evidências consolidada incorreta",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        4,
        "fontes são preservadas",
        lambda: assert_true(
            {
                item["fonte"]
                for item in evidencias
            }
            == {
                "listar_arquivos",
                "ler_arquivo",
            },
            "fontes não foram preservadas",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        5,
        "índice de consolidação é atribuído",
        lambda: assert_true(
            [
                item["indice_consolidacao"]
                for item in evidencias
            ]
            == [1, 2],
            "índices incorretos",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        6,
        "quantidade de evidências é preservada",
        lambda: assert_true(
            valor[
                "quantidade_evidencias"
            ]
            == 2,
            "quantidade incorreta",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        7,
        "evidência consolidada é marcada explicitamente",
        lambda: assert_true(
            valor[
                "evidencia_consolidada"
            ]
            is True,
            "marca de consolidação ausente",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        8,
        "hipótese não é formulada",
        lambda: assert_true(
            valor[
                "hipotese_formulada"
            ]
            is False,
            "hipótese foi formulada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        9,
        "conhecimento permanente não é promovido",
        lambda: assert_true(
            valor[
                "conhecimento_permanente"
            ]
            is False,
            "conhecimento permanente foi promovido",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        10,
        "entrada permanece inalterada",
        lambda: assert_true(
            resultado_execucao
            == entrada_antes,
            "entrada foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        11,
        "evidências retornadas são cópias isoladas",
        lambda: (
            lambda dados: (
                dados["valor"]["evidencias"][0].update(
                    {
                        "alterado": True
                    }
                ),
                assert_true(
                    "alterado"
                    not in consolidacao.consolidar(
                        resultado_execucao
                    )["valor"]["evidencias"][0],
                    "referência interna vazou",
                ),
            )
        )(
            consolidacao.consolidar(
                resultado_execucao
            )
        ),
    )
    falhas += erro
    testes += total

    resultado_sem_evidencias = {
        "sucesso": True,
        "estado": "plano_executado",
        "valor": {
            "plano": {
                "id": "plano-2"
            },
            "evidencias": [
                {
                    "fonte": "ler_arquivo",
                    "sucesso": False,
                    "estado": "falha_fonte",
                }
            ],
        },
    }

    erro, total = verificar(
        12,
        "ausência de evidência válida não é convertida em sucesso",
        lambda: assert_true(
            consolidacao.consolidar(
                resultado_sem_evidencias
            )["estado"]
            == "sem_evidencia_consolidada",
            "ausência foi tratada como evidência",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        13,
        "resultado de execução inválido é recusado",
        lambda: assert_true(
            consolidacao.consolidar(
                {}
            )["sucesso"]
            is False,
            "resultado inválido não foi recusado",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        14,
        "execução malsucedida é recusada",
        lambda: assert_true(
            consolidacao.consolidar(
                {
                    "sucesso": False,
                    "estado": "falha_execucao",
                }
            )["sucesso"]
            is False,
            "execução malsucedida foi consolidada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        15,
        "estado de execução incorreto é recusado",
        lambda: assert_true(
            consolidacao.consolidar(
                {
                    "sucesso": True,
                    "estado": "evidencia_coletada",
                    "valor": {
                        "evidencias": []
                    },
                }
            )["sucesso"]
            is False,
            "estado incorreto foi aceito",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        16,
        "lista de evidências ausente é recusada",
        lambda: assert_true(
            consolidacao.consolidar(
                {
                    "sucesso": True,
                    "estado": "plano_executado",
                    "valor": {},
                }
            )["sucesso"]
            is False,
            "lista ausente não foi recusada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        17,
        "evidência sem fonte válida é recusada",
        lambda: assert_true(
            consolidacao.consolidar(
                {
                    "sucesso": True,
                    "estado": "plano_executado",
                    "valor": {
                        "evidencias": [
                            {
                                "sucesso": True,
                                "estado": "evidencia_disponivel",
                            }
                        ]
                    },
                }
            )["sucesso"]
            is False,
            "evidência sem fonte foi aceita",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        18,
        "coleta continua bloqueada nesta camada",
        lambda: esperar_erro(
            consolidacao.coletar,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        19,
        "formulação de hipótese continua bloqueada",
        lambda: esperar_erro(
            consolidacao.formular_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        20,
        "avaliação de hipótese continua bloqueada",
        lambda: esperar_erro(
            consolidacao.avaliar_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        21,
        "modificação de arquitetura continua bloqueada",
        lambda: esperar_erro(
            consolidacao.modificar_arquitetura,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        22,
        "promoção de conhecimento continua bloqueada",
        lambda: esperar_erro(
            consolidacao.promover_conhecimento,
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
