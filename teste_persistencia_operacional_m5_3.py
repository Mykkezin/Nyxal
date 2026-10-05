#!/usr/bin/env python3
"""
NIXOS — TESTE M5.3
Persistência operacional e continuidade entre reinícios.
"""

from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

from nixal_persistencia_operacional import PersistenciaOperacionalNixOS


BASE_DIR = Path(__file__).resolve().parent
MODULO = BASE_DIR / "nixal_persistencia_operacional.py"
RUNTIME = BASE_DIR / "nixal_runtime.py"
API = BASE_DIR / "nyxal_web_api.py"

TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


def main() -> None:
    verificar(MODULO.exists(), "módulo de persistência operacional existe")
    verificar(RUNTIME.exists(), "Runtime existe")
    verificar(API.exists(), "API existe")

    texto_modulo = MODULO.read_text(encoding="utf-8")
    texto_runtime = RUNTIME.read_text(encoding="utf-8")
    texto_api = API.read_text(encoding="utf-8")

    try:
        ast.parse(texto_modulo)
        verificar(True, "nixal_persistencia_operacional.py possui sintaxe válida")
    except SyntaxError as erro:
        verificar(False, f"nixal_persistencia_operacional.py possui sintaxe válida: {erro}")

    verificar(
        "PersistenciaOperacionalNixOS" in texto_runtime
        and "estado_nyxos_operacional.json" in texto_runtime,
        "Runtime utiliza a camada de persistência operacional",
    )

    verificar(
        "PERSISTENCIA_OPERACIONAL" in texto_api
        and '"persistencia_operacional"' in texto_api,
        "API expõe o contexto persistido sem depender do GET para gravar",
    )

    verificar(
        all(
            proibido not in texto_modulo
            for proibido in (
                "subprocess.",
                "os.system(",
                "Popen(",
                "terminate(",
                "kill(",
            )
        ),
        "camada de persistência não executa comandos nem controla processos",
    )

    with tempfile.TemporaryDirectory(prefix="nyxal-m5-3-") as pasta:
        caminho = Path(pasta) / "estado_nyxos_operacional.json"

        primeira = PersistenciaOperacionalNixOS(caminho)
        verificar(
            primeira.contexto()["inicializacoes"] == 1,
            "primeira inicialização cria continuidade operacional",
        )

        ciclo = {
            "ciclo_id": "teste-ciclo-001",
            "estado": "ciclo_concluido",
            "sucesso": True,
            "iniciado_em": "2026-10-05T00:00:00+00:00",
            "concluido_em": "2026-10-05T00:00:01+00:00",
        }

        habitat = {
            "estado": "habitat_observado",
            "origem": "teste",
            "versao": "5.2.0",
            "host": {
                "sistema": "Linux",
                "release": "teste",
                "arquitetura": "x86_64",
            },
            "recursos": {
                "cpu": {
                    "uso_percentual": 12.5,
                    "estado": "baixa_carga",
                },
                "memoria": {
                    "uso_percentual": 42.0,
                    "usado_gb": 6.0,
                    "total_gb": 16.0,
                },
                "armazenamento": {
                    "uso_percentual": 61.0,
                    "estado": "normal",
                },
                "processos": 100,
                "uptime_segundos": 20.0,
                "processos_habitat": {
                    "sucesso": True,
                    "estado": "processos_observados",
                    "total": 100,
                    "limite": 12,
                    "entidades": [
                        {
                            "id": "processo:1:2",
                            "pid": 1,
                            "nome": "init",
                            "estado": "S",
                            "uso_cpu_percentual": 0.1,
                            "memoria_rss_mb": 1.2,
                        }
                    ],
                },
            },
            "timestamp": "2026-10-05T00:00:00+00:00",
        }

        registro = primeira.registrar(
            ciclo=ciclo,
            habitat=habitat,
            estado="ciclo_concluido",
        )
        verificar(
            registro.get("sucesso") is True,
            "registro operacional é persistido",
        )

        segunda = PersistenciaOperacionalNixOS(caminho)
        contexto = segunda.contexto()

        verificar(
            contexto.get("inicializacoes") == 2,
            "novo processo restaura e incrementa a contagem de inicializações",
        )
        verificar(
            contexto.get("ultimo_ciclo", {}).get("ciclo_id")
            == "teste-ciclo-001",
            "último ciclo sobrevive ao reinício",
        )
        verificar(
            contexto.get("ultimo_habitat", {}).get("recursos", {})
            .get("processos")
            == 100,
            "última observação do habitat sobrevive ao reinício",
        )

        for indice in range(60):
            segunda.registrar(
                estado=f"teste_{indice}",
            )

        recarregado = segunda.recarregar()
        verificar(
            recarregado.get("quantidade_historico") == 50,
            "histórico é limitado ao máximo definido",
        )

        caminho.write_text(
            "{ arquivo corrompido",
            encoding="utf-8",
        )

        terceira = PersistenciaOperacionalNixOS(caminho)
        contexto_corrompido = terceira.contexto()
        verificar(
            contexto_corrompido.get("inicializacoes") == 1
            and contexto_corrompido.get("ultimo_ciclo") is None,
            "arquivo corrompido não impede nova inicialização segura",
        )

        try:
            json.loads(caminho.read_text(encoding="utf-8"))
            json_valido = True
        except json.JSONDecodeError:
            json_valido = False

        verificar(
            json_valido,
            "nova persistência após corrupção mantém JSON válido",
        )

    print()
    print("=" * 64)
    print("TESTE — PERSISTÊNCIA OPERACIONAL NYXOS M5.3")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
