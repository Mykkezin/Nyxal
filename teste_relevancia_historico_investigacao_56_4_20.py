#!/usr/bin/env python3

"""
NIXAL — TESTE DA RELEVÂNCIA DO HISTÓRICO DE INVESTIGAÇÃO

Microetapa 56.4.20
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
from nixal_relevancia_historico_investigacao import (
    RelevanciaHistoricoInvestigacaoNixal,
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

        relevancia = (
            RelevanciaHistoricoInvestigacaoNixal(
                memoria
            )
        )

        necessidade = (
            "conhecer_dependencias_arquiteturais"
        )

        hipotese = (
            "As dependências arquiteturais "
            "podem estar incompletas."
        )

        ciclo.iniciar(
            {
                "hipotese": hipotese,
                "estado": "provisoria",
                "necessidade": necessidade,
                "pergunta": (
                    "Quais dependências ainda faltam?"
                ),
            }
        )

        primeiro_id = memoria.listar()[-1]["id"]

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

        segundo_id = memoria.listar()[-1]["id"]

        erro, total = verificar(
            1,
            "necessidade exata encontra histórico direto",
            lambda: assert_true(
                relevancia.analisar_necessidade(
                    necessidade
                )["valor"][
                    "historico_encontrado"
                ] is True,
                "histórico direto não foi encontrado",
            ),
        )
        falhas += erro
        testes += total

        analise_necessidade = (
            relevancia.analisar_necessidade(
                necessidade
            )
        )

        erro, total = verificar(
            2,
            "necessidade exata preserva quantidade de registros",
            lambda: assert_true(
                analise_necessidade["valor"][
                    "quantidade_direta"
                ]
                == 2,
                "quantidade direta incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            3,
            "necessidade exata preserva ordem histórica",
            lambda: assert_true(
                [
                    registro["id"]
                    for registro
                    in analise_necessidade["valor"][
                        "historico_direto"
                    ]
                ]
                == [
                    primeiro_id,
                    segundo_id,
                ],
                "ordem histórica incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            4,
            "hipótese encontra histórico relacionado",
            lambda: assert_true(
                relevancia.analisar_hipotese(
                    "dependências arquiteturais"
                )["valor"][
                    "historico_encontrado"
                ] is True,
                "histórico relacionado não foi encontrado",
            ),
        )
        falhas += erro
        testes += total

        analise_hipotese = (
            relevancia.analisar_hipotese(
                "DEPENDÊNCIAS ARQUITETURAIS"
            )
        )

        erro, total = verificar(
            5,
            "busca de hipótese ignora maiúsculas e minúsculas",
            lambda: assert_true(
                analise_hipotese["valor"][
                    "quantidade_relacionada"
                ]
                == 2,
                "busca case-insensitive falhou",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            6,
            "análise combinada aceita necessidade e hipótese",
            lambda: assert_true(
                relevancia.analisar(
                    necessidade=necessidade,
                    hipotese=(
                        "dependências"
                    ),
                )["sucesso"] is True,
                "análise combinada falhou",
            ),
        )
        falhas += erro
        testes += total

        analise_combinada = relevancia.analisar(
            necessidade=necessidade,
            hipotese="dependências",
        )

        erro, total = verificar(
            7,
            "necessidade exata tem precedência sobre hipótese relacionada",
            lambda: assert_true(
                analise_combinada["valor"][
                    "quantidade_direta"
                ] == 2
                and analise_combinada["valor"][
                    "quantidade_relacionada"
                ] == 0,
                "mesmo registro foi duplicado entre categorias",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            8,
            "ausência de histórico não é tratada como prova",
            lambda: assert_true(
                "não prova" in relevancia.analisar_hipotese(
                    "tema completamente ausente"
                )["valor"]["interpretacao"],
                "interpretação da ausência está incorreta",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            9,
            "histórico encontrado não é tratado como verdade",
            lambda: assert_true(
                "não determina a verdade" in relevancia.analisar(
                    necessidade=necessidade
                )["valor"]["interpretacao"],
                "interpretação epistemológica ausente",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            10,
            "entrada vazia é recusada",
            lambda: assert_true(
                relevancia.analisar()[
                    "sucesso"
                ] is False,
                "entrada vazia não foi recusada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            11,
            "necessidade vazia retorna resultado de hipótese válida",
            lambda: assert_true(
                relevancia.analisar(
                    necessidade="",
                    hipotese="dependências",
                )["sucesso"] is True,
                "hipótese válida não foi aceita",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            12,
            "hipótese vazia retorna resultado de necessidade válida",
            lambda: assert_true(
                relevancia.analisar(
                    necessidade=necessidade,
                    hipotese="",
                )["sucesso"] is True,
                "necessidade válida não foi aceita",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            13,
            "registros retornados são cópias isoladas",
            lambda: (
                lambda dados: (
                    dados["valor"][
                        "historico_direto"
                    ][0]["ciclo"].update(
                        {
                            "estado_atual": "alterado"
                        }
                    ),
                    assert_true(
                        relevancia.analisar_necessidade(
                            necessidade
                        )["valor"][
                            "historico_direto"
                        ][0]["ciclo"][
                            "estado_atual"
                        ]
                        != "alterado",
                        "referência interna vazou",
                    ),
                )
            )(
                relevancia.analisar_necessidade(
                    necessidade
                )
            ),
        )
        falhas += erro
        testes += total

        memoria_antes = memoria.listar()

        erro, total = verificar(
            14,
            "análise não modifica a memória",
            lambda: assert_true(
                relevancia.analisar(
                    necessidade=necessidade,
                    hipotese="dependências",
                )["sucesso"] is True
                and memoria.listar()
                == memoria_antes,
                "memória foi modificada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            15,
            "nova instância recupera o mesmo histórico",
            lambda: assert_true(
                RelevanciaHistoricoInvestigacaoNixal(
                    MemoriaInvestigacaoNixal(
                        caminho
                    )
                ).analisar_necessidade(
                    necessidade
                )["valor"][
                    "quantidade_direta"
                ]
                == 2,
                "nova instância perdeu histórico",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            16,
            "não executa capacidades",
            lambda: esperar_erro(
                lambda: relevancia.executar_capacidade(
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
                lambda: relevancia.modificar_arquitetura(
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
                relevancia.promover_conhecimento,
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            19,
            "memória permanece em JSON válido",
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
