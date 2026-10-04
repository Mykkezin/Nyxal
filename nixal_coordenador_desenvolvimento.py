#!/usr/bin/env python3

"""
NIXAL / NYXAL — COORDENADOR DE DESENVOLVIMENTO

Responsabilidade:
    observar o estado Git da branch de desenvolvimento,
    sincronizar somente por fast-forward,
    validar os arquivos Python alterados
    e executar os testes Python explicitamente
    identificados pelo prefixo "teste_".

Este componente NÃO:
    - escreve código automaticamente;
    - faz merge;
    - força refs;
    - altera main;
    - executa comandos arbitrários;
    - publica alterações sozinho.

Objetivo:
    criar um ciclo local de desenvolvimento
    observável, controlado e reversível.

Fluxo:
    estado
      ↓
    sincronização
      ↓
    descoberta dos arquivos alterados
      ↓
    validação de sintaxe
      ↓
    execução dos testes
      ↓
    resultado verificável
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

        self.python = (
            self.repositorio
            / ".venv"
            / "bin"
            / "python"
        )

    # ==========================================================
    # GIT
    # ==========================================================

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

    # ==========================================================
    # ESTADO
    # ==========================================================

    def estado(self) -> dict:
        status = self._git(
            "status",
            "--porcelain",
        )

        branch_atual = self._git(
            "branch",
            "--show-current",
        )

        return {
            "repositorio": str(
                self.repositorio
            ),
            "branch_atual": branch_atual,
            "branch_alvo": self.branch,
            "arvore_limpa": not bool(status),
            "status": (
                status.splitlines()
                if status
                else []
            ),
        }

    # ==========================================================
    # SINCRONIZAÇÃO
    # ==========================================================

    def sincronizar(self) -> dict:
        estado = self.estado()

        if not estado["arvore_limpa"]:
            return {
                **estado,
                "estado": "bloqueada_arvore_suja",
                "sincronizado": False,
            }

        if (
            estado["branch_atual"]
            != self.branch
        ):
            return {
                **estado,
                "estado": "bloqueada_branch_incorreta",
                "sincronizado": False,
            }

        self._git(
            "fetch",
            "origin",
            self.branch,
        )

        contagem = self._git(
            "rev-list",
            "--left-right",
            "--count",
            f"HEAD...origin/{self.branch}",
        )

        partes = contagem.split()

        if len(partes) != 2:
            raise RuntimeError(
                "Resposta inesperada do Git "
                f"ao comparar branches: {contagem}"
            )

        commits_locais = int(
            partes[0]
        )

        commits_remotos = int(
            partes[1]
        )

        # ------------------------------------------------------
        # DIVERGÊNCIA
        # ------------------------------------------------------

        if (
            commits_locais > 0
            and commits_remotos > 0
        ):
            return {
                **estado,
                "estado": "divergencia_detectada",
                "sincronizado": False,
                "commits_locais": commits_locais,
                "commits_remotos": commits_remotos,
            }

        # ------------------------------------------------------
        # JÁ SINCRONIZADO
        # ------------------------------------------------------

        if commits_remotos == 0:
            return {
                **estado,
                "estado": "ja_sincronizado",
                "sincronizado": True,
                "commits_locais": commits_locais,
                "commits_remotos": 0,
            }

        # ------------------------------------------------------
        # FAST-FORWARD
        # ------------------------------------------------------

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

    # ==========================================================
    # ARQUIVOS ALTERADOS
    # ==========================================================

    def arquivos_ultimo_commit(self) -> list[str]:
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
            if arquivo.strip()
        ]

    def arquivos_python_ultimo_commit(
        self,
    ) -> list[str]:
        return [
            arquivo
            for arquivo in self.arquivos_ultimo_commit()
            if arquivo.endswith(".py")
        ]

    def testes_python_ultimo_commit(
        self,
    ) -> list[str]:
        return [
            arquivo
            for arquivo
            in self.arquivos_python_ultimo_commit()
            if Path(arquivo).name.startswith(
                "teste_"
            )
        ]

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    def validar_python_alterado(
        self,
    ) -> dict:
        arquivos = (
            self.arquivos_python_ultimo_commit()
        )

        resultados = []

        if not self.python.exists():
            return {
                "estado": (
                    "python_virtualenv_nao_encontrado"
                ),
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
                    "sucesso": (
                        resultado.returncode == 0
                    ),
                    "erro": (
                        resultado.stderr.strip()
                    ),
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

    # ==========================================================
    # TESTES
    # ==========================================================

    def executar_testes_alterados(
        self,
    ) -> dict:
        testes = (
            self.testes_python_ultimo_commit()
        )

        resultados = []

        if not testes:
            return {
                "estado": "nenhum_teste_alterado",
                "testes_python": [],
                "sucesso": True,
            }

        if not self.python.exists():
            return {
                "estado": (
                    "python_virtualenv_nao_encontrado"
                ),
                "testes_python": [],
                "sucesso": False,
            }

        for teste in testes:
            try:
                resultado = subprocess.run(
                    [
                        str(self.python),
                        teste,
                    ],
                    cwd=self.repositorio,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=120,
                )

                resultados.append(
                    {
                        "arquivo": teste,
                        "sucesso": (
                            resultado.returncode == 0
                        ),
                        "codigo_saida": (
                            resultado.returncode
                        ),
                        "saida": (
                            resultado.stdout.strip()
                        ),
                        "erro": (
                            resultado.stderr.strip()
                        ),
                    }
                )

            except subprocess.TimeoutExpired as erro:
                resultados.append(
                    {
                        "arquivo": teste,
                        "sucesso": False,
                        "codigo_saida": None,
                        "saida": (
                            erro.stdout.strip()
                            if isinstance(
                                erro.stdout,
                                str,
                            )
                            else ""
                        ),
                        "erro": (
                            "timeout de 120 segundos"
                        ),
                    }
                )

        return {
            "estado": "testes_concluidos",
            "testes_python": resultados,
            "sucesso": all(
                item["sucesso"]
                for item in resultados
            ),
        }

    # ==========================================================
    # CICLO COMPLETO
    # ==========================================================

    def executar_ciclo(self) -> dict:
        sincronizacao = (
            self.sincronizar()
        )

        if not sincronizacao[
            "sincronizado"
        ]:
            return {
                "sincronizacao": sincronizacao,
                "arquivos": None,
                "validacao": None,
                "testes": None,
                "ciclo_sucesso": False,
            }

        arquivos = (
            self.arquivos_ultimo_commit()
        )

        validacao = (
            self.validar_python_alterado()
        )

        if not validacao["sucesso"]:
            return {
                "sincronizacao": sincronizacao,
                "arquivos": arquivos,
                "validacao": validacao,
                "testes": None,
                "ciclo_sucesso": False,
            }

        testes = (
            self.executar_testes_alterados()
        )

        return {
            "sincronizacao": sincronizacao,
            "arquivos": arquivos,
            "validacao": validacao,
            "testes": testes,
            "ciclo_sucesso": (
                validacao["sucesso"]
                and testes["sucesso"]
            ),
        }


# ==============================================================
# EXECUÇÃO DIRETA
# ==============================================================

if __name__ == "__main__":
    coordenador = (
        CoordenadorDesenvolvimentoNixal()
    )

    try:
        resultado = (
            coordenador.executar_ciclo()
        )

        print(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
            )
        )

    except Exception as erro:
        print(
            json.dumps(
                {
                    "estado": (
                        "erro_no_ciclo"
                    ),
                    "erro": str(erro),
                    "ciclo_sucesso": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
