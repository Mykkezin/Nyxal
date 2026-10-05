#!/usr/bin/env python3
"""Auditoria somente leitura das evidências persistidas pela AE5 econômica."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def carregar(caminho: Path) -> dict[str, Any] | None:
    try:
        valor = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return valor if isinstance(valor, dict) else None


def auditar(repositorio: Path, limite: int = 200) -> dict[str, Any]:
    if not isinstance(limite, int) or limite < 1:
        raise ValueError("limite_invalido")
    base = repositorio.resolve()
    if base.is_file():
        base = base.parent
    diretorio = base.parent / "Nyxal-evolution-discovery"
    linhas_dir = diretorio
    auditoria_dir = diretorio / "auditoria"

    linhas: list[dict[str, Any]] = []
    if linhas_dir.is_dir():
        arquivos = sorted(
            linhas_dir.glob("valor-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limite]
        for caminho in arquivos:
            linha = carregar(caminho)
            if isinstance(linha, dict):
                linhas.append(linha)

    auditorias: list[dict[str, Any]] = []
    if auditoria_dir.is_dir():
        arquivos = sorted(
            auditoria_dir.glob("ae5-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limite]
        for caminho in arquivos:
            registro = carregar(caminho)
            if isinstance(registro, dict):
                auditorias.append(registro)

    estados = {}
    for linha in linhas:
        estado = linha.get("estado")
        if isinstance(estado, str):
            estados[estado] = estados.get(estado, 0) + 1

    return {
        "gate": "AE5_VALOR_ECONOMICO",
        "estado": (
            "evidencia_economica_encontrada"
            if auditorias
            else "sem_evidencia_economica"
        ),
        "somente_leitura": True,
        "linhas_economicas": len(linhas),
        "linhas_maduras": sum(
            x.get("estado") == "maduro_para_formalizacao" for x in linhas
        ),
        "estados": estados,
        "auditorias_ae5": len(auditorias),
        "descobertas_novas": sum(
            x.get("nova_linha") is True for x in auditorias
        ),
        "duplicadas_24h": sum(
            x.get("motivo") == "duplicata_exata_24h" for x in auditorias
        ),
        "cooldown": sum(
            x.get("motivo") == "tipo_em_cooldown" for x in auditorias
        ),
        "sem_valor": sum(
            x.get("motivo") == "valor_economico_ausente_ou_incompleto"
            for x in auditorias
        ),
        "invariantes": {
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audita evidências econômicas reais da AE5."
    )
    parser.add_argument(
        "--repositorio",
        type=Path,
        default=Path(__file__).resolve(),
    )
    parser.add_argument("--limite", type=int, default=200)
    args = parser.parse_args()
    if args.limite < 1:
        parser.error("--limite deve ser >= 1")
    resultado = auditar(args.repositorio, args.limite)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado["estado"] == "evidencia_economica_encontrada" else 2


if __name__ == "__main__":
    raise SystemExit(main())
