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

        caminho_relatorio = Path(
            resultado["relatorio"]
        )

        assert caminho_relatorio.exists()

    print(
        "TESTE_PIPELINE_DESENVOLVIMENTO_OK"
    )


if __name__ == "__main__":
    executar()
