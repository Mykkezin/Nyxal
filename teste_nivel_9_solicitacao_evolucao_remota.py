#!/usr/bin/env python3
"""Teste da ponte solicitação formal → evolução remota."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import MethodType
from typing import Any

from nixal_aprendizado_persistente import AprendizadoPersistenteNixal
from nixal_evolucao_controlada import EvolucaoControladaNixal
from nixal_evolucao_remota import CicloEvolucaoRemotaNixal
from nixal_laboratorio_remoto import LaboratorioRemotoNixal
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal
from nixal_runtime import NyxalRuntime
from nixal_solicitacao_evolucao import SolicitacaoEvolucaoNixal


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="nyxal-solicitacao-remota-"
    ) as diretorio:
        raiz = Path(diretorio)

        artefato = raiz / "melhoria.py"
        artefato.write_text(
            "print('EXPERIMENTO')\n",
            encoding="utf-8",
        )

        solicitacoes = SolicitacaoEvolucaoNixal(
            repositorio=raiz / "repo",
            solicitacoes=raiz / "solicitacoes",
        )

        ciclo_hipotese = {
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

        criado = solicitacoes.criar(
            ciclo_hipotese=ciclo_hipotese,
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
        )
        pronto = solicitacoes.anexar_artefato(
            criado["solicitacao_id"],
            artefato,
        )

        evolucao = EvolucaoControladaNixal(
            repositorio=raiz / "repo",
            experimentos=raiz / "experimentos",
            candidatos=raiz / "candidatos",
            propostas=raiz / "propostas",
        )
        laboratorio = LaboratorioRemotoNixal(
            repositorio=raiz / "repo",
        )
        memoria = AprendizadoPersistenteNixal(
            raiz / "memoria_aprendizado.json"
        )

        remoto = CicloEvolucaoRemotaNixal(
            evolucao=evolucao,
            laboratorio=laboratorio,
            memoria_aprendizado=memoria,
            repositorio=raiz / "repo",
        )

        chamadas: list[dict[str, Any]] = []

        def fake_executar(
            self: CicloEvolucaoRemotaNixal,
            **kwargs: Any,
        ) -> dict[str, Any]:
            chamadas.append(dict(kwargs))
            return {
                "sucesso": True,
                "estado": "proposta_criada",
                "experimento_id": "exp-teste",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        remoto.executar = MethodType(
            fake_executar,
            remoto,
        )

        resultado = remoto.executar_solicitacao(
            pronto,
            descricao="Teste da ponte formal → remoto.",
        )

        assert resultado["sucesso"] is True
        assert resultado["estado"] == "solicitacao_executada"
        assert resultado["solicitacao_id"] == pronto["solicitacao_id"]
        assert resultado["autorizacao_explicita"] is False
        assert resultado["integracao_executada"] is False
        assert resultado["stable_modificada"] is False
        assert len(chamadas) == 1
        assert chamadas[0]["limitacao"] == "reduzir_latencia"
        assert chamadas[0]["hipotese"] == (
            "A nova estratégia pode reduzir a latência."
        )
        assert chamadas[0]["objetivo"] == "reduzir tempo de execução"
        assert chamadas[0]["metrica"] == "tempo_execucao_ms"
        assert chamadas[0]["direcao_melhor"] == "menor"
        assert chamadas[0]["baseline"] == 100.0
        assert chamadas[0]["artefato_origem"] == str(
            artefato.resolve()
        )

        aguardando = dict(pronto)
        aguardando["estado"] = "aguardando_artefato"
        chamadas.clear()
        rejeitada = remoto.executar_solicitacao(
            aguardando
        )
        assert rejeitada["sucesso"] is False
        assert rejeitada["estado"] == "solicitacao_nao_pronta"
        assert chamadas == []

        runtime = NyxalRuntime(
            arquivo_estado=raiz / "estado_runtime.json",
            arquivo_log=raiz / "log_runtime.json",
            arquivo_memoria_investigacao=raiz / "memoria_investigacao.json",
            memoria_investigacao=MemoriaInvestigacaoNixal(
                raiz / "memoria_investigacao.json"
            ),
            arquivo_memoria_aprendizado=raiz / "memoria_aprendizado.json",
            memoria_aprendizado=memoria,
            evolucao_remota=remoto,
            solicitacao_evolucao=solicitacoes,
        )

        ponte = runtime.executar_solicitacao_evolucao_remota(
            pronto["solicitacao_id"]
        )

        assert ponte["sucesso"] is True
        assert ponte["estado"] == (
            "solicitacao_evolucao_remota_executada"
        )
        assert ponte["solicitacao_id"] == pronto["solicitacao_id"]
        assert ponte["autorizacao_explicita"] is False
        assert ponte["integracao_executada"] is False
        assert ponte["stable_modificada"] is False
        assert ponte["persistencia_solicitacao"]["estado"] == (
            "experimento_concluido"
        )
        solicitacao_final = solicitacoes.consultar(
            pronto["solicitacao_id"]
        )
        assert solicitacao_final["estado"] == "experimento_concluido"
        assert solicitacao_final["resultado_experimento"]["sucesso"] is True
        assert solicitacao_final["autorizacao_explicita"] is False
        assert solicitacao_final["integracao_executada"] is False
        assert solicitacao_final["stable_modificada"] is False
        assert len(chamadas) == 1

    print("=" * 64)
    print("TESTE — SOLICITAÇÃO FORMAL → EVOLUÇÃO REMOTA")
    print("=" * 64)
    print("SOLICITACAO_PRONTA=OK")
    print("DELEGACAO_REMOTA=OK")
    print("PARAMETROS_PRESERVADOS=OK")
    print("BLOQUEIO_SOLICITACAO_INCOMPLETA=OK")
    print("RUNTIME_INTEGRADO=OK")
    print("SEM_EXECUCAO_LOCAL=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("STABLE_MODIFICADA=FALSE")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
