#!/usr/bin/env python3
"""Teste da formalização de hipótese em solicitação de evolução no Runtime."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_runtime import NyxalRuntime
from nixal_solicitacao_evolucao import SolicitacaoEvolucaoNixal


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="nyxal-runtime-solicitacao-evolucao-"
    ) as diretorio:
        raiz = Path(diretorio)

        solicitacoes = SolicitacaoEvolucaoNixal(
            repositorio=raiz / "repo",
            solicitacoes=raiz / "solicitacoes",
        )

        runtime = NyxalRuntime(
            arquivo_estado=raiz / "estado_runtime.json",
            arquivo_log=raiz / "log_runtime.json",
            arquivo_memoria_investigacao=raiz / "memoria_investigacao.json",
            arquivo_memoria_aprendizado=raiz / "memoria_aprendizado.json",
            solicitacao_evolucao=solicitacoes,
        )

        runtime._ultimo_ciclo = {
            "sucesso": True,
            "estado": "ciclo_concluido",
            "valor": {
                "hipotese": {
                    "hipotese": "Esta hipótese posterior já foi confirmada.",
                    "necessidade": "outra_necessidade",
                    "pergunta": "Outra pergunta",
                    "estado_atual": "confirmada",
                    "confirmada": True,
                    "testada": True,
                }
            },
        }

        hipotese_provisoria = {
            "hipotese": (
                "A nova estratégia pode reduzir a latência."
            ),
            "necessidade": "reduzir_latencia",
            "pergunta": (
                "Como reduzir a latência do componente?"
            ),
            "estado_atual": "provisoria",
            "tipo": "explicacao_candidata",
            "razao": "Hipótese derivada das evidências.",
            "evidencias_de_suporte": [
                {"id": "e1", "fonte": "benchmark"}
            ],
            "evidencias_contrarias_conhecidas": [],
            "contrarias_avaliadas": False,
            "confianca": "indeterminada",
            "confirmada": False,
            "testada": False,
        }
        runtime._capturar_hipotese_provisoria(
            hipotese_provisoria
        )

        try:
            runtime._capturar_hipotese_provisoria(
                {
                    **hipotese_provisoria,
                    "estado_atual": "confirmada",
                    "confirmada": True,
                }
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "hipótese não provisória deveria ser rejeitada"
            )

        resultado = runtime.criar_solicitacao_evolucao(
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
            observacao="Solicitação derivada do ciclo investigativo.",
        )

        assert resultado["sucesso"] is True
        assert resultado["estado"] == "solicitacao_evolucao_criada"
        assert resultado["valor"]["estado"] == "aguardando_artefato"
        assert resultado["valor"]["necessidade"] == "reduzir_latencia"
        assert resultado["valor"]["pergunta"].startswith("Como reduzir")
        assert resultado["valor"]["hipotese"]["estado"] == "provisoria"
        assert resultado["valor"]["hipotese"]["confirmada"] is False
        assert resultado["valor"]["hipotese"]["testada"] is False
        assert resultado["valor"]["objetivo"] == "reduzir tempo de execução"
        assert resultado["valor"]["metrica"] == "tempo_execucao_ms"
        assert resultado["valor"]["direcao_melhor"] == "menor"
        assert resultado["valor"]["baseline"] == 100.0
        assert resultado["valor"]["execucao_solicitada"] is False
        assert resultado["valor"]["execucao_local"] is False
        assert resultado["autorizacao_explicita"] is False
        assert resultado["integracao_executada"] is False
        assert resultado["stable_modificada"] is False

        erro = NyxalRuntime(
            arquivo_estado=raiz / "estado_runtime_2.json",
            arquivo_log=raiz / "log_runtime_2.json",
            arquivo_memoria_investigacao=raiz / "memoria_investigacao_2.json",
            arquivo_memoria_aprendizado=raiz / "memoria_aprendizado_2.json",
            solicitacao_evolucao=solicitacoes,
        ).criar_solicitacao_evolucao(
            objetivo="x",
            metrica="tempo",
            direcao_melhor="menor",
            baseline=1,
        )

        assert erro["sucesso"] is False
        assert erro["estado"] == "solicitacao_indisponivel"

    print("=" * 64)
    print("TESTE — RUNTIME → SOLICITAÇÃO FORMAL DE EVOLUÇÃO")
    print("=" * 64)
    print("HIPOTESE_EXTRAIDA=OK")
    print("SOLICITACAO_FORMALIZADA=OK")
    print("PLANO_EXPLICITO=OK")
    print("AGUARDANDO_ARTEFATO=OK")
    print("SEM_EXECUCAO_LOCAL=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("STABLE_MODIFICADA=FALSE")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
