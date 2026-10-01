#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from nixal_fila_tarefas import FilaTarefasNixal

def verificar(condicao: bool, mensagem: str) -> None:
    estado = "PASS" if condicao else "FALHA"
    print(f"[{estado}] {mensagem}")
    if not condicao:
        raise AssertionError(mensagem)

def main() -> None:
    with TemporaryDirectory() as tmp:
        caminho = Path(tmp) / "fila_tarefas.json"
        fila = FilaTarefasNixal(caminho)

        adicionar = fila.adicionar(capacidade="obter_hora", argumentos={})
        verificar(adicionar.get("sucesso") is True, "fila aceita nova tarefa")
        verificar(adicionar.get("estado") == "pendente", "nova tarefa entra como pendente")
        verificar(fila.quantidade_pendentes() == 1, "fila possui uma tarefa pendente")

        executar = fila.executar_proxima()
        verificar(executar.get("sucesso") is True, "fila executa a próxima tarefa")
        verificar(executar.get("estado") == "concluida", "tarefa termina como concluída")
        verificar(fila.quantidade_pendentes() == 0, "não restam tarefas pendentes")

        recarregada = FilaTarefasNixal(caminho)
        verificar(recarregada.quantidade() == 1, "tarefa permanece após reinicialização")

    print("=" * 60)
    print("TESTE — FILA DE TAREFAS NYXAL")
    print("=" * 60)
    print("PASSOU: True")
    print("=" * 60)

if __name__ == "__main__":
    main()
