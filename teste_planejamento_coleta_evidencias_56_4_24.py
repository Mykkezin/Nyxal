#!/usr/bin/env python3

"""
NIXAL — TESTE DO PLANEJAMENTO DA COLETA DE EVIDÊNCIAS

Microetapa 56.4.24
"""

from __future__ import annotations

from copy import deepcopy

from nixal_analise_lacunas_investigacao import (
    AnaliseLacunasInvestigacaoNixal,
)
from nixal_planejamento_coleta_evidencias import (
    FONTES_AUTORIZADAS_INVESTIGACAO_INTERNA,
    PlanejamentoColetaEvidenciasNixal,
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
    planejamento = PlanejamentoColetaEvidenciasNixal()

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
        "contexto_historico_relevante": [],
        "historico_consultado": True,
        "historico_encontrado": False,
    }

    analise_resultado = analise.analisar(
        investigacao
    )

    analise_valor = analise_resultado.get(
        "valor",
        {}
    )

    analise_valor["investigacao_original"] = deepcopy(
        investigacao
    )

    resultado = planejamento.planejar(
        analise_resultado
    )

    erro, total = verificar(
        1,
        "planejamento retorna sucesso",
        lambda: assert_true(
            resultado.get("sucesso") is True,
            "planejamento não retornou sucesso",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        2,
        "estado identifica plano de coleta criado",
        lambda: assert_true(
            resultado.get("estado")
            == "plano_coleta_criado",
            "estado incorreto",
        ),
    )
    falhas += erro
    testes += total

    valor = resultado.get(
        "valor",
        {}
    )

    planos = valor.get(
        "planos",
        []
    )

    erro, total = verificar(
        3,
        "existe um plano para a lacuna",
        lambda: assert_true(
            isinstance(planos, list)
            and len(planos) == 1,
            "quantidade de planos incorreta",
        ),
    )
    falhas += erro
    testes += total

    plano = planos[0]

    erro, total = verificar(
        4,
        "plano nasce da lacuna aberta",
        lambda: assert_true(
            plano["lacuna_origem"]["estado"]
            == "aberta",
            "lacuna de origem não preservada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        5,
        "descrição da lacuna é preservada",
        lambda: assert_true(
            plano["descricao_alvo"]
            == investigacao["evidencia_necessaria"],
            "descrição da lacuna foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        6,
        "tipo da investigação é preservado",
        lambda: assert_true(
            plano["tipo_investigacao"]
            == "mapeamento_arquitetural",
            "tipo incorreto",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        7,
        "fontes arquiteturais declaradas são selecionadas",
        lambda: assert_true(
            plano["fontes_autorizadas"]
            == [
                "listar_arquivos",
                "ler_arquivo",
            ],
            "fontes incorretas",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        8,
        "todas as fontes selecionadas são autorizadas",
        lambda: assert_true(
            set(
                plano["fontes_autorizadas"]
            ).issubset(
                FONTES_AUTORIZADAS_INVESTIGACAO_INTERNA
            ),
            "fonte não autorizada entrou no plano",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        9,
        "estratégia é explicitamente declarada",
        lambda: assert_true(
            plano["estrategia"]
            == "investigacao_interna_controlada",
            "estratégia incorreta",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        10,
        "plano não pode executar",
        lambda: assert_true(
            plano["pode_executar"] is False,
            "planejamento recebeu permissão de execução",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        11,
        "nenhuma evidência foi coletada pelo planejamento",
        lambda: assert_true(
            plano["evidencia_coletada"] is False,
            "planejamento marcou evidência como coletada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        12,
        "investigação original é preservada",
        lambda: assert_true(
            valor["investigacao_original"]
            == investigacao,
            "investigação original foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        13,
        "planejamento não modifica a análise de lacunas",
        lambda: assert_true(
            analise_valor["lacunas_abertas"][0][
                "estado"
            ]
            == "aberta",
            "lacuna foi alterada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        14,
        "planejamento não executa capacidades",
        lambda: esperar_erro(
            lambda: planejamento.executar_capacidade(
                "ler_arquivo"
            ),
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        15,
        "planejamento não executa investigação",
        lambda: esperar_erro(
            planejamento.executar_investigacao,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        16,
        "planejamento não formula hipóteses",
        lambda: esperar_erro(
            planejamento.formular_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        17,
        "planejamento não modifica arquitetura",
        lambda: esperar_erro(
            planejamento.modificar_arquitetura,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        18,
        "planejamento não promove conhecimento permanente",
        lambda: esperar_erro(
            planejamento.promover_conhecimento,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    sem_estrategia = deepcopy(
        analise_resultado
    )

    sem_estrategia["valor"][
        "investigacao_original"
    ]["tipo_investigacao"] = (
        "tipo_nunca_declarado"
    )

    resultado_sem_estrategia = planejamento.planejar(
        sem_estrategia
    )

    erro, total = verificar(
        19,
        "tipo desconhecido não recebe fonte inventada",
        lambda: assert_true(
            resultado_sem_estrategia["valor"][
                "planos"
            ][0]["fontes_autorizadas"]
            == [],
            "fonte foi inventada para tipo desconhecido",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        20,
        "tipo desconhecido fica explicitamente sem estratégia",
        lambda: assert_true(
            resultado_sem_estrategia["valor"][
                "planos"
            ][0]["estado"]
            == "sem_estrategia_declarada",
            "estado incorreto para tipo desconhecido",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        21,
        "análise inválida é recusada",
        lambda: assert_true(
            planejamento.planejar(
                {}
            )["sucesso"]
            is False,
            "análise inválida não foi recusada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        22,
        "sem lacunas abertas o planejamento é recusado",
        lambda: assert_true(
            planejamento.planejar(
                {
                    "sucesso": True,
                    "valor": {
                        "lacunas_abertas": [],
                        "pergunta": "Pergunta",
                        "investigacao_original": {
                            "tipo_investigacao": (
                                "mapeamento_arquitetural"
                            )
                        },
                    },
                }
            )["sucesso"]
            is False,
            "ausência de lacunas não foi recusada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        23,
        "lacuna fechada não entra no plano",
        lambda: assert_true(
            planejamento.planejar(
                {
                    "sucesso": True,
                    "valor": {
                        "lacunas_abertas": [
                            {
                                "estado": "fechada",
                                "descricao": "teste",
                            }
                        ],
                        "pergunta": "Pergunta",
                        "investigacao_original": {
                            "tipo_investigacao": (
                                "mapeamento_arquitetural"
                            )
                        },
                    },
                }
            )["sucesso"]
            is False,
            "lacuna fechada não foi recusada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        24,
        "planejamento preserva separação entre contexto e evidência",
        lambda: assert_true(
            resultado["valor"][
                "historico_nao_evidencia_automatica"
            ]
            is True,
            "separação epistemológica ausente",
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
