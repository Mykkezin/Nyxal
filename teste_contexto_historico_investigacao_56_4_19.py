#!/usr/bin/env python3

"""
NIXAL — TESTE DO CONTEXTO HISTÓRICO DE INVESTIGAÇÃO

Microetapa 56.4.19
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_contexto_historico_investigacao import (
    ContextoHistoricoInvestigacaoNixal,
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

        contexto = ContextoHistoricoInvestigacaoNixal(
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

        registro_provisorio = memoria.listar()[-1]

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

        registro_testado = memoria.listar()[-1]

        ciclo.registrar_avaliacao(
            {
                "estado": "inconclusiva",
                "motivo": (
                    "Ainda faltam evidências."
                ),
            }
        )

        registro_inconclusivo = memoria.listar()[-1]

        erro, total = verificar(
            1,
            "recupera contexto por ID",
            lambda: assert_true(
                contexto.obter(
                    registro_inconclusivo["id"]
                )["sucesso"] is True,
                "contexto não foi recuperado",
            ),
        )
        falhas += erro
        testes += total

        obtido = contexto.obter(
            registro_inconclusivo["id"]
        )

        erro, total = verificar(
            2,
            "preserva a origem histórica",
            lambda: assert_true(
                obtido["valor"][
                    "origem_historica"
                ]["id"]
                == registro_inconclusivo["id"],
                "origem histórica incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            3,
            "marca explicitamente que histórico não é verdade",
            lambda: assert_true(
                obtido["valor"][
                    "status_epistemico"
                ]["nao_equivale_a_verdade"]
                is True,
                "distinção epistemológica ausente",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            4,
            "preserva hipótese e estado atual",
            lambda: (
                assert_true(
                    obtido["valor"][
                        "investigacao"
                    ]["hipotese"]
                    == "As dependências arquiteturais podem estar incompletas.",
                    "hipótese incorreta",
                ),
                assert_true(
                    obtido["valor"][
                        "investigacao"
                    ]["estado_atual"]
                    == "inconclusiva",
                    "estado incorreto",
                ),
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            5,
            "preserva histórico, testes e avaliações",
            lambda: (
                assert_true(
                    len(
                        obtido["valor"][
                            "investigacao"
                        ]["historico"]
                    )
                    == 3,
                    "histórico incompleto",
                ),
                assert_true(
                    len(
                        obtido["valor"][
                            "investigacao"
                        ]["testes"]
                    )
                    == 1,
                    "testes incompletos",
                ),
                assert_true(
                    len(
                        obtido["valor"][
                            "investigacao"
                        ]["avaliacoes"]
                    )
                    == 1,
                    "avaliações incompletas",
                ),
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            6,
            "ultimos retorna o número solicitado",
            lambda: assert_true(
                len(
                    contexto.ultimos(
                        2
                    )["valor"]["registros"]
                )
                == 2,
                "quantidade de contextos incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            7,
            "ultimos preserva a ordem histórica",
            lambda: assert_true(
                [
                    item["origem_historica"]["id"]
                    for item in contexto.ultimos(
                        2
                    )["valor"]["registros"]
                ]
                == [
                    registro_testado["id"],
                    registro_inconclusivo["id"],
                ],
                "ordem histórica incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            8,
            "por_necessidade filtra o histórico correto",
            lambda: assert_true(
                all(
                    item["investigacao"][
                        "necessidade"
                    ]
                    == "conhecer_dependencias_arquiteturais"
                    for item in contexto.por_necessidade(
                        "conhecer_dependencias_arquiteturais",
                        10,
                    )["valor"]["registros"]
                ),
                "necessidade incorreta no contexto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            9,
            "por_necessidade respeita limite",
            lambda: assert_true(
                len(
                    contexto.por_necessidade(
                        "conhecer_dependencias_arquiteturais",
                        2,
                    )["valor"]["registros"]
                )
                == 2,
                "limite não foi respeitado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            10,
            "limite inválido é recusado",
            lambda: assert_true(
                contexto.ultimos(
                    0
                )["sucesso"] is False,
                "limite inválido não foi recusado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            11,
            "ID inexistente é recusado",
            lambda: assert_true(
                contexto.obter(
                    "id-inexistente"
                )["sucesso"] is False,
                "ID inexistente não foi recusado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            12,
            "necessidade inválida é recusada",
            lambda: assert_true(
                contexto.por_necessidade(
                    ""
                )["sucesso"] is False,
                "necessidade vazia não foi recusada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            13,
            "contexto retorna cópias isoladas",
            lambda: (
                lambda dados: (
                    dados["valor"][
                        "investigacao"
                    ].update(
                        {
                            "estado_atual": "alterado"
                        }
                    ),
                    assert_true(
                        contexto.obter(
                            registro_inconclusivo["id"]
                        )["valor"][
                            "investigacao"
                        ]["estado_atual"]
                        == "inconclusiva",
                        "referência interna vazou",
                    ),
                )
            )(
                contexto.obter(
                    registro_inconclusivo["id"]
                )
            ),
        )
        falhas += erro
        testes += total

        memoria_antes = memoria.listar()

        erro, total = verificar(
            14,
            "consulta não modifica memória persistida",
            lambda: assert_true(
                memoria.listar()
                == memoria_antes,
                "memória foi alterada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            15,
            "não executa capacidades",
            lambda: esperar_erro(
                lambda: contexto.executar_capacidade(
                    "obter_hora"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            16,
            "não modifica arquitetura",
            lambda: esperar_erro(
                lambda: contexto.modificar_arquitetura(
                    "planta_nixal"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            17,
            "não promove conhecimento permanente",
            lambda: esperar_erro(
                contexto.promover_conhecimento,
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            18,
            "arquivo persistido permanece válido",
            lambda: assert_true(
                json.loads(
                    caminho.read_text(
                        encoding="utf-8"
                    )
                )["versao"]
                == "56.4.15",
                "JSON persistido inválido",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            19,
            "estado histórico permanece distinguido de verdade",
            lambda: assert_true(
                contexto.obter(
                    registro_provisorio["id"]
                )["valor"][
                    "status_epistemico"
                ]["nao_equivale_a_verdade"]
                is True,
                "distinção não foi preservada",
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
