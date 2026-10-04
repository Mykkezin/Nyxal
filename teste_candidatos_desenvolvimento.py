#!/usr/bin/env python3

"""Teste do registro de candidatos da Nyxal."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_candidatos_desenvolvimento import (
    RegistroCandidatosDesenvolvimentoNixal,
)


def executar() -> None:
    with TemporaryDirectory() as temporario:
        raiz = Path(temporario)

        experimento = raiz / "experimento"
        (experimento / "sub").mkdir(
            parents=True
        )
        (experimento / "sub" / "codigo.py").write_text(
            "def ok():\n"
            "    return True\n",
            encoding="utf-8",
        )

        registro = RegistroCandidatosDesenvolvimentoNixal(
            repositorio=raiz,
            candidatos=raiz / "candidates",
        )

        resultado = registro.registrar(
            ciclo_id="20261001T000000000000Z",
            arquivo="codigo.py",
            manifesto="codigo.py.nyxal.json",
            fingerprint="abcdef1234567890",
            experimento_raiz=experimento,
            avaliacao={
                "aprovado": True,
                "criterios": {
                    "contrato_declarativo_valido": True
                },
                "motivos": [],
            },
        )

        assert resultado["estado"] == "candidato"
        assert resultado["candidato_id"].endswith(
            "-abcdef123456"
        )
        assert resultado["integracao_stable"] is False

        destino = Path(
            resultado["diretorio_candidato"]
        )

        assert (
            destino / "sub" / "codigo.py"
        ).exists()

        registro_json = destino / "candidato.json"
        assert registro_json.exists()

        dados = json.loads(
            registro_json.read_text(
                encoding="utf-8"
            )
        )

        assert dados["candidato_id"] == (
            resultado["candidato_id"]
        )
        assert dados["estado"] == "candidato"
        assert dados["avaliacao"]["aprovado"] is True

        try:
            registro.registrar(
                ciclo_id="20261001T000000000000Z",
                arquivo="codigo.py",
                manifesto="codigo.py.nyxal.json",
                fingerprint="abcdef1234567890",
                experimento_raiz=experimento,
                avaliacao={
                    "aprovado": True
                },
            )
        except FileExistsError as erro:
            assert str(erro) == (
                "candidato_ja_existente"
            )
        else:
            raise AssertionError(
                "duplicacao de candidato nao bloqueada"
            )

    print(
        "TESTE_CANDIDATOS_DESENVOLVIMENTO_OK"
    )


if __name__ == "__main__":
    executar()
