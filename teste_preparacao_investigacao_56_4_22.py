#!/usr/bin/env python3

"""
NIXAL — TESTE DA PREPARAÇÃO CONTEXTUAL DA INVESTIGAÇÃO

Microetapa 56.4.22
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
from nixal_preparacao_investigacao import (
    PreparacaoInvestigacaoNixal,
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

        preparacao = PreparacaoInvestigacaoNixal(
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

        investigacao = {
            "necessidade": (
                "conhecer_dependencias_arquiteturais"
            ),
            "pergunta": (
                "Quais relações de dependência "
                "existem entre os componentes?"
            ),
            "tipo_investigacao": (
                "mapeamento_arquitetural"
            ),
            "evidencia_necessaria": (
                "Relações explicitamente observadas."
            ),
        }

        memoria_antes = memoria.listar()

        erro, total = verificar(
            1,
            "preparação retorna sucesso",
            lambda: assert_true(
                preparacao.preparar(
                    investigacao
                )["sucesso"] is True,
                "preparação falhou",
            ),
        )
        falhas += erro
        testes += total

        resultado = preparacao.preparar(
            investigacao,
            limite_historico=2,
        )

        erro, total = verificar(
            2,
            "investigação original é preservada",
            lambda: assert_true(
                resultado["valor"][
                    "investigacao_original"
                ]
                == investigacao,
                "investigação original foi alterada",
            ),
        )
        falhas += erro
        testes += total

        contextualizada = resultado["valor"][
            "investigacao_contextualizada"
        ]

        erro, total = verificar(
            3,
            "contexto histórico é anexado à investigação",
            lambda: assert_true(
                len(
                    contextualizada[
                        "contexto_historico_relevante"
                    ]
                )
                == 2,
                "contexto histórico não foi anexado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            4,
            "histórico consultado é marcado explicitamente",
            lambda: assert_true(
                contextualizada[
                    "historico_consultado"
                ]
                is True,
                "consulta histórica não foi registrada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            5,
            "histórico encontrado é preservado",
            lambda: assert_true(
                contextualizada[
                    "historico_encontrado"
                ]
                is True,
                "presença do histórico foi perdida",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            6,
            "histórico é explicitamente separado de verdade",
            lambda: assert_true(
                contextualizada[
                    "historico_nao_equivale_a_verdade"
                ]
                is True,
                "distinção epistemológica ausente",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            7,
            "histórico não substitui nova investigação",
            lambda: assert_true(
                contextualizada[
                    "historico_nao_substitui_investigacao"
                ]
                is True,
                "histórico foi tratado como substituto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            8,
            "limite histórico é preservado",
            lambda: assert_true(
                contextualizada[
                    "limite_historico_utilizado"
                ]
                == 2,
                "limite utilizado incorreto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            9,
            "contexto possui origem histórica",
            lambda: assert_true(
                all(
                    item.get(
                        "origem_historica"
                    )
                    for item
                    in contextualizada[
                        "contexto_historico_relevante"
                    ]
                ),
                "origem histórica ausente",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            10,
            "investigação original continua contendo sua necessidade",
            lambda: assert_true(
                contextualizada[
                    "necessidade"
                ]
                == investigacao[
                    "necessidade"
                ],
                "necessidade original foi alterada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            11,
            "investigação original continua contendo sua pergunta",
            lambda: assert_true(
                contextualizada[
                    "pergunta"
                ]
                == investigacao[
                    "pergunta"
                ],
                "pergunta original foi alterada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            12,
            "cópias retornadas são isoladas",
            lambda: (
                lambda dados: (
                    dados["valor"][
                        "investigacao_contextualizada"
                    ]["contexto_historico_relevante"][0][
                        "investigacao"
                    ].update(
                        {
                            "estado_atual": "alterado"
                        }
                    ),
                    assert_true(
                        preparacao.preparar(
                            investigacao
                        )["valor"][
                            "investigacao_contextualizada"
                        ]["contexto_historico_relevante"][0][
                            "investigacao"
                        ]["estado_atual"]
                        != "alterado",
                        "referência interna vazou",
                    ),
                )
            )(
                preparacao.preparar(
                    investigacao
                )
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            13,
            "preparação não modifica a memória",
            lambda: assert_true(
                memoria.listar()
                == memoria_antes,
                "memória foi modificada",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            14,
            "nova instância preserva o contexto",
            lambda: assert_true(
                len(
                    PreparacaoInvestigacaoNixal(
                        MemoriaInvestigacaoNixal(
                            caminho
                        )
                    ).preparar(
                        investigacao,
                        limite_historico=2,
                    )["valor"][
                        "contexto_historico_relevante"
                    ]
                )
                == 2,
                "nova instância não preservou contexto",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            15,
            "pergunta ausente é recusada",
            lambda: assert_true(
                preparacao.preparar(
                    {
                        "necessidade": (
                            "conhecer_dependencias_arquiteturais"
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
            16,
            "limite zero é recusado",
            lambda: assert_true(
                preparacao.preparar(
                    investigacao,
                    limite_historico=0,
                )["sucesso"]
                is False,
                "limite zero não foi recusado",
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            17,
            "investigação não é executada nesta camada",
            lambda: esperar_erro(
                preparacao.executar_investigacao,
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            18,
            "capacidades não são executadas nesta camada",
            lambda: esperar_erro(
                lambda: preparacao.executar_capacidade(
                    "obter_hora"
                ),
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            19,
            "arquitetura não é modificada nesta camada",
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
            20,
            "conhecimento permanente não é promovido",
            lambda: esperar_erro(
                preparacao.promover_conhecimento,
                PermissionError,
            ),
        )
        falhas += erro
        testes += total

        erro, total = verificar(
            21,
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
