#!/usr/bin/env python3
"""Teste do encaixe AE3 no ciclo residente."""

from __future__ import annotations

from nixal_ciclo_residente import CicloResidenteNixOS


class RuntimeFalso:
    def executar_ciclo(self):
        return {
            "sucesso": True,
            "estado": "ciclo_concluido",
            "ciclo_id": "ciclo-ae3",
            "valor": {},
        }


class AE2Falso:
    FONTE = "ae2_falso"

    def __init__(self) -> None:
        self.habilitada = True

    def processar_pendentes(self):
        return {
            "sucesso": True,
            "estado": "experimento_processado",
            "processada": True,
            "solicitacao_id": "solicitacao-ae3",
            "valor": {
                "sucesso": True,
                "estado": "solicitacao_evolucao_remota_executada",
                "valor": {
                    "sucesso": True,
                    "estado": "proposta_criada",
                    "solicitacao_id": "solicitacao-ae3",
                    "comparacao": {
                        "metrica": "tempo_execucao_ms",
                        "baseline": 100.0,
                        "experimental": 80.0,
                        "melhoria_absoluta": 20.0,
                        "melhoria_relativa": 0.2,
                        "aprovado": True,
                    },
                    "aprendizado": {
                        "sucesso": True,
                        "estado": "aprendizado_persistido",
                    },
                    "candidato": {"estado": "candidato"},
                    "proposta": {"estado": "aguardando_autorizacao"},
                },
            },
            "retry_automatico": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }


class PersistenciaFalsa:
    def registrar(self, *, ciclo, estado):
        return None


def main() -> int:
    residente = CicloResidenteNixOS(
        RuntimeFalso(),
        PersistenciaFalsa(),
        None,
        AE2Falso(),
        None if False else __import__(
            "nixal_auto_avaliacao_ae3",
            fromlist=["AutoAvaliacaoAE3"],
        ).AutoAvaliacaoAE3(),
        intervalo_segundos=0,
    )

    resultados = residente.executar(max_ciclos=1)
    avaliacao = resultados[0]["auto_avaliacao_ae3"]

    assert avaliacao["estado"] == "melhoria_comprovada"
    assert avaliacao["aprovado"] is True
    assert avaliacao["aprendizado_disponivel"] is True
    assert avaliacao["melhoria_absoluta"] == 20.0
    assert avaliacao["autorizacao_explicita"] is False
    assert avaliacao["stable_modificada"] is False

    print("=" * 64)
    print("TESTE — AE3 NO CICLO RESIDENTE")
    print("=" * 64)
    print("AE2_PROCESSADO=OK")
    print("AE3_AVALIACAO=OK")
    print("MELHORIA_COMPROVADA=OK")
    print("APRENDIZADO_REUTILIZADO=OK")
    print("SEM_AUTORIZACAO=OK")
    print("SEM_ALTERACAO_STABLE=OK")
    print("PASSOU: True")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
