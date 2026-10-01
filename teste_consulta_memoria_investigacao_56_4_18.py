#!/usr/bin/env python3

"""
NIXAL — TESTE DA CONSULTA DO HISTÓRICO DE INVESTIGAÇÕES

Microetapa 56.4.18
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_consulta_memoria_investigacao import (
    ConsultaMemoriaInvestigacaoNixal,
)
from nixal_memoria_investigacao import (
    MemoriaInvestigacaoNixal,
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

    with tempfile.TemporaryDirectory() as diretorio:
        caminho = (
            Path(diretorio)
            / "memoria.json"
        )

        memoria = MemoriaInvestigacaoNixal(
            caminho
        )

        ciclo = CicloMemoriaHipoteseNixal(
            memoria
        )

        consulta = ConsultaMemoriaInvestigacaoNixal(
            memoria
        )

        ciclo.iniciar(
            {
                "hipotese": (
                    "As dependências arquiteturais "
                    "podem estar incompletas."
                ),
                "estado": "provisoria",
                "necessidade": (
                    "conhecer_dependencias_arquiteturais"
                ),
                "pergunta": (
                    "Quais dependências ainda faltam?"
                ),
            }
        )

        ciclo.registrar_teste(
            {
                "estado": "teste_concluido",
                "suporte": True,
                "contraria": False,
                "inconclusivo": False,
                "evidencias": [
                    {
                        "fonte": "teste_controlado"
                    }
                ],
            }
        )

        ciclo.registrar_avaliacao(
            {
                "estado": "inconclusiva",
                "motivo": (
                    "Ainda faltam evidências."
                ),
            }
        )

        ciclo.iniciar(
            {
                "hipotese": (
                    "A memória corporal pode revelar "
                    "eventos relevantes para investigação."
                ),
                "estado": "provisoria",
                "necessidade": (
                    "investigar_memoria_corporal"
                ),
                "pergunta": (
                    "Existem eventos corporais relevantes?"
                ),
            }
        )

        registros_antes = memoria.listar()

        erro, total = verificar(
            1,
            "listar retorna todos os registros",
            lambda: assert_true(
                len(
                    consulta.listar()
                ) == len(
                    registros_antes
                ),
                "quantidade listada incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            2,
            "quantidade corresponde à memória",
            lambda: assert_true(
                consulta.quantidade()
                == memoria.quantidade(),
                "quantidade divergente",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            3,
            "consulta por estado encontra somente o estado pedido",
            lambda: assert_true(
                all(
                    registro["ciclo"]["estado_atual"]
                    == "provisoria"
                    for registro in consulta.por_estado(
                        "provisoria"
                    )
                ),
                "estado incorreto na consulta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            4,
            "consulta por estado preserva a ordem da memória",
            lambda: assert_true(
                [
                    registro["id"]
                    for registro in consulta.por_estado(
                        "provisoria"
                    )
                ]
                == [
                    registro["id"]
                    for registro in registros_antes
                    if registro["ciclo"][
                        "estado_atual"
                    ]
                    == "provisoria"
                ],
                "ordem da memória não foi preservada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            5,
            "consulta por necessidade encontra registros exatos",
            lambda: assert_true(
                all(
                    registro["ciclo"]["necessidade"]
                    == "conhecer_dependencias_arquiteturais"
                    for registro
                    in consulta.por_necessidade(
                        "conhecer_dependencias_arquiteturais"
                    )
                ),
                "necessidade incorreta na consulta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            6,
            "busca de hipótese é case-insensitive",
            lambda: assert_true(
                len(
                    consulta.buscar_hipotese(
                        "DEPENDÊNCIAS"
                    )
                )
                >= 1,
                "busca não encontrou hipótese",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            7,
            "busca de hipótese usa correspondência parcial",
            lambda: assert_true(
                len(
                    consulta.buscar_hipotese(
                        "eventos relevantes"
                    )
                )
                == 1,
                "busca parcial encontrou quantidade inesperada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            8,
            "último registro de uma necessidade é recuperável",
            lambda: (
                lambda registro: assert_true(
                    registro is not None
                    and registro["ciclo"][
                        "estado_atual"
                    ]
                    == "inconclusiva",
                    "último registro incorreto",
                )
            )(
                consulta.ultima_por_necessidade(
                    "conhecer_dependencias_arquiteturais"
                )
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            9,
            "necessidade inexistente retorna None",
            lambda: assert_true(
                consulta.ultima_por_necessidade(
                    "nao_existe"
                )
                is None,
                "necessidade inexistente não foi recusada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            10,
            "resumo contabiliza os snapshots históricos",
            lambda: (
                lambda resumo: (
                    assert_true(
                        resumo["sucesso"] is True,
                        "resumo não foi produzido com sucesso",
                    ),
                    assert_true(
                        resumo["valor"][
                            "quantidade_registros"
                        ]
                        == len(
                            registros_antes
                        ),
                        "quantidade de registros incorreta",
                    ),
                    assert_true(
                        resumo["valor"][
                            "por_estado"
                        ].get(
                            "provisoria",
                            0,
                        )
                        == 2,
                        "deveriam existir dois snapshots provisórios",
                    ),
                    assert_true(
                        resumo["valor"][
                            "por_estado"
                        ].get(
                            "testada",
                            0,
                        )
                        == 1,
                        "deveria existir um snapshot testado",
                    ),
                    assert_true(
                        resumo["valor"][
                            "por_estado"
                        ].get(
                            "inconclusiva",
                            0,
                        )
                        == 1,
                        "deveria existir um snapshot inconclusivo",
                    ),
                )
            )(
                consulta.resumo()
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            11,
            "leituras retornam cópias isoladas",
            lambda: (
                lambda registros: (
                    registros[0]["ciclo"].update(
                        {
                            "estado_atual": "alterado"
                        }
                    ),
                    assert_true(
                        consulta.listar()[0]["ciclo"][
                            "estado_atual"
                        ]
                        != "alterado",
                        "referência interna vazou",
                    ),
                )
            )(
                consulta.listar()
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            12,
            "consulta vazia por estado retorna lista vazia",
            lambda: assert_true(
                consulta.por_estado(
                    ""
                )
                == [],
                "estado vazio não retornou lista vazia",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            13,
            "consulta vazia por necessidade retorna lista vazia",
            lambda: assert_true(
                consulta.por_necessidade(
                    ""
                )
                == [],
                "necessidade vazia não retornou lista vazia",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            14,
            "busca vazia de hipótese retorna lista vazia",
            lambda: assert_true(
                consulta.buscar_hipotese(
                    ""
                )
                == [],
                "busca vazia não retornou lista vazia",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            15,
            "memória persiste após nova instância",
            lambda: assert_true(
                ConsultaMemoriaInvestigacaoNixal(
                    MemoriaInvestigacaoNixal(
                        caminho
                    )
                ).quantidade()
                == len(
                    registros_antes
                ),
                "nova instância perdeu registros",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            16,
            "consulta não altera o arquivo persistido",
            lambda: (
                memoria.recarregar(),
                assert_true(
                    memoria.listar()
                    == registros_antes,
                    "consulta alterou a memória",
                ),
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            17,
            "execução de capacidade é bloqueada",
            lambda: esperar_erro(
                lambda: consulta.executar_capacidade(
                    "obter_hora"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            18,
            "modificação e promoção são bloqueadas",
            lambda: (
                esperar_erro(
                    lambda: consulta.modificar_arquitetura(
                        "planta_nixal"
                    ),
                    PermissionError,
                ),
                esperar_erro(
                    consulta.promover_conhecimento,
                    PermissionError,
                ),
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            19,
            "memória continua em JSON válido",
            lambda: assert_true(
                json.loads(
                    caminho.read_text(
                        encoding="utf-8"
                    )
                )["versao"]
                == "56.4.15",
                "versão persistida inesperada",
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
