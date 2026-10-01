#!/usr/bin/env python3

"""
NIXAL / NYXAL — OBSERVADOR DE DESENVOLVIMENTO

Responsabilidade:
    observar continuamente a branch de desenvolvimento e acionar
    o CoordenadorDesenvolvimentoNixal quando houver trabalho remoto.

Este componente NÃO:
    - escreve código;
    - faz merge;
    - altera main;
    - força refs;
    - executa comandos arbitrários;
    - publica alterações.

Fluxo:
    observação
        ↓
    coordenador
        ↓
    fetch/pull fast-forward
        ↓
    validação
        ↓
    testes
        ↓
    resultado
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from nixal_coordenador_desenvolvimento import (
    CoordenadorDesenvolvimentoNixal,
)


class ObservadorDesenvolvimentoNixal:
    def __init__(
        self,
        repositorio: str | Path | None = None,
        branch: str = "desenvolvimento/mcp-bridge",
        intervalo: float = 30.0,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )

        self.branch = branch
        self.intervalo = float(intervalo)

        self.coordenador = (
            CoordenadorDesenvolvimentoNixal(
                repositorio=self.repositorio,
                branch=self.branch,
            )
        )

        self.ativo = True
        self.ultimo_estado: dict | None = None

    def parar(self) -> None:
        """Solicita encerramento do observador."""
        self.ativo = False

    def ciclo(self) -> dict:
        """Executa uma única verificação."""
        resultado = (
            self.coordenador.executar_ciclo()
        )

        self.ultimo_estado = resultado

        return resultado

    def iniciar(self) -> None:
        """Executa observação contínua."""
        print(
            json.dumps(
                {
                    "estado": "observador_iniciado",
                    "repositorio": str(
                        self.repositorio
                    ),
                    "branch": self.branch,
                    "intervalo_segundos": self.intervalo,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        while self.ativo:
            inicio = time.monotonic()

            try:
                resultado = self.ciclo()

                print(
                    json.dumps(
                        resultado,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    flush=True,
                )

            except Exception as erro:
                erro_resultado = {
                    "estado": "erro_no_observador",
                    "erro": str(erro),
                    "ciclo_sucesso": False,
                }

                self.ultimo_estado = (
                    erro_resultado
                )

                print(
                    json.dumps(
                        erro_resultado,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    flush=True,
                )

            decorrido = (
                time.monotonic() - inicio
            )

            restante = max(
                0.0,
                self.intervalo - decorrido,
            )

            if self.ativo and restante > 0:
                time.sleep(restante)


if __name__ == "__main__":
    observador = (
        ObservadorDesenvolvimentoNixal(
            intervalo=30.0,
        )
    )

    try:
        observador.iniciar()

    except KeyboardInterrupt:
        observador.parar()

        print(
            json.dumps(
                {
                    "estado": (
                        "observador_encerrado"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
