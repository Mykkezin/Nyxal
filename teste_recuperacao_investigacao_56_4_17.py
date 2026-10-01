#!/usr/bin/env python3

"""
NIXAL — TESTE DA RECUPERAÇÃO DE INVESTIGAÇÃO PERSISTIDA

Microetapa 56.4.17
"""

from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from pathlib import Path

from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_memoria_investigacao import (
    MemoriaInvestigacaoNixal,
)
from nixal_recuperacao_investigacao import (
    RecuperacaoInvestigacaoNixal,
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

        recuperacao = RecuperacaoInvestigacaoNixal(
            memoria
        )

        hipotese = {
            "hipotese": (
                "Uma dependência ainda pode "
                "não estar formalizada."
            ),
            "estado": "provisoria",
            "necessidade": (
                "conhecer_dependencias_arquiteturais"
            ),
            "pergunta": (
                "Quais dependências ainda "
                "não estão declaradas?"
            ),
        }

        integracao.iniciar(
            hipotese
        )

        teste = {
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

        integracao.registrar_teste(
            teste
        )

        integracao.registrar_avaliacao(
            {
                "estado": "inconclusiva",
                "motivo": (
                    "Os dados ainda não permitem "
                    "concluir."
                ),
            }
        )

        registros_antes = memoria.listar()
        assert_true(
            len(registros_antes) == 3,
            "preparação deveria possuir três estados persistidos",
        )

        registro_id = registros_antes[-1]["id"]

        erro, total = verificar(
            1,
            "lista registros persistidos",
            lambda: assert_true(
                recuperacao.quantidade() == 3,
                "quantidade recuperada incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            2,
            "recupera um registro existente",
            lambda: assert_true(
                recuperacao.recuperar(
                    registro_id
                )["sucesso"] is True,
                "registro não foi recuperado",
            ),
        )
        falhas += erro
        testes += total

        recuperado = recuperacao.recuperar(
            registro_id
        )

        erro, total = verificar(
            3,
            "recuperação preserva o ID",
            lambda: assert_true(
                recuperado["valor"]["id"]
                == registro_id,
                "ID recuperado incorreto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            4,
            "recuperação preserva o estado atual",
            lambda: assert_true(
                recuperado["valor"]["ciclo"][
                    "estado_atual"
                ] == "inconclusiva",
                "estado recuperado incorreto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            5,
            "recuperação preserva o histórico",
            lambda: assert_true(
                len(
                    recuperado["valor"]["ciclo"][
                        "historico"
                    ]
                ) == 3,
                "histórico recuperado incompleto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            6,
            "recuperação preserva testes e avaliações",
            lambda: (
                assert_true(
                    len(
                        recuperado["valor"]["ciclo"][
                            "testes"
                        ]
                    ) == 1,
                    "teste não recuperado",
                ),
                assert_true(
                    len(
                        recuperado["valor"]["ciclo"][
                            "avaliacoes"
                        ]
                    ) == 1,
                    "avaliação não recuperada",
                ),
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            7,
            "recuperação nunca marca conhecimento permanente",
            lambda: assert_true(
                recuperado["valor"]["ciclo"][
                    "conhecimento_permanente"
                ] is False,
                "conhecimento permanente foi alterado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            8,
            "recuperar_ciclo retorna somente o ciclo",
            lambda: assert_true(
                recuperacao.recuperar_ciclo(
                    registro_id
                )["estado_atual"]
                == "inconclusiva",
                "ciclo recuperado incorreto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            9,
            "recuperado é uma cópia isolada",
            lambda: (
                lambda ciclo: (
                    ciclo.update(
                        {
                            "estado_atual": "alterado"
                        }
                    ),
                    assert_true(
                        recuperacao.recuperar_ciclo(
                            registro_id
                        )["estado_atual"]
                        == "inconclusiva",
                        "referência interna vazou",
                    ),
                )
            )(
                recuperacao.recuperar_ciclo(
                    registro_id
                )
            ),
        )
        falhas += erro
        testes += total

        registros_depois_leitura = (
            memoria.listar()
        )

        erro, total = verificar(
            10,
            "leituras não modificam a memória persistida",
            lambda: assert_true(
                registros_depois_leitura
                == registros_antes,
                "leitura modificou a memória",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            11,
            "nova instância recupera o mesmo registro",
            lambda: (
                lambda nova_memoria: (
                    lambda nova_recuperacao: assert_true(
                        nova_recuperacao.recuperar(
                            registro_id
                        )
                        == recuperado,
                        "nova instância recuperou dados diferentes",
                    )
                )(
                    RecuperacaoInvestigacaoNixal(
                        nova_memoria
                    )
                )
            )(
                MemoriaInvestigacaoNixal(
                    caminho
                )
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            12,
            "ID vazio é recusado",
            lambda: assert_true(
                recuperacao.recuperar(
                    ""
                )["sucesso"] is False,
                "ID vazio não foi recusado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            13,
            "registro inexistente é recusado",
            lambda: assert_true(
                recuperacao.recuperar(
                    "id-inexistente"
                )["sucesso"] is False,
                "registro inexistente não foi recusado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            14,
            "execução de capacidade é bloqueada",
            lambda: esperar_erro(
                lambda: recuperacao.executar_capacidade(
                    "obter_hora"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            15,
            "modificação arquitetural é bloqueada",
            lambda: esperar_erro(
                lambda: recuperacao.modificar_arquitetura(
                    "planta_nixal"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            16,
            "promoção de conhecimento é bloqueada",
            lambda: esperar_erro(
                recuperacao.promover_conhecimento,
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            17,
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

        erro, total = verificar(
            18,
            "modificar a cópia recuperada não altera o original",
            lambda: (
                lambda original: (
                    lambda copia: (
                        copia["historico"].append(
                            {
                                "evento": "teste_local"
                            }
                        ),
                        assert_true(
                            len(
                                recuperacao.recuperar_ciclo(
                                    registro_id
                                )["historico"]
                            )
                            == len(
                                original["historico"]
                            ),
                            "alteração local vazou para o registro",
                        ),
                    )
                )(
                    deepcopy(original)
                )
            )(
                recuperacao.recuperar_ciclo(
                    registro_id
                )
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
