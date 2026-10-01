#!/usr/bin/env python3

from __future__ import annotations

import threading
import time

from nixal_executor_ordens import ExecutorOrdensNixal


INTERVALO_WORKER = 1.0


class NyxalOperacional:
    """Interface contínua para receber e executar ordens."""

    def __init__(self) -> None:
        self.executor = ExecutorOrdensNixal()
        self.executando = True

    def worker(self) -> None:
        while self.executando:
            resultado = self.executor.executar_proxima()
            estado = resultado.get("estado")

            if estado == "fila_vazia":
                time.sleep(INTERVALO_WORKER)
                continue

            tarefa = resultado.get("valor", {})

            if resultado.get("sucesso"):
                capacidade = (
                    tarefa.get("capacidade")
                    if isinstance(tarefa, dict)
                    else None
                )

                print(
                    f"\n[Nyxal] concluída: {capacidade}"
                )

                if isinstance(tarefa, dict):
                    execucao = tarefa.get(
                        "resultado"
                    )

                    if execucao is not None:
                        print(
                            f"[Nyxal] resultado: {execucao}"
                        )
            else:
                erro = (
                    tarefa.get("erro")
                    if isinstance(tarefa, dict)
                    else None
                )

                print(
                    f"\n[Nyxal] falhou: {erro}"
                )

            print("\nVocê: ", end="", flush=True)

    def receber(self, texto: str) -> None:
        resultado = self.executor.receber_ordem(
            texto
        )

        if resultado.get("sucesso"):
            valor = resultado.get("valor", {})

            capacidade = (
                valor.get("capacidade")
                if isinstance(valor, dict)
                else None
            )

            print(
                f"\n[Nyxal] ordem recebida → {capacidade}"
            )
        else:
            print(
                "\n[Nyxal] não consegui colocar a ordem na fila."
            )

            motivo = resultado.get("motivo")

            if motivo:
                print(
                    f"[Nyxal] motivo: {motivo}"
                )

    def iniciar(self) -> None:
        thread = threading.Thread(
            target=self.worker,
            daemon=True,
        )

        thread.start()

        print("=" * 60)
        print("NYXAL — MODO OPERACIONAL")
        print("=" * 60)
        print("Digite uma ordem.")
        print("As ordens entram na fila e são executadas automaticamente.")
        print("Ctrl+C ou Ctrl+D para encerrar.")
        print("=" * 60)

        try:
            while self.executando:
                try:
                    texto = input("\nVocê: ")
                except (KeyboardInterrupt, EOFError):
                    break

                texto = texto.strip()

                if not texto:
                    continue

                self.receber(texto)

        finally:
            self.executando = False
            print("\n\nNyxal encerrada.")


if __name__ == "__main__":
    NyxalOperacional().iniciar()
