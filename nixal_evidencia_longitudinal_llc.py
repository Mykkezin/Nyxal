#!/usr/bin/env python3
"""LLC.5 — evidência causal longitudinal do habitat.

Vincula snapshots ambientais do LLC.4 a transições LLC explícitas,
exigindo repetição, controle, ordem temporal e direção consistente.
Não coleta automaticamente, não executa ações, não treina e não autoriza.
"""
from __future__ import annotations

import copy
import math
from typing import Any

from nixal_evidencia_ambiental_llc import EvidenciaAmbientalLLC


class EvidenciaLongitudinalLLC:
    FONTE = "llc_evidencia_longitudinal"
    VERSAO = "LLC.5.0.0"
    DESENHO = "llc_transicao_ambiental_longitudinal"
    MIN_REPETICOES = 3

    INVARIANTES = {
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "stable_modificada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
        "execucao_local": False,
        "treinamento_automatico": False,
        "implantacao_automatica": False,
    }

    @staticmethod
    def _texto(valor: Any) -> str | None:
        if not isinstance(valor, str):
            return None
        valor = valor.strip()
        return valor or None

    @staticmethod
    def _numero(valor: Any) -> float | None:
        if isinstance(valor, bool):
            return None
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
        return numero if math.isfinite(numero) else None

    @classmethod
    def _validar_obs(cls, obs: Any, nome: str, metrica: dict[str, Any]) -> list[str]:
        if not isinstance(obs, dict):
            return [f"{nome}_invalida"]
        erros = []
        if obs.get("evidencia_ambiental_observacional") is not True:
            erros.append(f"{nome}_sem_evidencia_ambiental")
        if not cls._texto(obs.get("snapshot_id")):
            erros.append(f"{nome}_sem_snapshot_id")
        if not cls._texto(obs.get("timestamp")):
            erros.append(f"{nome}_sem_timestamp")
        for chave in ("nome", "caminho", "unidade", "fonte", "direcao_melhor"):
            if obs.get(chave) != metrica.get(chave):
                erros.append(f"{nome}_{chave}_divergente")
        if cls._numero(obs.get("valor")) is None:
            erros.append(f"{nome}_valor_invalido")
        if obs.get("causalidade_ambiental_comprovada") is True:
            erros.append(f"{nome}_causalidade_preexistente")
        return erros

    @classmethod
    def _avaliar_transicao(
        cls,
        transicao: dict[str, Any],
        metrica: dict[str, Any],
        acao_esperada: str,
    ) -> tuple[dict[str, Any], list[str]]:
        erros = []
        tid = cls._texto(transicao.get("transicao_id"))
        cid = cls._texto(transicao.get("ciclo_id"))
        acao = cls._texto(transicao.get("acao"))
        decisao = transicao.get("decisao")
        acao_resultado = transicao.get("acao_resultado")
        resultado_observado = transicao.get("resultado_observado")

        if not tid:
            erros.append("transicao_id_invalido")
        if not cid:
            erros.append("ciclo_id_invalido")
        if acao != acao_esperada:
            erros.append("acao_diverge_da_acao_esperada")
        if not isinstance(decisao, dict):
            erros.append("decisao_invalida")
        if not isinstance(acao_resultado, dict):
            erros.append("acao_resultado_invalido")
        if not isinstance(resultado_observado, dict):
            erros.append("resultado_observado_invalido")

        influencia = bool(
            isinstance(decisao, dict)
            and isinstance(decisao.get("llc"), dict)
            and decisao["llc"].get("influencia_decisoria_comprovada") is True
        )
        if not influencia:
            erros.append("influencia_decisoria_nao_comprovada")
        if isinstance(decisao, dict) and decisao.get("acao") != acao:
            erros.append("acao_diverge_da_decisao")
        if isinstance(acao_resultado, dict):
            if acao_resultado.get("acao") != acao:
                erros.append("acao_resultado_diverge_da_transicao")
            if acao_resultado.get("sucesso") is not True:
                erros.append("acao_nao_sucesso")
        if isinstance(resultado_observado, dict) and resultado_observado.get("sucesso") is not True:
            erros.append("resultado_nao_sucesso")

        nomes = ("intervencao_antes", "intervencao_depois", "controle_antes", "controle_depois")
        obs = {nome: transicao.get(nome) for nome in nomes}
        for nome in nomes:
            erros.extend(cls._validar_obs(obs[nome], nome, metrica))

        efeito = None
        melhoria = False
        if not erros:
            if not (
                obs["intervencao_antes"]["timestamp"] < obs["intervencao_depois"]["timestamp"]
                and obs["controle_antes"]["timestamp"] < obs["controle_depois"]["timestamp"]
            ):
                erros.append("ordem_temporal_invalida")

        if not erros:
            di = float(obs["intervencao_depois"]["valor"]) - float(obs["intervencao_antes"]["valor"])
            dc = float(obs["controle_depois"]["valor"]) - float(obs["controle_antes"]["valor"])
            efeito = di - dc
            melhoria = efeito > 0 if metrica["direcao_melhor"] == "maior" else efeito < 0

        return {
            "transicao_id": tid,
            "ciclo_id": cid,
            "acao": acao,
            "influencia_decisoria_comprovada": influencia,
            "snapshot_ids": {
                nome: obs[nome].get("snapshot_id") if isinstance(obs[nome], dict) else None
                for nome in nomes
            },
            "efeito_contrafactual": efeito,
            "melhoria": melhoria,
            "erros": erros,
        }, erros

    @classmethod
    def avaliar(
        cls,
        *,
        metrica: dict[str, Any],
        transicoes: list[dict[str, Any]],
        acao_esperada: str,
    ) -> dict[str, Any]:
        base = {
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "desenho_experimental": cls.DESENHO,
        }
        if not isinstance(metrica, dict):
            return {"sucesso": False, "estado": "llc5_metrica_invalida",
                    "causalidade_ambiental_comprovada": False, **base, **copy.deepcopy(cls.INVARIANTES)}
        if metrica.get("caminho") not in EvidenciaAmbientalLLC.METRICAS_NUMERICAS:
            return {"sucesso": False, "estado": "llc5_metrica_nao_declarada",
                    "causalidade_ambiental_comprovada": False, **base, **copy.deepcopy(cls.INVARIANTES)}
        if (
            not cls._texto(metrica.get("nome"))
            or not cls._texto(metrica.get("unidade"))
            or not cls._texto(metrica.get("fonte"))
            or metrica.get("direcao_melhor") not in {"maior", "menor"}
            or not cls._texto(acao_esperada)
        ):
            return {"sucesso": False, "estado": "llc5_parametros_invalidos",
                    "causalidade_ambiental_comprovada": False, **base, **copy.deepcopy(cls.INVARIANTES)}
        if not isinstance(transicoes, list):
            return {"sucesso": False, "estado": "llc5_transicoes_invalidas",
                    "causalidade_ambiental_comprovada": False, **base, **copy.deepcopy(cls.INVARIANTES)}

        erros = []
        vistas = []
        ids_t, ids_c = set(), set()
        if len(transicoes) < cls.MIN_REPETICOES:
            erros.append("repeticoes_insuficientes")

        for item in transicoes:
            if not isinstance(item, dict):
                erros.append("transicao_invalida")
                continue
            vista, erros_item = cls._avaliar_transicao(item, metrica, acao_esperada)
            vistas.append(vista)
            erros.extend(erros_item)
            tid, cid = vista["transicao_id"], vista["ciclo_id"]
            if tid in ids_t:
                erros.append("transicao_id_duplicado")
            if cid in ids_c:
                erros.append("ciclo_id_duplicado")
            if tid:
                ids_t.add(tid)
            if cid:
                ids_c.add(cid)

        if len(ids_c) < cls.MIN_REPETICOES:
            erros.append("ciclos_longitudinais_insuficientes")

        efeitos = [v["efeito_contrafactual"] for v in vistas if v["efeito_contrafactual"] is not None]
        melhorias = [v["melhoria"] for v in vistas]
        consistente = bool(vistas) and len(efeitos) == len(vistas) and all(melhorias)
        evidencia = bool(
            not erros
            and len(vistas) >= cls.MIN_REPETICOES
            and len(efeitos) == len(vistas)
            and consistente
        )
        return {
            "sucesso": True,
            "estado": "evidencia_causal_longitudinal" if evidencia else "evidencia_longitudinal_inconclusiva",
            **base,
            "metrica": copy.deepcopy(metrica),
            "acao_esperada": acao_esperada,
            "repeticoes": len(vistas),
            "ciclos_distintos": len(ids_c),
            "transicoes_distintas": len(ids_t),
            "contrastes": vistas,
            "efeito_medio_contrafactual": sum(efeitos) / len(efeitos) if efeitos else None,
            "efeito_minimo": min(efeitos) if efeitos else None,
            "efeito_maximo": max(efeitos) if efeitos else None,
            "estabilidade_direcional": consistente,
            "erros": erros,
            "evidencia_causal_longitudinal": evidencia,
            "causalidade_ambiental_comprovada": evidencia,
            **copy.deepcopy(cls.INVARIANTES),
        }

    @classmethod
    def contexto(cls) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "llc5_disponivel",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "desenho_experimental": cls.DESENHO,
            "min_repeticoes": cls.MIN_REPETICOES,
            "usa_metricas_llc4": True,
            "coleta_automatica": False,
            "causalidade_ambiental": False,
            "invariantes": {
                **copy.deepcopy(cls.INVARIANTES),
                "causalidade_ambiental_comprovada": False,
            },
        }


__all__ = ["EvidenciaLongitudinalLLC"]
