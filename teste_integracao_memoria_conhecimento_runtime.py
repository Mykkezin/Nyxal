#!/usr/bin/env python3

"""
Prova da integração da memória de conhecimento ao NyxalRuntime.

O teste garante:
- um candidato consolidado é persistido;
- a persistência sobrevive em arquivo JSON;
- o candidato preserva o contrato de não permanência;
- a arquitetura não é modificada automaticamente.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import corpo_nixal
from nixal_runtime import NyxalRuntime


def perceber_corpo_fake(cpu_anterior):
    return (
        {
            "identidade": {"nome": "Nixal"},
            "corpo": {
                "cpu": {
                    "uso_percentual": 12.0,
                    "estado": "baixa_carga",
                    "calibrada": True,
                },
                "memoria": {"uso_percentual": 20.0},
                "temperaturas_gerais": [],
                "gpu": [],
                "armazenamento": {"uso_percentual": 50.0},
                "processos": 1,
                "uptime_segundos": 10.0,
            },
            "percepcao": {
                "timestamp": "2026-10-01T00:00:00-03:00"
            },
        },
        {"cpu": [1, 2, 3]},
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as diretorio:
        base = Path(diretorio)

        estado = base / "estado_runtime.json"
        log = base / "log_runtime.json"
        memoria_investigacao = (
            base / "memoria_investigacao.json"
        )
        memoria_conhecimento = (
            base / "memoria_conhecimento.json"
        )

        salvar_original = corpo_nixal.salvar_estado_corpo
        corpo_nixal.salvar_estado_corpo = lambda estado_corpo: None

        try:
            runtime = NyxalRuntime(
                perceber_corpo=perceber_corpo_fake,
                arquivo_estado=estado,
                arquivo_log=log,
                arquivo_memoria_investigacao=(
                    memoria_investigacao
                ),
                arquivo_memoria_conhecimento=(
                    memoria_conhecimento
                ),
            )

            resultado = runtime.executar_ciclo()
        finally:
            corpo_nixal.salvar_estado_corpo = salvar_original

        assert resultado.get("sucesso") is True, resultado
        assert resultado.get("estado") == "ciclo_concluido"

        investigacao = resultado["valor"]["investigacao"]
        valor_investigacao = investigacao["valor"]

        consolidacao = valor_investigacao[
            "consolidacao_conhecimento"
        ]
        memoria_resultado = valor_investigacao[
            "memoria_conhecimento"
        ]

        assert (
            consolidacao.get("estado")
            == "candidato_conhecimento_criado"
        )

        candidato = consolidacao["valor"]

        assert memoria_resultado.get("sucesso") is True
        assert memoria_resultado.get("estado") in {
            "persistido",
            "ja_existente",
        }

        assert (
            memoria_resultado.get(
                "conhecimento_permanente"
            )
            is False
        )
        assert (
            memoria_resultado.get(
                "arquitetura_modificada"
            )
            is False
        )

        assert memoria_conhecimento.exists()

        dados = json.loads(
            memoria_conhecimento.read_text(
                encoding="utf-8"
            )
        )

        assert dados["versao"] == "1.0"
        assert len(dados["registros"]) == 1

        registro = dados["registros"][0]
        assert registro["candidato"] == candidato
        assert (
            registro["conhecimento_permanente"]
            is False
        )

        print("=" * 60)
        print(
            "TESTE — INTEGRAÇÃO MEMÓRIA DE CONHECIMENTO + RUNTIME"
        )
        print("=" * 60)
        print("CANDIDATO_CONSOLIDADO=OK")
        print("CANDIDATO_PERSISTIDO=OK")
        print("ARQUIVO_PERSISTENTE=OK")
        print("CONHECIMENTO_PERMANENTE=FALSE")
        print("ARQUITETURA_MODIFICADA=FALSE")
        print("PASSOU: True")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
