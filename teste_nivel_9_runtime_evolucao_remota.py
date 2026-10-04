#!/usr/bin/env python3
"""Teste da ponte entre NyxalRuntime e o ciclo de evolução remota."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_aprendizado_persistente import AprendizadoPersistenteNixal
from nixal_evolucao_remota import CicloEvolucaoRemotaNixal
from nixal_runtime import NyxalRuntime


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="nyxal-runtime-evolucao-bridge-"
    ) as diretorio:
        raiz = Path(diretorio)

        memoria = AprendizadoPersistenteNixal(
            raiz / "memoria_aprendizado.json"
        )

        ciclo = CicloEvolucaoRemotaNixal(
            repositorio=raiz / "repo",
            memoria_aprendizado=memoria,
        )

        chamadas = []

        def executar_fake(**kwargs):
            chamadas.append(dict(kwargs))
            return {
                "sucesso": True,
                "estado": "proposta_criada",
                "experimento_id": "evolucao-runtime-test",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        ciclo.executar = executar_fake

        runtime = NyxalRuntime(
            arquivo_estado=raiz / "estado_runtime.json",
            arquivo_log=raiz / "log_runtime.json",
            arquivo_memoria_investigacao=raiz / "memoria_investigacao.json",
            memoria_aprendizado=memoria,
            evolucao_remota=ciclo,
        )

        arquivo = raiz / "melhoria.py"
        arquivo.write_text(
            "print('EXPERIMENTO')\n",
            encoding="utf-8",
        )

        resultado = runtime.executar_evolucao_remota(
            limitacao="latencia alta",
            hipotese="a alteração reduz a latência",
            objetivo="reduzir tempo de execução",
            metrica="tempo_execucao_ms",
            direcao_melhor="menor",
            baseline=100.0,
            artefato_origem=arquivo,
            arquivo_destino="experimento.py",
            descricao="Ponte Runtime → Evolução Remota",
            timeout_seconds=30,
            timeout_resultado_segundos=120,
            intervalo_resultado_segundos=2,
        )

        assert resultado["sucesso"] is True
        assert resultado["estado"] == "evolucao_remota_executada"
        assert resultado["autorizacao_explicita"] is False
        assert resultado["integracao_executada"] is False
        assert resultado["stable_modificada"] is False
        assert len(chamadas) == 1

        chamada = chamadas[0]
        assert chamada["limitacao"] == "latencia alta"
        assert chamada["hipotese"] == "a alteração reduz a latência"
        assert chamada["objetivo"] == "reduzir tempo de execução"
        assert chamada["metrica"] == "tempo_execucao_ms"
        assert chamada["direcao_melhor"] == "menor"
        assert chamada["baseline"] == 100.0
        assert chamada["artefato_origem"] == arquivo
        assert chamada["arquivo_destino"] == "experimento.py"
        assert chamada["timeout_seconds"] == 30
        assert chamada["timeout_resultado_segundos"] == 120
        assert chamada["intervalo_resultado_segundos"] == 2

        assert runtime.evolucao_remota is ciclo

    print("=" * 64)
    print("TESTE — PONTE RUNTIME → EVOLUÇÃO REMOTA")
    print("=" * 64)
    print("INJECAO_CICLO=OK")
    print("DELEGACAO_EXPLICITA=OK")
    print("PARAMETROS_PRESERVADOS=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("STABLE_MODIFICADA=FALSE")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
