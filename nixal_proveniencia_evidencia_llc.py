#!/usr/bin/env python3
"""LLC.6 — integridade e proveniencia verificavel da evidencia do LLC.4.

Esta camada nao coleta dados, nao executa acoes e nao prova causalidade.
Ela verifica se uma observacao usada pelo LLC.5 pode ser rastreada
deterministicamente ate um snapshot produzido pelo LLC.4.
"""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from nixal_evidencia_ambiental_llc import EvidenciaAmbientalLLC


class ProvenienciaEvidenciaLLC:
    FONTE = "llc_proveniencia_evidencia"
    VERSAO = "LLC.6.0.0"
    ORIGEM_ESPERADA = EvidenciaAmbientalLLC.FONTE
    VERSAO_ESPERADA = EvidenciaAmbientalLLC.VERSAO
    MODO_ESPERADO = EvidenciaAmbientalLLC.MODO

    INVARIANTES = {
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "stable_modificada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
        "execucao_local": False,
        "treinamento_automatico": False,
        "implantacao_automatica": False,
        "causalidade_ambiental_comprovada": False,
    }

    @staticmethod
    def _texto(valor: Any) -> str | None:
        if not isinstance(valor, str):
            return None
        valor = valor.strip()
        return valor or None

    @staticmethod
    def _timestamp_valido(valor: Any) -> bool:
        if not isinstance(valor, str) or not valor.strip():
            return False
        try:
            dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return False
        return dt.tzinfo is not None

    @classmethod
    def _snapshot_id_esperado(cls, snapshot: dict[str, Any]) -> str | None:
        host = snapshot.get("host")
        recursos = snapshot.get("recursos")
        timestamp = snapshot.get("timestamp")
        if not isinstance(host, dict) or not isinstance(recursos, dict):
            return None
        corpo_minimo = {
            "host": {
                "sistema": host.get("sistema"),
                "release": host.get("release"),
                "arquitetura": host.get("arquitetura"),
                "modo": cls.MODO_ESPERADO,
            },
            "recursos": copy.deepcopy(recursos),
            "timestamp": timestamp,
        }
        return EvidenciaAmbientalLLC._hash(corpo_minimo)

    @classmethod
    def _observacao_id_esperado(cls, observacao: dict[str, Any]) -> str | None:
        if not all(chave in observacao for chave in (
            "snapshot_id", "caminho", "valor", "timestamp"
        )):
            return None
        return EvidenciaAmbientalLLC._hash({
            "snapshot_id": observacao.get("snapshot_id"),
            "caminho": observacao.get("caminho"),
            "valor": observacao.get("valor"),
            "timestamp": observacao.get("timestamp"),
        })

    @classmethod
    def validar(
        cls,
        *,
        evidencia: dict[str, Any],
        metrica: dict[str, Any],
        transicao_id: str,
        ciclo_id: str,
    ) -> dict[str, Any]:
        erros: list[str] = []

        if not isinstance(evidencia, dict):
            return {
                "sucesso": False,
                "estado": "proveniencia_evidencia_invalida",
                "proveniencia_evidencia_valida": False,
                "erros": ["evidencia_invalida"],
                **copy.deepcopy(cls.INVARIANTES),
            }

        if not isinstance(metrica, dict):
            erros.append("metrica_invalida")

        snapshot = evidencia.get("snapshot")
        observacao = evidencia.get("observacao")
        for nome, valor in (("snapshot", snapshot), ("observacao", observacao)):
            if not isinstance(valor, dict):
                erros.append(f"{nome}_invalido")

        origem = evidencia.get("origem")
        versao = evidencia.get("versao")
        modo = evidencia.get("modo")
        if origem != cls.ORIGEM_ESPERADA:
            erros.append("origem_llc4_invalida")
        if versao != cls.VERSAO_ESPERADA:
            erros.append("versao_llc4_invalida")
        if modo != cls.MODO_ESPERADO:
            erros.append("modo_nao_somente_leitura")

        tid = cls._texto(transicao_id)
        cid = cls._texto(ciclo_id)
        if not tid:
            erros.append("transicao_id_invalido")
        if not cid:
            erros.append("ciclo_id_invalido")

        if isinstance(snapshot, dict):
            if snapshot.get("evidencia_ambiental_observacional") is not True:
                erros.append("snapshot_sem_evidencia_observacional")
            if snapshot.get("causalidade_ambiental_comprovada") is True:
                erros.append("snapshot_com_causalidade_preexistente")
            if not cls._timestamp_valido(snapshot.get("timestamp")):
                erros.append("snapshot_timestamp_invalido")

            esperado = cls._snapshot_id_esperado(snapshot)
            if not cls._texto(snapshot.get("snapshot_id")):
                erros.append("snapshot_id_ausente")
            elif esperado != snapshot.get("snapshot_id"):
                erros.append("snapshot_id_integro_invalido")

        if isinstance(observacao, dict):
            if observacao.get("evidencia_ambiental_observacional") is not True:
                erros.append("observacao_sem_evidencia_observacional")
            if observacao.get("causalidade_ambiental_comprovada") is True:
                erros.append("observacao_com_causalidade_preexistente")
            if not cls._timestamp_valido(observacao.get("timestamp")):
                erros.append("observacao_timestamp_invalido")
            if isinstance(snapshot, dict) and observacao.get("snapshot_id") != snapshot.get("snapshot_id"):
                erros.append("observacao_snapshot_divergente")
            if isinstance(snapshot, dict) and observacao.get("timestamp") != snapshot.get("timestamp"):
                erros.append("observacao_timestamp_divergente")

            esperado_obs = cls._observacao_id_esperado(observacao)
            if not cls._texto(observacao.get("id")):
                erros.append("observacao_id_ausente")
            elif esperado_obs != observacao.get("id"):
                erros.append("observacao_id_integro_invalido")

        if isinstance(metrica, dict) and isinstance(observacao, dict):
            for chave in ("nome", "caminho", "unidade", "direcao_melhor"):
                if observacao.get(chave) != metrica.get(chave):
                    erros.append(f"metrica_{chave}_divergente")
            if observacao.get("fonte") != metrica.get("fonte"):
                erros.append("metrica_fonte_divergente")
            caminho = metrica.get("caminho")
            if caminho not in EvidenciaAmbientalLLC.METRICAS_NUMERICAS:
                erros.append("metrica_nao_declarada_llc4")

        valido = not erros
        observacao_id = observacao.get("id") if isinstance(observacao, dict) else None
        snapshot_id = snapshot.get("snapshot_id") if isinstance(snapshot, dict) else None

        return {
            "sucesso": True,
            "estado": "proveniencia_evidencia_valida" if valido else "proveniencia_evidencia_invalida",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "proveniencia_evidencia_valida": valido,
            "proveniencia": {
                "snapshot_id": snapshot_id,
                "observacao_id": observacao_id,
                "transicao_id": tid,
                "ciclo_id": cid,
            },
            "erros": erros,
            **copy.deepcopy(cls.INVARIANTES),
        }


__all__ = ["ProvenienciaEvidenciaLLC"]
