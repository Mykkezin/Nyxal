#!/usr/bin/env python3

"""Teste do pipeline controlado de desenvolvimento da Nyxal."""

from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_pipeline_desenvolvimento import (
    PipelineDesenvolvimentoNixal,
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

        (entrada / "valido.py").write_text(
            "def soma(a, b):\n"
            "    return a + b\n",
            encoding="utf-8",
        )

        (entrada / "invalido.py").write_text(
            "def quebrado(:\n"
            "    pass\n",
            encoding="utf-8",
        )

        pipeline = PipelineDesenvolvimentoNixal(
            repositorio=repositorio,
            entrada=entrada,
            workspace=workspace,
            experimentos=experimentos,
            relatorios=relatorios,
        )

        resultado = pipeline.executar_ciclo()

        assert resultado["arquivos_detectados"] == 2
        assert resultado["arquivos_novos"] == 2
        assert resultado["candidatos"] == 1
        assert resultado["rejeitados"] == 1
        assert resultado["codigo_executado"] is False
        assert resultado["integracao_stable"] is False

        nomes = {
            item["arquivo"]: item
            for item in resultado[
                "arquivos_processados"
            ]
        }

        assert nomes["valido.py"]["decisao"] == "candidato"
        assert nomes["valido.py"]["validacao_python"]["sucesso"] is True

        assert nomes["invalido.py"]["decisao"] == "rejeitado"
        assert nomes["invalido.py"]["validacao_python"]["sucesso"] is False

        primeiro = pipeline.executar_ciclo()

        assert primeiro["arquivos_detectados"] == 2
        assert primeiro["arquivos_novos"] == 0
        assert primeiro["candidatos"] == 0
        assert primeiro["rejeitados"] == 0
        assert primeiro["estado"] == "nenhum_artefato_novo"
        assert len(primeiro["arquivos_ignorados"]) == 2

        assert all(
            item["motivo"] == "artefato_ja_processado"
            for item in primeiro["arquivos_ignorados"]
        )

        (entrada / "valido.py").write_text(
            "def soma(a, b):\n"
            "    return a + b + 1\n",
            encoding="utf-8",
        )

        segundo = pipeline.executar_ciclo()

        assert segundo["arquivos_detectados"] == 2
        assert segundo["arquivos_novos"] == 1
        assert segundo["candidatos"] == 1
        assert segundo["rejeitados"] == 0

        nomes_segundo = {
            item["arquivo"]: item
            for item in segundo[
                "arquivos_processados"
            ]
        }

        assert nomes_segundo["valido.py"]["decisao"] == "candidato"
        assert nomes_segundo["valido.py"]["sha256"] != (
            nomes["valido.py"]["sha256"]
        )

        assert Path(
            resultado["relatorio"]
        ).exists()

    print(
        "TESTE_PIPELINE_DESENVOLVIMENTO_OK"
    )


if __name__ == "__main__":
    executar()
