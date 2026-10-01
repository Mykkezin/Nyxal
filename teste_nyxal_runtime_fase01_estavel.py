#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_runtime import NyxalRuntime


TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    if not condicao:
        FALHAS += 1
        print(f"FALHA: {mensagem}")


class PercepcaoDeterministica:
    def __init__(self) -> None:
        self.chamadas = 0

    def __call__(self, cpu_anterior=None):
        self.chamadas += 1
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
                "percepcao": {"timestamp": "2026-10-01T00:00:00-03:00"},
            },
            {"cpu": [1, 2, 3]},
        )


def construir() -> tuple[NyxalRuntime, PercepcaoDeterministica, Path, Path]:
    temporario = TemporaryDirectory()
    base = Path(temporario.name)

    # Mantém a TemporaryDirectory viva através do atributo do runtime.
    percepcao = PercepcaoDeterministica()
    runtime = NyxalRuntime(
        perceber_corpo=percepcao,
        arquivo_estado=base / "estado_runtime.json",
        arquivo_log=base / "log_runtime.json",
    )
    runtime._tmpdir = temporario
    return runtime, percepcao, base / "estado_runtime.json", base / "log_runtime.json"


def main() -> None:
    runtime, percepcao, arquivo_estado, arquivo_log = construir()

    verificar(runtime.VERSAO == "fase_01", "versão da Fase 01")
    verificar("registrar_estado_corpo" in runtime.ACOES_AUTORIZADAS, "ação autorizada registrada")

    resultado = runtime.executar_ciclo()

    verificar(resultado.get("sucesso") is True, "ciclo executado com sucesso")
    verificar(resultado.get("estado") == "ciclo_concluido", "ciclo concluído")
    verificar(percepcao.chamadas == 1, "percepção chamada uma vez")
    verificar(arquivo_estado.exists(), "estado do runtime persistido")
    verificar(arquivo_log.exists(), "log do runtime persistido")

    estado = json.loads(arquivo_estado.read_text(encoding="utf-8"))
    log = json.loads(arquivo_log.read_text(encoding="utf-8"))

    verificar(isinstance(estado, dict), "estado é objeto JSON")
    verificar(isinstance(log, list), "log é lista JSON")
    verificar(len(log) == 1, "primeiro ciclo registrado no log")
    verificar(
        estado["ultimo_ciclo"]["valor"]["conhecimento_permanente"] is False,
        "conhecimento permanente permanece falso",
    )
    verificar(
        estado["ultimo_ciclo"]["valor"]["arquitetura_modificada"] is False,
        "arquitetura permanece inalterada",
    )

    etapas = resultado["valor"]["etapas"]
    nomes = [item.get("etapa") for item in etapas if isinstance(item, dict)]

    verificar("percepcao" in nomes, "etapa de percepção registrada")
    verificar("estado_interno" in nomes, "etapa de estado interno registrada")
    verificar("diagnostico" in nomes, "etapa de diagnóstico registrada")
    verificar("necessidades" in nomes, "etapa de necessidades registrada")
    verificar("decisao" in nomes, "etapa de decisão registrada")
    verificar("acao" in nomes, "etapa de ação registrada")
    verificar("resultado" in nomes, "etapa de resultado registrada")

    resultados = runtime.executar(
        max_ciclos=2,
        intervalo_segundos=0.0,
    )
    verificar(len(resultados) == 2, "dois ciclos executados")
    verificar(all(item.get("sucesso") is True for item in resultados), "segundo ciclo também concluído")

    log_final = json.loads(arquivo_log.read_text(encoding="utf-8"))
    verificar(len(log_final) == 3, "três ciclos totais no log")

    print("=" * 60)
    print("TESTE — NYXAL RUNTIME FASE 01")
    print("=" * 60)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 60)

    runtime._tmpdir.cleanup()

    raise SystemExit(0 if FALHAS == 0 else 1)


if __name__ == "__main__":
    main()
