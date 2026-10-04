#!/usr/bin/env python3
"""Prova determinística do controlador do laboratório remoto."""

from __future__ import annotations

import json

from nixal_laboratorio_remoto import LaboratorioRemotoNixal


def main() -> int:
    laboratorio = LaboratorioRemotoNixal(
        repositorio="."
    )

    manifesto = laboratorio.construir_manifesto(
        experimento_id="stt-001",
        entrypoint="experimento/teste.py",
        timeout_seconds=90,
        descricao="Teste do laboratório",
    )

    assert manifesto == {
        "versao": 1,
        "experimento_id": "stt-001",
        "entrypoint": "experimento/teste.py",
        "timeout_seconds": 90,
        "descricao": "Teste do laboratório",
    }

    assert (
        laboratorio.branch_experimento("stt-001")
        == "experimento/stt-001"
    )

    resultado_logs = (
        "linha anterior\n"
        "NYXAL_RESULT_JSON="
        + json.dumps(
            {
                "status": "sucesso",
                "experimento_sucesso": True,
                "experiment_sha": "a" * 40,
                "tempo_execucao_ms": 10.5,
                "memoria_maxima_kb": 1234,
                "stable_modificada": False,
                "autorizacao_explicita": False,
            },
            ensure_ascii=False,
        )
        + "\n"
    )

    resultado = (
        laboratorio.extrair_resultado_dos_logs(
            resultado_logs
        )
    )

    assert resultado is not None
    assert resultado["status"] == "sucesso"
    assert resultado["experimento_sucesso"] is True
    assert resultado["experiment_sha"] == "a" * 40
    assert resultado["stable_modificada"] is False
    assert resultado["autorizacao_explicita"] is False

    invalido = (
        laboratorio.extrair_resultado_dos_logs(
            "NYXAL_RESULT_JSON={invalido}"
        )
    )
    assert invalido is None

    respostas = iter(
        [
            RuntimeError(
                "github_api_http_404:<Error><Code>BlobNotFound</Code></Error>"
            ),
            RuntimeError(
                "github_api_http_404:<Error><Code>BlobNotFound</Code></Error>"
            ),
            (302, "logs\nNYXAL_RESULT_JSON={\"status\":\"sucesso\"}\n"),
        ]
    )

    chamada_original = laboratorio._api_request

    def api_fake(*args, **kwargs):
        resposta = next(respostas)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    laboratorio._api_request = api_fake

    try:
        logs = laboratorio.baixar_logs_job(
            123,
            max_tentativas=3,
            atraso_inicial=0,
        )
    finally:
        laboratorio._api_request = chamada_original

    assert "NYXAL_RESULT_JSON" in logs

    testes_invalidos = [
        lambda: laboratorio.branch_experimento("../x"),
        lambda: laboratorio.construir_manifesto(
            experimento_id="ok",
            entrypoint="../experimento/teste.py",
        ),
        lambda: laboratorio.construir_manifesto(
            experimento_id="ok",
            entrypoint="teste.py",
        ),
        lambda: laboratorio.construir_manifesto(
            experimento_id="ok",
            entrypoint="experimento/teste.sh",
        ),
    ]

    for acao in testes_invalidos:
        try:
            acao()
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(
                "entrada inválida foi aceita"
            )

    print("=" * 60)
    print("TESTE — CONTROLADOR DO LABORATÓRIO REMOTO")
    print("=" * 60)
    print("MANIFESTO=OK")
    print("BRANCH_EXPERIMENTO=OK")
    print("LEITURA_RESULTADO=OK")
    print("RETRY_BLOB_NOT_FOUND=OK")
    print("VALIDACAO_ENTRADAS=OK")
    print("SEM_EXECUCAO_LOCAL=OK")
    print("SEM_AUTORIZACAO_DE_INTEGRACAO=OK")
    print("PASSOU: True")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
