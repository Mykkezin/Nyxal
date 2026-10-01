#!/usr/bin/env python3

"""
NIXAL — TESTE DA EXECUÇÃO CONTROLADA DO PLANO DE INVESTIGAÇÃO

Microetapa 56.4.25
"""

from __future__ import annotations

from copy import deepcopy

from nixal_execucao_plano_investigacao import (
    ExecucaoPlanoInvestigacaoNixal,
)


class InvestigadorFalso:
    """Investigador determinístico para o teste da camada de execução."""

    def __init__(
        self,
        resultado: dict,
    ) -> None:
        self.resultado = deepcopy(
            resultado
        )
        self.chamadas: list[dict] = []

    def executar(
        self,
        investigacao: dict,
    ) -> dict:
        self.chamadas.append(
            deepcopy(
                investigacao
            )
        )
        return deepcopy(
            self.resultado
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

    resultado_investigacao = {
        "sucesso": True,
        "estado": "evidencia_coletada",
        "origem": "investigacao_interna_nixal",
        "valor": {
            "pergunta": (
                "Quais relações de dependência existem?"
            ),
            "tipo_investigacao": (
                "mapeamento_arquitetural"
            ),
            "fontes_utilizadas": [
                "listar_arquivos",
                "ler_arquivo",
            ],
            "evidencias": [
                {
                    "fonte": "listar_arquivos",
                    "sucesso": True,
                    "resultado": [
                        "planta_nixal/planta.json"
                    ],
                },
                {
                    "fonte": "ler_arquivo",
                    "sucesso": True,
                    "arquivo": (
                        "nixal_composicao.py"
                    ),
                    "resultado": (
                        "evidencia de teste"
                    ),
                },
            ],
            "conclusao": None,
            "hipotese": None,
        },
    }

    investigador = InvestigadorFalso(
        resultado_investigacao
    )

    executor = ExecucaoPlanoInvestigacaoNixal(
        investigador=investigador
    )

    plano = {
        "id": "plano-1",
        "estado": "planejada",
        "tipo_investigacao": (
            "mapeamento_arquitetural"
        ),
        "pergunta": (
            "Quais relações de dependência existem?"
        ),
        "fontes_autorizadas": [
            "listar_arquivos",
            "ler_arquivo",
        ],
        "pode_executar": False,
        "evidencia_coletada": False,
        "lacuna_origem": {
            "tipo": "evidencia_necessaria",
            "estado": "aberta",
            "descricao": (
                "Relações explicitamente observadas."
            ),
        },
    }

    plano_antes = deepcopy(
        plano
    )

    resultado = executor.executar(
        plano
    )

    erro, total = verificar(
        1,
        "execução retorna sucesso",
        lambda: assert_true(
            resultado.get("sucesso") is True,
            "execução não retornou sucesso",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        2,
        "estado registra plano executado",
        lambda: assert_true(
            resultado.get("estado")
            == "plano_executado",
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
        "plano original é preservado",
        lambda: assert_true(
            valor["plano"]
            == plano_antes,
            "plano foi alterado",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        4,
        "investigação recebe pergunta do plano",
        lambda: assert_true(
            investigador.chamadas[0]["pergunta"]
            == plano["pergunta"],
            "pergunta incorreta enviada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        5,
        "investigação recebe tipo do plano",
        lambda: assert_true(
            investigador.chamadas[0][
                "tipo_investigacao"
            ]
            == plano["tipo_investigacao"],
            "tipo incorreto enviado",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        6,
        "fontes utilizadas pertencem às fontes autorizadas",
        lambda: assert_true(
            set(
                valor["fontes_utilizadas"]
            ).issubset(
                set(
                    plano["fontes_autorizadas"]
                )
            ),
            "fonte não autorizada foi aceita",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        7,
        "evidências são retornadas",
        lambda: assert_true(
            valor["evidencia_coletada"] is True
            and valor["quantidade_evidencias"] == 2,
            "evidências não foram retornadas corretamente",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        8,
        "hipótese não é formulada",
        lambda: assert_true(
            valor["hipotese_formulada"] is False,
            "hipótese foi marcada como formulada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        9,
        "conhecimento permanente não é promovido",
        lambda: assert_true(
            valor[
                "conhecimento_permanente_promovido"
            ]
            is False,
            "conhecimento permanente foi promovido",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        10,
        "arquitetura permanece sem modificação",
        lambda: assert_true(
            valor[
                "arquitetura_modificada"
            ]
            is False,
            "arquitetura foi marcada como modificada",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        11,
        "execução de plano não altera o plano de entrada",
        lambda: assert_true(
            plano
            == plano_antes,
            "plano de entrada foi alterado",
        ),
    )
    falhas += erro
    testes += total

    resultado_investigador_falhou = {
        "sucesso": False,
        "estado": "negado",
        "origem": "investigacao_interna_nixal",
        "valor": None,
        "motivo": "fonte indisponível",
    }

    executor_falha = ExecucaoPlanoInvestigacaoNixal(
        investigador=InvestigadorFalso(
            resultado_investigador_falhou
        )
    )

    erro, total = verificar(
        12,
        "falha do investigador não vira sucesso artificial",
        lambda: assert_true(
            executor_falha.executar(
                plano
            )["sucesso"]
            is False,
            "falha foi mascarada",
        ),
    )
    falhas += erro
    testes += total

    plano_nao_planejado = deepcopy(
        plano
    )
    plano_nao_planejado["estado"] = (
        "sem_estrategia_declarada"
    )

    erro, total = verificar(
        13,
        "plano não planejado é recusado",
        lambda: assert_true(
            executor.executar(
                plano_nao_planejado
            )["sucesso"]
            is False,
            "plano não planejado foi executado",
        ),
    )
    falhas += erro
    testes += total

    plano_permissao = deepcopy(
        plano
    )
    plano_permissao["pode_executar"] = True

    erro, total = verificar(
        14,
        "plano com flag de execução incompatível é recusado",
        lambda: assert_true(
            executor.executar(
                plano_permissao
            )["sucesso"]
            is False,
            "flag incompatível foi aceita",
        ),
    )
    falhas += erro
    testes += total

    plano_tipo_ausente = deepcopy(
        plano
    )
    plano_tipo_ausente["tipo_investigacao"] = None

    erro, total = verificar(
        15,
        "tipo ausente é recusado",
        lambda: assert_true(
            executor.executar(
                plano_tipo_ausente
            )["sucesso"]
            is False,
            "tipo ausente não foi recusado",
        ),
    )
    falhas += erro
    testes += total

    plano_pergunta_ausente = deepcopy(
        plano
    )
    plano_pergunta_ausente["pergunta"] = ""

    erro, total = verificar(
        16,
        "pergunta ausente é recusada",
        lambda: assert_true(
            executor.executar(
                plano_pergunta_ausente
            )["sucesso"]
            is False,
            "pergunta ausente não foi recusada",
        ),
    )
    falhas += erro
    testes += total

    plano_fontes_invalidas = deepcopy(
        plano
    )
    plano_fontes_invalidas[
        "fontes_autorizadas"
    ] = {}

    erro, total = verificar(
        17,
        "fontes em formato inválido são recusadas",
        lambda: assert_true(
            executor.executar(
                plano_fontes_invalidas
            )["sucesso"]
            is False,
            "fontes inválidas não foram recusadas",
        ),
    )
    falhas += erro
    testes += total

    investigador_nao_autorizado = InvestigadorFalso(
        {
            "sucesso": True,
            "estado": "evidencia_coletada",
            "origem": "investigacao_interna_nixal",
            "valor": {
                "fontes_utilizadas": [
                    "fonte_nao_autorizada"
                ],
                "evidencias": [
                    {
                        "fonte": "fonte_nao_autorizada"
                    }
                ],
            },
        }
    )

    executor_nao_autorizado = ExecucaoPlanoInvestigacaoNixal(
        investigador=investigador_nao_autorizado
    )

    erro, total = verificar(
        18,
        "fonte não autorizada é recusada",
        lambda: assert_true(
            executor_nao_autorizado.executar(
                plano
            )["sucesso"]
            is False,
            "fonte não autorizada foi aceita",
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        19,
        "hipóteses continuam bloqueadas",
        lambda: esperar_erro(
            executor.formular_hipotese,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        20,
        "incorporação de conhecimento continua bloqueada",
        lambda: esperar_erro(
            executor.incorporar_conhecimento,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        21,
        "modificação da arquitetura continua bloqueada",
        lambda: esperar_erro(
            executor.modificar_arquitetura,
            PermissionError,
        ),
    )
    falhas += erro
    testes += total

    erro, total = verificar(
        22,
        "promoção de conhecimento continua bloqueada",
        lambda: esperar_erro(
            executor.promover_conhecimento,
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
