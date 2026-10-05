#!/usr/bin/env python3
"""Testes da descoberta contínua governada AE5."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_descoberta_continua_ae5 import DescobertaContinuaGovernadaAE5


def _resultado(ciclo_id: str, sucesso: bool = True, oportunidade_id: str | None = None) -> dict:
    return {
        "sucesso": sucesso,
        "estado": "ae4_ciclo_observado",
        "ciclo_id": ciclo_id,
        "ae1": {
            "sucesso": True,
            "estado": "oportunidade_criada",
            "valor": {
                "oportunidade_id": oportunidade_id or f"op-{ciclo_id}",
                "limitacao": "latência operacional repetida",
                "hipotese": "reduzir o custo da etapa crítica",
                "evidencias": {"ciclo_sucesso": sucesso},
            },
        },
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "stable_modificada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
    }


def testar_maturidade_progressiva() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = DescobertaContinuaGovernadaAE5(repositorio=Path(temporario))

        primeiro = ae5.processar(_resultado("ciclo-1"))
        segundo = ae5.processar(_resultado("ciclo-2"))
        terceiro = ae5.processar(_resultado("ciclo-3"))

        assert primeiro["estado"] == "sinal_em_observacao"
        assert segundo["observacoes"] == 2
        assert segundo["madura_para_formalizacao"] is False
        assert terceiro["estado"] == "oportunidade_madura_para_formalizacao"
        assert terceiro["madura_para_formalizacao"] is True
        assert terceiro["observacoes"] == 3
        assert terceiro["observacoes_sucesso"] == 3


def testar_sucessos_minimos() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = DescobertaContinuaGovernadaAE5(repositorio=Path(temporario))

        ae5.processar(_resultado("ciclo-1", sucesso=False))
        ae5.processar(_resultado("ciclo-2", sucesso=False))
        resultado = ae5.processar(_resultado("ciclo-3", sucesso=True))

        assert resultado["observacoes"] == 3
        assert resultado["observacoes_sucesso"] == 1
        assert resultado["madura_para_formalizacao"] is False


def testar_deduplicacao_por_ciclo() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = DescobertaContinuaGovernadaAE5(repositorio=Path(temporario))

        primeiro = ae5.processar(_resultado("ciclo-1"))
        repetido = ae5.processar(_resultado("ciclo-1", oportunidade_id="outro"))

        assert primeiro["linha_id"] == repetido["linha_id"]
        assert repetido["observacoes"] == 1

        arquivos = list(
            (Path(temporario).parent / "Nyxal-evolution-discovery").glob("linha-*.json")
        )
        assert len(arquivos) == 1


def testar_sem_sinal() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = DescobertaContinuaGovernadaAE5(repositorio=Path(temporario))

        resultado = ae5.processar(
            {
                "sucesso": True,
                "estado": "ae4_sem_experimento_para_avaliar",
                "ciclo_id": "ciclo-vazio",
            }
        )

        assert resultado["estado"] == "sem_sinal_para_acumular"
        assert resultado["madura_para_formalizacao"] is False


def testar_invariantes_e_fonte() -> None:
    origem = Path("nixal_descoberta_continua_ae5.py").read_text(encoding="utf-8")

    assert "subprocess" not in origem
    assert "os.system" not in origem
    assert "Popen" not in origem
    assert "git merge" not in origem

    ae5 = DescobertaContinuaGovernadaAE5(repositorio=Path(".").resolve())
    resultado = ae5.processar(
        {
            "sucesso": True,
            "estado": "ae4_sem_experimento_para_avaliar",
            "ciclo_id": "ciclo-invariante",
        }
    )

    for chave in (
        "autorizacao_explicita",
        "integracao_executada",
        "stable_modificada",
        "arquitetura_modificada",
        "conhecimento_permanente",
    ):
        assert resultado[chave] is False


def main() -> None:
    testar_maturidade_progressiva()
    testar_sucessos_minimos()
    testar_deduplicacao_por_ciclo()
    testar_sem_sinal()
    testar_invariantes_e_fonte()
    print("TESTE_AE5_DESCOBERTA_CONTINUA_OK")


if __name__ == "__main__":
    main()
