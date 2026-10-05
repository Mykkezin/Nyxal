#!/usr/bin/env python3
"""Cobertura automática da proposta M5.8 por imports diretos entre componentes."""

from __future__ import annotations

import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PLANTA = BASE_DIR / "planta_nixal" / "planta.json"
PROPOSTA = BASE_DIR / "m5_8_dependencias_arquiteturais_proposta.json"


def _imports_diretos_por_componentes(planta: dict) -> tuple[set[tuple[str, str]], dict[tuple[str, str], dict]]:
    componentes = {
        item["id"]: item.get("arquivo_principal")
        for item in planta.get("componentes", [])
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("arquivo_principal"), str)
    }

    componentes_python = {
        componente_id: arquivo
        for componente_id, arquivo in componentes.items()
        if arquivo.endswith(".py")
    }

    relacoes: set[tuple[str, str]] = set()
    evidencias: dict[tuple[str, str], dict] = {}

    for origem, arquivo_origem in componentes_python.items():
        codigo = (BASE_DIR / arquivo_origem).read_text(encoding="utf-8")
        linhas = codigo.splitlines()

        for destino, arquivo_destino in componentes_python.items():
            if origem == destino:
                continue

            modulo = Path(arquivo_destino).stem
            padroes = (
                re.compile(rf"^\s*from\s+{re.escape(modulo)}\s+import\b"),
                re.compile(rf"^\s*import\s+{re.escape(modulo)}(?:\s|$)"),
            )

            for numero, linha in enumerate(linhas, start=1):
                if any(padrao.search(linha) for padrao in padroes):
                    par = (origem, destino)
                    relacoes.add(par)
                    evidencias[par] = {
                        "arquivo": arquivo_origem,
                        "linha": numero,
                        "trecho": linha.strip(),
                    }
                    break

    return relacoes, evidencias


def main() -> None:
    planta = json.loads(PLANTA.read_text(encoding="utf-8"))
    proposta = json.loads(PROPOSTA.read_text(encoding="utf-8"))

    encontradas, evidencias = _imports_diretos_por_componentes(planta)
    declaradas = {
        (relacao.get("origem"), relacao.get("destino"))
        for relacao in proposta.get("relacoes", [])
        if isinstance(relacao, dict)
    }

    assert encontradas == declaradas, {
        "encontradas_na_fonte_e_ausentes_na_proposta": sorted(encontradas - declaradas),
        "declaradas_na_proposta_sem_evidencia_direta": sorted(declaradas - encontradas),
    }

    for relacao in proposta.get("relacoes", []):
        par = (relacao["origem"], relacao["destino"])
        evidencia = evidencias[par]

        arquivo = relacao["evidencia"]
        assert isinstance(arquivo, str) and arquivo.strip()
        assert evidencia["arquivo"] in arquivo

    assert len(encontradas) == 4

    print("TESTE_M5_8_COBERTURA_IMPORTACOES_OK")
    print(f"RELACOES_DIRETAS: {len(encontradas)}")


if __name__ == "__main__":
    main()
