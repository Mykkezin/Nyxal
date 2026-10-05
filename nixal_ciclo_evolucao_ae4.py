#!/usr/bin/env python3
"""
NYXAL — CICLO DE EVOLUÇÃO RESIDENTE AE4

Orquestra, em um único ciclo residente, as camadas já existentes:
AE1 → AE2 → AE3.

Responsabilidade:
- observar a descoberta AE1;
- permitir a execução AE2 somente pela política já existente;
- interpretar o resultado por AE3;
- registrar um resumo auditável das etapas observadas no ciclo.

Não:
- gera código;
- executa código localmente;
- cria autorização;
- faz merge;
- altera stable/main;
- promove conhecimento permanente;
- modifica arquitetura;
- executa retry automático;
- substitui os gates N9.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CicloEvolucaoResidenteAE4:
    """Coordena AE1, AE2 e AE3 sem ampliar a autoridade de integração."""

    FONTE = "ciclo_evolucao_residente_ae4"
    VERSAO = "AE4.0.0"
    MAX_POR_CICLO = 1
    MAX_AUDITORIAS = 200

    def __init__(
        self,
        auto_evolucao: Any,
        auto_experimento: Any,
        auto_avaliacao: Any,
        *,
        repositorio: str | Path,
        habilitada: bool = True,
    ) -> None:
        if not hasattr(auto_evolucao, "avaliar_ciclo") or not callable(
            auto_evolucao.avaliar_ciclo
        ):
            raise TypeError("ae1_precisa_avaliar_ciclo")

        if not hasattr(auto_experimento, "processar_pendentes") or not callable(
            auto_experimento.processar_pendentes
        ):
            raise TypeError("ae2_precisa_processar_pendentes")

        if not hasattr(auto_avaliacao, "avaliar") or not callable(
            auto_avaliacao.avaliar
        ):
            raise TypeError("ae3_precisa_avaliar")

        self.auto_evolucao = auto_evolucao
        self.auto_experimento = auto_experimento
        self.auto_avaliacao = auto_avaliacao
        self.repositorio = Path(repositorio).resolve()
        self.diretorio_auditorias = (
            self.repositorio.parent / "Nyxal-evolution-ae4"
        ).resolve()
        self.diretorio_auditorias.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.habilitada = bool(habilitada)
        self._ultimo_resultado: dict[str, Any] | None = None

    @staticmethod
    def _agora() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _id_auditoria(ciclo_id: str) -> str:
        digest = hashlib.sha256(
            ciclo_id.encode("utf-8")
        ).hexdigest()[:20]
        return f"ae4-ciclo-{digest}"

    @classmethod
    def _arquivo_auditoria(
        cls,
        diretorio: Path,
        ciclo_id: str,
    ) -> Path:
        return diretorio / f"{cls._id_auditoria(ciclo_id)}.json"

    @staticmethod
    def _atomic_write_json(
        caminho: Path,
        dados: dict[str, Any],
    ) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_name(
            caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                dados,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporario, caminho)

    @staticmethod
    def _texto(valor: Any) -> str | None:
        if not isinstance(valor, str):
            return None
        valor = valor.strip()
        return valor or None

    @classmethod
    def _resumir_etapa(
        cls,
        nome: str,
        resultado: Any,
    ) -> dict[str, Any]:
        dados = resultado if isinstance(resultado, dict) else {}
        resumo = {
            "etapa": nome,
            "sucesso": dados.get("sucesso"),
            "estado": dados.get("estado"),
        }

        for chave in (
            "oportunidade_criada",
            "processada",
            "retry_automatico",
            "aprovado",
            "comparacao_disponivel",
            "aprendizado_disponivel",
            "candidato_presente",
            "proposta_presente",
            "autorizacao_explicita",
            "integracao_executada",
            "stable_modificada",
            "arquitetura_modificada",
            "conhecimento_permanente",
        ):
            if chave in dados:
                resumo[chave] = dados.get(chave)

        for chave in ("oportunidade_id", "solicitacao_id"):
            valor = dados.get(chave)
            if isinstance(valor, str) and valor.strip():
                resumo[chave] = valor

        valor = dados.get("valor")
        if isinstance(valor, dict):
            oportunidade_id = valor.get("oportunidade_id")
            if isinstance(oportunidade_id, str) and oportunidade_id.strip():
                resumo["oportunidade_id"] = oportunidade_id

        return resumo

    @staticmethod
    def _extrair_oportunidade(
        resultado_ae1: dict[str, Any],
    ) -> dict[str, Any]:
        valor = resultado_ae1.get("valor")
        if isinstance(valor, dict):
            return copy.deepcopy(valor)
        return {}

    @classmethod
    def _estado_final(
        cls,
        *,
        ae1: dict[str, Any],
        ae2: dict[str, Any],
        ae3: dict[str, Any],
    ) -> str:
        if ae1.get("sucesso") is not True:
            return "ae4_ae1_falhou"

        if ae2.get("processada") is not True:
            return "ae4_sem_experimento_para_avaliar"

        if ae3.get("estado") == "melhoria_comprovada":
            return "ae4_melhoria_comprovada"

        if ae3.get("estado") == "evolucao_rejeitada":
            return "ae4_evolucao_rejeitada"

        if ae3.get("estado") == "resultado_inconclusivo":
            return "ae4_resultado_inconclusivo"

        return "ae4_ciclo_observado"

    def _salvar_auditoria(
        self,
        auditoria: dict[str, Any],
    ) -> None:
        ciclo_id = auditoria.get("ciclo_id")
        if not isinstance(ciclo_id, str) or not ciclo_id.strip():
            raise ValueError("ciclo_id_invalido")

        caminho = self._arquivo_auditoria(
            self.diretorio_auditorias,
            ciclo_id,
        )
        self._atomic_write_json(caminho, auditoria)

        arquivos = sorted(
            self.diretorio_auditorias.glob("ae4-ciclo-*.json"),
            key=lambda item: item.stat().st_mtime,
        )
        excesso = len(arquivos) - self.MAX_AUDITORIAS
        if excesso > 0:
            for antigo in arquivos[:excesso]:
                try:
                    antigo.unlink()
                except OSError:
                    pass

    def processar_ciclo(
        self,
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        """Executa uma passagem AE1→AE2→AE3 e registra o resumo auditável."""
        if not isinstance(ciclo, dict):
            raise ValueError("ciclo_invalido")

        ciclo_id = self._texto(ciclo.get("ciclo_id"))
        if ciclo_id is None:
            raise ValueError("ciclo_id_invalido")

        if not self.habilitada:
            resultado = {
                "sucesso": True,
                "estado": "ae4_desabilitada",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "ciclo_id": ciclo_id,
                "processada": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        try:
            ae1 = self.auto_evolucao.avaliar_ciclo(copy.deepcopy(ciclo))
        except Exception as erro:
            ae1 = {
                "sucesso": False,
                "estado": "ae1_falhou",
                "origem": getattr(self.auto_evolucao, "FONTE", "auto_evolucao"),
                "motivo": f"{type(erro).__name__}: {erro}",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }

        try:
            ae2 = self.auto_experimento.processar_pendentes()
        except Exception as erro:
            ae2 = {
                "sucesso": False,
                "estado": "ae2_falhou",
                "origem": getattr(self.auto_experimento, "FONTE", "auto_experimento"),
                "processada": False,
                "retry_automatico": False,
                "motivo": f"{type(erro).__name__}: {erro}",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }

        if ae2.get("processada") is True:
            try:
                ae3 = self.auto_avaliacao.avaliar(copy.deepcopy(ae2))
            except Exception as erro:
                ae3 = {
                    "sucesso": False,
                    "estado": "ae3_falhou",
                    "origem": getattr(self.auto_avaliacao, "FONTE", "auto_avaliacao"),
                    "motivo": f"{type(erro).__name__}: {erro}",
                    "autorizacao_explicita": False,
                    "integracao_executada": False,
                    "stable_modificada": False,
                    "arquitetura_modificada": False,
                    "conhecimento_permanente": False,
                }
        else:
            ae3 = {
                "sucesso": True,
                "estado": "sem_experimento_para_avaliar",
                "origem": getattr(self.auto_avaliacao, "FONTE", "auto_avaliacao"),
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }

        oportunidade = self._extrair_oportunidade(ae1)
        oportunidade_id = self._texto(oportunidade.get("oportunidade_id"))
        solicitacao_id = self._texto(ae2.get("solicitacao_id")) or self._texto(
            ae3.get("solicitacao_id")
        )

        auditoria = {
            "auditoria_id": self._id_auditoria(ciclo_id),
            "versao": self.VERSAO,
            "criada_em": self._agora(),
            "ciclo_id": ciclo_id,
            "estado": self._estado_final(ae1=ae1, ae2=ae2, ae3=ae3),
            "pipeline": {
                "ordem": ["AE1", "AE2", "AE3"],
                "quantidade_experimentos_maxima": self.MAX_POR_CICLO,
                "execucao_local": False,
                "retry_automatico": False,
            },
            "vinculos": {
                "oportunidade_id": oportunidade_id,
                "solicitacao_id": solicitacao_id,
                "relacao_confirmada": False,
                "tipo_relacao": "observacional",
                "motivo": (
                    "AE2 consome solicitações formais pendentes do repositório "
                    "global; a AE4 não presume causalidade entre uma oportunidade "
                    "AE1 e uma solicitação AE2 sem vínculo explícito persistido."
                ),
            },
            "etapas": [
                self._resumir_etapa("AE1", ae1),
                self._resumir_etapa("AE2", ae2),
                self._resumir_etapa("AE3", ae3),
            ],
            "invariantes": {
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }

        self._salvar_auditoria(auditoria)

        resultado = {
            "sucesso": ae1.get("sucesso") is True
            and ae2.get("sucesso") is True
            and ae3.get("sucesso") is True,
            "estado": auditoria["estado"],
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "ciclo_id": ciclo_id,
            "processada": True,
            "oportunidade_id": oportunidade_id,
            "solicitacao_id": solicitacao_id,
            "vinculo_observacional_confirmado": False,
            "ae1": copy.deepcopy(ae1),
            "ae2": copy.deepcopy(ae2),
            "ae3": copy.deepcopy(ae3),
            "auditoria_id": auditoria["auditoria_id"],
            "auditoria_arquivo": str(
                self._arquivo_auditoria(self.diretorio_auditorias, ciclo_id)
            ),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }
        self._ultimo_resultado = copy.deepcopy(resultado)
        return resultado

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "ae4_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "habilitada": self.habilitada,
            "max_por_ciclo": self.MAX_POR_CICLO,
            "ultimo_resultado": copy.deepcopy(self._ultimo_resultado),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = ["CicloEvolucaoResidenteAE4"]
