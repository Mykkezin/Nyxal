#!/usr/bin/env python3
"""Teste do ponto de entrada do loop operacional autônomo."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_loop_autonomo import LoopAutonomoNixal


class RuntimeFalso:
    def __init__(self) -> None:
        self.chamadas = 0

    def executar_ciclo(self) -> dict:
        self.chamadas += 1
        return {
            "sucesso": True,
            "estado": "ciclo_concluido",
            "ciclo_id": f"teste-{self.chamadas}",
            "valor": {
                "arquitetura_modificada": False,
            },
        }


def main() -> int:
    with tempfile.TemporaryDirectory() as diretorio:
        runtime = RuntimeFalso()
        loop = LoopAutonomoNixal(
            runtime=runtime,
            estado_path=Path(diretorio) / "estado.json",
        )

        resultado = loop.executar(ciclos=2)

        assert resultado["sucesso"] is True
        assert resultado["ciclos_solicitados"] == 2
        assert resultado["ciclos_executados"] == 2
        assert resultado["ciclos_concluidos"] == 2
        assert resultado["arquitetura_modificada"] is False
        assert runtime.chamadas == 2

        estado = Path(diretorio) / "estado.json"
        assert estado.exists()

    print("TESTE_LOOP_AUTONOMO_NYXAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
