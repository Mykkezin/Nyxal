#!/usr/bin/env python3
"""
NYXOS — RECURSOS DO HABITAT M5.6

Catálogo somente leitura dos recursos disponíveis à Nyxal:
- capacidades declaradas em capacidades_nixal.json;
- módulos Python presentes no núcleo do projeto.

Este módulo não importa dinamicamente módulos, não executa ferramentas
e não concede autorização de execução.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


class RecursosHabitatNixOS:
    """Descreve recursos declarados do habitat sem executá-los."""

    FONTE = "recursos_habitat_nyxos"
    VERSAO = "5.6.0"
    LIMITE_FERRAMENTAS = 50
    LIMITE_MODULOS = 100

    def __init__(
        self,
        base_dir: str | Path,
        capacidades_path: str | Path | None = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.capacidades_path = Path(
            capacidades_path
            if capacidades_path is not None
            else self.base_dir / "capacidades_nixal.json"
        ).resolve()

    def _carregar_capacidades(self) -> list[dict[str, Any]]:
        if not self.capacidades_path.is_file():
            return []

        try:
            dados = json.loads(
                self.capacidades_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return []

        if not isinstance(dados, list):
            return []

        resultado: list[dict[str, Any]] = []

        for item in dados[: self.LIMITE_FERRAMENTAS]:
            if not isinstance(item, dict):
                continue

            nome = item.get("nome")
            if not isinstance(nome, str) or not nome.strip():
                continue

            argumentos = item.get("argumentos")
            dominios = item.get("dominios")

            resultado.append(
                {
                    "nome": nome.strip()[:80],
                    "descricao": (
                        str(item.get("descricao", "")).strip()[:240]
                        or None
                    ),
                    "objetivo": (
                        str(item.get("objetivo", "")).strip()[:240]
                        or None
                    ),
                    "argumentos": copy.deepcopy(
                        argumentos
                        if isinstance(argumentos, dict)
                        else {}
                    ),
                    "dominios": [
                        str(dominio).strip()[:80]
                        for dominio in (dominios or [])
                        if str(dominio).strip()
                    ][:10],
                    "executavel": False,
                    "autorizacao_explicita": False,
                }
            )

        return resultado

    def _listar_modulos(self) -> list[dict[str, Any]]:
        if not self.base_dir.is_dir():
            return []

        modulos: list[dict[str, Any]] = []

        for caminho in sorted(
            self.base_dir.glob("nixal_*.py")
        )[: self.LIMITE_MODULOS]:
            if not caminho.is_file():
                continue

            modulos.append(
                {
                    "nome": caminho.stem,
                    "arquivo": caminho.name,
                    "tipo": "modulo_python",
                    "observavel": True,
                    "carregamento_dinamico": False,
                }
            )

        return modulos

    def snapshot(self) -> dict[str, Any]:
        ferramentas = self._carregar_capacidades()
        modulos = self._listar_modulos()

        return {
            "sucesso": True,
            "estado": "recursos_observados",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "modo": "somente_leitura",
            "ferramentas": ferramentas,
            "modulos": modulos,
            "quantidades": {
                "ferramentas": len(ferramentas),
                "modulos": len(modulos),
            },
            "execucao_habilitada": False,
            "arquitetura_modificada": False,
        }


__all__ = ["RecursosHabitatNixOS"]
