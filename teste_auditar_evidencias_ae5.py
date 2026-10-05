#!/usr/bin/env python3
"""Teste do auditor somente leitura do Gate AE5."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from auditar_evidencias_ae5 import auditar


def escrever(caminho: Path, valor: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as temporario:
        raiz = Path(temporario)
        repo = raiz / "repo"
        ae4 = raiz / "Nyxal-evolution-ae4"
        oportunidades = raiz / "Nyxal-evolution-opportunities"

        resultado_vazio = auditar(repo)
        assert resultado_vazio["evidencia_operacional_encontrada"] is False
        assert resultado_vazio["somente_leitura"] is True

        # Cobre o contrato da AE4 que também persiste o vínculo
        # oportunidade em "vinculos", mesmo quando o resumo AE1 não
        # expõe o identificador diretamente.
        oportunidade_id_vinculo = "op-vinculo"
        escrever(
            oportunidades / f"{oportunidade_id_vinculo}.json",
            {
                "oportunidade_id": oportunidade_id_vinculo,
                "limitacao": "lacuna persistente",
                "hipotese": "registrar dependencias declaradas",
            },
        )
        escrever(
            ae4 / "ae4-ciclo-vinculo.json",
            {
                "ciclo_id": "real-vinculo",
                "estado": "ae4_ciclo_observado",
                "vinculos": {
                    "oportunidade_id": oportunidade_id_vinculo,
                },
                "etapas": [
                    {
                        "etapa": "AE1",
                        "sucesso": True,
                    }
                ],
            },
        )

        for i in range(1, 4):
            oportunidade_id = f"op-real-{i}"
            escrever(
                oportunidades / f"{oportunidade_id}.json",
                {
                    "oportunidade_id": oportunidade_id,
                    "limitacao": "latencia observada",
                    "hipotese": "reduzir etapa critica",
                },
            )
            escrever(
                ae4 / f"ae4-ciclo-real-{i}.json",
                {
                    "ciclo_id": f"real-{i}",
                    "estado": "ae4_ciclo_observado",
                    "etapas": [
                        {
                            "etapa": "AE1",
                            "sucesso": True,
                            "oportunidade_id": oportunidade_id,
                        }
                    ],
                },
            )

        resultado = auditar(repo)
        assert resultado["evidencia_operacional_encontrada"] is True
        assert resultado["auditorias_ae4_validas"] == 4
        assert resultado["ciclos_distintos"] == 4
        assert resultado["linhas_maduras"] == 1
        assert resultado["somente_leitura"] is True
        for chave in (
            "autorizacao_explicita",
            "integracao_executada",
            "stable_modificada",
            "arquitetura_modificada",
            "conhecimento_permanente",
        ):
            assert resultado[chave] is False

    print("TESTE_AUDITOR_EVIDENCIAS_AE5_OK")


if __name__ == "__main__":
    main()
