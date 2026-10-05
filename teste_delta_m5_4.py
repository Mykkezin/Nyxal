#!/usr/bin/env python3
"""
NYXOS — TESTE M5.4
Eventos Delta de primeira classe.
"""

from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path

from nixal_delta import RegistroDeltaNixOS


BASE_DIR = Path(__file__).resolve().parent
MODULO = BASE_DIR / "nixal_delta.py"
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
    verificar(MODULO.exists(), "módulo Delta existe")
    verificar(RUNTIME.exists(), "Runtime existe")
    verificar(API.exists(), "API existe")

    texto_modulo = MODULO.read_text(encoding="utf-8")
    texto_runtime = RUNTIME.read_text(encoding="utf-8")
    texto_api = API.read_text(encoding="utf-8")

    try:
        ast.parse(texto_modulo)
        verificar(True, "nixal_delta.py possui sintaxe válida")
    except SyntaxError as erro:
        verificar(False, f"nixal_delta.py possui sintaxe válida: {erro}")

    verificar(
        "RegistroDeltaNixOS" in texto_runtime
        and "eventos_delta_nyxos.json" in texto_runtime,
        "Runtime utiliza o registro persistente de Delta",
    )

    verificar(
        "DELTA_NYXOS" in texto_api
        and '"delta"' in texto_api,
        "API pública expõe o contexto Delta",
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
        "Delta não executa comandos nem controla processos",
    )

    with tempfile.TemporaryDirectory(prefix="nyxal-m5-4-") as pasta:
        caminho = Path(pasta) / "eventos_delta_nyxos.json"
        delta = RegistroDeltaNixOS(caminho)

        evento1 = delta.criar_evento(
            tipo="ciclo",
            estado_anterior="inicial",
            estado_novo="ciclo_concluido",
            causa="ciclo_runtime_concluido",
            evidencias=[{"teste": True}],
            ciclo="ciclo-001",
            resultado={"avaliacao": "sucesso"},
        )

        evento2 = delta.criar_evento(
            tipo="ciclo",
            estado_anterior="inicial",
            estado_novo="ciclo_concluido",
            causa="ciclo_runtime_concluido",
            evidencias=[{"teste": True}],
            ciclo="ciclo-001",
            resultado={"avaliacao": "sucesso"},
        )

        verificar(
            evento1["delta_id"] == evento2["delta_id"],
            "identidade Delta é determinística",
        )

        registro = delta.registrar(evento1)
        verificar(
            registro.get("sucesso") is True
            and registro.get("novo") is True,
            "evento Delta é persistido",
        )

        duplicado = delta.registrar(evento2)
        verificar(
            duplicado.get("sucesso") is True
            and duplicado.get("novo") is False
            and delta.quantidade() == 1,
            "registro duplicado não cria segundo evento",
        )

        recarregado = RegistroDeltaNixOS(caminho)
        ultimo = recarregado.ultimo()
        verificar(
            ultimo is not None
            and ultimo.get("delta_id") == evento1.get("delta_id")
            and ultimo.get("estado_anterior") == "inicial"
            and ultimo.get("estado_novo") == "ciclo_concluido",
            "evento sobrevive ao reinício do registro",
        )

        for indice in range(250):
            recarregado.registrar(
                RegistroDeltaNixOS.criar_evento(
                    tipo="estado",
                    estado_anterior=str(indice),
                    estado_novo=str(indice + 1),
                    causa="teste_limite",
                    ciclo=f"ciclo-{indice}",
                )
            )

        verificar(
            recarregado.quantidade() == RegistroDeltaNixOS.MAX_EVENTOS,
            "registro Delta respeita o limite de eventos",
        )

        try:
            json.loads(caminho.read_text(encoding="utf-8"))
            valido = True
        except json.JSONDecodeError:
            valido = False

        verificar(
            valido,
            "arquivo persistido do Delta permanece JSON válido",
        )

    print()
    print("=" * 64)
    print("TESTE — EVENTOS DELTA NYXOS M5.4")
    print("=" * 64)
    print(f"TESTES EXECUTADOS: {TESTES}")
    print(f"FALHAS: {FALHAS}")
    print(f"PASSOU: {FALHAS == 0}")
    print("=" * 64)

    if FALHAS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
