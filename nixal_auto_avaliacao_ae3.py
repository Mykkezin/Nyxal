#!/usr/bin/env python3
"""
NYXAL — AUTO-AVALIAÇÃO AE3

Camada de interpretação automática do resultado produzido pela AE2/N9.

Responsabilidade:
- validar que a comparação experimental existe;
- validar que o aprendizado persistente foi registrado;
- classificar o resultado como melhoria_comprovada, evolucao_rejeitada
  ou resultado_inconclusivo;
- devolver um resumo auditável para o ciclo residente.

Não:
- executa experimentos;
- cria candidatos;
- cria propostas;
- autoriza integração;
- modifica stable;
- promove conhecimento permanente;
- cria uma segunda memória de aprendizado.
"""

from __future__ import annotations

import copy
import math
from typing import Any


class AutoAvaliacaoAE3:
    """Interpreta automaticamente um resultado de experimento já processado."""

    FONTE = "auto_avaliacao_ae3"
    VERSAO = "AE3.0.0"

    @staticmethod
    def _numero(valor: Any) -> float | None:
        if isinstance(valor, bool):
            return None
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
        return numero if math.isfinite(numero) else None

    @staticmethod
    def _desembrulhar(resultado: dict[str, Any]) -> dict[str, Any]:
        atual = resultado
        for _ in range(6):
            valor = atual.get("valor")
            if not isinstance(valor, dict):
                break
            atual = valor
        return atual

    @classmethod
    def avaliar(cls, resultado_ae2: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(resultado_ae2, dict):
            return {
                "sucesso": False,
                "estado": "resultado_ae2_invalido",
                "origem": cls.FONTE,
                "motivo": "AE2 não retornou um objeto válido.",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }

        remoto = cls._desembrulhar(resultado_ae2)
        if not isinstance(remoto, dict):
            remoto = {}

        comparacao = remoto.get("comparacao")
        aprendizado = remoto.get("aprendizado")
        solicitacao_id = (
            resultado_ae2.get("solicitacao_id")
            or remoto.get("solicitacao_id")
        )

        flags = {
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }

        if not isinstance(comparacao, dict):
            return {
                "sucesso": True,
                "estado": "resultado_inconclusivo",
                "origem": cls.FONTE,
                "versao": cls.VERSAO,
                "solicitacao_id": solicitacao_id,
                "motivo": "Resultado sem comparação formal disponível.",
                "comparacao_disponivel": False,
                "aprendizado_disponivel": isinstance(aprendizado, dict),
                **flags,
            }

        aprovado = comparacao.get("aprovado")
        if not isinstance(aprovado, bool):
            return {
                "sucesso": True,
                "estado": "resultado_inconclusivo",
                "origem": cls.FONTE,
                "versao": cls.VERSAO,
                "solicitacao_id": solicitacao_id,
                "motivo": "Comparação sem decisão booleana válida.",
                "comparacao_disponivel": True,
                "aprendizado_disponivel": isinstance(aprendizado, dict),
                **flags,
            }

        aprendizado_ok = (
            isinstance(aprendizado, dict)
            and aprendizado.get("sucesso") is True
            and aprendizado.get("estado") in {"aprendizado_persistido", "ja_existente"}
        )

        melhoria = comparacao.get("melhoria_absoluta")
        melhoria_numero = cls._numero(melhoria)

        if aprovado is True and aprendizado_ok:
            estado = "melhoria_comprovada"
            motivo = (
                "O resultado experimental foi melhor que o baseline "
                "segundo a métrica declarada e o aprendizado foi registrado."
            )
        elif aprovado is False and aprendizado_ok:
            estado = "evolucao_rejeitada"
            motivo = (
                "O resultado experimental não superou o baseline; "
                "o aprendizado da avaliação foi registrado."
            )
        else:
            estado = "resultado_inconclusivo"
            motivo = (
                "Existe comparação experimental, mas o aprendizado persistente "
                "não foi confirmado pela resposta recebida."
            )

        return {
            "sucesso": True,
            "estado": estado,
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "solicitacao_id": solicitacao_id,
            "comparacao_disponivel": True,
            "aprendizado_disponivel": aprendizado_ok,
            "aprovado": aprovado,
            "metrica": comparacao.get("metrica"),
            "baseline": comparacao.get("baseline"),
            "experimental": comparacao.get("experimental"),
            "melhoria_absoluta": melhoria_numero,
            "melhoria_relativa": comparacao.get("melhoria_relativa"),
            "avaliacao": (
                "sucesso" if aprovado else "falha"
            ),
            "motivo": motivo,
            "candidato_presente": isinstance(remoto.get("candidato"), dict),
            "proposta_presente": isinstance(remoto.get("proposta"), dict),
            **flags,
        }

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "ae3_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "comparacao_automatica": True,
            "aprendizado_reutilizado": True,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = ["AutoAvaliacaoAE3"]
