#!/usr/bin/env python3
"""Prova do Nível 8: aprendizado persistente é usado pelo ciclo seguinte."""

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


def executar_um_ciclo(
    estado,
    log,
    memoria_investigacao,
    memoria_aprendizado,
):
    runtime = NyxalRuntime(
        perceber_corpo=perceber_corpo_fake,
        arquivo_estado=estado,
        arquivo_log=log,
        arquivo_memoria_investigacao=memoria_investigacao,
        arquivo_memoria_aprendizado=memoria_aprendizado,
    )

    resultado = runtime.executar(
        max_ciclos=1,
        intervalo_segundos=0.0,
        parar_em_erro=True,
    )[0]

    assert resultado.get("sucesso") is True, resultado
    assert resultado.get("estado") == "ciclo_concluido", resultado

    return resultado


def main() -> int:
    with tempfile.TemporaryDirectory() as diretorio:
        base = Path(diretorio)

        estado = base / "estado_runtime.json"
        log = base / "log_runtime.json"
        memoria_investigacao = base / "memoria_investigacao.json"
        memoria_aprendizado = base / "memoria_aprendizado.json"

        salvar_original = corpo_nixal.salvar_estado_corpo
        corpo_nixal.salvar_estado_corpo = (
            lambda estado_corpo: None
        )

        try:
            primeiro = executar_um_ciclo(
                estado,
                log,
                memoria_investigacao,
                memoria_aprendizado,
            )
            segundo = executar_um_ciclo(
                estado,
                log,
                memoria_investigacao,
                memoria_aprendizado,
            )
        finally:
            corpo_nixal.salvar_estado_corpo = salvar_original

        assert primeiro["ciclo_id"] != segundo["ciclo_id"]

        aprendizado_primeiro = (
            primeiro["valor"]["aprendizado"]["valor"]
        )
        contexto_segundo = (
            segundo["valor"]["aprendizado_anterior"]
        )

        assert aprendizado_primeiro["id"]
        assert isinstance(
            aprendizado_primeiro["conhecimento"],
            dict,
        )
        assert isinstance(
            aprendizado_primeiro["cristal"],
            dict,
        )

        assert contexto_segundo["disponivel"] is True
        assert contexto_segundo["aplicado_no_ciclo_atual"] is True
        assert (
            contexto_segundo["ciclo_origem"]
            == primeiro["ciclo_id"]
        )
        assert (
            contexto_segundo["aprendizado_id"]
            == aprendizado_primeiro["id"]
        )

        decisao_aprendizado = (
            segundo["valor"]["decisao"]["aprendizado_considerado"]
        )

        assert decisao_aprendizado["disponivel"] is True
        assert (
            decisao_aprendizado["aprendizado_id"]
            == aprendizado_primeiro["id"]
        )

        memoria = json.loads(
            memoria_aprendizado.read_text(
                encoding="utf-8"
            )
        )

        assert len(memoria["aprendizados"]) == 2

        assert all(
            item.get("conhecimento_permanente") is False
            for item in memoria["aprendizados"]
        )
        assert all(
            item.get("arquitetura_modificada") is False
            for item in memoria["aprendizados"]
        )

        log_data = json.loads(
            log.read_text(encoding="utf-8")
        )
        assert len(log_data) >= 2

        print("TESTE_NIVEL_8_APRENDIZADO_PERSISTENTE_OK")
        print(f"CICLO_ORIGEM={primeiro['ciclo_id']}")
        print(f"CICLO_APRENDIZ={segundo['ciclo_id']}")
        print(
            f"APRENDIZADO_ID={aprendizado_primeiro['id']}"
        )
        print("PERSISTENCIA_ENTRE_RUNTIME=OK")
        print("CRISTAL_PRESENTE=OK")
        print("APRENDIZADO_USADO_NO_CICLO_SEGUINTE=OK")
        print("ARQUITETURA_MODIFICADA=FALSE")
        print("CONHECIMENTO_PERMANENTE=FALSE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
