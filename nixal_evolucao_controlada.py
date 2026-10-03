#!/usr/bin/env python3
"""
NYXAL — CICLO DE EVOLUÇÃO CONTROLADA

Orquestra a cadeia:
limitação → hipótese → experimento → avaliação → candidato
→ proposta → integração controlada → baseline/rollback.

A classe não modifica stable por conta própria. A integração exige
autorização explícita e ocorre em branch separada, usando a infraestrutura
já existente do projeto.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from nixal_avaliador_desenvolvimento import AvaliacaoDesenvolvimentoNixal
from nixal_candidatos_desenvolvimento import RegistroCandidatosDesenvolvimentoNixal
from nixal_proposta_integracao import PropostaIntegracaoDesenvolvimentoNixal
from nixal_integracao_controlada import IntegracaoControladaDesenvolvimentoNixal


class EvolucaoControladaNixal:
    VERSAO = 1

    def __init__(self, repositorio: str | Path | None = None) -> None:
        self.repositorio = Path(repositorio or Path(__file__).resolve().parent)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def fingerprint(caminho: str | Path) -> str:
        dados = Path(caminho).read_bytes()
        return hashlib.sha256(dados).hexdigest()

    def avaliar_experimento(self, *, contrato: dict, arquivo: str | Path) -> dict:
        caminho = Path(arquivo)
        validacao = None
        if contrato.get("tipo") == "python":
            resultado = subprocess.run(
                ["python", "-m", "py_compile", str(caminho)],
                cwd=self.repositorio,
                text=True,
                capture_output=True,
                check=False,
            )
            validacao = {
                "sucesso": resultado.returncode == 0,
                "stdout": resultado.stdout,
                "stderr": resultado.stderr,
            }

        avaliacao = AvaliacaoDesenvolvimentoNixal.avaliar(
            contrato=contrato,
            validacao_python=validacao,
        ).como_dict()

        return {
            "avaliacao": avaliacao,
            "fingerprint": self.fingerprint(caminho),
            "validacao_python": validacao,
        }

    def executar_ciclo(
        self,
        *,
        ciclo_id: str,
        arquivo: str | Path,
        manifesto: str,
        contrato: dict,
        experimento_raiz: str | Path,
        autorizar_integracao: bool = False,
        stable: str = "main",
    ) -> dict:
        aval = self.avaliar_experimento(
            contrato=contrato,
            arquivo=arquivo,
        )
        avaliacao = aval["avaliacao"]

        if not avaliacao["aprovado"]:
            return {
                "sucesso": False,
                "estado": "experimento_rejeitado",
                "ciclo_id": ciclo_id,
                "avaliacao": avaliacao,
                "fingerprint": aval["fingerprint"],
            }

        registro = RegistroCandidatosDesenvolvimentoNixal(
            repositorio=self.repositorio,
        ).registrar(
            ciclo_id=ciclo_id,
            arquivo=Path(arquivo).name,
            manifesto=manifesto,
            fingerprint=aval["fingerprint"],
            experimento_raiz=experimento_raiz,
            avaliacao=avaliacao,
        )

        proposta = PropostaIntegracaoDesenvolvimentoNixal(
            repositorio=self.repositorio,
        ).criar(
            candidato_dir=registro["diretorio_candidato"],
            destino=stable,
        )

        resultado = {
            "sucesso": True,
            "estado": "proposta_criada",
            "ciclo_id": ciclo_id,
            "avaliacao": avaliacao,
            "candidato_id": registro["candidato_id"],
            "proposta_id": proposta["proposta_id"],
            "fingerprint": aval["fingerprint"],
            "integracao": None,
        }

        if autorizar_integracao:
            integracao = IntegracaoControladaDesenvolvimentoNixal(
                repositorio=self.repositorio,
            ).preparar(
                proposta_path=proposta["arquivo_proposta"],
                autorizacao_explicita=True,
                stable=stable,
            )
            resultado["estado"] = "integracao_preparada"
            resultado["integracao"] = integracao

        return resultado

    @staticmethod
    def rollback(repo: str | Path, stable: str = "main") -> dict:
        raiz = Path(repo)

        def git(*args: str) -> str:
            r = subprocess.run(
                ["git", *args],
                cwd=raiz,
                text=True,
                capture_output=True,
                check=False,
            )
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip() or "git_falhou")
            return r.stdout.strip()

        branch_atual = git("branch", "--show-current")
        git("switch", stable)
        return {
            "estado": "rollback_concluido",
            "branch_anterior": branch_atual,
            "branch_atual": git("branch", "--show-current"),
            "stable": stable,
            "stable_modificada": False,
        }
