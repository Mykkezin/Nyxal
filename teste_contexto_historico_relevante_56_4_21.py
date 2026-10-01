#!/usr/bin/env python3

"""
NIXAL — TESTE DO CONTEXTO HISTÓRICO RELEVANTE

Microetapa 56.4.21
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_contexto_historico_relevante import (
    ContextoHistoricoRelevanteNixal,
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

        contexto = (
            ContextoHistoricoRelevanteNixal(
                memoria
            )
        )

        necessidade = (
            "conhecer_dependencias_arquiteturais"
        )

        ciclo.iniciar(
            {
                "hipotese": (
                    "As dependências arquiteturais "
                    "podem estar incompletas."
                ),
                "estado": "provisoria",
                "necessidade": necessidade,
                "pergunta": (
                    "Quais dependências ainda faltam?"
                ),
            }
        )

        primeiro = memoria.listar()[-1]

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

        segundo = memoria.listar()[-1]

        ciclo.registrar_avaliacao(
            {
                "estado": "inconclusiva",
                "motivo": (
                    "Ainda faltam evidências."
                ),
            }
        )

        terceiro = memoria.listar()[-1]

        erro, total = verificar(
            1,
            "análise retorna contexto relevante",
            lambda: assert_true(
                contexto.analisar(
                    necessidade=necessidade
                )["sucesso"] is True,
                "análise falhou",
            ),
        )
        falhas += erro
        testes += total

        resultado = contexto.analisar(
            necessidade=necessidade,
            limite=2,
        )

        erro, total = verificar(
            2,
            "limite retorna os dois registros mais recentes",
            lambda: assert_true(
                len(
                    resultado["valor"]["contextos"]
                )
                == 2,
                "limite não foi respeitado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            3,
            "ordem cronológica é preservada",
            lambda: assert_true(
                [
                    item["origem_historica"]["id"]
                    for item in resultado["valor"][
                        "contextos"
                    ]
                ]
                == [
                    segundo["id"],
                    terceiro["id"],
                ],
                "ordem cronológica incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            4,
            "contexto preserva o estado mais recente",
            lambda: assert_true(
                resultado["valor"]["contextos"][-1][
                    "investigacao"
                ]["estado_atual"]
                == "inconclusiva",
                "estado mais recente incorreto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            5,
            "histórico é explicitamente separado de verdade",
            lambda: assert_true(
                all(
                    contexto_item[
                        "status_epistemico"
                    ]["nao_equivale_a_verdade"]
                    is True
                    for contexto_item
                    in resultado["valor"]["contextos"]
                ),
                "distinção epistemológica ausente",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            6,
            "histórico não é interpretado como encerramento da investigação",
            lambda: assert_true(
                "não encerra" in resultado["valor"][
                    "interpretacao"
                ],
                "interpretação do histórico está incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            7,
            "necessidade e hipótese podem ser combinadas",
            lambda: assert_true(
                contexto.analisar(
                    necessidade=necessidade,
                    hipotese="dependências",
                    limite=5,
                )["sucesso"] is True,
                "análise combinada falhou",
            ),
        )
        falhas += erro
        testes += total

        resultado_combinado = contexto.analisar(
            necessidade=necessidade,
            hipotese="dependências",
        )

        erro, total = verificar(
            8,
            "registros iguais entre critérios não são duplicados",
            lambda: assert_true(
                len(
                    {
                        item["origem_historica"]["id"]
                        for item
                        in resultado_combinado["valor"][
                            "contextos"
                        ]
                    }
                )
                == len(
                    resultado_combinado["valor"][
                        "contextos"
                    ]
                ),
                "contexto duplicado encontrado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            9,
            "ausência de histórico não é tratada como prova",
            lambda: assert_true(
                "não prova" in contexto.analisar(
                    necessidade="necessidade_ausente"
                )["valor"]["interpretacao"],
                "interpretação da ausência incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            10,
            "entrada sem necessidade e sem hipótese é recusada",
            lambda: assert_true(
                contexto.analisar()["sucesso"]
                is False,
                "entrada vazia não foi recusada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            11,
            "limite zero é recusado",
            lambda: assert_true(
                contexto.analisar(
                    necessidade=necessidade,
                    limite=0,
                )["sucesso"]
                is False,
                "limite zero não foi recusado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            12,
            "limite não inteiro é recusado",
            lambda: assert_true(
                contexto.analisar(
                    necessidade=necessidade,
                    limite="2",
                )["sucesso"]
                is False,
                "limite inválido não foi recusado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            13,
            "contextos retornados são cópias isoladas",
            lambda: (
                lambda dados: (
                    dados["valor"]["contextos"][0][
                        "investigacao"
                    ].update(
                        {
                            "estado_atual": "alterado"
                        }
                    ),
                    assert_true(
                        contexto.analisar(
                            necessidade=necessidade
                        )["valor"]["contextos"][0][
                            "investigacao"
                        ]["estado_atual"]
                        != "alterado",
                        "referência interna vazou",
                    ),
                )
            )(
                contexto.analisar(
                    necessidade=necessidade
                )
            ),
        )
        falhas += erro
        testes += total

        memoria_antes = memoria.listar()

        erro, total = verificar(
            14,
            "análise não altera a memória",
            lambda: assert_true(
                contexto.analisar(
                    necessidade=necessidade
                )["sucesso"] is True
                and memoria.listar()
                == memoria_antes,
                "memória foi alterada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            15,
            "nova instância recupera o mesmo contexto",
            lambda: assert_true(
                ContextoHistoricoRelevanteNixal(
                    MemoriaInvestigacaoNixal(
                        caminho
                    )
                ).analisar(
                    necessidade=necessidade
                )["valor"]["quantidade"]
                == 3,
                "nova instância perdeu contexto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            16,
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
            17,
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
            18,
            "não promove conhecimento permanente",
            lambda: esperar_erro(
                contexto.promover_conhecimento,
                PermissionError,
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
                "JSON persistido inválido",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            20,
            "o primeiro registro continua presente no histórico",
            lambda: assert_true(
                memoria.obter(
                    primeiro["id"]
                ) is not None,
                "primeiro registro desapareceu",
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
