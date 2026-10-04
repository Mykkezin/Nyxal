#!/usr/bin/env python3
"""Teste integrado: investigação/hipótese → solicitação → evolução remota."""

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
        prefix="nyxal-ciclo-formal-evolucao-"
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
        memoria_aprendizado = AprendizadoPersistenteNixal(
            raiz / "memoria_aprendizado.json"
        )

        runtime = NyxalRuntime(
            arquivo_estado=raiz / "estado_runtime.json",
            arquivo_log=raiz / "log_runtime.json",
            arquivo_memoria_investigacao=raiz / "memoria_investigacao.json",
            memoria_investigacao=MemoriaInvestigacaoNixal(
                raiz / "memoria_investigacao.json"
            ),
            arquivo_memoria_aprendizado=raiz / "memoria_aprendizado.json",
            memoria_aprendizado=memoria_aprendizado,
            solicitacao_evolucao=solicitacoes,
        )

        hipotese = {
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

        runtime._capturar_hipotese_provisoria(hipotese)

        criado = runtime.criar_solicitacao_evolucao(
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
            observacao="Ciclo integrado de evolução.",
        )

        assert criado["sucesso"] is True
        assert criado["valor"]["estado"] == "aguardando_artefato"

        pronto = solicitacoes.anexar_artefato(
            criado["valor"]["solicitacao_id"],
            artefato,
            observacao="Artefato experimental preparado.",
        )
        assert pronto["estado"] == "pronta_para_experimento"

        evolucao = EvolucaoControladaNixal(
            repositorio=raiz / "repo",
            experimentos=raiz / "experimentos",
            candidatos=raiz / "candidatos",
            propostas=raiz / "propostas",
        )
        laboratorio = LaboratorioRemotoNixal(
            repositorio=raiz / "repo",
        )
        remoto = CicloEvolucaoRemotaNixal(
            evolucao=evolucao,
            laboratorio=laboratorio,
            memoria_aprendizado=memoria_aprendizado,
            solicitacao_evolucao=solicitacoes,
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
                "experimento_id": "exp-integrado",
                "commit_sha": "b" * 40,
                "comparacao": {
                    "aprovado": True,
                    "melhoria_absoluta": 20.0,
                },
                "candidato": {
                    "estado": "candidato"
                },
                "proposta": {
                    "estado": "aguardando_autorizacao"
                },
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        remoto.executar = MethodType(
            fake_executar,
            remoto,
        )
        runtime.evolucao_remota = remoto

        resultado = runtime.executar_solicitacao_evolucao_remota(
            pronto["solicitacao_id"]
        )

        assert resultado["sucesso"] is True
        assert resultado["estado"] == (
            "solicitacao_evolucao_remota_executada"
        )
        assert resultado["persistencia_solicitacao"]["estado"] == (
            "experimento_concluido"
        )

        final = solicitacoes.consultar(
            pronto["solicitacao_id"]
        )
        assert final["estado"] == "experimento_concluido"
        assert final["estado_anterior"] == "experimento_em_execucao"
        assert final["experimento_id"] == "exp-integrado"
        assert final["comparacao"]["aprovado"] is True
        assert final["candidato"]["estado"] == "candidato"
        assert final["proposta"]["estado"] == (
            "aguardando_autorizacao"
        )
        assert final["autorizacao_explicita"] is False
        assert final["integracao_executada"] is False
        assert final["stable_modificada"] is False

        assert len(chamadas) == 1
        assert chamadas[0]["hipotese"] == (
            "A nova estratégia pode reduzir a latência."
        )
        assert chamadas[0]["baseline"] == 100.0
        assert chamadas[0]["artefato_origem"] == str(
            artefato.resolve()
        )

    print("=" * 64)
    print("TESTE — CICLO FORMAL DE EVOLUÇÃO INTEGRADO")
    print("=" * 64)
    print("HIPOTESE_PROVISORIA=OK")
    print("SOLICITACAO_FORMAL=OK")
    print("ARTEFATO_ANEXADO=OK")
    print("EVOLUCAO_REMOTA=OK")
    print("RESULTADO_PERSISTIDO=OK")
    print("CANDIDATO_PROPAGADO=OK")
    print("PROPOSTA_PROPAGADA=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("STABLE_MODIFICADA=FALSE")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
