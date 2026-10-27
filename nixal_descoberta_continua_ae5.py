#!/usr/bin/env python3
"""NYXAL — AE5: descoberta contínua governada de valor econômico."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from itertools import islice
from pathlib import Path
from typing import Any, Callable, Iterable


class DescobertaContinuaGovernadaAE5:
    """Interpreta sinais persistentes e mantém linhas econômicas separadas de AE1."""

    FONTE = "descoberta_continua_governada_ae5"
    VERSAO = "AE5.2.0"
    MAX_LINHAS = 200
    MAX_CICLOS_POR_LINHA = 20
    MAX_SINAIS_POR_PASSAGEM = 50
    MAX_AUDITORIAS = 1000
    MIN_OBSERVACOES_PADRAO = 3
    MIN_SUCESSOS_PADRAO = 2
    COOLDOWN_TIPO = timedelta(minutes=30)
    JANELA_DUPLICATA = timedelta(hours=24)

    TIPOS_VALOR = {
        "receita", "custo", "produtividade", "capacidade",
        "confiabilidade", "risco", "eficiencia_recursos",
        "capital", "opcionalidade",
    }
    ESTADOS = {
        "sem_valor_identificado", "valor_candidato",
        "valor_observacional", "valor_sustentado",
        "maduro_para_formalizacao",
    }

    def __init__(
        self,
        *,
        repositorio: str | Path,
        min_observacoes: int = MIN_OBSERVACOES_PADRAO,
        min_sucessos: int = MIN_SUCESSOS_PADRAO,
        habilitada: bool = True,
        agora: Callable[[], datetime] | None = None,
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
        self.diretorio_auditorias = (self.diretorio_linhas / "auditoria").resolve()
        self.diretorio_solicitacoes = (externo / "Nyxal-evolution-requests").resolve()
        self.diretorio_linhas.mkdir(parents=True, exist_ok=True)
        self.diretorio_auditorias.mkdir(parents=True, exist_ok=True)
        self.min_observacoes = min_observacoes
        self.min_sucessos = min_sucessos
        self.habilitada = bool(habilitada)
        self._agora_fn = agora or (lambda: datetime.now(timezone.utc))
        self._ultimo_resultado: dict[str, Any] | None = None

    @classmethod
    def _agora(cls, fn: Callable[[], datetime]) -> datetime:
        valor = fn()
        if not isinstance(valor, datetime):
            raise TypeError("agora_precisa_retornar_datetime")
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(timezone.utc)

    @classmethod
    def _timestamp(cls, fn: Callable[[], datetime]) -> str:
        return cls._agora(fn).isoformat()

    @staticmethod
    def _texto(valor: Any) -> str | None:
        return valor.strip() or None if isinstance(valor, str) and valor.strip() else None

    @staticmethod
    def _normalizar(valor: Any) -> str:
        return re.sub(r"\s+", " ", valor.strip().casefold()) if isinstance(valor, str) else ""

    @staticmethod
    def _json(valor: Any) -> str:
        return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _sha(cls, valor: Any) -> str:
        return hashlib.sha256(cls._json(valor).encode("utf-8")).hexdigest()

    @staticmethod
    def _carregar(caminho: Path) -> dict[str, Any] | None:
        try:
            valor = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return valor if isinstance(valor, dict) else None

    @staticmethod
    def _atomic_write(caminho: Path, dados: dict[str, Any]) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporario, caminho)

    @classmethod
    def _invariantes(cls) -> dict[str, bool]:
        return {
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }

    @classmethod
    def _extrair_valor(
        cls,
        oportunidade: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, list[str]]:
        bruto = oportunidade.get("valor_economico")
        if not isinstance(bruto, dict):
            return None, ["valor_economico_ausente"]
        tipo = cls._normalizar(bruto.get("tipo_valor"))
        campos = {
            "mecanismo_valor": cls._texto(bruto.get("mecanismo_valor")),
            "metrica_economica": cls._texto(bruto.get("metrica_economica")),
            "unidade": cls._texto(bruto.get("unidade")),
            "direcao": cls._texto(bruto.get("direcao")),
        }
        erros = []
        if tipo not in cls.TIPOS_VALOR:
            erros.append("tipo_valor_invalido")
        erros.extend(chave + "_ausente" for chave, valor in campos.items() if not valor)
        evidencia = bruto.get("evidencia")
        if evidencia in (None, "", [], {}):
            erros.append("evidencia_economica_ausente")
        observado = bruto.get("resultado_observado")
        if observado is not None and not isinstance(observado, bool):
            erros.append("resultado_observado_invalido")
            observado = None
        referencia = bruto.get("referencia")
        if referencia is None and "baseline_economico" in bruto:
            referencia = bruto.get("baseline_economico")
        campos.update(
            tipo_valor=tipo or None,
            evidencia=copy.deepcopy(evidencia),
            referencia=copy.deepcopy(referencia),
            confianca=copy.deepcopy(bruto.get("confianca")),
            resultado_observado=observado,
        )
        return (campos if not erros else None), erros

    @classmethod
    def _extrair_sinal(
        cls,
        resultado: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, list[str]]:
        if not isinstance(resultado, dict):
            return None, ["resultado_ae4_invalido"]
        oportunidade = None
        ae1 = resultado.get("ae1")
        if isinstance(ae1, dict) and isinstance(ae1.get("valor"), dict):
            oportunidade = ae1["valor"]
        if oportunidade is None:
            return None, ["oportunidade_ae1_ausente"]
        ciclo_id = cls._texto(resultado.get("ciclo_id") or oportunidade.get("ciclo_origem"))
        limitacao = cls._texto(oportunidade.get("limitacao"))
        hipotese = cls._texto(oportunidade.get("hipotese"))
        if not ciclo_id or not limitacao or not hipotese:
            return None, ["proveniencia_tecnica_incompleta"]
        valor, erros = cls._extrair_valor(oportunidade)
        fontes = ["AE4", "AE1"]
        etapas = resultado.get("etapas")
        if isinstance(etapas, list) and any(
            isinstance(e, dict)
            and e.get("etapa") == "AE3"
            and e.get("aprendizado_disponivel") is True
            for e in etapas
        ):
            fontes.append("AE3")
        return {
            "ciclo_id": ciclo_id,
            "oportunidade_id": cls._texto(oportunidade.get("oportunidade_id")),
            "limitacao": limitacao,
            "hipotese_tecnica": hipotese,
            "estado_ae4": resultado.get("estado"),
            "sucesso_ae4": resultado.get("sucesso") is True,
            "valor_economico": valor,
            "erros_valor": erros,
            "fontes": fontes,
        }, erros

    @classmethod
    def _chave(
        cls,
        sinal: dict[str, Any],
    ) -> tuple[str, str, str]:
        valor = sinal.get("valor_economico") or {}
        tipo = cls._normalizar(valor.get("tipo_valor")) or "desconhecido"
        principal = valor.get("evidencia")
        if principal in (None, "", [], {}):
            principal = {
                "limitacao": sinal.get("limitacao"),
                "hipotese_tecnica": sinal.get("hipotese_tecnica"),
            }
        base = {
            "tipo_valor": tipo,
            "origem": "|".join(sinal.get("fontes", [])),
            "principal_evidencia": cls._normalizar(cls._json(principal)),
        }
        digest = cls._sha(base)
        return f"valor-{digest}", digest, base["principal_evidencia"]

    def _linhas_paths(self) -> list[Path]:
        return sorted(
            self.diretorio_linhas.glob("valor-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def _auditorias_paths(self) -> list[Path]:
        return sorted(
            self.diretorio_auditorias.glob("ae5-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[: self.MAX_AUDITORIAS]

    def _linhas_ativas(self) -> list[dict[str, Any]]:
        linhas = []
        for caminho in self._linhas_paths():
            registro = self._carregar(caminho)
            if isinstance(registro, dict) and registro.get("estado") != "encerrada":
                linhas.append(registro)
        return linhas

    def _auditoria_recente(self, digest: str, agora: datetime) -> dict[str, Any] | None:
        limite = agora - self.JANELA_DUPLICATA
        for caminho in self._auditorias_paths():
            registro = self._carregar(caminho)
            if (
                not isinstance(registro, dict)
                or registro.get("chave_deduplicacao") != digest
                or registro.get("nova_linha") is not True
            ):
                continue
            try:
                instante = datetime.fromisoformat(str(registro.get("observado_em")))
            except ValueError:
                continue
            if instante.tzinfo is None:
                instante = instante.replace(tzinfo=timezone.utc)
            if instante.astimezone(timezone.utc) >= limite:
                return registro
        return None

    def _tipo_em_cooldown(self, tipo_valor: str, agora: datetime) -> bool:
        limite = agora - self.COOLDOWN_TIPO
        for caminho in self._auditorias_paths():
            registro = self._carregar(caminho)
            if not isinstance(registro, dict):
                continue
            if registro.get("tipo_valor") != tipo_valor or registro.get("nova_linha") is not True:
                continue
            try:
                instante = datetime.fromisoformat(str(registro.get("observado_em")))
            except ValueError:
                continue
            if instante.tzinfo is None:
                instante = instante.replace(tzinfo=timezone.utc)
            if instante.astimezone(timezone.utc) >= limite:
                return True
        return False

    def _ciclo_tem_descoberta(self, ciclo_id: str) -> bool:
        return any(
            isinstance(registro := self._carregar(caminho), dict)
            and registro.get("ciclo_id") == ciclo_id
            and registro.get("nova_linha") is True
            for caminho in self._auditorias_paths()
        )

    @classmethod
    def _descricao(cls, sinal: dict[str, Any], valor: dict[str, Any]) -> str:
        return " ".join(
            str(item)
            for item in (
                valor.get("tipo_valor"),
                valor.get("mecanismo_valor"),
                valor.get("metrica_economica"),
                valor.get("unidade"),
                sinal.get("limitacao"),
                sinal.get("hipotese_tecnica"),
            )
            if isinstance(item, str) and item.strip()
        )

    @classmethod
    def _tokens(cls, valor: str) -> set[str]:
        return {x for x in re.findall(r"[a-z0-9_]+", valor.casefold()) if len(x) > 2}

    @classmethod
    def _similaridade(cls, a: str, b: str) -> float:
        ta, tb = cls._tokens(a), cls._tokens(b)
        jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
        return max(
            jaccard,
            SequenceMatcher(None, cls._normalizar(a), cls._normalizar(b)).ratio(),
        )

    @classmethod
    def _possivel_semantica(
        cls,
        sinal: dict[str, Any],
        valor: dict[str, Any],
        linhas: Iterable[dict[str, Any]],
    ) -> tuple[bool, float | None, str | None]:
        descricao = cls._descricao(sinal, valor)
        melhor = (0.0, None)
        for linha in linhas:
            if linha.get("tipo_valor") != valor.get("tipo_valor"):
                continue
            similaridade = cls._similaridade(descricao, linha.get("descricao_semantica", ""))
            if similaridade > melhor[0]:
                melhor = (similaridade, linha.get("linha_id"))
        return (True, melhor[0], melhor[1]) if melhor[0] >= 0.78 else (False, None, None)

    def _reconciliar_n9(self, linha: dict[str, Any]) -> None:
        linha["n9_vinculos_explicitos"] = []
        linha["n9_relacoes_observacionais"] = []
        if not self.diretorio_solicitacoes.is_dir():
            return
        hipotese = self._normalizar(linha.get("hipotese_tecnica"))
        for caminho in sorted(self.diretorio_solicitacoes.glob("solicitacao-*.json")):
            registro = self._carregar(caminho)
            if not isinstance(registro, dict):
                continue
            solicitacao_id = self._texto(registro.get("solicitacao_id"))
            if not solicitacao_id:
                continue
            if registro.get("economic_line_id") == linha.get("linha_id"):
                linha["n9_vinculos_explicitos"].append(solicitacao_id)
                continue
            h = registro.get("hipotese")
            htexto = h.get("hipotese") if isinstance(h, dict) else h
            if hipotese and self._normalizar(htexto) == hipotese:
                linha["n9_relacoes_observacionais"].append(solicitacao_id)

    @classmethod
    def _estado(
        cls,
        linha: dict[str, Any],
        min_observacoes: int,
        min_sucessos: int,
    ) -> str:
        if not linha.get("valor_economico_explicito"):
            return "sem_valor_identificado"
        evidencias = [x for x in linha.get("evidencias", []) if isinstance(x, dict)]
        n = len(evidencias)
        positivos = sum(x.get("resultado_observado") is True for x in evidencias)
        contradicoes = sum(x.get("resultado_observado") is False for x in evidencias)
        if n < 2:
            return "valor_candidato"
        if n < min_observacoes or positivos < min_sucessos:
            return "valor_observacional"
        valor = linha.get("valor_economico") or {}
        completo = all(
            valor.get(k) not in (None, "")
            for k in ("tipo_valor", "mecanismo_valor", "metrica_economica", "unidade", "direcao", "referencia")
        )
        if contradicoes == 0 and completo:
            return "maduro_para_formalizacao"
        return "valor_sustentado"

    def _salvar_linha(self, linha: dict[str, Any]) -> None:
        self._atomic_write(
            self.diretorio_linhas / f"{linha['linha_id']}.json",
            linha,
        )

    def _salvar_auditoria(self, auditoria: dict[str, Any]) -> None:
        agora = self._timestamp(self._agora_fn)
        auditoria = copy.deepcopy(auditoria)
        auditoria["observado_em"] = agora
        auditoria["auditoria_id"] = "ae5-" + self._sha({
            "ciclo_id": auditoria.get("ciclo_id"),
            "chave": auditoria.get("chave_deduplicacao"),
            "observado_em": agora,
        })[:24]
        self._atomic_write(
            self.diretorio_auditorias / f"{auditoria['auditoria_id']}.json",
            auditoria,
        )
        arquivos = sorted(
            self.diretorio_auditorias.glob("ae5-*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        for antigo in arquivos[: max(0, len(arquivos) - self.MAX_AUDITORIAS)]:
            try:
                antigo.unlink()
            except OSError:
                pass

    def _auditar(
        self,
        *,
        resultado: dict[str, Any],
        sinal: dict[str, Any],
        nova_linha: bool,
        linha_id: str | None,
        motivo: str,
        tipo_valor: str,
        digest: str | None,
        semantica: bool = False,
        similaridade: float | None = None,
        linha_similar: str | None = None,
    ) -> None:
        self._salvar_auditoria({
            "versao": self.VERSAO,
            "origem": self.FONTE,
            "ciclo_id": sinal.get("ciclo_id"),
            "oportunidade_id": sinal.get("oportunidade_id"),
            "linha_id": linha_id,
            "tipo_valor": tipo_valor,
            "chave_deduplicacao": digest,
            "nova_linha": nova_linha,
            "motivo": motivo,
            "estado_resultado": resultado.get("estado"),
            "estado_economico": resultado.get("estado_economico"),
            "valor_economico_identificado": resultado.get("valor_economico_identificado"),
            "fontes": sinal.get("fontes", []),
            "motivos_sinal": copy.deepcopy(
                sinal.get("motivos")
                or sinal.get("erros_valor")
                or []
            ),
            "possivel_duplicata_semantica": semantica,
            "similaridade_textual_indicativa": similaridade,
            "linha_semelhante": linha_similar,
            "invariantes": self._invariantes(),
        })

    def _base_resultado(self, estado: str, ciclo_id: str, digest: str | None = None) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": estado,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "ciclo_id": ciclo_id,
            "chave_deduplicacao": digest,
            **self._invariantes(),
        }

    def _base_linha(
        self,
        linha_id: str,
        sinal: dict[str, Any],
        valor: dict[str, Any],
        descricao: str,
        digest: str,
    ) -> dict[str, Any]:
        agora = self._timestamp(self._agora_fn)
        return {
            "linha_id": linha_id,
            "versao": self.VERSAO,
            "origem": self.FONTE,
            "criada_em": agora,
            "atualizada_em": agora,
            "estado": "valor_candidato",
            "valor_economico_explicito": True,
            "tipo_valor": valor["tipo_valor"],
            "problema_tecnico": sinal["limitacao"],
            "hipotese_valor": valor["mecanismo_valor"],
            "mecanismo_valor": valor["mecanismo_valor"],
            "metrica_economica": valor["metrica_economica"],
            "unidade": valor["unidade"],
            "direcao": valor["direcao"],
            "referencia": copy.deepcopy(valor.get("referencia")),
            "confianca": copy.deepcopy(valor.get("confianca")),
            "valor_economico": copy.deepcopy(valor),
            "descricao_semantica": descricao,
            "chave_deduplicacao": digest,
            "hipotese_tecnica": sinal["hipotese_tecnica"],
            "oportunidades_tecnicas": [],
            "evidencias": [],
            "n9_vinculos_explicitos": [],
            "n9_relacoes_observacionais": [],
            "observacoes": 0,
            "observacoes_positivas": 0,
            "contradicoes": 0,
            "ciclos_observados": [],
            "matura_para_formalizacao": False,
            "formalizacao": {"estado": "nao_iniciada", "solicitacao_id": None},
            **self._invariantes(),
        }

    def _adicionar_evidencia(
        self,
        linha: dict[str, Any],
        sinal: dict[str, Any],
        valor: dict[str, Any],
    ) -> bool:
        ciclo = sinal.get("ciclo_id")
        if not isinstance(ciclo, str) or ciclo in {
            e.get("ciclo_id") for e in linha.get("evidencias", []) if isinstance(e, dict)
        }:
            return False
        linha.setdefault("evidencias", []).append({
            "ciclo_id": ciclo,
            "oportunidade_id": sinal.get("oportunidade_id"),
            "resultado_observado": valor.get("resultado_observado"),
            "evidencia_economica": copy.deepcopy(valor.get("evidencia")),
            "evidencia_tecnica": {
                "limitacao": sinal.get("limitacao"),
                "hipotese": sinal.get("hipotese_tecnica"),
                "estado_ae4": sinal.get("estado_ae4"),
                "sucesso_ae4": sinal.get("sucesso_ae4"),
            },
            "fontes": copy.deepcopy(sinal.get("fontes", [])),
        })
        linha["evidencias"] = linha["evidencias"][-self.MAX_CICLOS_POR_LINHA:]
        linha["ciclos_observados"] = [
            e.get("ciclo_id") for e in linha["evidencias"] if isinstance(e, dict) and e.get("ciclo_id")
        ]
        linha["observacoes"] = len(linha["evidencias"])
        linha["observacoes_positivas"] = sum(
            e.get("resultado_observado") is True for e in linha["evidencias"]
        )
        linha["contradicoes"] = sum(
            e.get("resultado_observado") is False for e in linha["evidencias"]
        )
        oportunidade = sinal.get("oportunidade_id")
        if isinstance(oportunidade, str) and oportunidade and oportunidade not in linha["oportunidades_tecnicas"]:
            linha["oportunidades_tecnicas"].append(oportunidade)
            linha["oportunidades_tecnicas"] = linha["oportunidades_tecnicas"][-self.MAX_CICLOS_POR_LINHA:]
        return True

    def processar(self, resultado_ae4: dict[str, Any]) -> dict[str, Any]:
        """Processa um único sinal; a residência chama esta etapa uma vez por ciclo."""
        sinal, erros = self._extrair_sinal(resultado_ae4)
        ciclo_id = self._texto((resultado_ae4 or {}).get("ciclo_id")) or "sem-ciclo"

        if not self.habilitada:
            resultado = self._base_resultado("ae5_desabilitada", ciclo_id)
            resultado.update({"observada": False, "valor_economico_identificado": False})
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        if sinal is None:
            resultado = self._base_resultado("sem_sinal_ae4", ciclo_id)
            resultado.update({
                "observada": False,
                "valor_economico_identificado": False,
                "motivos": erros,
            })
            # A ausência de oportunidade também precisa ser observável.
            # Sem este registro, a AE5 pode ser chamada a cada ciclo e ainda
            # deixar a pasta de auditoria vazia, ocultando a causa do silêncio.
            self._auditar(
                resultado=resultado,
                sinal={
                    "ciclo_id": ciclo_id,
                    "oportunidade_id": None,
                    "fontes": [],
                    "motivos": erros,
                },
                nova_linha=False,
                linha_id=None,
                motivo="sinal_ae1_ausente_ou_incompleto",
                tipo_valor="desconhecido",
                digest=None,
            )
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        if sinal["valor_economico"] is None:
            resultado = self._base_resultado("sem_valor_identificado", sinal["ciclo_id"])
            resultado.update({
                "observada": False,
                "valor_economico_identificado": False,
                "oportunidade_id": sinal.get("oportunidade_id"),
                "motivos": sinal.get("erros_valor") or erros,
                "fontes": sinal.get("fontes", []),
            })
            self._auditar(
                resultado=resultado,
                sinal=sinal,
                nova_linha=False,
                linha_id=None,
                motivo="valor_economico_ausente_ou_incompleto",
                tipo_valor="desconhecido",
                digest=None,
            )
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        valor = sinal["valor_economico"]
        linha_id, digest, _ = self._chave(sinal)
        agora = self._agora(self._agora_fn)
        existente = self._carregar(self.diretorio_linhas / f"{linha_id}.json")
        duplicata_24h = self._auditoria_recente(digest, agora)

        if existente is None and duplicata_24h is not None:
            resultado = self._base_resultado("duplicata_exata_24h", sinal["ciclo_id"], digest)
            resultado.update({
                "observada": False,
                "nova_linha": False,
                "deduplicada_24h": True,
                "valor_economico_identificado": True,
                "valor": copy.deepcopy(valor),
                "linha_id": linha_id,
            })
            self._auditar(
                resultado=resultado,
                sinal=sinal,
                nova_linha=False,
                linha_id=linha_id,
                motivo="duplicata_exata_24h",
                tipo_valor=valor["tipo_valor"],
                digest=digest,
            )
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        if (
            existente is None
            and self._ciclo_tem_descoberta(sinal["ciclo_id"])
        ):
            resultado = self._base_resultado(
                "limite_uma_descoberta_por_ciclo",
                sinal["ciclo_id"],
                digest,
            )
            resultado.update({
                "observada": False,
                "nova_linha": False,
                "valor_economico_identificado": True,
                "valor": copy.deepcopy(valor),
            })
            self._auditar(
                resultado=resultado,
                sinal=sinal,
                nova_linha=False,
                linha_id=None,
                motivo="ciclo_ja_possui_descoberta",
                tipo_valor=valor["tipo_valor"],
                digest=digest,
            )
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        if existente is None and len(self._linhas_ativas()) >= self.MAX_LINHAS:
            resultado = self._base_resultado(
                "limite_linhas_economicas",
                sinal["ciclo_id"],
                digest,
            )
            resultado.update({
                "observada": False,
                "nova_linha": False,
                "valor_economico_identificado": True,
                "valor": copy.deepcopy(valor),
            })
            self._auditar(
                resultado=resultado,
                sinal=sinal,
                nova_linha=False,
                linha_id=None,
                motivo="max_200_linhas_ativas",
                tipo_valor=valor["tipo_valor"],
                digest=digest,
            )
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        if existente is None and self._tipo_em_cooldown(valor["tipo_valor"], agora):
            resultado = self._base_resultado("cooldown_tipo", sinal["ciclo_id"], digest)
            resultado.update({
                "observada": False,
                "nova_linha": False,
                "valor_economico_identificado": True,
                "valor": copy.deepcopy(valor),
                "cooldown_segundos": int(self.COOLDOWN_TIPO.total_seconds()),
            })
            self._auditar(
                resultado=resultado,
                sinal=sinal,
                nova_linha=False,
                linha_id=None,
                motivo="tipo_em_cooldown",
                tipo_valor=valor["tipo_valor"],
                digest=digest,
            )
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        descricao = self._descricao(sinal, valor)
        possivel, similaridade, semelhante = self._possivel_semantica(
            sinal, valor, self._linhas_ativas()
        )
        nova_linha = existente is None
        if existente is None:
            existente = self._base_linha(linha_id, sinal, valor, descricao, digest)
        else:
            existente.setdefault("evidencias", [])
            existente.setdefault("oportunidades_tecnicas", [])
            existente.setdefault("formalizacao", {"estado": "nao_iniciada", "solicitacao_id": None})
            existente["versao"] = self.VERSAO

        observada = self._adicionar_evidencia(existente, sinal, valor)
        existente["atualizada_em"] = self._timestamp(self._agora_fn)
        existente["estado"] = self._estado(
            existente,
            self.min_observacoes,
            self.min_sucessos,
        )
        existente["matura_para_formalizacao"] = (
            existente["estado"] == "maduro_para_formalizacao"
        )
        if existente["matura_para_formalizacao"]:
            existente["formalizacao"]["estado"] = "pronta_para_avaliacao"
        self._reconciliar_n9(existente)
        existente["possivel_duplicata_semantica"] = bool(possivel)
        existente["similaridade_textual_indicativa"] = similaridade
        existente["linha_semelhante"] = semelhante
        self._salvar_linha(existente)

        estado = (
            "oportunidade_economica_criada"
            if nova_linha
            else "evidencia_economica_acumulada"
            if observada
            else "duplicada_no_ciclo"
        )
        resultado = self._base_resultado(estado, sinal["ciclo_id"], digest)
        resultado.update({
            "observada": observada,
            "nova_linha": nova_linha,
            "deduplicada_24h": bool(duplicata_24h),
            "possivel_duplicata_semantica": bool(possivel),
            "similaridade_textual_indicativa": similaridade,
            "linha_semelhante": semelhante,
            "linha_id": linha_id,
            "valor_economico_identificado": True,
            "valor": copy.deepcopy(valor),
            "observacoes": existente["observacoes"],
            "observacoes_positivas": existente["observacoes_positivas"],
            "contradicoes": existente["contradicoes"],
            "estado_economico": existente["estado"],
            "madura_para_formalizacao": existente["matura_para_formalizacao"],
            "n9_vinculos_explicitos": copy.deepcopy(existente["n9_vinculos_explicitos"]),
            "n9_relacoes_observacionais": copy.deepcopy(existente["n9_relacoes_observacionais"]),
        })
        self._auditar(
            resultado=resultado,
            sinal=sinal,
            nova_linha=nova_linha,
            linha_id=linha_id,
            motivo="nova_linha_economica" if nova_linha else (
                "duplicata_exata_24h" if duplicata_24h else "evidencia_acumulada"
            ),
            tipo_valor=valor["tipo_valor"],
            digest=digest,
            semantica=possivel,
            similaridade=similaridade,
            linha_similar=semelhante,
        )
        self._ultimo_resultado = copy.deepcopy(resultado)
        return resultado

    def processar_lote(self, resultados_ae4: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """Processa no máximo 50 sinais sem materializar uma entrada ilimitada."""
        resultados: list[dict[str, Any]] = []
        for indice, item in enumerate(islice(resultados_ae4, self.MAX_SINAIS_POR_PASSAGEM + 1)):
            if indice == self.MAX_SINAIS_POR_PASSAGEM:
                resultados.append({
                    "sucesso": True,
                    "estado": "limite_50_sinais",
                    "origem": self.FONTE,
                    "observada": False,
                    **self._invariantes(),
                })
                break
            resultados.append(self.processar(item))
        return {
            "sucesso": all(x.get("sucesso") is True for x in resultados),
            "estado": "passagem_ae5_processada",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "sinais_processados": min(len(resultados), self.MAX_SINAIS_POR_PASSAGEM),
            "novas_linhas": sum(x.get("nova_linha") is True for x in resultados),
            "duplicadas_24h": sum(x.get("deduplicada_24h") is True for x in resultados),
            "resultados": copy.deepcopy(resultados),
            **self._invariantes(),
        }

    def reconciliar_historico(self, limite: int = 200) -> dict[str, Any]:
        if not isinstance(limite, int) or limite < 1:
            raise ValueError("limite_invalido")
        diretorio = self.repositorio.parent / "Nyxal-evolution-ae4"
        if not diretorio.is_dir():
            return {
                "sucesso": True,
                "estado": "sem_auditorias_ae4",
                "auditorias_processadas": 0,
                "novos_sinais": 0,
                **self._invariantes(),
            }
        arquivos = sorted(
            diretorio.glob("ae4-ciclo-*.json"),
            key=lambda p: p.stat().st_mtime,
        )[-limite:]
        processadas = novas = 0
        for caminho in arquivos:
            auditoria = self._carregar(caminho)
            if not isinstance(auditoria, dict):
                continue
            etapas = auditoria.get("etapas")
            ae1 = next(
                (
                    e for e in etapas
                    if isinstance(e, dict) and e.get("etapa") == "AE1"
                ),
                None,
            ) if isinstance(etapas, list) else None
            oportunidade_id = self._texto(ae1.get("oportunidade_id")) if isinstance(ae1, dict) else None
            if not oportunidade_id:
                continue
            oportunidade = self._carregar(
                self.repositorio.parent
                / "Nyxal-evolution-opportunities"
                / f"{oportunidade_id}.json"
            )
            if not isinstance(oportunidade, dict):
                continue
            antes = set()
            for linha in self._linhas_ativas():
                if oportunidade_id in linha.get("oportunidades_tecnicas", []):
                    antes = set(linha.get("ciclos_observados", []))
                    break
            resultado = self.processar({
                "ciclo_id": auditoria.get("ciclo_id"),
                "sucesso": auditoria.get("estado") != "ae4_ae1_falhou",
                "estado": auditoria.get("estado"),
                "ae1": {"valor": oportunidade},
            })
            processadas += 1
            if resultado.get("observada") is True:
                depois = set()
                linha_id = resultado.get("linha_id")
                if isinstance(linha_id, str):
                    linha = self._carregar(self.diretorio_linhas / f"{linha_id}.json")
                    if linha:
                        depois = set(linha.get("ciclos_observados", []))
                if depois != antes:
                    novas += 1
        return {
            "sucesso": True,
            "estado": "historico_ae4_reconciliado",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "auditorias_processadas": processadas,
            "novos_sinais": novas,
            "linhas_economicas": len(self._linhas_ativas()),
            **self._invariantes(),
        }

    def listar(self, *, maduras: bool = False, limite: int = 20) -> list[dict[str, Any]]:
        if not isinstance(limite, int) or limite < 1:
            raise ValueError("limite_invalido")
        registros = []
        for caminho in self._linhas_paths():
            registro = self._carregar(caminho)
            if not isinstance(registro, dict):
                continue
            if maduras and registro.get("estado") != "maduro_para_formalizacao":
                continue
            registros.append(registro)
            if len(registros) >= limite:
                break
        return registros

    def contexto(self) -> dict[str, Any]:
        linhas = self._linhas_ativas()
        por_estado = {estado: 0 for estado in self.ESTADOS}
        for linha in linhas:
            estado = linha.get("estado")
            if estado in por_estado:
                por_estado[estado] += 1
        auditorias = self._auditorias_paths()
        sem_valor = sum(
            1 for caminho in auditorias
            if (self._carregar(caminho) or {}).get("motivo") == "valor_economico_ausente_ou_incompleto"
        )
        duplicadas = sum(
            1 for caminho in auditorias
            if (self._carregar(caminho) or {}).get("motivo") == "duplicata_exata_24h"
        )
        cooldowns = sum(
            1 for caminho in auditorias
            if (self._carregar(caminho) or {}).get("motivo") == "tipo_em_cooldown"
        )
        return {
            "sucesso": True,
            "estado": "ae5_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "habilitada": self.habilitada,
            "linhas_economicas_ativas": len(linhas),
            "linhas_maduras": por_estado["maduro_para_formalizacao"],
            "linhas_candidatas": por_estado["valor_candidato"],
            "linhas_observacionais": por_estado["valor_observacional"],
            "linhas_sustentadas": por_estado["valor_sustentado"],
            "auditorias": len(auditorias),
            "sinais_sem_valor": sem_valor,
            "duplicadas_24h": duplicadas,
            "bloqueios_cooldown": cooldowns,
            "estados_observados": por_estado,
            "limites": {
                "max_linhas": self.MAX_LINHAS,
                "max_ciclos_por_linha": self.MAX_CICLOS_POR_LINHA,
                "max_sinais_por_passagem": self.MAX_SINAIS_POR_PASSAGEM,
                "cooldown_minutos": 30,
                "janela_duplicata_horas": 24,
            },
            "linhas_maduras_resumo": [
                {
                    "linha_id": linha.get("linha_id"),
                    "tipo_valor": linha.get("tipo_valor"),
                    "metrica_economica": linha.get("metrica_economica"),
                    "estado": linha.get("estado"),
                    "observacoes": linha.get("observacoes"),
                }
                for linha in self.listar(maduras=True, limite=5)
            ],
            "ultimo_resultado": copy.deepcopy(self._ultimo_resultado),
            **self._invariantes(),
        }


__all__ = ["DescobertaContinuaGovernadaAE5"]
