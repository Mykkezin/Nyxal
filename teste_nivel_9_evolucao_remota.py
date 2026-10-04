#!/usr/bin/env python3
"""Teste determinístico do ciclo integrado de evolução remota."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_evolucao_controlada import EvolucaoControladaNixal
from nixal_evolucao_remota import CicloEvolucaoRemotaNixal


class LaboratorioFalso:
    def __init__(self, resultado: dict) -> None:
        self.resultado = resultado
        self.removida = False
        self.publicou = False
        self.disparou = False

    def publicar_experimento(self, **kwargs):
        self.publicou = True
        origem = Path(kwargs["arquivo_origem"])
        assert origem.is_file()
        return {
            "sucesso": True,
            "estado": "experimento_publicado",
            "experimento_id": kwargs["experimento_id"],
            "branch": "experimento/integracao-teste",
            "commit_sha": "a" * 40,
            "stable_modificada": False,
            "integracao_executada": False,
            "autorizacao_explicita": False,
        }

    def disparar_workflow(self, **kwargs):
        self.disparou = True
        assert kwargs["expected_sha"] == "a" * 40
        return {
            "sucesso": True,
            "estado": "workflow_disparado",
            "experimento_id": kwargs["experimento_id"],
        }

    def aguardar_resultado(self, **kwargs):
        return {
            "sucesso": True,
            "estado": "resultado_recuperado",
            "experimento_id": kwargs["experimento_id"],
            "resultado": dict(self.resultado),
        }

    def remover_branch_experimento(self, branch):
        self.removida = True
        assert branch == "experimento/integracao-teste"
        return {
            "sucesso": True,
            "estado": "branch_experimental_removida",
            "branch": branch,
            "stable_modificada": False,
        }


def executar_caso_aprovado(raiz: Path) -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    arquivo = raiz / "melhoria.py"
    arquivo.write_text(
        "print('EXPERIMENTO')\n",
        encoding="utf-8",
    )

    evolucao = EvolucaoControladaNixal(
        repositorio=raiz / "repo",
        experimentos=raiz / "experimentos",
        candidatos=raiz / "candidatos",
        propostas=raiz / "propostas",
    )
    laboratorio = LaboratorioFalso(
        {
            "experimento_id": "",
            "experiment_sha": "a" * 40,
            "status": "sucesso",
            "experimento_sucesso": True,
            "tempo_execucao_ms": 50.0,
            "stable_modificada": False,
            "autorizacao_explicita": False,
        }
    )

    ciclo = CicloEvolucaoRemotaNixal(
        evolucao=evolucao,
        laboratorio=laboratorio,
        repositorio=raiz / "repo",
    )

    resultado = ciclo.executar(
        limitacao="latencia alta",
        hipotese="a nova implementação reduz a latência",
        objetivo="reduzir tempo de execução",
        metrica="tempo_execucao_ms",
        direcao_melhor="menor",
        baseline=100.0,
        artefato_origem=arquivo,
        descricao="Teste determinístico",
        intervalo_resultado_segundos=1,
    )

    assert resultado["sucesso"] is True
    assert resultado["estado"] == "proposta_criada"
    assert resultado["comparacao"]["aprovado"] is True
    assert resultado["candidato"] is not None
    assert resultado["proposta"] is not None
    assert resultado["autorizacao_explicita"] is False
    assert resultado["integracao_executada"] is False
    assert resultado["stable_modificada"] is False
    assert resultado["branch_removida"] is True
    assert laboratorio.publicou is True
    assert laboratorio.disparou is True
    assert laboratorio.removida is True

    manifesto = Path(resultado["manifesto"])
    assert manifesto.is_file()


def executar_caso_rejeitado(raiz: Path) -> None:
    raiz.mkdir(parents=True, exist_ok=True)
    arquivo = raiz / "regressao.py"
    arquivo.write_text(
        "print('REGRESSAO')\n",
        encoding="utf-8",
    )

    evolucao = EvolucaoControladaNixal(
        repositorio=raiz / "repo",
        experimentos=raiz / "experimentos",
        candidatos=raiz / "candidatos",
        propostas=raiz / "propostas",
    )
    laboratorio = LaboratorioFalso(
        {
            "experimento_id": "",
            "experiment_sha": "a" * 40,
            "status": "sucesso",
            "experimento_sucesso": True,
            "tempo_execucao_ms": 140.0,
            "stable_modificada": False,
            "autorizacao_explicita": False,
        }
    )

    ciclo = CicloEvolucaoRemotaNixal(
        evolucao=evolucao,
        laboratorio=laboratorio,
        repositorio=raiz / "repo",
    )

    resultado = ciclo.executar(
        limitacao="latencia alta",
        hipotese="a alteração piora a latência",
        objetivo="testar regressão",
        metrica="tempo_execucao_ms",
        direcao_melhor="menor",
        baseline=100.0,
        artefato_origem=arquivo,
    )

    assert resultado["sucesso"] is False
    assert resultado["estado"] == "evolucao_rejeitada"
    assert resultado["comparacao"]["aprovado"] is False
    assert resultado["candidato"] is None
    assert resultado["proposta"] is None
    assert resultado["stable_modificada"] is False
    assert resultado["autorizacao_explicita"] is False
    assert resultado["branch_removida"] is True


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="nyxal-ciclo-evolucao-remota-"
    ) as diretorio:
        raiz = Path(diretorio)
        executar_caso_aprovado(raiz / "aprovado")
        executar_caso_rejeitado(raiz / "rejeitado")

    print("=" * 64)
    print("TESTE — CICLO INTEGRADO DE EVOLUÇÃO REMOTA")
    print("=" * 64)
    print("BASELINE=OK")
    print("PUBLICACAO_EXPERIMENTO=OK")
    print("LABORATORIO_REMOTO=OK")
    print("RESULTADO_RECUPERADO=OK")
    print("COMPARACAO=OK")
    print("CANDIDATO=OK")
    print("PROPOSTA=OK")
    print("REJEICAO_REGRESSAO=OK")
    print("SEM_EXECUCAO_LOCAL=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("STABLE_MODIFICADA=FALSE")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
