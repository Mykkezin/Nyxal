#!/usr/bin/env python3
"""Validação estrutural da proposta M5.8 de dependências arquiteturais."""

from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PLANTA = BASE_DIR / "planta_nixal" / "planta.json"
PROPOSTA = BASE_DIR / "m5_8_dependencias_arquiteturais_proposta.json"


def main() -> None:
    planta = json.loads(PLANTA.read_text(encoding="utf-8"))
    proposta = json.loads(PROPOSTA.read_text(encoding="utf-8"))

    componentes = {
        item["id"]
        for item in planta.get("componentes", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    relacoes = proposta.get("relacoes")
    assert proposta.get("estado") == "proposta_supervisionada"
    assert proposta.get("escopo", {}).get("nao_autoritativo") is True
    assert proposta.get("escopo", {}).get("somente_leitura") is True
    assert isinstance(relacoes, list) and relacoes

    pares = set()
    arquivos_componentes = {
        item["id"]: item.get("arquivo_principal")
        for item in planta.get("componentes", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    evidencias_diretas = {
        ("agente_qwen", "capacidades"): (
            "nixal_agente_qwen.py",
            "from nixal_capacidades import",
        ),
        ("composicao", "agente_qwen"): (
            "nixal_composicao.py",
            "from nixal_agente_qwen import",
        ),
        ("executor_contexto", "operacoes_contexto"): (
            "executor_contexto_nixal.py",
            "from nixal_operacoes_contexto import",
        ),
        ("interpretacao_qwen", "gerenciador_cristal"): (
            "experiencia_qwen.py",
            "from gerenciador_cristal import",
        ),
    }

    for relacao in relacoes:
        assert isinstance(relacao, dict)
        origem = relacao.get("origem")
        destino = relacao.get("destino")
        assert origem in componentes
        assert destino in componentes
        assert origem != destino
        assert relacao.get("tipo") == "importacao_direta"
        assert isinstance(relacao.get("evidencia"), str) and relacao["evidencia"].strip()
        par = (origem, destino)
        assert par not in pares
        pares.add(par)

        arquivo_esperado, importacao_esperada = evidencias_diretas[par]
        assert arquivos_componentes.get(origem) == arquivo_esperado

        codigo = (BASE_DIR / arquivo_esperado).read_text(encoding="utf-8")
        assert importacao_esperada in codigo

    invariantes = proposta.get("invariantes", {})
    for chave in (
        "autorizacao_explicita",
        "integracao_executada",
        "stable_modificada",
        "arquitetura_modificada",
        "conhecimento_permanente",
    ):
        assert invariantes.get(chave) is False

    print("TESTE_M5_8_DEPENDENCIAS_ARQUITETURAIS_OK")


if __name__ == "__main__":
    main()
