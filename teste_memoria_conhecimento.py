#!/usr/bin/env python3

from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

from nixal_memoria_conhecimento import MemoriaConhecimentoNixal


def verificar(condicao: bool, mensagem: str) -> None:
    estado = "PASS" if condicao else "FALHA"
    print(f"[{estado}] {mensagem}")
    if not condicao:
        raise AssertionError(mensagem)


def main() -> None:
    with TemporaryDirectory() as tmp:
        caminho = Path(tmp) / "memoria_conhecimento.json"
        memoria = MemoriaConhecimentoNixal(caminho)

        candidato = {
            "texto": (
                "Uma representação pode preservar relações."
            ),
            "tipo": "estrutura",
            "origem": {
                "estado": "suportada",
                "indice_avaliacao": 1,
            },
            "conhecimento_permanente": False,
            "gravado": False,
        }

        resultado = memoria.registrar(candidato)

        verificar(
            resultado.get("sucesso") is True,
            "memória aceita candidato válido",
        )

        verificar(
            resultado.get("estado") == "persistido",
            "candidato é persistido",
        )

        registro = resultado.get("valor", {})

        verificar(
            isinstance(registro, dict),
            "registro possui estrutura válida",
        )

        verificar(
            registro.get("candidato") == candidato,
            "registro preserva exatamente o candidato",
        )

        verificar(
            registro.get("conhecimento_permanente") is False,
            "registro continua não permanente",
        )

        verificar(
            memoria.quantidade() == 1,
            "memória possui um registro",
        )

        memoria_recarregada = MemoriaConhecimentoNixal(caminho)

        verificar(
            memoria_recarregada.quantidade() == 1,
            "registro sobrevive ao recarregamento",
        )

        duplicado = memoria_recarregada.registrar(candidato)

        verificar(
            duplicado.get("sucesso") is True,
            "duplicata é tratada sem falha",
        )

        verificar(
            duplicado.get("estado") == "ja_existente",
            "duplicata não cria novo registro",
        )

        verificar(
            memoria_recarregada.quantidade() == 1,
            "duplicata não aumenta a memória",
        )

        verificar(
            memoria_recarregada.promover_conhecimento(
                candidato
            ).get("sucesso")
            is False,
            "memória não promove conhecimento permanente",
        )

        verificar(
            memoria_recarregada.modificar_arquitetura(
                candidato
            ).get("sucesso")
            is False,
            "memória não modifica arquitetura",
        )

    print("=" * 60)
    print("TESTE — MEMÓRIA DE CONHECIMENTO")
    print("=" * 60)
    print("PASSOU: True")
    print("=" * 60)


if __name__ == "__main__":
    main()
