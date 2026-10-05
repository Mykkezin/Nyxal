#!/usr/bin/env python3
"""
NIXAL — TESTE M5.1
Observabilidade real e somente leitura do habitat.
"""

from __future__ import annotations

import ast
from pathlib import Path

from nixal_habitat import HabitatNixOS


BASE_DIR = Path(__file__).resolve().parent
API = BASE_DIR / "nyxal_web_api.py"
MODULO = BASE_DIR / "nixal_habitat.py"

TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


def main() -> None:
    verificar(MODULO.exists(), "módulo do habitat existe")
    verificar(API.exists(), "API principal existe")

    texto_modulo = MODULO.read_text(encoding="utf-8")
    texto_api = API.read_text(encoding="utf-8")

    try:
        ast.parse(texto_modulo)
        verificar(True, "nixal_habitat.py possui sintaxe válida")
    except SyntaxError as erro:
        verificar(False, f"nixal_habitat.py possui sintaxe válida: {erro}")

    verificar(
        "somente_leitura" in texto_modulo
        and "perceber_corpo" in texto_modulo,
        "adaptador usa somente a observação corporal existente",
    )

    verificar(
        '"/api/public/status"' in texto_api
        and "HABITAT_NYXOS" in texto_api,
        "API publica o habitat pelo endpoint de status",
    )

    habitat = HabitatNixOS().snapshot()

    verificar(
        habitat.get("sucesso") is True
        and habitat.get("estado") == "habitat_observado",
        "snapshot do habitat foi coletado",
    )

    verificar(
        habitat.get("host", {}).get("modo") == "somente_leitura",
        "snapshot declara modo somente leitura",
    )

    recursos = habitat.get("recursos", {})

    verificar(
        all(
            campo in recursos
            for campo in (
                "cpu",
                "memoria",
                "armazenamento",
                "processos",
                "uptime_segundos",
            )
        ),
        "snapshot contém recursos computacionais fundamentais",
    )

    verificar(
        habitat.get("arquitetura_modificada") is False
        and habitat.get("persistente") is False,
        "snapshot não altera arquitetura nem cria persistência",
    )

    print()
    print("=" * 64)
    print("TESTE — HABITAT NYXOS M5.1")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
