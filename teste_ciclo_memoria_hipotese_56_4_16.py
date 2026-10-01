#!/usr/bin/env python3

"""
NIXAL — TESTE DA INTEGRAÇÃO DO CICLO COM MEMÓRIA

Microetapa 56.4.16

Valida a integração entre:
    CicloVidaHipoteseNixal
    MemoriaInvestigacaoNixal
    CicloMemoriaHipoteseNixal
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
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

        integracao = CicloMemoriaHipoteseNixal(
            memoria
        )

        hipotese = {
            "hipotese": (
                "As dependências arquiteturais "
                "podem ser reconstruídas a partir "
                "dos componentes declarados."
            ),
            "estado": "provisoria",
            "necessidade": (
                "conhecer_dependencias_arquiteturais"
            ),
            "pergunta": (
                "Quais componentes dependem "
                "uns dos outros?"
            ),
        }

        erro, total = verificar(
            1,
            "iniciar cria e persiste o ciclo",
            lambda: (
                lambda resultado: (
                    assert_true(
                        resultado["sucesso"] is True,
                        "início do ciclo falhou",
                    ),
                    assert_true(
                        memoria.quantidade() == 1,
                        "ciclo não foi persistido",
                    ),
                )
            )(
                integracao.iniciar(
                    hipotese
                )
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            2,
            "ciclo atual é disponibilizado por leitura",
            lambda: assert_true(
                integracao.obter_ciclo()
                is not None,
                "ciclo atual ausente",
            ),
        )
        falhas += erro
        testes += total

        resultado_teste = {
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

        erro, total = verificar(
            3,
            "registrar_teste atualiza e persiste",
            lambda: (
                lambda resultado: (
                    assert_true(
                        resultado["sucesso"] is True,
                        "registro do teste falhou",
                    ),
                    assert_true(
                        resultado["estado"] == "testada",
                        "estado não virou testada",
                    ),
                    assert_true(
                        memoria.quantidade() == 2,
                        "novo estado do ciclo não foi persistido",
                    ),
                )
            )(
                integracao.registrar_teste(
                    resultado_teste
                )
            ),
        )
        falhas += erro
        testes += total

        avaliacao = {
            "estado": "suportada",
            "motivo": (
                "Evidência favorável."
            ),
        }

        erro, total = verificar(
            4,
            "registrar_avaliacao atualiza e persiste",
            lambda: (
                lambda resultado: (
                    assert_true(
                        resultado["sucesso"] is True,
                        "avaliação falhou",
                    ),
                    assert_true(
                        resultado["estado"] == "suportada",
                        "estado não virou suportada",
                    ),
                    assert_true(
                        memoria.quantidade() == 3,
                        "avaliação não foi persistida",
                    ),
                )
            )(
                integracao.registrar_avaliacao(
                    avaliacao
                )
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            5,
            "o estado mais recente do ciclo é mantido",
            lambda: assert_true(
                integracao.obter_ciclo()[
                    "estado_atual"
                ] == "suportada",
                "estado atual inesperado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            6,
            "o histórico completo é preservado",
            lambda: assert_true(
                len(
                    integracao.obter_ciclo()[
                        "historico"
                    ]
                ) == 3,
                "histórico deveria conter criação, teste e avaliação",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            7,
            "listar_memoria retorna cópias",
            lambda: (
                lambda registros: (
                    registros[0].update(
                        {"id": "alterado"}
                    ),
                    assert_true(
                        memoria.obter(
                            registros[0]["id"]
                        ) is None
                        or registros[0]["id"] != memoria.obter(
                            registros[0]["id"]
                        )["id"],
                        "referência interna vazou",
                    ),
                )
            )(
                integracao.listar_memoria()
            ),
        )
        falhas += erro
        testes += total

        registros = (
            integracao.listar_memoria()
        )

        erro, total = verificar(
            8,
            "obter_memoria recupera registro existente",
            lambda: assert_true(
                integracao.obter_memoria(
                    registros[-1]["id"]
                ) == memoria.obter(
                    registros[-1]["id"]
                ),
                "registro recuperado difere do armazenado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            9,
            "nova instância recupera a memória persistida",
            lambda: assert_true(
                MemoriaInvestigacaoNixal(
                    caminho
                ).quantidade() == 3,
                "memória não foi recuperada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            10,
            "arquivo persistido permanece em JSON válido",
            lambda: assert_true(
                json.loads(
                    caminho.read_text(
                        encoding="utf-8"
                    )
                )["versao"] == "56.4.15",
                "versão da memória inesperada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            11,
            "registrar o ciclo atual novamente é deduplicado",
            lambda: (
                lambda resultado: (
                    assert_true(
                        resultado["estado"]
                        == "ja_existente",
                        "a memória não deduplicou o ciclo",
                    ),
                    assert_true(
                        memoria.quantidade() == 3,
                        "registro duplicado criado",
                    ),
                )
            )(
                integracao.registrar_ciclo_atual()
            ),
        )
        falhas += erro
        testes += total

        sem_ciclo = CicloMemoriaHipoteseNixal(
            memoria
        )

        erro, total = verificar(
            12,
            "registrar ciclo inexistente é bloqueado",
            lambda: esperar_erro(
                sem_ciclo.registrar_ciclo_atual,
                ValueError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            13,
            "execução de capacidade é bloqueada",
            lambda: esperar_erro(
                lambda: integracao.executar_capacidade(
                    "obter_hora"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            14,
            "modificação arquitetural é bloqueada",
            lambda: esperar_erro(
                lambda: integracao.modificar_arquitetura(
                    "planta_nixal"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            15,
            "promoção de conhecimento é bloqueada",
            lambda: esperar_erro(
                integracao.promover_conhecimento,
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            16,
            "leituras não alteram o ciclo atual",
            lambda: (
                integracao.listar_memoria(),
                integracao.obter_memoria(
                    registros[-1]["id"]
                ),
                assert_true(
                    integracao.obter_ciclo()[
                        "estado_atual"
                    ] == "suportada",
                    "leitura alterou o ciclo",
                ),
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            17,
            "definir_ciclo aceita somente dicionário",
            lambda: esperar_erro(
                lambda: integracao.definir_ciclo(
                    []
                ),
                TypeError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            18,
            "obter_ciclo retorna cópia",
            lambda: (
                lambda ciclo: (
                    ciclo.update(
                        {"estado_atual": "alterado"}
                    ),
                    assert_true(
                        integracao.obter_ciclo()[
                            "estado_atual"
                        ] == "suportada",
                        "exportação vazou referência interna",
                    ),
                )
            )(
                integracao.obter_ciclo()
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
