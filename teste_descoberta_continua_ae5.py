#!/usr/bin/env python3
"""Testes da descoberta contínua governada AE5."""

from __future__ import annotations

import tempfile
from pathlib import Path

from nixal_descoberta_continua_ae5 import DescobertaContinuaGovernadaAE5


def _nova_ae5(temporario: str) -> DescobertaContinuaGovernadaAE5:
    return DescobertaContinuaGovernadaAE5(
        repositorio=Path(temporario) / "repo"
    )


def _resultado(
    ciclo_id: str,
    sucesso: bool = True,
    oportunidade_id: str | None = None,
) -> dict:
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
        ae5 = _nova_ae5(temporario)

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
        ae5 = _nova_ae5(temporario)

        ae5.processar(_resultado("ciclo-1", sucesso=False))
        ae5.processar(_resultado("ciclo-2", sucesso=False))
        resultado = ae5.processar(_resultado("ciclo-3", sucesso=True))

        assert resultado["observacoes"] == 3
        assert resultado["observacoes_sucesso"] == 1
        assert resultado["madura_para_formalizacao"] is False


def testar_deduplicacao_por_ciclo() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = _nova_ae5(temporario)

        primeiro = ae5.processar(_resultado("ciclo-1"))
        repetido = ae5.processar(_resultado("ciclo-1", oportunidade_id="outro"))

        assert primeiro["linha_id"] == repetido["linha_id"]
        assert repetido["observacoes"] == 1

        arquivos = list(
            (Path(temporario) / "Nyxal-evolution-discovery").glob("linha-*.json")
        )
        assert len(arquivos) == 1


def testar_sem_sinal() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = _nova_ae5(temporario)

        resultado = ae5.processar(
            {
                "sucesso": True,
                "estado": "ae4_sem_experimento_para_avaliar",
                "ciclo_id": "ciclo-vazio",
            }
        )

        assert resultado["estado"] == "sem_sinal_para_acumular"
        assert resultado["madura_para_formalizacao"] is False


def testar_janela_recente() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = _nova_ae5(temporario)
        for i in range(1, 21):
            ae5.processar(_resultado(f"ciclo-{i}", sucesso=(i >= 19)))
        resultado = ae5.processar(_resultado("ciclo-21", sucesso=False))
        assert resultado["observacoes"] == 20
        assert resultado["observacoes_sucesso"] == 2
        assert resultado["madura_para_formalizacao"] is True

        resultado = ae5.processar(_resultado("ciclo-22", sucesso=False))
        assert resultado["observacoes"] == 20
        assert resultado["observacoes_sucesso"] == 1
        assert resultado["madura_para_formalizacao"] is False


def testar_formalizacao_persistente_e_deduplicacao() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        ae5 = _nova_ae5(temporario)
        for ciclo in ("ciclo-1", "ciclo-2", "ciclo-3"):
            resultado = ae5.processar(_resultado(ciclo))
        assert resultado["formalizacao"]["estado"] == "preparada"

        repetido = ae5.processar(_resultado("ciclo-3"))
        assert repetido["deduplicada"] is True
        assert repetido["observacoes"] == 3
        registro = ae5.listar(limite=1)[0]
        assert registro["formalizacao"]["estado"] == "preparada"


def testar_reconciliacao_historica() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario)
        ae5 = DescobertaContinuaGovernadaAE5(repositorio=raiz / "repo")
        oportunidades = raiz / "Nyxal-evolution-opportunities"
        auditorias = raiz / "Nyxal-evolution-ae4"
        oportunidades.mkdir(parents=True)
        auditorias.mkdir(parents=True)

        for i in range(1, 4):
            oportunidade_id = f"oportunidade-historica-{i}"
            (oportunidades / f"{oportunidade_id}.json").write_text(
                __import__("json").dumps({
                    "oportunidade_id": oportunidade_id,
                    "limitacao": "falha repetida de descoberta",
                    "hipotese": "melhorar a identificação",
                    "evidencias": {"ciclo_sucesso": True},
                }),
                encoding="utf-8",
            )
            (auditorias / f"ae4-ciclo-historico-{i}.json").write_text(
                __import__("json").dumps({
                    "ciclo_id": f"historico-{i}",
                    "estado": "ae4_ciclo_observado",
                    "etapas": [{
                        "etapa": "AE1",
                        "sucesso": True,
                        "estado": "oportunidade_criada",
                        "oportunidade_id": oportunidade_id,
                    }],
                }),
                encoding="utf-8",
            )

        resultado = ae5.reconciliar_historico()
        assert resultado["auditorias_processadas"] == 3
        assert resultado["novos_sinais"] == 3
        assert resultado["linhas_maduras"] == 1


def testar_invariantes_e_fonte() -> None:
    origem = Path("nixal_descoberta_continua_ae5.py").read_text(
        encoding="utf-8"
    )

    assert "subprocess" not in origem
    assert "os.system" not in origem
    assert "Popen" not in origem
    assert "git merge" not in origem

    with tempfile.TemporaryDirectory() as temporario:
        ae5 = _nova_ae5(temporario)
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
    testar_janela_recente()
    testar_formalizacao_persistente_e_deduplicacao()
    testar_reconciliacao_historica()
    testar_invariantes_e_fonte()
    print("TESTE_AE5_DESCOBERTA_CONTINUA_OK")


if __name__ == "__main__":
    main()
