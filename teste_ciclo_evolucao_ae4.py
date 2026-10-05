#!/usr/bin/env python3
"""Testes do AE4 — ciclo residente de evolução."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_auto_avaliacao_ae3 import AutoAvaliacaoAE3
from nixal_ciclo_evolucao_ae4 import CicloEvolucaoResidenteAE4


class FakeAE1:
    FONTE = "fake_ae1"

    def avaliar_ciclo(self, ciclo: dict) -> dict:
        return {
            "sucesso": True,
            "estado": "oportunidade_criada",
            "valor": {
                "oportunidade_id": "oportunidade-teste",
                "ciclo_origem": ciclo["ciclo_id"],
                "hipotese": "A proposta deve melhorar a métrica.",
            },
            "oportunidade_criada": True,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


class FakeAE2:
    FONTE = "fake_ae2"

    def processar_pendentes(self) -> dict:
        return {
            "sucesso": True,
            "estado": "experimento_processado",
            "processada": True,
            "solicitacao_id": "solicitacao-teste",
            "valor": {
                "comparacao": {
                    "aprovado": True,
                    "metrica": "latencia",
                    "baseline": 100.0,
                    "experimental": 80.0,
                    "melhoria_absoluta": 20.0,
                },
                "aprendizado": {
                    "sucesso": True,
                    "estado": "aprendizado_persistido",
                },
            },
            "retry_automatico": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


class FakeAE2SemExperimento:
    FONTE = "fake_ae2_sem_experimento"

    def processar_pendentes(self) -> dict:
        return {
            "sucesso": True,
            "estado": "sem_solicitacao_pendente",
            "processada": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


def _ciclo() -> dict:
    return {
        "sucesso": True,
        "estado": "ciclo_concluido",
        "ciclo_id": "ciclo-ae4-teste",
        "valor": {},
    }


def testar_pipeline_completo() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae4 = CicloEvolucaoResidenteAE4(
            FakeAE1(),
            FakeAE2(),
            AutoAvaliacaoAE3(),
            repositorio=Path(temporario),
        )
        resultado = ae4.processar_ciclo(_ciclo())

        assert resultado["sucesso"] is True
        assert resultado["estado"] == "ae4_melhoria_comprovada"
        assert resultado["oportunidade_id"] == "oportunidade-teste"
        assert resultado["solicitacao_id"] == "solicitacao-teste"
        assert resultado["vinculo_observacional_confirmado"] is False
        for chave in (
            "autorizacao_explicita",
            "integracao_executada",
            "stable_modificada",
            "arquitetura_modificada",
            "conhecimento_permanente",
        ):
            assert resultado[chave] is False

        auditoria = Path(resultado["auditoria_arquivo"])
        assert auditoria.is_file()
        texto = auditoria.read_text(encoding="utf-8")
        assert '"ordem": [' in texto
        assert '"AE1"' in texto
        assert '"AE2"' in texto
        assert '"AE3"' in texto


def testar_sem_experimento() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae4 = CicloEvolucaoResidenteAE4(
            FakeAE1(),
            FakeAE2SemExperimento(),
            AutoAvaliacaoAE3(),
            repositorio=Path(temporario),
        )
        resultado = ae4.processar_ciclo(_ciclo())

        assert resultado["sucesso"] is True
        assert resultado["estado"] == "ae4_sem_experimento_para_avaliar"
        assert resultado["ae3"]["estado"] == "sem_experimento_para_avaliar"


def testar_idempotencia_por_ciclo() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae4 = CicloEvolucaoResidenteAE4(
            FakeAE1(),
            FakeAE2(),
            AutoAvaliacaoAE3(),
            repositorio=Path(temporario),
        )
        primeira = ae4.processar_ciclo(_ciclo())
        segunda = ae4.processar_ciclo(_ciclo())

        assert primeira["auditoria_id"] == segunda["auditoria_id"]
        arquivos = list(
            (Path(temporario).parent / "Nyxal-evolution-ae4").glob("ae4-ciclo-*.json")
        )
        assert len(arquivos) == 1


def testar_fonte_sem_execucao_externa() -> None:
    origem = Path("nixal_ciclo_evolucao_ae4.py").read_text(encoding="utf-8")
    assert "subprocess" not in origem
    assert "os.system" not in origem
    assert "Popen" not in origem
    assert "git merge" not in origem
    assert "stable/main" in origem


def main() -> None:
    testar_pipeline_completo()
    testar_sem_experimento()
    testar_idempotencia_por_ciclo()
    testar_fonte_sem_execucao_externa()
    print("TESTE_AE4_CICLO_EVOLUCAO_OK")


if __name__ == "__main__":
    main()
