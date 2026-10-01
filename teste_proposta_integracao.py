#!/usr/bin/env python3

"""Teste da proposta de integração controlada da Nyxal."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from nixal_proposta_integracao import (
    PropostaIntegracaoDesenvolvimentoNixal,
)


def executar() -> None:
    with TemporaryDirectory() as temporario:
        raiz = Path(temporario)
        candidato = raiz / "candidate"
        candidato.mkdir()

        (candidato / "candidato.json").write_text(
            json.dumps(
                {
                    "candidato_id": "candidato-001",
                    "estado": "candidato",
                    "arquivo": "codigo.py",
                    "manifesto": "codigo.py.nyxal.json",
                    "fingerprint": "abc123",
                    "avaliacao": {
                        "aprovado": True,
                        "criterios": {
                            "contrato_declarativo_valido": True
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        gerador = (
            PropostaIntegracaoDesenvolvimentoNixal(
                repositorio=raiz,
                propostas=raiz / "proposals",
            )
        )

        proposta = gerador.criar(
            candidato_dir=candidato
        )

        assert proposta["estado"] == (
            "aguardando_autorizacao"
        )
        assert proposta["autorizacao_explicita"] is False
        assert proposta["integracao_executada"] is False
        assert proposta["stable_modificada"] is False
        assert proposta["destino_sugerido"] == "main"

        caminho = Path(
            proposta["arquivo_proposta"]
        )

        assert caminho.exists()

        dados = json.loads(
            caminho.read_text(
                encoding="utf-8"
            )
        )

        assert dados["proposta_id"] == proposta[
            "proposta_id"
        ]

        try:
            gerador.criar(
                candidato_dir=candidato
            )
        except FileExistsError as erro:
            assert str(erro) == (
                "proposta_ja_existente"
            )
        else:
            raise AssertionError(
                "duplicacao de proposta nao bloqueada"
            )

    print(
        "TESTE_PROPOSTA_INTEGRACAO_OK"
    )


if __name__ == "__main__":
    executar()
