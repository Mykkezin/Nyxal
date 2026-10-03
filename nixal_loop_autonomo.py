#!/usr/bin/env python3
"""
NYXAL — LOOP OPERACIONAL AUTÔNOMO

Camada de inicialização do Runtime.
Não substitui nixal_runtime.py: apenas transforma o Runtime existente
em um processo que pode iniciar sem mensagem humana.

Garantias:
- usa o NyxalRuntime existente;
- não altera código durante o ciclo;
- registra cada ciclo concluído;
- interrompe em erro quando solicitado;
- mantém arquitetura_modificada=False nesta etapa;
- serve como ponto de entrada para a futura evolução controlada.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nixal_runtime import NyxalRuntime


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_ESTADO = BASE_DIR / "estado_loop_autonomo_nixal.json"


def agora() -> str:
    return datetime.now(timezone.utc).isoformat()


class LoopAutonomoNixal:
    """Orquestra ciclos do Runtime sem depender de entrada humana."""

    VERSAO = "1.0"

    def __init__(
        self,
        runtime: NyxalRuntime | None = None,
        estado_path: Path = ARQUIVO_ESTADO,
    ) -> None:
        if runtime is None:
            from nixal_runtime import NyxalRuntime

            runtime = NyxalRuntime()
        self.runtime = runtime
        self.estado_path = Path(estado_path)

    def _salvar(self, estado: dict[str, Any]) -> None:
        self.estado_path.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.estado_path.with_suffix(".tmp")
        temporario.write_text(
            json.dumps(estado, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporario.replace(self.estado_path)

    def executar(
        self,
        ciclos: int = 2,
        intervalo_segundos: float = 0.0,
        parar_em_erro: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(ciclos, int) or ciclos < 1:
            raise ValueError("ciclos deve ser inteiro >= 1")

        if intervalo_segundos < 0:
            raise ValueError("intervalo_segundos não pode ser negativo")

        inicio = agora()
        resultados: list[dict[str, Any]] = []

        for indice in range(1, ciclos + 1):
            resultado = self.runtime.executar_ciclo()
            resultados.append(resultado)

            if parar_em_erro and resultado.get("sucesso") is not True:
                break

            if indice < ciclos and intervalo_segundos:
                time.sleep(intervalo_segundos)

        concluidos = sum(
            1 for item in resultados if item.get("sucesso") is True
        )
        sucesso = (
            len(resultados) == ciclos
            and concluidos == ciclos
        )

        estado = {
            "sucesso": sucesso,
            "estado": (
                "loop_concluido"
                if sucesso
                else "loop_interrompido"
            ),
            "origem": "nixal_loop_autonomo",
            "versao": self.VERSAO,
            "iniciado_em": inicio,
            "concluido_em": agora(),
            "ciclos_solicitados": ciclos,
            "ciclos_executados": len(resultados),
            "ciclos_concluidos": concluidos,
            "arquitetura_modificada": False,
            "resultados": resultados,
        }

        self._salvar(estado)
        return estado


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa o Runtime Nyxal sem mensagem humana."
    )
    parser.add_argument(
        "--ciclos",
        type=int,
        default=2,
        help="Quantidade de ciclos a executar (padrão: 2).",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=0.0,
        help="Intervalo em segundos entre ciclos.",
    )
    parser.add_argument(
        "--continuo",
        action="store_true",
        help="Executa continuamente até interrupção.",
    )
    args = parser.parse_args()

    loop = LoopAutonomoNixal()

    if args.continuo:
        estado = loop.runtime.executar(
            max_ciclos=None,
            intervalo_segundos=args.intervalo,
            parar_em_erro=True,
        )
        print(
            json.dumps(
                estado,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    estado = loop.executar(
        ciclos=args.ciclos,
        intervalo_segundos=args.intervalo,
        parar_em_erro=True,
    )
    print(
        json.dumps(
            estado,
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if estado["sucesso"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
