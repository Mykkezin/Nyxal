#!/usr/bin/env python3

"""
NYXAL — INTEGRAÇÃO CONTROLADA DE DESENVOLVIMENTO

Primeira etapa da barreira entre proposta e stable.

Fluxo:
    proposta
        ↓
    autorização externa explícita
        ↓
    branch de integração
        ↓
    revisão/testes
        ↓
    promoção futura para stable

Garantias desta camada:
- não aceita um simples booleano interno como autorização;
- autorização precisa vir de registro externo;
- valida proposta, candidato e fingerprint;
- trabalha a partir do tip atual de stable;
- nunca modifica stable;
- nunca usa force push;
- nunca executa o código do candidato.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from nixal_proposta_integracao import (
    PropostaIntegracaoDesenvolvimentoNixal,
)


class IntegracaoControladaDesenvolvimentoNixal:
    VERSAO = 2
    BRANCH_STABLE_PADRAO = "main"
    PREFIXO_BRANCH = "integracao"

    ARQUIVOS_PROTEGIDOS = {
        "estado_corpo_nixal.json",
        "estado_nixal.json",
        "estado_nyxal_runtime.json",
        "fila_tarefas_nixal.json",
        "log_capacidades_nixal.json",
        "log_nyxal_runtime.json",
        "memoria_investigacao_nixal.json",
        "backup_nixal_memoria_conhecimento_2026-10-04.py",
        "backup_nixal_runtime_pre_nivel8.py",
        "log_nyxal_runtime.json.tmp",
    }

    def __init__(
        self,
        repositorio: str | Path | None = None,
        propostas: str | Path | None = None,
        autorizacoes: str | Path | None = None,
        remote: str = "origin",
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        ).resolve()
        self.remote = remote
        self.propostas = PropostaIntegracaoDesenvolvimentoNixal(
            repositorio=self.repositorio,
            propostas=propostas,
        )
        self.autorizacoes = Path(
            autorizacoes
            or self.repositorio.parent
            / "Nyxal-integration-authorizations"
        ).resolve()
        self.autorizacoes.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _texto(valor: Any, nome: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    @staticmethod
    def _hash_arquivo(caminho: Path) -> str:
        digest = hashlib.sha256()
        with caminho.open("rb") as arquivo:
            for bloco in iter(
                lambda: arquivo.read(1024 * 1024),
                b"",
            ):
                digest.update(bloco)
        return digest.hexdigest()

    @staticmethod
    def _git(
        repositorio: Path,
        *args: str,
        cwd: Path | None = None,
    ) -> str:
        resultado = subprocess.run(
            ["git", *args],
            cwd=cwd or repositorio,
            text=True,
            capture_output=True,
            check=False,
            env={
                **os.environ,
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
        if resultado.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} falhou: "
                f"{resultado.stderr.strip()}"
            )
        return resultado.stdout.strip()

    @staticmethod
    def _validar_nome_branch(nome: str) -> None:
        if (
            not isinstance(nome, str)
            or not nome
            or not re.fullmatch(
                r"[A-Za-z0-9._/-]+",
                nome,
            )
            or nome.startswith("/")
            or nome.endswith("/")
            or ".." in nome
            or "@{" in nome
        ):
            raise ValueError("nome_de_branch_invalido")

    @classmethod
    def _validar_arquivo_relativo(
        cls,
        nome: str,
    ) -> Path:
        if (
            not isinstance(nome, str)
            or not nome.strip()
        ):
            raise ValueError(
                "arquivo_do_candidato_invalido"
            )

        destino = Path(nome)

        if (
            destino.is_absolute()
            or ".." in destino.parts
            or destino.name in cls.ARQUIVOS_PROTEGIDOS
        ):
            raise ValueError(
                "destino_do_candidato_invalido"
            )

        return destino

    def _carregar_autorizacao(
        self,
        caminho: str | Path,
    ) -> dict[str, Any]:
        origem = Path(caminho).expanduser().resolve()

        if not origem.is_file():
            raise FileNotFoundError(
                "arquivo_autorizacao_nao_encontrado"
            )

        try:
            dados = json.loads(
                origem.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError(
                "arquivo_autorizacao_invalido"
            ) from erro

        if not isinstance(dados, dict):
            raise ValueError(
                "arquivo_autorizacao_invalido"
            )

        dados["origem"] = f"arquivo:{origem}"
        return dados

    def consumir_autorizacao(
        self,
        proposta_id: str,
        caminho_autorizacao: str | Path,
    ) -> dict[str, Any]:
        """
        Consome um registro de autorização que veio de fora do ciclo.

        Não existe método neste componente para gerar a autorização.
        """
        autorizacao = self._carregar_autorizacao(
            caminho_autorizacao
        )

        return self.propostas.registrar_autorizacao(
            proposta_id,
            autorizacao,
        )

    def _carregar_candidato(
        self,
        proposta: dict[str, Any],
    ) -> tuple[dict[str, Any], Path, Path]:
        candidato_dir = Path(
            self._texto(
                proposta.get("candidato_dir"),
                "candidato_dir",
            )
        ).expanduser().resolve()

        registro_path = candidato_dir / "candidato.json"
        if not registro_path.is_file():
            raise FileNotFoundError(
                "registro_do_candidato_nao_encontrado"
            )

        try:
            candidato = json.loads(
                registro_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError(
                "registro_do_candidato_invalido"
            ) from erro

        if not isinstance(candidato, dict):
            raise ValueError(
                "registro_do_candidato_invalido"
            )

        if candidato.get("estado") != "candidato":
            raise ValueError(
                "estado_do_candidato_invalido"
            )

        avaliacao = candidato.get("avaliacao")
        if (
            not isinstance(avaliacao, dict)
            or avaliacao.get("aprovado") is not True
        ):
            raise ValueError(
                "candidato_sem_avaliacao_aprovada"
            )

        arquivo = self._texto(
            proposta.get("arquivo"),
            "arquivo_da_proposta",
        )
        candidato_arquivo = self._texto(
            candidato.get("arquivo"),
            "arquivo_do_candidato",
        )

        if arquivo != candidato_arquivo:
            raise ValueError(
                "arquivo_proposta_candidato_inconsistente"
            )

        destino = self._validar_arquivo_relativo(
            arquivo
        )
        origem = candidato_dir / destino

        if not origem.is_file():
            raise FileNotFoundError(
                "arquivo_do_candidato_nao_encontrado"
            )

        fingerprint_proposta = self._texto(
            proposta.get("fingerprint"),
            "fingerprint_da_proposta",
        )
        fingerprint_candidato = self._texto(
            candidato.get("fingerprint"),
            "fingerprint_do_candidato",
        )
        fingerprint_atual = self._hash_arquivo(origem)

        if fingerprint_proposta != fingerprint_candidato:
            raise ValueError(
                "fingerprint_proposta_candidato_inconsistente"
            )

        if fingerprint_atual != fingerprint_proposta:
            raise ValueError(
                "fingerprint_do_candidato_inconsistente"
            )

        return candidato, origem, destino

    def preparar(
        self,
        *,
        proposta_id: str,
        caminho_autorizacao: str | Path,
        stable: str = BRANCH_STABLE_PADRAO,
        branch_integracao: str | None = None,
    ) -> dict[str, Any]:
        """
        Consome autorização e cria somente a branch de integração.

        Stable permanece inalterada nesta etapa.
        """
        stable = self._texto(stable, "stable")
        self._validar_nome_branch(stable)

        if stable != self.BRANCH_STABLE_PADRAO:
            raise ValueError(
                "branch_stable_nao_permitida"
            )

        autorizada = self.consumir_autorizacao(
            proposta_id,
            caminho_autorizacao,
        )

        if autorizada.get("estado") != (
            "autorizada_para_integracao"
        ):
            raise RuntimeError(
                "autorizacao_nao_registrada"
            )

        proposta = self.propostas.consultar(
            proposta_id
        )
        candidato, origem, destino = self._carregar_candidato(
            proposta
        )

        branch = branch_integracao or (
            f"{self.PREFIXO_BRANCH}/{proposta_id}"
        )
        self._validar_nome_branch(branch)

        if branch == stable:
            raise ValueError(
                "branch_de_integracao_nao_pode_ser_stable"
            )

        existente = self._git(
            self.repositorio,
            "branch",
            "--list",
            branch,
        )
        if existente:
            raise FileExistsError(
                "branch_de_integracao_ja_existente"
            )

        base_sha = self._git(
            self.repositorio,
            "rev-parse",
            f"refs/heads/{stable}",
        )

        with tempfile.TemporaryDirectory(
            prefix="nyxal-integracao-"
        ) as temporario:
            worktree = Path(temporario)

            self._git(
                self.repositorio,
                "worktree",
                "add",
                "-b",
                branch,
                str(worktree),
                base_sha,
            )

            try:
                destino_absoluto = worktree / destino
                destino_absoluto.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                shutil.copy2(
                    origem,
                    destino_absoluto,
                )

                self._git(
                    self.repositorio,
                    "add",
                    "--",
                    str(destino),
                    cwd=worktree,
                )

                diff = self._git(
                    self.repositorio,
                    "diff",
                    "--cached",
                    "--name-only",
                    cwd=worktree,
                ).splitlines()

                if diff != [str(destino)]:
                    raise RuntimeError(
                        "diff_de_integracao_inesperado"
                    )

                self._git(
                    self.repositorio,
                    "commit",
                    "-m",
                    f"feat: integra candidato {proposta_id}",
                    cwd=worktree,
                )

                commit_sha = self._git(
                    self.repositorio,
                    "rev-parse",
                    "HEAD",
                    cwd=worktree,
                )
            except Exception:
                try:
                    self._git(
                        self.repositorio,
                        "branch",
                        "-D",
                        branch,
                    )
                except Exception:
                    pass
                raise
            finally:
                self._git(
                    self.repositorio,
                    "worktree",
                    "remove",
                    "--force",
                    str(worktree),
                )

        stable_depois = self._git(
            self.repositorio,
            "rev-parse",
            f"refs/heads/{stable}",
        )
        if stable_depois != base_sha:
            raise RuntimeError(
                "stable_modificada_durante_preparacao"
            )

        preparado = self.propostas.registrar_preparacao(
            proposta_id,
            branch_integracao=branch,
            commit_integracao=commit_sha,
        )

        return {
            "versao_integracao": self.VERSAO,
            "estado": "integracao_preparada",
            "proposta_id": proposta_id,
            "candidato_id": candidato.get("candidato_id"),
            "stable": stable,
            "stable_base_sha": base_sha,
            "stable_modificada": False,
            "branch_integracao": branch,
            "commit_integracao": commit_sha,
            "autorizacao_explicita": True,
            "autorizacao": copy.deepcopy(
                preparado.get("autorizacao")
            ),
        }


__all__ = [
    "IntegracaoControladaDesenvolvimentoNixal",
]


if __name__ == "__main__":
    print(
        "IntegracaoControladaDesenvolvimentoNixal OK"
    )
