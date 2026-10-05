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
    VERSAO = "AE5.1.0"
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
        externo = self.repositorio.parent
        self.diretorio_linhas = (externo / "Nyxal-evolution-discovery").resolve()
        self.diretorio_ae4 = (externo / "Nyxal-evolution-ae4").resolve()
        self.diretorio_oportunidades = (externo / "Nyxal-evolution-opportunities").resolve()
        self.diretorio_solicitacoes = (externo / "Nyxal-evolution-requests").resolve()
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

    def _normalizar_linha(self, linha: dict[str, Any]) -> dict[str, Any]:
        linha.setdefault("versao", self.VERSAO)
        linha.setdefault("evidencias_observadas", [])
        linha.setdefault("solicitacoes_observadas", [])
        linha.setdefault("formalizacao", {
            "estado": "nao_iniciada",
            "objetivo": None,
            "metrica": None,
            "direcao_melhor": None,
            "baseline": None,
            "artefato_origem": None,
            "solicitacao_id": None,
            "observacao": None,
        })
        linha.setdefault("min_observacoes", self.min_observacoes)
        linha.setdefault("min_sucessos", self.min_sucessos)
        if not isinstance(linha["evidencias_observadas"], list):
            linha["evidencias_observadas"] = []
        if not isinstance(linha["solicitacoes_observadas"], list):
            linha["solicitacoes_observadas"] = []
        if not isinstance(linha["formalizacao"], dict):
            linha["formalizacao"] = {"estado": "nao_iniciada"}
        return linha

    def _recalcular_janela(self, linha: dict[str, Any]) -> None:
        evidencias = linha.get("evidencias_observadas", [])
        if not isinstance(evidencias, list):
            evidencias = []
        evidencias = evidencias[-self.MAX_CICLOS_POR_LINHA:]
        linha["evidencias_observadas"] = evidencias
        linha["ciclos_observados"] = [
            e["ciclo_id"] for e in evidencias
            if isinstance(e, dict) and isinstance(e.get("ciclo_id"), str)
        ]
        linha["oportunidades_observadas"] = list(dict.fromkeys(
            e["oportunidade_id"] for e in evidencias
            if isinstance(e, dict) and e.get("oportunidade_id")
        ))[-self.MAX_CICLOS_POR_LINHA:]
        linha["observacoes"] = len(evidencias)
        linha["observacoes_sucesso"] = sum(
            1 for e in evidencias
            if isinstance(e, dict) and e.get("ciclo_sucesso") is True
        )

    def _reconciliar_solicitacao(self, linha: dict[str, Any]) -> None:
        if not self.diretorio_solicitacoes.is_dir():
            return
        hipotese = self._normalizar(linha.get("hipotese", ""))
        for caminho in self.diretorio_solicitacoes.glob("solicitacao-*.json"):
            registro = self._carregar(caminho)
            if not isinstance(registro, dict):
                continue
            solicitacao_id = self._texto(registro.get("solicitacao_id"))
            h = registro.get("hipotese")
            htexto = h.get("hipotese") if isinstance(h, dict) else h
            if not solicitacao_id or self._normalizar(htexto or "") != hipotese:
                continue
            if solicitacao_id not in linha["solicitacoes_observadas"]:
                linha["solicitacoes_observadas"].append(solicitacao_id)
            formal = linha["formalizacao"]
            formal.update({
                "estado": "solicitacao_existente",
                "solicitacao_id": solicitacao_id,
                "objetivo": registro.get("objetivo"),
                "metrica": registro.get("metrica"),
                "direcao_melhor": registro.get("direcao_melhor"),
                "baseline": registro.get("baseline"),
                "artefato_origem": registro.get("artefato_origem"),
                "observacao": registro.get("observacao"),
            })
            break

    def _resultado_ae4_da_auditoria(self, auditoria: dict[str, Any]) -> dict[str, Any] | None:
        etapas = auditoria.get("etapas")
        if not isinstance(etapas, list):
            return None
        ae1 = next(
            (e for e in etapas if isinstance(e, dict) and e.get("etapa") == "AE1"),
            None,
        )
        if not isinstance(ae1, dict):
            return None
        oportunidade_id = self._texto(ae1.get("oportunidade_id"))
        if not oportunidade_id or not self.diretorio_oportunidades.is_dir():
            return None
        oportunidade = self._carregar(
            self.diretorio_oportunidades / f"{oportunidade_id}.json"
        )
        if not isinstance(oportunidade, dict):
            return None
        return {
            "sucesso": auditoria.get("estado") != "ae4_ae1_falhou",
            "estado": auditoria.get("estado"),
            "ciclo_id": auditoria.get("ciclo_id"),
            "ae1": {
                "sucesso": ae1.get("sucesso"),
                "estado": ae1.get("estado"),
                "valor": oportunidade,
            },
        }

    def reconciliar_historico(self, limite: int | None = None) -> dict[str, Any]:
        if not self.habilitada:
            return {"sucesso": True, "estado": "ae5_desabilitada", "auditorias_processadas": 0, "novos_sinais": 0}
        if not self.diretorio_ae4.is_dir():
            return {"sucesso": True, "estado": "sem_auditorias_ae4", "auditorias_processadas": 0, "novos_sinais": 0}
        arquivos = sorted(
            self.diretorio_ae4.glob("ae4-ciclo-*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        if limite is not None:
            if not isinstance(limite, int) or limite < 1:
                raise ValueError("limite_invalido")
            arquivos = arquivos[-limite:]
        processadas = novos = 0
        for caminho in arquivos:
            auditoria = self._carregar(caminho)
            if not isinstance(auditoria, dict):
                continue
            resultado = self._resultado_ae4_da_auditoria(auditoria)
            if resultado is None:
                continue
            sinal = self._extrair_sinal(resultado)
            if sinal is None:
                continue
            linha = self._carregar(self._arquivo(self._linha_id(sinal["limitacao"], sinal["hipotese"])))
            antes = len(linha.get("ciclos_observados", [])) if linha else 0
            self.processar(resultado)
            depois = self._carregar(self._arquivo(self._linha_id(sinal["limitacao"], sinal["hipotese"])))
            depois_n = len(depois.get("ciclos_observados", [])) if depois else 0
            processadas += 1
            if depois_n > antes:
                novos += 1
        return {
            "sucesso": True,
            "estado": "historico_ae4_reconciliado",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "auditorias_processadas": processadas,
            "novos_sinais": novos,
            "linhas_maduras": len(self.listar(maduras=True, limite=self.MAX_LINHAS)),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
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
                "evidencias_observadas": [],
                "solicitacoes_observadas": [],
                "formalizacao": {
                    "estado": "nao_iniciada",
                    "objetivo": None,
                    "metrica": None,
                    "direcao_melhor": None,
                    "baseline": None,
                    "artefato_origem": None,
                    "solicitacao_id": None,
                    "observacao": None,
                },
                "min_observacoes": self.min_observacoes,
                "min_sucessos": self.min_sucessos,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }

        linha = self._normalizar_linha(linha)
        ja_observado = sinal["ciclo_id"] in linha["ciclos_observados"]
        if not ja_observado:
            linha["evidencias_observadas"].append({
                "ciclo_id": sinal["ciclo_id"],
                "oportunidade_id": sinal["oportunidade_id"],
                "ciclo_sucesso": sinal["ciclo_sucesso"],
                "observado_em": self._agora(),
            })
            self._recalcular_janela(linha)

        oportunidade_id = sinal.get("oportunidade_id")
        if (
            oportunidade_id
            and oportunidade_id not in linha["oportunidades_observadas"]
        ):
            linha["oportunidades_observadas"].append(oportunidade_id)
            linha["oportunidades_observadas"] = linha[
                "oportunidades_observadas"
            ][-self.MAX_CICLOS_POR_LINHA :]

        self._reconciliar_solicitacao(linha)
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
        if madura and linha["formalizacao"].get("estado") == "nao_iniciada":
            linha["formalizacao"]["estado"] = "preparada"

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
            "observada": not ja_observado,
            "madura_para_formalizacao": madura,
            "observacoes": linha["observacoes"],
            "observacoes_sucesso": linha["observacoes_sucesso"],
            "proxima_etapa": linha["proxima_etapa"],
            "formalizacao": copy.deepcopy(linha["formalizacao"]),
            "solicitacoes_observadas": copy.deepcopy(linha["solicitacoes_observadas"]),
            "deduplicada": ja_observado,
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
