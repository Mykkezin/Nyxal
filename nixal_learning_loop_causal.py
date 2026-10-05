#!/usr/bin/env python3
"""NYXAL — Learning Loop Causal (LLC) / primeira camada decisoria.

Objetivo:
    demonstrar, de forma deterministica e auditavel, que um sinal de
    aprendizado anterior pode mudar a escolha entre alternativas
    previamente registradas.

Esta primeira versao NAO:
- executa treinamento;
- modifica arquitetura;
- cria memoria nova;
- autoriza integracao;
- acessa shell;
- executa a acao escolhida;
- afirma causalidade sobre o ambiente.

Ela prova somente influencia decisoria no mecanismo de selecao:
    decisao_sem_aprendizado
        vs.
    decisao_com_aprendizado

Quando as duas escolhas diferirem por causa de um sinal estruturado
valido, a influencia decisoria e considerada comprovada para aquele
ciclo. A causalidade ambiental continua explicitamente nao comprovada.
"""

from __future__ import annotations

import copy
from typing import Any


class LearningLoopCausalNixal:
    """Politica deterministica para a primeira etapa do LLC."""

    FONTE = "learning_loop_causal_nixal"
    VERSAO = "LLC.1.0.0"
    POLITICA = "repetir_sucesso_evitar_falha"

    CANDIDATAS = (
        {
            "estrategia": "persistir_estado",
            "acao": "registrar_estado_corpo",
            "pontuacao_base": 1.0,
        },
        {
            "estrategia": "somente_observar",
            "acao": "observar_sem_atuar",
            "pontuacao_base": 0.0,
        },
    )

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
    def _numero(valor: Any) -> float | None:
        if isinstance(valor, bool):
            return None
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
        return numero if numero == numero and abs(numero) != float("inf") else None

    @classmethod
    def _opcao_por_acao(cls, acao: str) -> dict[str, Any] | None:
        for opcao in cls.CANDIDATAS:
            if opcao["acao"] == acao:
                return copy.deepcopy(opcao)
        return None

    @classmethod
    def _sinal_aprendizado(
        cls,
        aprendizado_anterior: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(aprendizado_anterior, dict):
            return None

        if aprendizado_anterior.get("disponivel") is not True:
            return None

        experiencia = aprendizado_anterior.get("experiencia_anterior")
        avaliacao = aprendizado_anterior.get("avaliacao_anterior")

        if not isinstance(experiencia, dict) or not isinstance(avaliacao, dict):
            return None

        acao_anterior = experiencia.get("acao")
        avaliacao_anterior = avaliacao.get("avaliacao")

        if not isinstance(acao_anterior, str):
            return None
        if avaliacao_anterior not in {"sucesso", "falha"}:
            return None
        if cls._opcao_por_acao(acao_anterior) is None:
            return None

        return {
            "aprendizado_id": aprendizado_anterior.get("aprendizado_id"),
            "ciclo_origem": aprendizado_anterior.get("ciclo_origem"),
            "acao_anterior": acao_anterior,
            "avaliacao_anterior": avaliacao_anterior,
            "aplicado_no_ciclo_atual": bool(
                aprendizado_anterior.get("aplicado_no_ciclo_atual")
            ),
        }

    @classmethod
    def _pontuar_sem_aprendizado(cls) -> list[dict[str, Any]]:
        return [
            {
                **copy.deepcopy(opcao),
                "pontuacao": float(opcao["pontuacao_base"]),
            }
            for opcao in cls.CANDIDATAS
        ]

    @classmethod
    def _pontuar_com_aprendizado(
        cls,
        sinal: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        pontuacoes = cls._pontuar_sem_aprendizado()

        if sinal is None:
            return pontuacoes

        alvo = sinal["acao_anterior"]
        avaliacao = sinal["avaliacao_anterior"]

        for opcao in pontuacoes:
            if avaliacao == "sucesso":
                if opcao["acao"] == alvo:
                    opcao["pontuacao"] += 1.0
            elif avaliacao == "falha":
                if opcao["acao"] == alvo:
                    opcao["pontuacao"] -= 2.0
                else:
                    opcao["pontuacao"] += 1.0

        return pontuacoes

    @staticmethod
    def _selecionar(pontuacoes: list[dict[str, Any]]) -> dict[str, Any]:
        ordenadas = sorted(
            pontuacoes,
            key=lambda item: (
                -float(item.get("pontuacao", 0.0)),
                str(item.get("acao", "")),
            ),
        )
        return copy.deepcopy(ordenadas[0])

    @classmethod
    def selecionar(
        cls,
        *,
        estado_corpo: dict[str, Any],
        prioridades: dict[str, Any],
        aprendizado_anterior: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(estado_corpo, dict):
            return {
                "sucesso": False,
                "estado": "llc_estado_invalido",
                "origem": cls.FONTE,
                "versao": cls.VERSAO,
                "motivo": "O estado corporal precisa ser um objeto.",
                **cls.INVARIANTES,
            }

        if not isinstance(prioridades, dict):
            return {
                "sucesso": False,
                "estado": "llc_prioridades_invalidas",
                "origem": cls.FONTE,
                "versao": cls.VERSAO,
                "motivo": "As prioridades precisam ser um objeto.",
                **cls.INVARIANTES,
            }

        sinal = cls._sinal_aprendizado(aprendizado_anterior)
        sem_aprendizado = cls._selecionar(cls._pontuar_sem_aprendizado())
        com_aprendizado = cls._selecionar(
            cls._pontuar_com_aprendizado(sinal)
        )

        mudou = (
            sem_aprendizado.get("acao") != com_aprendizado.get("acao")
        )
        influencia_comprovada = bool(
            sinal is not None
            and aprendizado_anterior
            and aprendizado_anterior.get("aplicado_no_ciclo_atual") is True
            and mudou
        )

        motivo = (
            "O sinal de aprendizado alterou a escolha entre as alternativas."
            if influencia_comprovada
            else (
                "O aprendizado foi considerado, mas nao alterou a escolha."
                if sinal is not None
                else "Nao existe sinal de aprendizado estruturado valido."
            )
        )

        return {
            "sucesso": True,
            "estado": "decisao_llc",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "tipo": "acao_controlada",
            "acao": com_aprendizado["acao"],
            "estrategia": com_aprendizado["estrategia"],
            "motivo": motivo,
            "necessidade_prioritaria": copy.deepcopy(
                prioridades.get("selecionada")
            ),
            "aprendizado_considerado": copy.deepcopy(
                aprendizado_anterior
            ),
            "llc": {
                "politica": cls.POLITICA,
                "sinal_valido": sinal is not None,
                "decisao_sem_aprendizado": sem_aprendizado,
                "decisao_com_aprendizado": com_aprendizado,
                "influencia_decisoria_comprovada": influencia_comprovada,
                "mudou_escolha": mudou,
                "causalidade_ambiental_comprovada": False,
            },
            **cls.INVARIANTES,
        }

    @classmethod
    def contexto(cls) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "llc_disponivel",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "politica": cls.POLITICA,
            "alternativas": [
                copy.deepcopy(opcao) for opcao in cls.CANDIDATAS
            ],
            "execucao_de_acao": False,
            "treinamento_automatico": False,
            "implantacao_automatica": False,
            "influencia_decisoria": True,
            "causalidade_ambiental": False,
            "invariantes": copy.deepcopy(cls.INVARIANTES),
        }


__all__ = ["LearningLoopCausalNixal"]
