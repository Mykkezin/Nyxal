#!/usr/bin/env python3
"""Suite determinística consolidada para o Nível 9 / M4."""

from __future__ import annotations

import subprocess
import sys


TESTES = [
    "teste_nivel_9_evolucao_controlada.py",
    "teste_nivel_9_solicitacao_evolucao.py",
    "teste_nivel_9_runtime_solicitacao_evolucao.py",
    "teste_nivel_9_solicitacao_evolucao_remota.py",
    "teste_nivel_9_evolucao_remota.py",
    "teste_nivel_9_runtime_evolucao_remota.py",
    "teste_nivel_9_ciclo_formal_evolucao_integrado.py",
    "teste_integracao_controlada.py",
    "teste_nivel_9_integracao_autorizada.py",
    "teste_nivel_9_integracao_governanca.py",
]


def main() -> int:
    for teste in TESTES:
        print(f"\n>>> {teste}")
        resultado = subprocess.run(
            [sys.executable, teste],
            check=False,
        )
        if resultado.returncode != 0:
            print(f"FALHOU: {teste}")
            return resultado.returncode

    print("\n" + "=" * 64)
    print("SUITE NÍVEL 9 — DETERMINÍSTICA")
    print("=" * 64)
    print("TODOS_OS_TESTES_PASSARAM=OK")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
