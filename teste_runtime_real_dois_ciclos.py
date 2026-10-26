#!/usr/bin/env python3
"""Prova real do NyxalRuntime: dois ciclos consecutivos sem mensagem humana."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import corpo_nixal
from nixal_runtime import NyxalRuntime


def perceber_corpo_fake(cpu_anterior):
    return (
        {
            "cpu": {"percentual": 12.5},
            "ram": {"percentual": 40.0},
            "temperatura": {"cpu_c": 45.0},
            "gpu": {},
            "armazenamento": {},
            "processos": [],
            "uptime": 123.0,
        },
        {"percentual": 12.5},
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as diretorio:
        base = Path(diretorio)
        estado = base / "estado_runtime.json"
        log = base / "log_runtime.json"
        memoria = base / "memoria_investigacao.json"

        salvar_original = corpo_nixal.salvar_estado_corpo
        corpo_nixal.salvar_estado_corpo = lambda estado_corpo: None
        try:
            runtime = NyxalRuntime(
                perceber_corpo=perceber_corpo_fake,
                arquivo_estado=estado,
                arquivo_log=log,
                arquivo_memoria_investigacao=memoria,
            )

            resultados = runtime.executar(
                max_ciclos=2,
                intervalo_segundos=0.0,
                parar_em_erro=True,
            )
        finally:
            corpo_nixal.salvar_estado_corpo = salvar_original

        assert len(resultados) == 2, resultados
        assert all(item.get("sucesso") is True for item in resultados), resultados
        assert all(item.get("estado") == "ciclo_concluido" for item in resultados), resultados

        ids = [item["ciclo_id"] for item in resultados]
        assert ids[0] != ids[1], ids

        assert estado.exists(), "estado persistente não foi criado"
        assert log.exists(), "log persistente não foi criado"

        log_data = json.loads(log.read_text(encoding="utf-8"))
        assert isinstance(log_data, list)
        assert len(log_data) >= 2, log_data

        log_ids = [item["ciclo_id"] for item in log_data[-2:]]
        assert log_ids == ids, (log_ids, ids)

        for item in resultados:
            valor = item.get("valor", {})
            assert valor.get("arquitetura_modificada") is False
            assert valor.get("conhecimento_permanente") is False

        print("TESTE_RUNTIME_REAL_DOIS_CICLOS_OK")
        print(f"CICLO_1={ids[0]}")
        print(f"CICLO_2={ids[1]}")
        print(f"LOG_CICLOS={len(log_data)}")
        print("INICIO_SEM_MENSAGEM_HUMANA=OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
