#!/usr/bin/env python3

"""
NYXAL — INTEGRAÇÃO CONTROLADA DE DESENVOLVIMENTO

Promove um candidato aprovado para uma branch de integração
criada a partir de uma branch stable (por padrão: main).

Limites:
- exige autorização explícita do chamador;
- nunca escreve diretamente em stable;
- nunca usa force push;
- nunca executa o código do candidato;
- valida o candidato e o destino antes de escrever;
- registra rastreabilidade da integração;
- deixa a promoção para stable como etapa posterior.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


class IntegracaoControladaDesenvolvimentoNixal:
    VERSAO = 1
    BRANCH_STABLE_PADRAO = "main"
    PREFIXO_BRANCH = "integracao"

    def __init__(
        self,
        repositorio: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )

    def _git(self, *args: str) -> str:
        resultado = subprocess.run(
            ["git", *args],
            cwd=self.repositorio,
            text=True,
            capture_output=True,
            check=False,
        )

        if resultado.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} falhou: "
                f"{resultado.stderr.strip()}"
            )

        return resultado.stdout.strip()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _validar_nome_branch(self, nome: str) -> None:
        if not nome or not re.fullmatch(
            r"[A-Za-z0-9._/-]+",
            nome,
        ):
            raise ValueError("nome_de_branch_invalido")

        if nome.startswith("/") or nome.endswith("/"):
            raise ValueError("nome_de_branch_invalido")

        if ".." in nome or "@{" in nome:
            raise ValueError("nome_de_branch_invalido")

    def _validar_proposta(
        self,
        proposta_path: Path,
        autorizacao_explicita: bool,
        stable: str,
    ) -> dict:
        if not autorizacao_explicita:
            raise PermissionError(
                "autorizacao_explicita_obrigatoria"
            )

        if stable != self.BRANCH_STABLE_PADRAO:
            raise ValueError(
                "branch_stable_nao_permitida"
            )

        if not proposta_path.exists():
            raise FileNotFoundError(
                "proposta_nao_encontrada"
            )

        try:
            proposta = json.loads(
                proposta_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError(
                "proposta_invalida"
            ) from erro

        if proposta.get("estado") != "aguardando_autorizacao":
            raise ValueError(
                "estado_da_proposta_invalido"
            )

        if proposta.get("autorizacao_explicita") is not False:
            raise ValueError(
                "estado_de_autorizacao_invalido"
            )

        if proposta.get("integracao_executada") is True:
            raise ValueError(
                "integracao_ja_executada"
            )

        if proposta.get("stable_modificada") is True:
            raise ValueError(
                "stable_ja_modificada"
            )

        candidato_dir = Path(
            proposta.get("candidato_dir", "")
        )

        if not candidato_dir.exists():
            raise FileNotFoundError(
                "candidato_da_proposta_nao_encontrado"
            )

        candidato_registro = (
            candidato_dir / "candidato.json"
        )

        if not candidato_registro.exists():
            raise FileNotFoundError(
                "registro_do_candidato_nao_encontrado"
            )

        try:
            candidato = json.loads(
                candidato_registro.read_text(
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

        if candidato.get("estado") != "candidato":
            raise ValueError(
                "estado_do_candidato_invalido"
            )

        if candidato.get("avaliacao", {}).get(
            "aprovado"
        ) is not True:
            raise ValueError(
                "candidato_sem_avaliacao_aprovada"
            )

        arquivo = candidato.get("arquivo")

        if not isinstance(arquivo, str) or not arquivo:
            raise ValueError(
                "arquivo_do_candidato_invalido"
            )

        caminho_origem = candidato_dir / arquivo

        if not caminho_origem.is_file():
            raise FileNotFoundError(
                "arquivo_do_candidato_nao_encontrado"
            )

        destino = Path(arquivo)

        if (
            destino.is_absolute()
            or ".." in destino.parts
        ):
            raise ValueError(
                "destino_do_candidato_invalido"
            )

        return {
            "proposta": proposta,
            "candidato": candidato,
            "candidato_dir": candidato_dir,
            "origem": caminho_origem,
            "destino": destino,
        }

    def preparar(
        self,
        *,
        proposta_path: str | Path,
        autorizacao_explicita: bool = False,
        stable: str = BRANCH_STABLE_PADRAO,
        branch_integracao: str | None = None,
    ) -> dict:
        proposta_path = Path(proposta_path)

        dados = self._validar_proposta(
            proposta_path,
            autorizacao_explicita,
            stable,
        )

        proposta = dados["proposta"]
        candidato = dados["candidato"]
        origem = dados["origem"]
        destino = dados["destino"]

        proposta_id = proposta.get("proposta_id")

        if not isinstance(proposta_id, str) or not proposta_id:
            raise ValueError("proposta_id_invalido")

        branch = branch_integracao or (
            f"{self.PREFIXO_BRANCH}/{proposta_id}"
        )

        self._validar_nome_branch(branch)

        if branch == stable:
            raise ValueError(
                "branch_de_integracao_nao_pode_ser_stable"
            )

        arvore = self._git(
            "status",
            "--porcelain",
        )

        if arvore:
            raise RuntimeError(
                "arvore_git_suja"
            )

        branch_atual = self._git(
            "branch",
            "--show-current",
        )

        if branch_atual != stable:
            raise RuntimeError(
                "branch_atual_nao_e_stable"
            )

        existente = self._git(
            "branch",
            "--list",
            branch,
        )

        if existente:
            raise FileExistsError(
                "branch_de_integracao_ja_existente"
            )

        self._git(
            "switch",
            "-c",
            branch,
            stable,
        )

        destino_absoluto = (
            self.repositorio / destino
        )

        destino_absoluto.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            origem,
            destino_absoluto,
        )

        self._git(
            "add",
            "--",
            str(destino),
        )

        diff = self._git(
            "diff",
            "--cached",
            "--name-only",
        )

        if diff.splitlines() != [str(destino)]:
            self._git(
                "reset",
                "--",
                str(destino),
            )
            self._git(
                "switch",
                stable,
            )
            raise RuntimeError(
                "diff_de_integracao_inesperado"
            )

        mensagem = (
            f"feat: integra candidato {proposta_id}"
        )

        commit_sha = self._git(
            "commit",
            "-m",
            mensagem,
        )

        return {
            "versao_integracao": self.VERSAO,
            "estado": "integracao_preparada",
            "criada_em": self._timestamp(),
            "proposta_id": proposta_id,
            "candidato_id": candidato.get(
                "candidato_id"
            ),
            "stable": stable,
            "branch_integracao": branch,
            "arquivo_integrado": str(destino),
            "commit_integracao": commit_sha,
            "stable_modificada": False,
            "push_executado": False,
            "pr_criada": False,
            "merge_executado": False,
        }


if __name__ == "__main__":
    print(
        "IntegracaoControladaDesenvolvimentoNixal OK"
    )
