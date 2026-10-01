#!/usr/bin/env python3

"""
NIXAL / NYXAL — COORDENADOR DE DESENVOLVIMENTO

Responsabilidade:
    observar o estado Git da branch de desenvolvimento,
    sincronizar somente por fast-forward e validar os arquivos
    Python alterados no último avanço.

Este componente NÃO:
    - escreve código automaticamente;
    - faz merge;
    - força refs;
    - altera main;
    - executa comandos arbitrários vindos do repositório;
    - publica alterações sozinho.

Objetivo:
    criar um ciclo local de desenvolvimento observável,
    controlado e reversível.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


class CoordenadorDesenvolvimentoNixal:
    def __init__(
        self,
        repositorio: str | Path | None = None,
        branch: str = "desenvolvimento/mcp-bridge",
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )
        self.branch = branch

        self.python = self.repositorio / ".venv" / "bin" / "python"

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

    def estado(self) -> dict:
        status = self._git("status", "--porcelain")
        branch_atual = self._git("branch", "--show-current")

        return {
            "repositorio": str(self.repositorio),
            "branch_atual": branch_atual,
            "branch_alvo": self.branch,
            "arvore_limpa": not bool(status),
            "status": status.splitlines() if status else [],
        }

    def sincronizar(self) -> dict:
        estado = self.estado()

        if not estado["arvore_limpa"]:
            return {
                **estado,
                "estado": "bloqueada_arvore_suja",
                "sincronizado": False,
            }

        if estado["branch_atual"] != self.branch:
            return {
                **estado,
                "estado": "bloqueada_branch_incorreta",
                "sincronizado": False,
            }

        self._git("fetch", "origin", self.branch)

        contagem = self._git(
            "rev-list",
            "--left-right",
            "--count",
            f"HEAD...origin/{self.branch}",
        )

        partes = contagem.split()

        if len(partes) != 2:
            raise RuntimeError(
                f"Resposta inesperada de rev-list: {contagem}"
            )

        commits_locais = int(partes[0])
        commits_remotos = int(partes[1])

        if commits_locais > 0 and commits_remotos > 0:
            return {
                **estado,
                "estado": "divergencia_detectada",
                "sincronizado": False,
                "commits_locais": commits_locais,
                "commits_remotos": commits_remotos,
            }

        if commits_remotos == 0:
            return {
                **estado,
                "estado": "ja_sincronizado",
                "sincronizado": True,
                "commits_locais": commits_locais,
                "commits_remotos": 0,
            }

        self._git(
            "pull",
            "--ff-only",
            "origin",
            self.branch,
        )

        return {
            **estado,
            "estado": "sincronizado_fast_forward",
            "sincronizado": True,
            "commits_locais": commits_locais,
            "commits_remotos": commits_remotos,
        }

    def arquivos_python_ultimo_commit(self) -> list[str]:
        try:
            alterados = self._git(
                "diff",
                "--name-only",
                "HEAD^",
                "HEAD",
            )
        except RuntimeError:
            return []

        return [
            arquivo
            for arquivo in alterados.splitlines()
            if arquivo.endswith(".py")
        ]

    def validar_python_alterado(self) -> dict:
        arquivos = self.arquivos_python_ultimo_commit()

        resultados = []

        if not self.python.exists():
            return {
                "estado": "python_virtualenv_nao_encontrado",
                "arquivos_python": [],
                "sucesso": False,
            }

        for arquivo in arquivos:
            resultado = subprocess.run(
                [
                    str(self.python),
                    "-m",
                    "py_compile",
                    arquivo,
                ],
                cwd=self.repositorio,
                text=True,
                capture_output=True,
                check=False,
            )

            resultados.append(
                {
                    "arquivo": arquivo,
                    "sucesso": resultado.returncode == 0,
                    "erro": resultado.stderr.strip(),
                }
            )

        return {
            "estado": "validacao_concluida",
            "arquivos_python": resultados,
            "sucesso": all(
                item["sucesso"]
                for item in resultados
            ),
        }

    def executar_ciclo(self) -> dict:
        sincronizacao = self.sincronizar()

        if not sincronizacao["sincronizado"]:
            return {
                "sincronizacao": sincronizacao,
                "validacao": None,
            }

        validacao = self.validar_python_alterado()

        return {
            "sincronizacao": sincronizacao,
            "validacao": validacao,
        }


if __name__ == "__main__":
    coordenador = CoordenadorDesenvolvimentoNixal()

    print(
        json.dumps(
            coordenador.executar_ciclo(),
            ensure_ascii=False,
            indent=2,
        )
    )
