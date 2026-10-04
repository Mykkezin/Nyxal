#!/usr/bin/env python3
"""Teste determinístico da solicitação formal de evolução."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_solicitacao_evolucao import SolicitacaoEvolucaoNixal


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="nyxal-solicitacao-evolucao-"
    ) as diretorio:
        raiz = Path(diretorio)
        modulo = SolicitacaoEvolucaoNixal(
            repositorio=raiz / "repo",
            solicitacoes=raiz / "solicitacoes",
        )

        ciclo = {
            "estado_atual": "provisoria",
            "hipotese": (
                "A nova estratégia pode reduzir a latência."
            ),
            "necessidade": "reduzir_latencia",
            "pergunta": (
                "Como reduzir a latência do componente?"
            ),
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

        aguardando = modulo.criar(
            ciclo_hipotese=ciclo,
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
            observacao="Ainda sem artefato.",
        )

        assert aguardando["estado"] == "aguardando_artefato"
        assert aguardando["artefato_origem"] is None
        assert aguardando["execucao_solicitada"] is False
        assert aguardando["execucao_local"] is False
        assert aguardando["autorizacao_explicita"] is False
        assert aguardando["stable_modificada"] is False

        artefato = raiz / "melhoria.py"
        artefato.write_text(
            "print('EXPERIMENTO')\n",
            encoding="utf-8",
        )

        pronta = modulo.criar(
            ciclo_hipotese=ciclo,
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
            artefato_origem=artefato,
            observacao="Artefato preparado.",
        )

        assert pronta["estado"] == "pronta_para_experimento"
        assert pronta["artefato_origem"] == str(
            artefato.resolve()
        )
        assert pronta["execucao_solicitada"] is True
        assert pronta["execucao_local"] is False

        rejeitado = dict(ciclo)
        rejeitado["estado_atual"] = "confirmada"

        try:
            modulo.criar(
                ciclo_hipotese=rejeitado,
                objetivo="x",
                metrica="tempo",
                direcao_melhor="menor",
                baseline=1,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "hipótese não provisória foi aceita"
            )

    print("=" * 64)
    print("TESTE — SOLICITAÇÃO FORMAL DE EVOLUÇÃO")
    print("=" * 64)
    print("HIPOTESE_VALIDADA=OK")
    print("SOLICITACAO_CRIADA=OK")
    print("AGUARDANDO_ARTEFATO=OK")
    print("ARTEFATO_VALIDADO=OK")
    print("HIPOTESE_NAO_CONFIRMADA=OK")
    print("SEM_EXECUCAO_LOCAL=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("STABLE_MODIFICADA=FALSE")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
