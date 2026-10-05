#!/usr/bin/env python3
"""Testes da AE5 — descoberta contínua governada de valor econômico."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nixal_descoberta_continua_ae5 import DescobertaContinuaGovernadaAE5


class Relogio:
    def __init__(self) -> None:
        self.valor = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def agora(self) -> datetime:
        return self.valor

    def avancar(self, **kwargs: int) -> None:
        self.valor += timedelta(**kwargs)


def oportunidade(
    ciclo: str,
    *,
    tipo: str | None = "custo",
    evidencia: str = "uso computacional recorrente",
    observado: bool | None = True,
    mecanismo: str = "redução de processamento",
    metrica: str = "consumo computacional",
    unidade: str = "unidade/h",
    referencia: float | None = 100.0,
) -> dict:
    valor = {
        "oportunidade_id": f"op-{ciclo}",
        "limitacao": "processamento recorrente acima do necessário",
        "hipotese": "reduzir o processamento mantém a capacidade útil",
    }
    if tipo is not None:
        valor["valor_economico"] = {
            "tipo_valor": tipo,
            "mecanismo_valor": mecanismo,
            "metrica_economica": metrica,
            "unidade": unidade,
            "direcao": "reduzir",
            "referencia": referencia,
            "evidencia": evidencia,
            "confianca": "baixa",
            "resultado_observado": observado,
        }
    return {
        "sucesso": True,
        "estado": "ae4_melhoria_comprovada",
        "ciclo_id": ciclo,
        "ae1": {"sucesso": True, "valor": valor},
        "etapas": [
            {"etapa": "AE1", "oportunidade_id": f"op-{ciclo}"},
            {"etapa": "AE3", "aprendizado_disponivel": True},
        ],
    }


def nova_ae5(tmp: str, relogio: Relogio) -> DescobertaContinuaGovernadaAE5:
    return DescobertaContinuaGovernadaAE5(
        repositorio=Path(tmp) / "repo",
        agora=relogio.agora,
    )


def testar_sem_valor() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        resultado = ae5.processar(oportunidade("c1", tipo=None))
        assert resultado["estado"] == "sem_valor_identificado"
        assert resultado["valor_economico_identificado"] is False
        assert list((Path(tmp) / "Nyxal-evolution-discovery" / "auditoria").glob("ae5-*.json"))


def testar_progressao_economica() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        primeiro = ae5.processar(oportunidade("c1", evidencia="e1"))
        segundo = ae5.processar(oportunidade("c2", evidencia="e1"))
        terceiro = ae5.processar(oportunidade("c3", evidencia="e1"))
        assert primeiro["nova_linha"] is True
        assert primeiro["estado_economico"] == "valor_candidato"
        assert segundo["estado_economico"] == "valor_observacional"
        assert terceiro["estado_economico"] == "maduro_para_formalizacao"
        assert terceiro["madura_para_formalizacao"] is True
        assert terceiro["observacoes"] == 3
        assert terceiro["observacoes_positivas"] == 3


def testar_deduplicacao_24h() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        primeiro = ae5.processar(oportunidade("c1", evidencia="mesma evidencia"))
        segundo = ae5.processar(oportunidade("c2", evidencia="mesma evidencia"))
        assert primeiro["nova_linha"] is True
        assert segundo["nova_linha"] is False
        assert segundo["deduplicada_24h"] is True
        assert segundo["observada"] is True


def testar_cooldown_por_tipo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        ae5.processar(oportunidade("c1", evidencia="e1"))
        resultado = ae5.processar(oportunidade("c2", evidencia="e2"))
        assert resultado["estado"] == "cooldown_tipo"
        clock.avancar(minutes=31)
        resultado = ae5.processar(oportunidade("c3", evidencia="e2"))
        assert resultado["nova_linha"] is True


def testar_deduplicacao_idempotente_por_ciclo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        primeiro = ae5.processar(oportunidade("c1", evidencia="e1"))
        repetido = ae5.processar(oportunidade("c1", evidencia="e1"))
        assert primeiro["linha_id"] == repetido["linha_id"]
        assert repetido["observada"] is False
        assert repetido["nova_linha"] is False


def testar_contradicao_impede_maturidade() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        for i in range(1, 4):
            ae5.processar(oportunidade(f"c{i}", evidencia="e1", observado=True))
        clock.avancar(minutes=31)
        resultado = ae5.processar(oportunidade("c4", evidencia="e1", observado=False))
        assert resultado["contradicoes"] == 1
        assert resultado["madura_para_formalizacao"] is False
        assert resultado["estado_economico"] == "valor_sustentado"


def testar_duplicata_semantica_preserva_proveniencia() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        ae5.processar(oportunidade(
            "c1",
            evidencia="tempo de computação da etapa crítica",
            mecanismo="redução de computação",
        ))
        clock.avancar(minutes=31)
        resultado = ae5.processar(oportunidade(
            "c2",
            evidencia="tempo computacional da etapa crítica",
            mecanismo="redução de cálculo",
        ))
        assert resultado["nova_linha"] is True
        assert resultado["possivel_duplicata_semantica"] is True
        assert resultado["linha_id"] != resultado["linha_semelhante"]


def testar_limite_de_50_sinais() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        sinais = (
            oportunidade(f"c{i}", evidencia=f"e{i}", tipo="custo")
            for i in range(60)
        )
        resultado = ae5.processar_lote(sinais)
        assert resultado["sinais_processados"] == 50
        assert any(x["estado"] == "limite_50_sinais" for x in resultado["resultados"])


def testar_limite_20_ciclos_por_linha() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        for i in range(1, 26):
            ae5.processar(oportunidade(f"c{i}", evidencia="e", observado=True))
        linha = ae5.listar(limite=1)[0]
        assert len(linha["evidencias"]) <= 20
        assert len(linha["ciclos_observados"]) <= 20


def testar_vinculo_n9_explicito() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        raiz = Path(tmp)
        ae5 = nova_ae5(tmp, clock)
        primeiro = ae5.processar(oportunidade("c1", evidencia="n9"))
        requests = raiz / "Nyxal-evolution-requests"
        requests.mkdir()
        (requests / "solicitacao-teste.json").write_text(
            json.dumps({
                "solicitacao_id": "solicitacao-teste",
                "economic_line_id": primeiro["linha_id"],
                "hipotese": {"hipotese": "reduzir o processamento mantém a capacidade útil"},
            }),
            encoding="utf-8",
        )
        clock.avancar(minutes=1)
        segundo = ae5.processar(oportunidade("c2", evidencia="n9"))
        assert "solicitacao-teste" in segundo["n9_vinculos_explicitos"]


def testar_api_contexto_e_invariantes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clock = Relogio()
        ae5 = nova_ae5(tmp, clock)
        ae5.processar(oportunidade("c1"))
        contexto = ae5.contexto()
        assert contexto["linhas_economicas_ativas"] == 1
        assert contexto["versao"] == "AE5.2.0"
        for chave, valor in contexto.items():
            if chave in {
                "autorizacao_explicita",
                "integracao_executada",
                "stable_modificada",
                "arquitetura_modificada",
                "conhecimento_permanente",
            }:
                assert valor is False


def testar_fonte_sem_execucao_externa() -> None:
    origem = Path("nixal_descoberta_continua_ae5.py").read_text(encoding="utf-8")
    assert "subprocess" not in origem
    assert "os.system" not in origem
    assert "Popen" not in origem
    assert "git merge" not in origem
    assert "shell=True" not in origem


def main() -> None:
    testar_sem_valor()
    testar_progressao_economica()
    testar_deduplicacao_24h()
    testar_cooldown_por_tipo()
    testar_deduplicacao_idempotente_por_ciclo()
    testar_contradicao_impede_maturidade()
    testar_duplicata_semantica_preserva_proveniencia()
    testar_limite_de_50_sinais()
    testar_limite_20_ciclos_por_linha()
    testar_vinculo_n9_explicito()
    testar_api_contexto_e_invariantes()
    testar_fonte_sem_execucao_externa()
    print("TESTE_AE5_DESCOBERTA_ECONOMICA_OK")


if __name__ == "__main__":
    main()
