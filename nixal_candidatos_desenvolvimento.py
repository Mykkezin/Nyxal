#!/usr/bin/env python3

"""
NYXAL — REGISTRO DE CANDIDATOS DE DESENVOLVIMENTO

Mantém candidatos fora da árvore Git e separados dos experimentos.
Um candidato é apenas uma proposta aprovada pelos critérios atuais.
A classe não integra candidatos em stable.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class RegistroCandidatosDesenvolvimentoNixal:
    VERSAO = 1

    def __init__(
        self,
        repositorio: str | Path | None = None,
        candidatos: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )

        base_externa = self.repositorio.parent

        self.candidatos = Path(
            candidatos
            or base_externa / "Nyxal-candidates"
        )

        self.candidatos.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _timestamp(self) -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def registrar(
        self,
        *,
        ciclo_id: str,
        arquivo: str,
        manifesto: str,
        fingerprint: str,
        experimento_raiz: str | Path,
        avaliacao: dict,
    ) -> dict:
        candidato_id = (
            f"candidato-{ciclo_id}-"
            f"{fingerprint[:12]}"
        )

        origem = Path(experimento_raiz)

        if not origem.exists():
            raise FileNotFoundError(
                "experimento_nao_encontrado"
            )

        destino = (
            self.candidatos
            / candidato_id
        )

        if destino.exists():
            raise FileExistsError(
                "candidato_ja_existente"
            )

        shutil.copytree(
            origem,
            destino,
        )

        registro = {
            "versao_registro": self.VERSAO,
            "candidato_id": candidato_id,
            "estado": "candidato",
            "criado_em": self._timestamp(),
            "ciclo_id": ciclo_id,
            "arquivo": arquivo,
            "manifesto": manifesto,
            "fingerprint": fingerprint,
            "avaliacao": avaliacao,
            "integracao_stable": False,
            "origem_experimento": str(
                origem
            ),
            "diretorio_candidato": str(
                destino
            ),
        }

        caminho_registro = (
            destino / "candidato.json"
        )

        caminho_registro.write_text(
            json.dumps(
                registro,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return registro


if __name__ == "__main__":
    print(
        "RegistroCandidatosDesenvolvimentoNixal OK"
    )
