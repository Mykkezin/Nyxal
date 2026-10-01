#!/usr/bin/env python3

"""
NIXAL — TESTE DA PLANTA REAL

Microetapa 56.4.2

Valida a primeira planta_nixal/planta.json real da Nixal.
O teste verifica somente estrutura e invariantes declarados na planta.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARQUIVO = Path("planta_nixal/planta.json")


def main() -> None:
    falhas: list[str] = []
    total_testes = 0

    def verificar(condicao: bool, mensagem: str) -> None:
        nonlocal total_testes
        total_testes += 1
        if condicao:
            print(f"[PASS] {mensagem}")
        else:
            print(f"[FAIL] {mensagem}")
            falhas.append(mensagem)

    verificar(
        ARQUIVO.exists(),
        "planta_nixal/planta.json existe",
    )

    if not ARQUIVO.exists():
        raise SystemExit(1)

    try:
        dados: Any = json.loads(
            ARQUIVO.read_text(encoding="utf-8")
        )
        verificar(
            True,
            "JSON da planta é válido",
        )
    except (OSError, json.JSONDecodeError) as erro:
        verificar(
            False,
            f"JSON da planta é válido: {erro}",
        )
        raise SystemExit(1)

    verificar(
        isinstance(dados, dict),
        "raiz da planta é um objeto",
    )

    if not isinstance(dados, dict):
        raise SystemExit(1)

    identidade = dados.get("identidade", {})
    estado_atual = dados.get("estado_atual", {})
    componentes = dados.get("componentes", [])
    capacidades = dados.get("capacidades_conhecidas", [])
    limites = dados.get("limites_conhecidos", [])
    regras = dados.get("regras_modificacao", {})

    verificar(
        isinstance(identidade, dict)
        and identidade.get("nome") == "Nixal",
        "identidade declara Nixal",
    )

    verificar(
        isinstance(identidade, dict)
        and identidade.get("versao_arquitetura") == "56.4.2",
        "versão da arquitetura é 56.4.2",
    )

    verificar(
        isinstance(componentes, list) and len(componentes) >= 1,
        "há componentes declarados",
    )

    verificar(
        isinstance(capacidades, list) and len(capacidades) == 5,
        "há exatamente 5 capacidades conhecidas",
    )

    verificar(
        isinstance(limites, list) and len(limites) >= 1,
        "há limitações conhecidas",
    )

    verificar(
        isinstance(regras, dict)
        and regras.get("planta") == "somente_leitura",
        "a planta está protegida como somente leitura",
    )

    verificar(
        isinstance(estado_atual, dict)
        and estado_atual.get("camada_conversacional")
        == "ainda_nao_iniciada",
        "a camada conversacional permanece não iniciada",
    )

    verificar(
        isinstance(estado_atual, dict)
        and estado_atual.get("evolucao_autonoma")
        == "ainda_nao_iniciada",
        "a evolução autônoma permanece não iniciada",
    )

    ids = [
        item.get("id")
        for item in componentes
        if isinstance(item, dict)
    ]

    verificar(
        len(ids) == len(set(ids)),
        "IDs de componentes não são duplicados",
    )

    for item in componentes:
        if not isinstance(item, dict):
            verificar(False, "componente é um objeto JSON")
            continue

        componente_id = item.get("id")

        verificar(
            isinstance(componente_id, str)
            and bool(componente_id.strip()),
            f"componente possui ID válido: {componente_id!r}",
        )

        verificar(
            isinstance(item.get("arquivo_principal"), str)
            and bool(item["arquivo_principal"].strip()),
            f"componente possui arquivo principal: {componente_id!r}",
        )

        verificar(
            isinstance(item.get("funcao"), str)
            and bool(item["funcao"].strip()),
            f"componente possui função declarada: {componente_id!r}",
        )

    print()
    print("=" * 60)
    print(f"TESTES EXECUTADOS: {total_testes}")
    print(f"FALHAS: {len(falhas)}")
    print(f"PASSOU: {not falhas}")
    print("=" * 60)

    if falhas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
