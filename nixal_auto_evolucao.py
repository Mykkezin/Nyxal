#!/usr/bin/env python3
"""
NYXAL — AUTO-EVOLUTION GOVERNADA AE1

Primeira camada funcional de auto-evolution:
- observa ciclos residentes;
- identifica limitações/hipóteses candidatas;
- registra oportunidades de evolução;
- pode consultar oportunidades.

Não:
- gera código;
- executa candidatos;
- autoriza integração;
- modifica stable;
- faz merge;
- promove conhecimento permanente.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AutoEvolucaoGovernadaNixOS:
    """Descoberta e registro seguro de oportunidades de evolução."""

    FONTE = "auto_evolucao_governada_nyxos"
    VERSAO = "AE1.0.0"
    MAX_OPORTUNIDADES = 200

    def __init__(
        self,
        repositorio: str | Path,
        diretorio_oportunidades: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(repositorio).resolve()
        self.diretorio_oportunidades = Path(
            diretorio_oportunidades
            if diretorio_oportunidades is not None
            else self.repositorio.parent / "Nyxal-evolution-opportunities"
        ).resolve()
        self.diretorio_oportunidades.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _texto(valor: Any) -> str | None:
        if not isinstance(valor, str):
            return None
        valor = valor.strip()
        return valor or None

    @classmethod
    def _id_oportunidade(
        cls,
        ciclo_id: str,
        limitacao: str,
        hipotese: str,
    ) -> str:
        base = {
            "ciclo_id": ciclo_id,
            "limitacao": limitacao,
            "hipotese": hipotese,
        }
        canonico = json.dumps(
            base,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return (
            "oportunidade-"
            + hashlib.sha256(
                canonico.encode("utf-8")
            ).hexdigest()[:20]
        )

    def _arquivo(self, oportunidade_id: str) -> Path:
        return self.diretorio_oportunidades / f"{oportunidade_id}.json"

    @staticmethod
    def _carregar(caminho: Path) -> dict[str, Any] | None:
        if not caminho.is_file():
            return None

        try:
            dados = json.loads(
                caminho.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

        return dados if isinstance(dados, dict) else None

    def _salvar_oportunidade(
        self,
        oportunidade: dict[str, Any],
    ) -> None:
        oportunidade_id = oportunidade.get("oportunidade_id")
        if not isinstance(oportunidade_id, str) or not oportunidade_id:
            raise ValueError("oportunidade_id_invalido")

        caminho = self._arquivo(oportunidade_id)
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(
            json.dumps(
                oportunidade,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporario, caminho)

    def avaliar_ciclo(
        self,
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(ciclo, dict):
            return {
                "sucesso": False,
                "estado": "ciclo_invalido",
                "origem": self.FONTE,
                "motivo": "O ciclo precisa ser um objeto.",
            }

        ciclo_id = self._texto(ciclo.get("ciclo_id"))
        valor = ciclo.get("valor")
        valor = valor if isinstance(valor, dict) else {}

        prioridade = valor.get("necessidade_prioritaria")
        prioridade = (
            prioridade if isinstance(prioridade, dict) else {}
        )
        necessidade = (
            prioridade.get("selecionada")
            if isinstance(prioridade.get("selecionada"), dict)
            else prioridade
        )

        limitacao = self._texto(
            necessidade.get("problema")
            or necessidade.get("necessidade")
        )

        hipotese_obj = valor.get("hipotese")
        if not isinstance(hipotese_obj, dict):
            investigacao = valor.get("investigacao")
            investigacao_valor = (
                investigacao.get("valor")
                if isinstance(investigacao, dict)
                else None
            )
            if isinstance(investigacao_valor, dict):
                hipotese_obj = investigacao_valor.get("hipotese")

        hipotese = None
        if isinstance(hipotese_obj, dict):
            hipotese = self._texto(
                hipotese_obj.get("hipotese")
                or hipotese_obj.get("texto")
                or hipotese_obj.get("enunciado")
            )
        elif isinstance(hipotese_obj, str):
            hipotese = self._texto(hipotese_obj)

        if not ciclo_id or not limitacao or not hipotese:
            return {
                "sucesso": True,
                "estado": "sem_oportunidade",
                "origem": self.FONTE,
                "motivo": (
                    "O ciclo não contém simultaneamente uma limitação "
                    "e uma hipótese úteis para AE1."
                ),
                "oportunidade_criada": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "arquitetura_modificada": False,
            }

        oportunidade_id = self._id_oportunidade(
            ciclo_id,
            limitacao,
            hipotese,
        )
        caminho = self._arquivo(oportunidade_id)
        existente = self._carregar(caminho)

        if existente is not None:
            return {
                "sucesso": True,
                "estado": "oportunidade_ja_registrada",
                "origem": self.FONTE,
                "valor": copy.deepcopy(existente),
                "oportunidade_criada": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "arquitetura_modificada": False,
            }

        oportunidade = {
            "oportunidade_id": oportunidade_id,
            "versao": self.VERSAO,
            "origem": self.FONTE,
            "estado": "oportunidade",
            "criada_em": self._timestamp(),
            "ciclo_origem": ciclo_id,
            "limitacao": limitacao,
            "hipotese": hipotese,
            "prioridade": {
                "tipo": necessidade.get("tipo"),
                "prioridade": necessidade.get("prioridade"),
                "necessidade": necessidade.get("necessidade"),
            },
            "evidencias": {
                "ciclo_sucesso": ciclo.get("sucesso"),
                "estado_ciclo": ciclo.get("estado"),
            },
            "proxima_etapa": "avaliacao_e_preparacao_formal",
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

        self._salvar_oportunidade(oportunidade)

        arquivos = sorted(
            self.diretorio_oportunidades.glob("oportunidade-*.json")
        )
        if len(arquivos) > self.MAX_OPORTUNIDADES:
            for antigo in arquivos[: len(arquivos) - self.MAX_OPORTUNIDADES]:
                try:
                    antigo.unlink()
                except OSError:
                    pass

        return {
            "sucesso": True,
            "estado": "oportunidade_criada",
            "origem": self.FONTE,
            "valor": copy.deepcopy(oportunidade),
            "oportunidade_criada": True,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def listar(self, limite: int = 20) -> list[dict[str, Any]]:
        if not isinstance(limite, int) or limite <= 0:
            raise ValueError("limite_invalido")

        arquivos = sorted(
            self.diretorio_oportunidades.glob("oportunidade-*.json"),
            key=lambda caminho: caminho.stat().st_mtime,
        )[-min(limite, self.MAX_OPORTUNIDADES) :]

        resultado = []
        for caminho in reversed(arquivos):
            dados = self._carregar(caminho)
            if dados is not None:
                resultado.append(dados)
        return resultado

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "auto_evolution_ae1_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "descoberta_habilitada": True,
            "execucao_experimental_automatica": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "quantidade_oportunidades": len(self.listar(self.MAX_OPORTUNIDADES)),
            "ultimas_oportunidades": self.listar(5),
        }


__all__ = ["AutoEvolucaoGovernadaNixOS"]
