#!/usr/bin/env python3
"""Teste determinístico da auto-avaliação AE3."""

from __future__ import annotations

from nixal_auto_avaliacao_ae3 import AutoAvaliacaoAE3


def resultado(aprovado: bool, aprendizado_estado: str = "aprendizado_persistido"):
    return {
        "sucesso": True,
        "estado": "experimento_processado",
        "solicitacao_id": "solicitacao-teste",
        "valor": {
            "sucesso": True,
            "estado": "solicitacao_evolucao_remota_executada",
            "valor": {
                "sucesso": True,
                "estado": "proposta_criada" if aprovado else "evolucao_rejeitada",
                "solicitacao_id": "solicitacao-teste",
                "comparacao": {
                    "metrica": "tempo_execucao_ms",
                    "baseline": 100.0,
                    "experimental": 80.0 if aprovado else 120.0,
                    "melhoria_absoluta": 20.0 if aprovado else -20.0,
                    "melhoria_relativa": 0.2 if aprovado else -0.2,
                    "aprovado": aprovado,
                },
                "aprendizado": {
                    "sucesso": True,
                    "estado": aprendizado_estado,
                },
                "candidato": {"estado": "candidato"} if aprovado else None,
                "proposta": {"estado": "aguardando_autorizacao"} if aprovado else None,
            },
        },
    }


def main() -> int:
    avaliador = AutoAvaliacaoAE3()

    aprovado = avaliador.avaliar(resultado(True))
    assert aprovado["estado"] == "melhoria_comprovada"
    assert aprovado["aprovado"] is True
    assert aprovado["aprendizado_disponivel"] is True
    assert aprovado["candidato_presente"] is True
    assert aprovado["proposta_presente"] is True
    assert aprovado["autorizacao_explicita"] is False
    assert aprovado["stable_modificada"] is False

    rejeitado = avaliador.avaliar(resultado(False))
    assert rejeitado["estado"] == "evolucao_rejeitada"
    assert rejeitado["aprovado"] is False
    assert rejeitado["aprendizado_disponivel"] is True
    assert rejeitado["candidato_presente"] is False

    inconclusivo = avaliador.avaliar(resultado(True, "falhou"))
    assert inconclusivo["estado"] == "resultado_inconclusivo"
    assert inconclusivo["aprovado"] is True
    assert inconclusivo["aprendizado_disponivel"] is False

    sem_comparacao = avaliador.avaliar({
        "sucesso": True,
        "estado": "experimento_processado",
        "valor": {"sucesso": True},
    })
    assert sem_comparacao["estado"] == "resultado_inconclusivo"

    contexto = avaliador.contexto()
    assert contexto["comparacao_automatica"] is True
    assert contexto["aprendizado_reutilizado"] is True
    assert contexto["autorizacao_explicita"] is False
    assert contexto["stable_modificada"] is False

    print("=" * 64)
    print("TESTE — AUTO-AVALIAÇÃO AE3")
    print("=" * 64)
    print("DESEMPACOTAMENTO_RESULTADO=OK")
    print("COMPARACAO_MELHORIA=OK")
    print("REJEICAO_BASELINE=OK")
    print("INCONCLUSIVO=OK")
    print("APRENDIZADO_REUTILIZADO=OK")
    print("SEM_AUTORIZACAO=OK")
    print("SEM_ALTERACAO_STABLE=OK")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
