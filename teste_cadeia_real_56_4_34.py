#!/usr/bin/env python3

"""
NIXAL — TESTE DA CADEIA REAL DE HIPÓTESE

Fechamento da microetapa 56.4.34

Valida a integração real entre:
    56.4.29 — hipótese → ciclo
    56.4.30 — preparação do teste
    56.4.31 — execução do teste
    56.4.32 — resultado do teste → ciclo
    56.4.33 — avaliação da hipótese
    56.4.34 — avaliação → ciclo

A única fronteira simulada é a saída da 56.4.28,
para que o teste possa começar diretamente na 56.4.29
sem reexecutar a etapa anterior.

A memória usada é temporária e nunca altera o arquivo
persistente real do projeto.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
from typing import Any

from nixal_execucao_formulacao_hipotese import (
    ExecucaoFormulacaoHipoteseNixal,
)
from nixal_integracao_formulacao_ciclo_hipotese import (
    IntegracaoFormulacaoCicloHipoteseNixal,
)
from nixal_preparacao_teste_hipotese import (
    PreparacaoTesteHipoteseNixal,
)
from nixal_execucao_teste_hipotese import (
    ExecucaoTesteHipoteseNixal,
)
from nixal_integracao_teste_ciclo_hipotese import (
    IntegracaoTesteCicloHipoteseNixal,
)
from nixal_execucao_avaliacao_hipotese import (
    ExecucaoAvaliacaoHipoteseNixal,
)
from nixal_integracao_avaliacao_ciclo_hipotese import (
    IntegracaoAvaliacaoCicloHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import (
    CicloMemoriaHipoteseNixal,
)
from nixal_memoria_investigacao import (
    MemoriaInvestigacaoNixal,
)


TOTAL = 0
FALHAS = 0


def check(
    condicao: bool,
    mensagem: str,
) -> None:
    global TOTAL, FALHAS

    TOTAL += 1

    if condicao:
        print(f"[PASS] {TOTAL}. {mensagem}")
    else:
        FALHAS += 1
        print(f"[FAIL] {TOTAL}. {mensagem}")


class ExecutorFormulacaoFalso(ExecucaoFormulacaoHipoteseNixal):
    """
    Simula somente a saída já validada da 56.4.28.
    """

    def __init__(
        self,
        resultado: dict[str, Any],
    ) -> None:
        self._resultado = deepcopy(resultado)
        self.chamadas = 0

    def executar(
        self,
        entrada_preparada: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1
        return deepcopy(self._resultado)


class TestadorDeterministico:
    """
    Executor externo real da 56.4.31 para este teste.
    """

    def __init__(
        self,
        resultado: dict[str, Any],
    ) -> None:
        self._resultado = deepcopy(resultado)
        self.chamadas = 0
        self.entradas: list[dict[str, Any]] = []

    def executar(
        self,
        entrada_teste: dict[str, Any],
    ) -> dict[str, Any]:
        self.chamadas += 1
        self.entradas.append(
            deepcopy(entrada_teste)
        )
        return deepcopy(self._resultado)


def resultado_56_4_28() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "hipotese_provisoria_criada",
        "origem": "execucao_formulacao_hipotese_nixal",
        "valor": {
            "entrada_preparada": {
                "sucesso": True,
                "estado": "entrada_formulacao_preparada",
            },
            "hipotese": {
                "hipotese": (
                    "É possível que existam dependências "
                    "entre componentes."
                ),
                "necessidade": (
                    "conhecer_dependencias_arquiteturais"
                ),
                "pergunta": (
                    "Quais relações de dependência existem?"
                ),
                "estado": "provisoria",
                "confirmada": False,
                "testada": False,
            },
            "hipotese_provisoria": True,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        },
    }


def resultado_teste_externo() -> dict[str, Any]:
    return {
        "sucesso": True,
        "estado": "observacao_realizada",
        "evidencias": [
            {
                "fonte": "teste_deterministico_real",
                "descricao": (
                    "Uma relação de dependência foi observada "
                    "no cenário controlado."
                ),
            }
        ],
        "dados_observados": {
            "relacao_encontrada": True,
        },
        "suporte": True,
        "contraria": False,
        "inconclusivo": False,
    }


def hash_arquivo(
    caminho: Path,
) -> str:
    return hashlib.sha256(
        caminho.read_bytes()
    ).hexdigest()


def main() -> None:
    planta = (
        Path(__file__).resolve().parent
        / "planta_nixal"
        / "planta.json"
    )

    hash_planta_antes = hash_arquivo(
        planta
    )

    with tempfile.TemporaryDirectory() as diretorio:
        caminho_memoria = (
            Path(diretorio)
            / "memoria_investigacao_nixal.json"
        )

        memoria = MemoriaInvestigacaoNixal(
            caminho=caminho_memoria
        )

        ciclo_memoria = CicloMemoriaHipoteseNixal(
            memoria
        )

        executor_formulacao = ExecutorFormulacaoFalso(
            resultado_56_4_28()
        )

        integracao_formulacao = (
            IntegracaoFormulacaoCicloHipoteseNixal(
                executor_formulacao,
                ciclo_memoria,
            )
        )

        entrada_29 = {
            "sucesso": True,
            "estado": "entrada_formulacao_preparada",
            "origem": "preparacao_formulacao_hipotese_nixal",
            "valor": {
                "investigacao": {
                    "necessidade": (
                        "conhecer_dependencias_arquiteturais"
                    ),
                    "pergunta": (
                        "Quais relações de dependência existem?"
                    ),
                },
                "pode_formular_hipotese": True,
            },
        }

        original_29 = deepcopy(
            entrada_29
        )

        resultado_29 = integracao_formulacao.executar(
            entrada_29
        )

        check(
            resultado_29.get("sucesso") is True,
            "1. 56.4.29 integra a hipótese no ciclo real",
        )

        check(
            resultado_29.get("estado")
            == "hipotese_integrada_no_ciclo",
            "2. 56.4.29 retorna estado de hipótese integrada",
        )

        check(
            executor_formulacao.chamadas == 1,
            "3. executor da formulação é acionado uma vez",
        )

        ciclo_29 = resultado_29.get(
            "valor",
            {},
        ).get(
            "ciclo",
            {},
        )

        check(
            ciclo_29.get("estado_atual")
            == "provisoria",
            "4. ciclo real começa como provisório",
        )

        check(
            ciclo_29.get("conhecimento_permanente")
            is False,
            "5. ciclo provisório não promove conhecimento",
        )

        check(
            entrada_29 == original_29,
            "6. entrada da 56.4.29 permanece inalterada",
        )

        preparacao = PreparacaoTesteHipoteseNixal()

        resultado_30 = preparacao.preparar(
            resultado_29
        )

        check(
            resultado_30.get("sucesso") is True,
            "7. 56.4.30 prepara o teste real",
        )

        check(
            resultado_30.get("estado")
            == "entrada_teste_preparada",
            "8. 56.4.30 retorna entrada de teste preparada",
        )

        valor_30 = resultado_30.get(
            "valor",
            {},
        )

        entrada_teste_30 = valor_30.get(
            "entrada_teste",
            {},
        )

        check(
            valor_30.get("teste_preparado") is True,
            "9. teste fica explicitamente preparado",
        )

        check(
            entrada_teste_30.get("estado_hipotese")
            == "provisoria",
            "10. hipótese permanece provisória antes do teste",
        )

        check(
            valor_30.get("resultado_teste_disponivel")
            is False,
            "11. nenhum resultado é inventado na preparação",
        )

        testador = TestadorDeterministico(
            resultado_teste_externo()
        )

        execucao_teste = ExecucaoTesteHipoteseNixal(
            testador
        )

        resultado_31 = execucao_teste.executar(
            resultado_30
        )

        check(
            resultado_31.get("sucesso") is True,
            "12. 56.4.31 executa o teste real",
        )

        check(
            resultado_31.get("estado")
            == "teste_concluido",
            "13. 56.4.31 retorna teste concluído",
        )

        check(
            testador.chamadas == 1,
            "14. testador externo é acionado uma vez",
        )

        valor_31 = resultado_31.get(
            "valor",
            {},
        )

        check(
            valor_31.get("resultado_teste_disponivel")
            is True,
            "15. resultado do teste fica disponível",
        )

        check(
            valor_31.get("hipotese_avaliada")
            is False,
            "16. teste concluído ainda não avalia a hipótese",
        )

        integracao_teste = (
            IntegracaoTesteCicloHipoteseNixal(
                execucao_teste,
                ciclo_memoria,
            )
        )

        resultado_32 = integracao_teste.executar(
            resultado_30
        )

        # A 56.4.32 executa o 56.4.31 internamente.
        # O mesmo testador deve, portanto, contabilizar uma segunda chamada.
        check(
            resultado_32.get("sucesso") is True,
            "17. 56.4.32 integra o resultado ao ciclo real",
        )

        check(
            resultado_32.get("estado")
            == "teste_integrado_no_ciclo",
            "18. 56.4.32 retorna teste integrado no ciclo",
        )

        check(
            testador.chamadas == 2,
            "19. o executor do teste foi reutilizado pela 56.4.32",
        )

        valor_32 = resultado_32.get(
            "valor",
            {},
        )

        ciclo_32 = valor_32.get(
            "ciclo",
            {},
        )

        check(
            ciclo_32.get("estado_atual")
            == "testada",
            "20. ciclo real passa para testada",
        )

        check(
            len(
                ciclo_32.get(
                    "testes",
                    [],
                )
            )
            == 1,
            "21. ciclo real registra um teste",
        )

        check(
            ciclo_32.get("avaliacoes")
            == [],
            "22. nenhuma avaliação existe antes da 56.4.33",
        )

        execucao_avaliacao = ExecucaoAvaliacaoHipoteseNixal()

        resultado_33 = execucao_avaliacao.executar(
            resultado_32
        )

        check(
            resultado_33.get("sucesso") is True,
            "23. 56.4.33 avalia a hipótese real",
        )

        check(
            resultado_33.get("estado")
            == "hipotese_avaliada",
            "24. 56.4.33 retorna hipótese avaliada",
        )

        valor_33 = resultado_33.get(
            "valor",
            {},
        )

        check(
            valor_33.get("estado_avaliacao")
            == "suportada",
            "25. avaliação real produz classificação suportada",
        )

        check(
            valor_33.get("hipotese_avaliada")
            is True,
            "26. hipótese fica marcada como avaliada",
        )

        check(
            valor_33.get("conhecimento_permanente")
            is False,
            "27. avaliação não promove conhecimento permanente",
        )

        integracao_avaliacao = (
            IntegracaoAvaliacaoCicloHipoteseNixal(
                execucao_avaliacao,
                ciclo_memoria,
            )
        )

        resultado_34 = integracao_avaliacao.executar(
            resultado_32
        )

        check(
            resultado_34.get("sucesso") is True,
            "28. 56.4.34 integra a avaliação no ciclo real",
        )

        check(
            resultado_34.get("estado")
            == "avaliacao_integrada_no_ciclo",
            "29. 56.4.34 retorna avaliação integrada",
        )

        valor_34 = resultado_34.get(
            "valor",
            {},
        )

        ciclo_34 = valor_34.get(
            "ciclo",
            {},
        )

        check(
            ciclo_34.get("estado_atual")
            == "suportada",
            "30. ciclo real alcança suportada",
        )

        check(
            len(
                ciclo_34.get(
                    "avaliacoes",
                    [],
                )
            )
            == 1,
            "31. ciclo real registra uma avaliação",
        )

        check(
            ciclo_34.get("conhecimento_permanente")
            is False,
            "32. ciclo real continua sem conhecimento permanente",
        )

        registros = memoria.listar()

        check(
            len(registros) >= 3,
            "33. memória temporária contém os estados persistidos",
        )

        ultimo = registros[-1] if registros else {}

        check(
            ultimo.get("ciclo", {}).get("estado_atual")
            == "suportada",
            "34. último registro persistido está em suportada",
        )

        check(
            ultimo.get("ciclo", {}).get(
                "conhecimento_permanente"
            ) is False,
            "35. persistência não promove conhecimento permanente",
        )

        hash_planta_depois = hash_arquivo(
            planta
        )

        check(
            hash_planta_antes == hash_planta_depois,
            "36. planta arquitetural permanece inalterada",
        )

        check(
            entrada_teste_30.get("teste_executado")
            is False,
            "37. entrada original preparada permanece não executada",
        )

        check(
            valor_32.get("ciclo_anterior", {}).get("estado_atual")
            == "provisoria",
            "38. 56.4.32 preserva o ciclo anterior isolado",
        )

        check(
            valor_34.get("ciclo_anterior", {}).get("estado_atual")
            == "testada",
            "39. 56.4.34 preserva o ciclo testado isolado",
        )

        check(
            valor_34.get("arquitetura_modificada")
            is False,
            "40. cadeia completa não modifica arquitetura",
        )

    print()
    print("=" * 64)
    print(
        f"TESTES EXECUTADOS: {TOTAL}"
    )
    print(
        f"FALHAS: {FALHAS}"
    )
    print(
        f"PASSOU: {FALHAS == 0}"
    )
    print("=" * 64)


if __name__ == "__main__":
    main()
