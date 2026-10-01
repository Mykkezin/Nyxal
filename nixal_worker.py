#!/usr/bin/env python3

from __future__ import annotations

import time

from nixal_executor_ordens import ExecutorOrdensNixal


INTERVALO_SEGUNDOS = 1.0


class NyxalWorker:
    """Worker persistente que consome a fila de tarefas."""

    FONTE = "nyxal_worker"
    VERSAO = "1.0"

    def __init__(
        self,
        executor: ExecutorOrdensNixal | None = None,
    ) -> None:
        self.executor = (
            executor
            if executor is not None
            else ExecutorOrdensNixal()
        )
        self.executando = True

    def parar(self) -> None:
        self.executando = False

    def executar_ciclo(self) -> dict:
        return self.executor.executar_proxima()

    def iniciar(self) -> None:
        print("=" * 60)
        print("NYXAL — WORKER DE TAREFAS")
        print("=" * 60)
        print("Worker iniciado.")
        print("Pressione Ctrl+C para parar.")

        try:
            while self.executando:
                resultado = self.executar_ciclo()

                estado = resultado.get("estado")

                if estado == "fila_vazia":
                    time.sleep(INTERVALO_SEGUNDOS)
                    continue

                print(
                    f"[NYXAL] tarefa: {estado}"
                )

        except KeyboardInterrupt:
            print()
            print("[NYXAL] Worker interrompido.")


if __name__ == "__main__":
    NyxalWorker().iniciar()
