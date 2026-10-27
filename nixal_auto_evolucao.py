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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AutoEvolucaoGovernadaNixOS:
    """Descoberta e registro seguro de oportunidades de evolução."""

    FONTE = "auto_evolucao_governada_nyxos"
    VERSAO = "AE1.0.0"
    MAX_OPORTUNIDADES = 200
    MAX_CICLOS_OBSERVADOS = 20

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

    @staticmethod
    def _texto_limitado(valor: Any, limite: int) -> str | None:
        """Normaliza texto observado e limita o tamanho antes da persistência."""
        if not isinstance(valor, str) or isinstance(limite, bool) or limite < 1:
            return None
        valor = " ".join(valor.split())
        return valor[:limite] or None

    @classmethod
    def _id_oportunidade(
        cls,
        ciclo_id: str,
        limitacao: str,
        hipotese: str,
        *,
        recorrente: bool = False,
    ) -> str:
        base = {
            # Sinais automáticos recorrentes usam uma identidade estável para
            # atualizar a mesma oportunidade, em vez de criar uma por ciclo.
            "ciclo_id": "necessidade_recorrente" if recorrente else ciclo_id,
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

    @classmethod
    def _extrair_necessidade_observada(
        cls,
        ciclo: dict[str, Any],
        valor: dict[str, Any],
    ) -> dict[str, Any]:
        prioridade = valor.get("necessidade_prioritaria")
        prioridade = prioridade if isinstance(prioridade, dict) else {}
        necessidade = (
            prioridade.get("selecionada")
            if isinstance(prioridade.get("selecionada"), dict)
            else prioridade
        )

        if not cls._texto_limitado(
            necessidade.get("problema") or necessidade.get("necessidade"), 240
        ):
            decisao = valor.get("decisao")
            decisao = decisao if isinstance(decisao, dict) else {}
            alternativa = decisao.get("necessidade_prioritaria")
            if isinstance(alternativa, dict):
                necessidade = alternativa

        # Persistir apenas campos previstos; não copiar payloads, tokens ou objetos
        # arbitrários anexados à necessidade pelo Runtime ou por uma integração.
        limites = {
            "origem": 80,
            "problema": 240,
            "necessidade": 120,
            "tipo_problema": 40,
            "tipo": 80,
            "prioridade": 32,
            "motivo": 240,
        }
        normalizada = {}
        for campo, limite in limites.items():
            texto = cls._texto_limitado(necessidade.get(campo), limite)
            if texto is not None:
                normalizada[campo] = texto
        if "problema" not in normalizada and "necessidade" in normalizada:
            normalizada["problema"] = normalizada["necessidade"]
        if normalizada.get("problema") or normalizada.get("necessidade"):
            return normalizada

        erro = cls._texto_limitado(ciclo.get("erro") or ciclo.get("motivo"), 240)
        estado = cls._texto_limitado(ciclo.get("estado"), 40)
        if ciclo.get("sucesso") is False or estado == "erro":
            if erro:
                return {
                    "origem": "runtime_residente",
                    "problema": f"falha_ciclo_residente: {erro}"[:240],
                    "tipo_problema": "falha_operacional",
                    "tipo": "fiabilidade_operacional",
                    "necessidade": "investigar_falha_ciclo_residente",
                    "prioridade": "alta",
                    "motivo": (
                        "O ciclo registrou uma falha observada; a causa raiz "
                        "permanece não confirmada."
                    ),
                }

        return {}

    @classmethod
    def _formular_hipotese_observacional(
        cls,
        necessidade: dict[str, Any],
    ) -> dict[str, Any] | None:
        problema = cls._texto_limitado(
            necessidade.get("problema") or necessidade.get("necessidade"), 240
        )
        nome = cls._texto_limitado(necessidade.get("necessidade"), 120)
        if not problema:
            return None

        problema = problema[:240]
        nome = nome[:120] if nome else "investigar_necessidade_observada"
        tipo_problema = cls._texto_limitado(necessidade.get("tipo_problema"), 40) or ""
        if tipo_problema == "inconsistencia":
            texto = (
                f"Investigar a inconsistência observada '{problema}' e confrontar "
                "as fontes de evidência pode indicar uma correção mínima; a causa "
                "e o benefício continuam por confirmar em teste independente."
            )
        elif tipo_problema == "lacuna":
            texto = (
                f"Investigar a lacuna observada '{problema}' pode definir como "
                "documentá-la ou reduzi-la sem presumir que uma capacidade ausente "
                "já existe; o benefício continua por confirmar em teste."
            )
        elif tipo_problema == "falha_operacional":
            texto = (
                f"Investigar a falha operacional observada '{problema}' pode "
                "identificar uma causa reproduzível e uma correção reversível; "
                "nenhuma causa raiz é presumida antes da validação."
            )
        else:
            texto = (
                f"Investigar a necessidade '{nome}' diante do problema observado "
                f"'{problema}' pode revelar uma melhoria verificável; o benefício "
                "permanece não confirmado até um teste independente."
            )

        return {
            "estado_atual": "provisoria",
            "hipotese": texto,
            "origem": "ae1_hipotese_observacional_automatica",
            "necessidade": nome,
            "problema_observado": problema,
            "resultado_observado": None,
        }

    @classmethod
    def _evidencia_ciclo(
        cls,
        ciclo: dict[str, Any],
        necessidade: dict[str, Any],
    ) -> dict[str, Any]:
        sucesso = ciclo.get("sucesso")
        return {
            "ciclo_id": cls._texto_limitado(ciclo.get("ciclo_id"), 128),
            "observado_em": cls._timestamp(),
            "estado_ciclo": cls._texto_limitado(ciclo.get("estado"), 40) or "desconhecido",
            "ciclo_sucesso": sucesso if isinstance(sucesso, bool) else None,
            "prioridade": cls._texto_limitado(necessidade.get("prioridade"), 32) or "indeterminada",
            "origem_necessidade": cls._texto_limitado(necessidade.get("origem"), 80),
            "motivo_observado": cls._texto_limitado(necessidade.get("motivo"), 240),
        }

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
        temporario: Path | None = None
        try:
            # NamedTemporaryFile cria um temporário exclusivo com permissões
            # restritas; o replace atômico evita leitores observarem JSON parcial.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.diretorio_oportunidades,
                prefix=f".{oportunidade_id}.",
                suffix=".tmp",
                delete=False,
            ) as arquivo:
                temporario = Path(arquivo.name)
                arquivo.write(json.dumps(
                    oportunidade,
                    ensure_ascii=False,
                    indent=2,
                ))
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, caminho)
            temporario = None
        finally:
            if temporario is not None:
                try:
                    temporario.unlink(missing_ok=True)
                except OSError:
                    pass

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

        ciclo_id = self._texto_limitado(ciclo.get("ciclo_id"), 128)
        valor = ciclo.get("valor")
        valor = valor if isinstance(valor, dict) else {}
        necessidade = self._extrair_necessidade_observada(ciclo, valor)

        limitacao = self._texto_limitado(
            necessidade.get("problema")
            or necessidade.get("necessidade"),
            240,
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
            hipotese = self._texto_limitado(
                hipotese_obj.get("hipotese")
                or hipotese_obj.get("texto")
                or hipotese_obj.get("enunciado"),
                1000,
            )
        elif isinstance(hipotese_obj, str):
            hipotese = self._texto_limitado(hipotese_obj, 1000)

        hipotese_auto_formulada = False
        if hipotese is None and necessidade:
            formulacao = self._formular_hipotese_observacional(necessidade)
            if formulacao is not None:
                hipotese_obj = formulacao
                hipotese = self._texto(formulacao.get("hipotese"))
                hipotese_auto_formulada = hipotese is not None

        if not ciclo_id or not limitacao or not hipotese:
            return {
                "sucesso": True,
                "estado": "sem_oportunidade",
                "origem": self.FONTE,
                "motivo": (
                    "Não há uma limitação observada e uma hipótese útil, "
                    "explícita ou provisoriamente formulada a partir da evidência."
                ),
                "oportunidade_criada": False,
                "hipotese_auto_formulada": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "arquitetura_modificada": False,
            }

        oportunidade_id = self._id_oportunidade(
            ciclo_id,
            limitacao,
            hipotese,
            recorrente=hipotese_auto_formulada,
        )
        caminho = self._arquivo(oportunidade_id)
        existente = self._carregar(caminho)

        if existente is not None:
            observacao_atualizada = False
            if hipotese_auto_formulada:
                ciclos = existente.get("ciclos_observados")
                if not isinstance(ciclos, list):
                    ciclo_origem = self._texto(existente.get("ciclo_origem"))
                    ciclos = [ciclo_origem] if ciclo_origem else []
                ciclos = [item for item in ciclos if isinstance(item, str) and item]
                if ciclo_id not in ciclos:
                    evidencia_atual = self._evidencia_ciclo(ciclo, necessidade)
                    ciclos = (ciclos + [ciclo_id])[-self.MAX_CICLOS_OBSERVADOS:]
                    evidencias = existente.get("evidencias_observadas")
                    if not isinstance(evidencias, list):
                        evidencias = []
                    evidencias = [
                        item for item in evidencias if isinstance(item, dict)
                    ]
                    evidencias.append(evidencia_atual)
                    existente["ciclos_observados"] = ciclos
                    existente["evidencias_observadas"] = (
                        evidencias[-self.MAX_CICLOS_OBSERVADOS:]
                    )
                    total = existente.get("observacoes_total", 1)
                    if isinstance(total, bool) or not isinstance(total, int) or total < 1:
                        total = max(1, len(ciclos) - 1)
                    existente["observacoes_total"] = total + 1
                    existente["ultima_observacao_em"] = evidencia_atual["observado_em"]
                    existente["ultimo_ciclo_observado"] = ciclo_id
                    self._salvar_oportunidade(existente)
                    observacao_atualizada = True

            return {
                "sucesso": True,
                "estado": (
                    "oportunidade_reforcada"
                    if observacao_atualizada
                    else "oportunidade_ja_registrada"
                ),
                "origem": self.FONTE,
                "valor": copy.deepcopy(existente),
                "oportunidade_criada": False,
                "observacao_atualizada": observacao_atualizada,
                "hipotese_auto_formulada": hipotese_auto_formulada,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "arquitetura_modificada": False,
            }

        evidencia_inicial = self._evidencia_ciclo(ciclo, necessidade)
        oportunidade = {
            "oportunidade_id": oportunidade_id,
            "versao": self.VERSAO,
            "origem": self.FONTE,
            "estado": "oportunidade",
            "criada_em": evidencia_inicial["observado_em"],
            "ciclo_origem": ciclo_id,
            "limitacao": limitacao,
            "hipotese": hipotese,
            "hipotese_gerada_automaticamente": hipotese_auto_formulada,
            "estado_hipotese": (
                self._texto_limitado(hipotese_obj.get("estado_atual"), 32) or "provisoria"
                if isinstance(hipotese_obj, dict)
                else "provisoria"
            ),
            "prioridade": {
                "tipo": necessidade.get("tipo"),
                "tipo_problema": necessidade.get("tipo_problema"),
                "prioridade": necessidade.get("prioridade"),
                "necessidade": necessidade.get("necessidade"),
            },
            "evidencias": {
                "ciclo_sucesso": ciclo.get("sucesso") if isinstance(ciclo.get("sucesso"), bool) else None,
                "estado_ciclo": self._texto_limitado(ciclo.get("estado"), 40) or "desconhecido",
                "necessidade_observada": copy.deepcopy(necessidade),
                "origem_hipotese": (
                    "ae1_hipotese_observacional_automatica"
                    if hipotese_auto_formulada
                    else "hipotese_fornecida_pelo_ciclo"
                ),
            },
            "ciclos_observados": [ciclo_id] if hipotese_auto_formulada else [],
            "evidencias_observadas": (
                [evidencia_inicial] if hipotese_auto_formulada else []
            ),
            "observacoes_total": 1 if hipotese_auto_formulada else 0,
            "ultima_observacao_em": evidencia_inicial["observado_em"],
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
            "hipotese_auto_formulada": hipotese_auto_formulada,
            "observacao_atualizada": False,
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
            "hipotese_provisoria_por_necessidade_observada": True,
            "deduplicacao_de_necessidade_recorrente": True,
            "execucao_experimental_automatica": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "quantidade_oportunidades": len(self.listar(self.MAX_OPORTUNIDADES)),
            "ultimas_oportunidades": self.listar(5),
        }


__all__ = ["AutoEvolucaoGovernadaNixOS"]
