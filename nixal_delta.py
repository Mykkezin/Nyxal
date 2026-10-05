#!/usr/bin/env python3
"""
NYXOS — EVENTOS DELTA M5.4

Delta é a representação de uma mudança observável:

    ESTADO A → Δ → ESTADO B

O módulo cria e persiste eventos Delta como registros auditáveis.
Não executa ações, não controla processos e não autoriza evolução.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RegistroDeltaNixOS:
    """Cria e mantém uma trilha persistente de eventos Delta."""

    FONTE = "delta_nyxos"
    VERSAO = "5.4.0"
    MAX_EVENTOS = 200
    MAX_TAMANHO_TEXTO = 500
    TIPOS_VALIDOS = {
        "estado",
        "processo",
        "ambiente",
        "ciclo",
        "conhecimento",
        "memoria",
        "hipotese",
        "objetivo",
        "projeto",
        "sistema",
        "arquitetura",
    }

    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        self._dados = self._carregar()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _estrutura_vazia(cls) -> dict[str, Any]:
        return {
            "versao": cls.VERSAO,
            "origem": cls.FONTE,
            "eventos": [],
        }

    @classmethod
    def _texto(cls, valor: Any, nome: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()[: cls.MAX_TAMANHO_TEXTO]

    @staticmethod
    def _json_seguro(valor: Any, nome: str) -> Any:
        try:
            serializado = json.dumps(
                valor,
                ensure_ascii=False,
                sort_keys=True,
            )
        except (TypeError, ValueError) as erro:
            raise ValueError(f"{nome}_nao_serializavel") from erro

        try:
            return copy.deepcopy(json.loads(serializado))
        except json.JSONDecodeError as erro:
            raise ValueError(f"{nome}_invalido") from erro

    @classmethod
    def _normalizar(cls, dados: Any) -> dict[str, Any]:
        if not isinstance(dados, dict):
            return cls._estrutura_vazia()

        if dados.get("versao") != cls.VERSAO:
            return cls._estrutura_vazia()

        eventos = dados.get("eventos", [])
        if not isinstance(eventos, list):
            return cls._estrutura_vazia()

        validos = [
            copy.deepcopy(evento)
            for evento in eventos
            if isinstance(evento, dict)
            and isinstance(evento.get("delta_id"), str)
        ]

        return {
            "versao": cls.VERSAO,
            "origem": cls.FONTE,
            "eventos": validos[-cls.MAX_EVENTOS :],
        }

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho.is_file():
            return self._estrutura_vazia()

        try:
            dados = json.loads(
                self.caminho.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return self._estrutura_vazia()

        return self._normalizar(dados)

    def _salvar(self) -> None:
        self.caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporario = self.caminho.with_name(
            self.caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                self._dados,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporario, self.caminho)

    @classmethod
    def criar_evento(
        cls,
        *,
        tipo: str,
        estado_anterior: Any,
        estado_novo: Any,
        causa: str,
        evidencias: list[Any] | None = None,
        ciclo: str | None = None,
        resultado: Any = None,
    ) -> dict[str, Any]:
        tipo = cls._texto(tipo, "tipo").lower()
        if tipo not in cls.TIPOS_VALIDOS:
            raise ValueError("tipo_delta_nao_suportado")

        causa = cls._texto(causa, "causa")

        if ciclo is not None:
            ciclo = cls._texto(ciclo, "ciclo")

        evidencias = [] if evidencias is None else evidencias
        if not isinstance(evidencias, list):
            raise ValueError("evidencias_invalidas")

        evento_base = {
            "tipo": tipo,
            "estado_anterior": cls._json_seguro(
                estado_anterior,
                "estado_anterior",
            ),
            "estado_novo": cls._json_seguro(
                estado_novo,
                "estado_novo",
            ),
            "causa": causa,
            "evidencias": cls._json_seguro(
                evidencias,
                "evidencias",
            ),
            "ciclo": ciclo,
            "resultado": cls._json_seguro(
                resultado,
                "resultado",
            ),
        }

        canonico = json.dumps(
            evento_base,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        delta_id = (
            "Δ-"
            + hashlib.sha256(
                canonico.encode("utf-8")
            ).hexdigest()[:20]
        )

        return {
            "delta_id": delta_id,
            "versao": cls.VERSAO,
            "origem": cls.FONTE,
            "tipo": tipo,
            "estado_anterior": evento_base["estado_anterior"],
            "estado_novo": evento_base["estado_novo"],
            "causa": causa,
            "evidencias": evento_base["evidencias"],
            "ciclo": ciclo,
            "resultado": evento_base["resultado"],
            "criado_em": cls._timestamp(),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
        }

    def registrar(self, evento: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(evento, dict):
            raise ValueError("evento_delta_invalido")

        delta_id = evento.get("delta_id")
        if not isinstance(delta_id, str) or not delta_id.startswith("Δ-"):
            raise ValueError("delta_id_invalido")

        copia = copy.deepcopy(evento)

        for existente in self._dados["eventos"]:
            if (
                isinstance(existente, dict)
                and existente.get("delta_id") == delta_id
            ):
                return {
                    "sucesso": True,
                    "estado": "delta_ja_registrado",
                    "origem": self.FONTE,
                    "valor": copy.deepcopy(existente),
                    "novo": False,
                }

        self._dados["eventos"].append(copia)
        self._dados["eventos"] = (
            self._dados["eventos"][-self.MAX_EVENTOS :]
        )
        self._salvar()

        return {
            "sucesso": True,
            "estado": "delta_registrado",
            "origem": self.FONTE,
            "valor": copy.deepcopy(copia),
            "novo": True,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
        }

    def listar(self, limite: int = 20) -> list[dict[str, Any]]:
        if not isinstance(limite, int) or limite <= 0:
            raise ValueError("limite_invalido")

        limite = min(limite, self.MAX_EVENTOS)

        return copy.deepcopy(
            self._dados["eventos"][-limite:]
        )

    def ultimo(self) -> dict[str, Any] | None:
        eventos = self._dados["eventos"]
        if not eventos:
            return None
        return copy.deepcopy(eventos[-1])

    def quantidade(self) -> int:
        return len(self._dados["eventos"])

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "delta_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "quantidade": self.quantidade(),
            "ultimo": self.ultimo(),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
        }


__all__ = ["RegistroDeltaNixOS"]
