#!/usr/bin/env python3
"""
NYXOS — TESTE M5.6
Ferramentas e módulos como recursos observáveis.
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from nixal_recursos_habitat import RecursosHabitatNixOS


BASE_DIR = Path(__file__).resolve().parent
MODULO = BASE_DIR / "nixal_recursos_habitat.py"
API = BASE_DIR / "nyxal_web_api.py"
INTERFACE = BASE_DIR / "interface" / "index.html"

TESTES = 0
FALHAS = 0


def verificar(condicao: bool, mensagem: str) -> None:
    global TESTES, FALHAS
    TESTES += 1
    print(f"[{'PASS' if condicao else 'FAIL'}] {TESTES}. {mensagem}")
    if not condicao:
        FALHAS += 1


def main() -> None:
    verificar(MODULO.exists(), "módulo de recursos do habitat existe")
    verificar(API.exists(), "API existe")
    verificar(INTERFACE.exists(), "interface existe")

    texto_modulo = MODULO.read_text(encoding="utf-8")
    texto_api = API.read_text(encoding="utf-8")
    texto_interface = INTERFACE.read_text(encoding="utf-8")

    try:
        ast.parse(texto_modulo)
        verificar(True, "nixal_recursos_habitat.py possui sintaxe válida")
    except SyntaxError as erro:
        verificar(False, f"nixal_recursos_habitat.py possui sintaxe válida: {erro}")

    verificar(
        "RecursosHabitatNixOS" in texto_api
        and '"recursos"' in texto_api,
        "API integra recursos do habitat",
    )

    verificar(
        "recursosHabitat" in texto_interface
        and "ferramentas" in texto_interface
        and "modulos" in texto_interface,
        "interface consome recursos observáveis",
    )

    verificar(
        all(
            proibido not in texto_modulo
            for proibido in (
                "importlib.import_module",
                "__import__(",
                "subprocess.",
                "os.system(",
                "Popen(",
            )
        ),
        "catálogo não executa nem importa módulos dinamicamente",
    )

    with tempfile.TemporaryDirectory(prefix="nyxal-m5-6-") as pasta:
        base = Path(pasta)
        (base / "capacidades_nixal.json").write_text(
            '[{"nome":"teste_tool","descricao":"Ferramenta de teste",'
            '"objetivo":"validar catalogo","argumentos":{},'
            '"dominios":["teste"]}]',
            encoding="utf-8",
        )
        (base / "nixal_teste.py").write_text(
            "# módulo de teste",
            encoding="utf-8",
        )
        (base / "outro.py").write_text(
            "# não deve ser classificado",
            encoding="utf-8",
        )

        recursos = RecursosHabitatNixOS(base).snapshot()

        verificar(
            recursos.get("sucesso") is True
            and recursos.get("estado") == "recursos_observados",
            "snapshot de recursos foi coletado",
        )

        ferramentas = recursos.get("ferramentas", [])
        modulos = recursos.get("modulos", [])

        verificar(
            len(ferramentas) == 1
            and ferramentas[0].get("nome") == "teste_tool",
            "ferramenta declarada é catalogada",
        )

        verificar(
            len(modulos) == 1
            and modulos[0].get("nome") == "nixal_teste",
            "módulo Python do habitat é catalogado",
        )

        verificar(
            recursos.get("execucao_habilitada") is False
            and recursos.get("arquitetura_modificada") is False
            and recursos.get("modo") == "somente_leitura",
            "snapshot de recursos não concede execução nem alteração",
        )

        verificar(
            recursos.get("quantidades", {}).get("ferramentas") == 1
            and recursos.get("quantidades", {}).get("modulos") == 1,
            "contadores do catálogo são consistentes",
        )

    print()
    print("=" * 64)
    print("TESTE — RECURSOS DO HABITAT NYXOS M5.6")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
