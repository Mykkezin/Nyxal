#!/usr/bin/env python3
"""
NIXAL — TESTE M5.2
Processos como entidades do habitat.
"""

from __future__ import annotations

import ast
from pathlib import Path

from nixal_processos_habitat import ProcessosHabitat


BASE_DIR = Path(__file__).resolve().parent
MODULO = BASE_DIR / "nixal_processos_habitat.py"
HABITAT = BASE_DIR / "nixal_habitat.py"
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
    verificar(MODULO.exists(), "módulo de processos do habitat existe")
    verificar(HABITAT.exists(), "adaptador do habitat existe")
    verificar(API.exists(), "API principal existe")

    texto_modulo = MODULO.read_text(encoding="utf-8")
    texto_habitat = HABITAT.read_text(encoding="utf-8")
    texto_api = API.read_text(encoding="utf-8")

    try:
        ast.parse(texto_modulo)
        verificar(True, "nixal_processos_habitat.py possui sintaxe válida")
    except SyntaxError as erro:
        verificar(False, f"nixal_processos_habitat.py possui sintaxe válida: {erro}")

    verificar(
        "ProcessosHabitat" in texto_habitat
        and "processos_habitat" in texto_habitat,
        "HabitatNixOS integra o adaptador de processos",
    )

    verificar(
        '"processos_habitat"' in texto_api
        or "HABITAT_NYXOS" in texto_api,
        "API continua expondo o snapshot do habitat",
    )

    verificar(
        all(
            proibido not in texto_modulo
            for proibido in (
                "subprocess.",
                "os.system(",
                "Popen(",
                ".terminate(",
                ".kill(",
            )
        ),
        "adaptador não contém caminho de controle ou execução externa",
    )

    verificar(
        ProcessosHabitat(limite=999).limite
        == ProcessosHabitat.LIMITE_MAXIMO,
        "limite de exposição respeita o teto de segurança",
    )

    verificar(
        ProcessosHabitat(limite=0).limite
        == ProcessosHabitat.LIMITE_MINIMO,
        "limite de exposição respeita o piso de segurança",
    )

    snapshot = ProcessosHabitat(limite=5).snapshot()

    verificar(
        snapshot.get("sucesso") is True
        and snapshot.get("estado") == "processos_observados",
        "snapshot real de processos foi coletado",
    )

    entidades = snapshot.get("entidades", [])

    verificar(
        snapshot.get("total", 0) >= len(entidades)
        and len(entidades) <= 5,
        "quantidade total e limite de entidades são consistentes",
    )

    campos = {
        "id",
        "pid",
        "nome",
        "estado",
        "uso_cpu_percentual",
        "memoria_rss_percentual",
        "memoria_rss_mb",
    }

    verificar(
        all(
            campos.issubset(entidade.keys())
            for entidade in entidades
        ),
        "entidades possuem o contrato mínimo de identidade e telemetria",
    )

    verificar(
        all(
            isinstance(entidade.get("pid"), int)
            and entidade.get("pid") > 0
            and isinstance(entidade.get("id"), str)
            and entidade.get("id", "").startswith("processo:")
            for entidade in entidades
        ),
        "identidades de processo são sanitizadas",
    )

    verificar(
        all(
            entidade.get("uso_cpu_percentual") is None
            or 0.0 <= entidade["uso_cpu_percentual"] <= 100.0
            for entidade in entidades
        ),
        "telemetria de CPU permanece dentro de 0–100%",
    )

    verificar(
        snapshot.get("persistente") is False
        and snapshot.get("controle_habilitado") is False
        and snapshot.get("modo") == "somente_leitura",
        "snapshot de processos permanece somente leitura e não persistente",
    )

    print()
    print("=" * 64)
    print("TESTE — PROCESSOS DO HABITAT NYXOS M5.2")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
