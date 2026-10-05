#!/usr/bin/env python3
"""
NYXAL — DESCOBERTA CONTÍNUA AE5

Consolida sinais repetidos produzidos pela AE1/AE4 ao longo de ciclos
residentes, transformando repetição observada em estado de maturidade
para formalização.

Não:
- gera código;
- cria uma solicitação formal automaticamente;
- inventa objetivo, métrica, baseline ou artefato;
- executa experimentos;
- autoriza integração;
- modifica stable/main;
- promove conhecimento permanente;
- faz retry de experimentos.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DescobertaContinuaGovernadaAE5:
    """Acumula evidência de oportunidades sem ampliar autoridade de evolução."""

    FONTE = "descoberta_continua_governada_ae5"
    VERSAO = "AE5.0.0"
    MAX_LINHAS = 200
    MAX_CICLOS_POR_LINHA = 20
    MIN_OBSERVACOES_PADRAO = 3
    MIN_SUCESSOS_PADRAO = 2

    def __init__(
        self,
        *,
        repositorio: str | Path,
        min_observacoes: int = MIN_OBSERVACOES_PADRAO,
        min_sucessos: int = MIN_SUCESSOS_PADRAO,
        habilitada: bool = True,
    ) -> None:
        if not isinstance(min_observacoes, int) or min_observacoes < 1:
            raise ValueError("min_observacoes_invalido")

        if (
            not isinstance(min_sucessos, int)
            or min_sucessos < 1
            or min_sucessos > min_observacoes
        ):
            raise ValueError("min_sucessos_invalido")

        self.repositorio = Path(repositorio).resolve()
        self.diretorio_linhas = (
            self.repositorio.parent / "Nyxal-evolution-discovery"
        ).resolve()
        self.diretorio_linhas.mkdir(parents=True, exist_ok=True)
        self.min_observacoes = min_observacoes
        self.min_sucessos = min_sucessos
        self.habilitada = bool(habilitada)
        self._ultimo_resultado: dict[str, Any] | None = None

    @staticmethod
    def _agora() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _texto(valor: Any) -> str | None:
        if not isinstance(valor, str):
            return None
        valor = valor.strip()
        return valor or None

    @staticmethod
    def _normalizar(valor: str) -> str:
        return re.sub(r"\s+", " ", valor.strip().casefold())

    @classmethod
    def _linha_id(cls, limitacao: str, hipotese: str) -> str:
        canonico = json.dumps(
            {
                "limitacao": cls._normalizar(limitacao),
                "hipotese": cls._normalizar(hipotese),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:20]
        return f"linha-{digest}"

    def _arquivo(self, linha_id: str) -> Path:
        return self.diretorio_linhas / f"{linha_id}.json"

    @staticmethod
    def _carregar(caminho: Path) -> dict[str, Any] | None:
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return dados if isinstance(dados, dict) else None

    @staticmethod
    def _atomic_write_json(caminho: Path, dados: dict[str, Any]) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporario, caminho)

    @classmethod
    def _extrair_sinal(cls, resultado_ae4: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(resultado_ae4, dict):
            return None

        ae1 = resultado_ae4.get("ae1")
        if not isinstance(ae1, dict):
            return None

        valor = ae1.get("valor")
        if not isinstance(valor, dict):
            return None

        limitacao = cls._texto(valor.get("limitacao"))
        hipotese = cls._texto(valor.get("hipotese"))
        ciclo_id = cls._texto(
            resultado_ae4.get("ciclo_id") or valor.get("ciclo_origem")
        )
        oportunidade_id = cls._texto(valor.get("oportunidade_id"))

        if not limitacao or not hipotese or not ciclo_id:
            return None

        ciclo_sucesso = resultado_ae4.get("sucesso")
        if not isinstance(ciclo_sucesso, bool):
            evidencias = valor.get("evidencias")
            ciclo_sucesso = (
                evidencias.get("ciclo_sucesso")
                if isinstance(evidencias, dict)
                else False
            )

        return {
            "limitacao": limitacao,
            "hipotese": hipotese,
            "ciclo_id": ciclo_id,
            "oportunidade_id": oportunidade_id,
            "ciclo_sucesso": bool(ciclo_sucesso),
        }

    def _salvar(self, linha: dict[str, Any]) -> None:
        linha_id = linha.get("linha_id")
        if not isinstance(linha_id, str) or not linha_id:
            raise ValueError("linha_id_invalido")

        self._atomic_write_json(self._arquivo(linha_id), linha)

        arquivos = sorted(
            self.diretorio_linhas.glob("linha-*.json"),
            key=lambda item: item.stat().st_mtime,
        )
        excesso = len(arquivos) - self.MAX_LINHAS
        if excesso > 0:
            for antigo in arquivos[:excesso]:
                try:
                    antigo.unlink()
                except OSError:
                    pass

    def processar(self, resultado_ae4: dict[str, Any]) -> dict[str, Any]:
        """Acumula um sinal da AE1/AE4 e avalia sua maturidade."""
        if not self.habilitada:
            resultado = {
                "sucesso": True,
                "estado": "ae5_desabilitada",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "observada": False,
                "madura_para_formalizacao": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        sinal = self._extrair_sinal(resultado_ae4)
        if sinal is None:
            resultado = {
                "sucesso": True,
                "estado": "sem_sinal_para_acumular",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "observada": False,
                "madura_para_formalizacao": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        linha_id = self._linha_id(sinal["limitacao"], sinal["hipotese"])
        caminho = self._arquivo(linha_id)
        linha = self._carregar(caminho)

        if linha is None:
            linha = {
                "linha_id": linha_id,
                "versao": self.VERSAO,
                "origem": self.FONTE,
                "criada_em": self._agora(),
                "estado": "observando",
                "limitacao": sinal["limitacao"],
                "hipotese": sinal["hipotese"],
                "observacoes": 0,
                "observacoes_sucesso": 0,
                "primeiro_ciclo": sinal["ciclo_id"],
                "ultimo_ciclo": sinal["ciclo_id"],
                "ciclos_observados": [],
                "oportunidades_observadas": [],
                "min_observacoes": self.min_observacoes,
                "min_sucessos": self.min_sucessos,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }

        if sinal["ciclo_id"] not in linha["ciclos_observados"]:
            linha["observacoes"] += 1
            if sinal["ciclo_sucesso"]:
                linha["observacoes_sucesso"] += 1

            linha["ciclos_observados"].append(sinal["ciclo_id"])
            linha["ciclos_observados"] = linha["ciclos_observados"][
                -self.MAX_CICLOS_POR_LINHA :
            ]

        oportunidade_id = sinal.get("oportunidade_id")
        if (
            oportunidade_id
            and oportunidade_id not in linha["oportunidades_observadas"]
        ):
            linha["oportunidades_observadas"].append(oportunidade_id)
            linha["oportunidades_observadas"] = linha[
                "oportunidades_observadas"
            ][-self.MAX_CICLOS_POR_LINHA :]

        linha["ultimo_ciclo"] = sinal["ciclo_id"]
        linha["atualizada_em"] = self._agora()

        madura = (
            linha["observacoes"] >= self.min_observacoes
            and linha["observacoes_sucesso"] >= self.min_sucessos
        )

        linha["estado"] = (
            "madura_para_formalizacao"
            if madura
            else "observando"
        )

        linha["proxima_etapa"] = (
            "coletar_objetivo_metrica_baseline_e_artefato"
            if madura
            else "continuar_observando"
        )
        linha["campos_formais"] = {
            "objetivo": None,
            "metrica": None,
            "direcao_melhor": None,
            "baseline": None,
            "artefato_origem": None,
        }

        self._salvar(linha)

        resultado = {
            "sucesso": True,
            "estado": (
                "oportunidade_madura_para_formalizacao"
                if madura
                else "sinal_em_observacao"
            ),
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "linha_id": linha_id,
            "observada": True,
            "madura_para_formalizacao": madura,
            "observacoes": linha["observacoes"],
            "observacoes_sucesso": linha["observacoes_sucesso"],
            "proxima_etapa": linha["proxima_etapa"],
            "campos_formais": copy.deepcopy(linha["campos_formais"]),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }
        self._ultimo_resultado = copy.deepcopy(resultado)
        return resultado

    def listar(self, *, maduras: bool = False, limite: int = 20) -> list[dict[str, Any]]:
        if not isinstance(limite, int) or limite < 1:
            raise ValueError("limite_invalido")

        registros = []
        arquivos = sorted(
            self.diretorio_linhas.glob("linha-*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )

        for caminho in arquivos[: self.MAX_LINHAS]:
            registro = self._carregar(caminho)
            if registro is None:
                continue
            if maduras and registro.get("estado") != "madura_para_formalizacao":
                continue
            registros.append(registro)
            if len(registros) >= limite:
                break

        return registros

    def contexto(self) -> dict[str, Any]:
        maduras = self.listar(maduras=True, limite=self.MAX_LINHAS)
        return {
            "sucesso": True,
            "estado": "ae5_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "habilitada": self.habilitada,
            "min_observacoes": self.min_observacoes,
            "min_sucessos": self.min_sucessos,
            "quantidade_linhas_maduras": len(maduras),
            "linhas_maduras": self.listar(maduras=True, limite=5),
            "ultimo_resultado": copy.deepcopy(self._ultimo_resultado),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = ["DescobertaContinuaGovernadaAE5"]
