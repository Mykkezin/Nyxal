#!/usr/bin/env python3

"""
NYXAL — PROPOSTA DE INTEGRAÇÃO CONTROLADA

Cria uma proposta persistente a partir de um candidato validado.
A proposta não modifica o repositório e não integra em stable.

Próxima etapa futura:
    proposta aprovada
        ↓
    integração controlada
        ↓
    revisão/testes
        ↓
    stable
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class PropostaIntegracaoDesenvolvimentoNixal:
    VERSAO = 1

    def __init__(
        self,
        repositorio: str | Path | None = None,
        propostas: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )

        base_externa = self.repositorio.parent

        self.propostas = Path(
            propostas
            or base_externa
            / "Nyxal-integration-proposals"
        )

        self.propostas.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _timestamp(self) -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def criar(
        self,
        *,
        candidato_dir: str | Path,
        destino: str = "main",
    ) -> dict:
        origem = Path(candidato_dir)

        if not origem.exists():
            raise FileNotFoundError(
                "candidato_nao_encontrado"
            )

        registro_path = (
            origem / "candidato.json"
        )

        if not registro_path.exists():
            raise FileNotFoundError(
                "registro_do_candidato_nao_encontrado"
            )

        try:
            registro = json.loads(
                registro_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError(
                "registro_do_candidato_invalido"
            ) from erro

        if registro.get("estado") != "candidato":
            raise ValueError(
                "estado_do_candidato_invalido"
            )

        avaliacao = registro.get(
            "avaliacao",
            {},
        )

        if avaliacao.get("aprovado") is not True:
            raise ValueError(
                "candidato_sem_avaliacao_aprovada"
            )

        candidato_id = registro.get(
            "candidato_id"
        )

        if not isinstance(
            candidato_id,
            str,
        ) or not candidato_id:
            raise ValueError(
                "candidato_id_invalido"
            )

        proposta_id = (
            f"integracao-{candidato_id}"
        )

        caminho = (
            self.propostas
            / f"{proposta_id}.json"
        )

        if caminho.exists():
            raise FileExistsError(
                "proposta_ja_existente"
            )

        proposta = {
            "versao_proposta": self.VERSAO,
            "proposta_id": proposta_id,
            "estado": "aguardando_autorizacao",
            "criada_em": self._timestamp(),
            "candidato_id": candidato_id,
            "candidato_dir": str(origem),
            "arquivo": registro.get("arquivo"),
            "manifesto": registro.get("manifesto"),
            "fingerprint": registro.get("fingerprint"),
            "avaliacao": avaliacao,
            "destino_sugerido": destino,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

        caminho.write_text(
            json.dumps(
                proposta,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        proposta["arquivo_proposta"] = str(
            caminho
        )

        return proposta


if __name__ == "__main__":
    print(
        "PropostaIntegracaoDesenvolvimentoNixal OK"
    )
