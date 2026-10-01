#!/usr/bin/env python3

"""Teste do pipeline controlado de desenvolvimento da Nyxal."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_pipeline_desenvolvimento import (
    PipelineDesenvolvimentoNixal,
)


def escrever_manifesto(
    caminho: Path,
    **sobrescritos,
) -> None:
    dados = {
        "versao_contrato": 1,
        "nome": "artefato_teste",
        "objetivo": "validar pipeline",
        "tipo": "python",
        "arquivo": caminho.name,
        "operacoes_permitidas": [
            "analise",
            "py_compile",
        ],
        "executar": False,
    }

    dados.update(
        sobrescritos
    )

    caminho.with_name(
        f"{caminho.name}.nyxal.json"
    ).write_text(
        json.dumps(
            dados,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def executar() -> None:
    repositorio = Path(__file__).resolve().parent

    with TemporaryDirectory() as temporario:
        raiz = Path(temporario)

        entrada = raiz / "incoming"
        workspace = raiz / "workspace"
        experimentos = raiz / "experiments"
        relatorios = raiz / "reports"

        entrada.mkdir()

        sem_contrato = entrada / "sem_contrato.py"
        sem_contrato.write_text(
            "def ignorado():\n"
            "    return True\n",
            encoding="utf-8",
        )

        valido = entrada / "valido.py"
        valido.write_text(
            "def soma(a, b):\n"
            "    return a + b\n",
            encoding="utf-8",
        )
        escrever_manifesto(valido)

        pipeline = PipelineDesenvolvimentoNixal(
            repositorio=repositorio,
            entrada=entrada,
            workspace=workspace,
            experimentos=experimentos,
            relatorios=relatorios,
        )

        resultado = pipeline.executar_ciclo()

        assert resultado["versao_pipeline"] == 2
        assert resultado["arquivos_detectados"] == 2
        assert resultado["arquivos_novos"] == 1
        assert resultado["candidatos"] == 1
        assert resultado["rejeitados"] == 0
        assert resultado["codigo_executado"] is False
        assert resultado["integracao_stable"] is False

        assert any(
            item["arquivo"] == "sem_contrato.py"
            and item["motivo"] == "contrato_ausente"
            for item in resultado[
                "arquivos_ignorados"
            ]
        )

        item = resultado[
            "arquivos_processados"
        ][0]

        assert item["decisao"] == "candidato"
        assert item["contrato"]["nome"] == (
            "artefato_teste"
        )
        assert item[
            "validacao_python"
        ]["sucesso"] is True

        segundo = pipeline.executar_ciclo()

        assert segundo["arquivos_detectados"] == 2
        assert segundo["arquivos_novos"] == 0
        assert segundo["candidatos"] == 0
        assert segundo["estado"] == (
            "nenhum_artefato_novo"
        )
        assert any(
            item["motivo"] == "artefato_ja_processado"
            for item in segundo[
                "arquivos_ignorados"
            ]
        )

        valido.write_text(
            "def soma(a, b):\n"
            "    return a + b + 1\n",
            encoding="utf-8",
        )

        terceiro = pipeline.executar_ciclo()

        assert terceiro["arquivos_novos"] == 1
        assert terceiro["candidatos"] == 1
        assert terceiro[
            "arquivos_processados"
        ][0]["sha256"] != item["sha256"]

        escrever_manifesto(
            valido,
            operacoes_permitidas=[
                "comando_arbitrario"
            ],
        )

        quarto = pipeline.executar_ciclo()

        assert quarto["arquivos_novos"] == 0
        assert any(
            item["motivo"] == "contrato_invalido"
            and item["erro"] == "operacao_nao_permitida"
            for item in quarto[
                "arquivos_ignorados"
            ]
        )

    print(
        "TESTE_PIPELINE_DESENVOLVIMENTO_OK"
    )


if __name__ == "__main__":
    executar()
