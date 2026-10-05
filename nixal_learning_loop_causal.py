#!/usr/bin/env python3
"""NYXAL — Learning Loop Causal (LLC).

LLC.1 prova influencia decisoria pela comparacao entre uma escolha
contrafactual sem aprendizado e a escolha usando aprendizado.

LLC.2 fecha o feedback operacional do ciclo:
decisao -> acao -> resultado -> ganho/perda operacional -> novo aprendizado.

A metrica de ganho/perda e operacional. Ela mede somente o sucesso
observado da acao e do resultado, sem afirmar causalidade ambiental.
Esta camada nao treina, implanta, autoriza integracao ou cria memoria nova.
"""

from __future__ import annotations

import copy
from typing import Any


class LearningLoopCausalNixal:
    """Politica deterministica para a primeira etapa do LLC."""

    FONTE = "learning_loop_causal_nixal"
    VERSAO = "LLC.2.0.0"
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
    def avaliar_resultado(
        cls,
        *,
        decisao: dict[str, Any],
        acao_resultado: dict[str, Any],
        resultado_observado: dict[str, Any],
    ) -> dict[str, Any]:
        """Calcula apenas ganho/perda operacional observada."""
        if not isinstance(decisao, dict):
            return {
                "sucesso": False,
                "estado": "llc2_decisao_invalida",
                "motivo": "A decisao precisa ser um objeto.",
                **cls.INVARIANTES,
            }
        if not isinstance(acao_resultado, dict):
            return {
                "sucesso": False,
                "estado": "llc2_acao_invalida",
                "motivo": "O resultado da acao precisa ser um objeto.",
                **cls.INVARIANTES,
            }
        if not isinstance(resultado_observado, dict):
            return {
                "sucesso": False,
                "estado": "llc2_resultado_invalido",
                "motivo": "O resultado observado precisa ser um objeto.",
                **cls.INVARIANTES,
            }

        acao = decisao.get("acao")
        acao_sucesso = bool(acao_resultado.get("sucesso"))
        resultado_sucesso = bool(resultado_observado.get("sucesso"))

        if not acao_sucesso or not resultado_sucesso:
            ganho_perda = -1.0
            classificacao = "perda_operacional"
        elif acao == "observar_sem_atuar":
            ganho_perda = 0.0
            classificacao = "neutro_operacional"
        else:
            ganho_perda = 1.0
            classificacao = "ganho_operacional"

        return {
            "sucesso": True,
            "estado": "feedback_operacional_calculado",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "ganho_perda_operacional": ganho_perda,
            "classificacao": classificacao,
            "base": "sucesso_da_acao_e_do_resultado_observado",
            "acao": acao,
            "acao_sucesso": acao_sucesso,
            "resultado_sucesso": resultado_sucesso,
            "influencia_decisoria_comprovada": bool(
                (decisao.get("llc") or {}).get(
                    "influencia_decisoria_comprovada"
                ) is True
            ),
            "causalidade_ambiental_comprovada": False,
            **cls.INVARIANTES,
        }

    @classmethod
    def fechar_transicao(
        cls,
        *,
        aprendizado_anterior: dict[str, Any] | None,
        decisao: dict[str, Any],
        acao_resultado: dict[str, Any],
        resultado_observado: dict[str, Any],
        avaliacao: dict[str, Any],
        aprendizado_novo: dict[str, Any],
    ) -> dict[str, Any]:
        """Fecha o encadeamento decisao -> resultado -> aprendizado."""
        feedback = avaliacao.get("llc2") if isinstance(avaliacao, dict) else None
        if not isinstance(feedback, dict):
            feedback = {}

        novo_valor = (
            aprendizado_novo.get("valor")
            if isinstance(aprendizado_novo, dict)
            else None
        )
        novo_id = novo_valor.get("id") if isinstance(novo_valor, dict) else None
        anterior_id = (
            aprendizado_anterior.get("aprendizado_id")
            if isinstance(aprendizado_anterior, dict)
            else None
        )

        return {
            "versao": cls.VERSAO,
            "estado": "transicao_llc2_fechada",
            "aprendizado_anterior_id": anterior_id,
            "decisao": {
                "acao": decisao.get("acao"),
                "estrategia": decisao.get("estrategia"),
                "influencia_decisoria_comprovada": bool(
                    (decisao.get("llc") or {}).get(
                        "influencia_decisoria_comprovada"
                    ) is True
                ),
                "mudou_escolha": bool(
                    (decisao.get("llc") or {}).get("mudou_escolha") is True
                ),
            },
            "acao": copy.deepcopy(acao_resultado),
            "resultado": copy.deepcopy(resultado_observado),
            "feedback_operacional": copy.deepcopy(feedback),
            "avaliacao": copy.deepcopy(avaliacao),
            "aprendizado_novo_id": novo_id,
            "ciclo_fechado": True,
            "causalidade_ambiental_comprovada": False,
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
            "feedback_operacional": True,
            "transicao_completa": True,
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
