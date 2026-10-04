#!/usr/bin/env python3
"""
NYXAL — OBSERVADOR DE DESENVOLVIMENTO

Nível 10 — primeiro componente operacional.

Responsabilidade:
    observar uma branch explicitamente configurada, comparar seu commit
    atual com o último commit observado e abrir um ciclo auditável quando
    houver alteração.

Este módulo é somente observacional:
- não faz checkout;
- não cria branch;
- não faz merge;
- não modifica refs Git;
- não executa código;
- não instala dependências;
- não interpreta uma alteração como autorização.

O estado persistente fica fora da árvore Git por padrão.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ObservadorDesenvolvimentoNixal:
    VERSAO = "10.1.0"
    FONTE = "observador_desenvolvimento_nixal"

    ESTADOS = {
        "observado",
        "alteracao_detectada",
    }

    SHA_RE = re.compile(r"^[0-9a-f]{40}$")

    def __init__(
        self,
        *,
        repositorio: str | Path,
        branch: str,
        estado_path: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(repositorio).resolve()
        if not self.repositorio.is_dir():
            raise FileNotFoundError("repositorio_nao_encontrado")

        if not isinstance(branch, str) or not branch.strip():
            raise ValueError("branch_invalida")

        self.branch = branch.strip()

        if estado_path is None:
            estado_path = (
                self.repositorio.parent
                / "Nyxal-reports"
                / "nivel10"
                / f"{self._nome_arquivo_branch(self.branch)}.json"
            )

        self.estado_path = Path(estado_path).resolve()
        self.estado_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _nome_arquivo_branch(branch: str) -> str:
        normalizado = []
        for caractere in branch:
            if caractere.isalnum() or caractere in {"-", "_"}:
                normalizado.append(caractere)
            else:
                normalizado.append("_")
        nome = "".join(normalizado).strip("_")
        return nome or "branch"

    @classmethod
    def _validar_sha(cls, valor: Any, nome: str) -> str:
        if not isinstance(valor, str):
            raise ValueError(f"{nome}_invalido")
        valor = valor.strip().lower()
        if not cls.SHA_RE.fullmatch(valor):
            raise ValueError(f"{nome}_invalido")
        return valor

    @staticmethod
    def _validar_texto(valor: Any, nome: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    def _git(self, *args: str) -> str:
        processo = subprocess.run(
            ["git", *args],
            cwd=self.repositorio,
            text=True,
            capture_output=True,
            check=False,
        )

        if processo.returncode != 0:
            detalhe = processo.stderr.strip()
            raise RuntimeError(
                f"git {' '.join(args)} falhou"
                + (f": {detalhe}" if detalhe else "")
            )

        return processo.stdout.strip()

    def _commit_atual(self) -> str:
        saida = self._git(
            "rev-parse",
            "--verify",
            f"refs/heads/{self.branch}",
        )
        return self._validar_sha(
            saida,
            "commit_atual",
        )

    @staticmethod
    def _ciclo_id(
        *,
        branch: str,
        commit_anterior: str,
        commit_novo: str,
    ) -> str:
        canonico = json.dumps(
            {
                "branch": branch,
                "commit_anterior": commit_anterior,
                "commit_novo": commit_novo,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()[:20]
        return f"n10-{digest}"

    def _carregar_estado(self) -> dict[str, Any] | None:
        if not self.estado_path.exists():
            return None

        try:
            estado = json.loads(
                self.estado_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError(
                "estado_observador_invalido"
            ) from erro

        if not isinstance(estado, dict):
            raise ValueError(
                "estado_observador_invalido"
            )

        self._validar_estado(estado)
        return estado

    def _salvar_estado(
        self,
        estado: dict[str, Any],
    ) -> None:
        self._validar_estado(estado)

        temporario = self.estado_path.with_name(
            self.estado_path.name + ".tmp"
        )

        temporario.write_text(
            json.dumps(
                estado,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporario.replace(
            self.estado_path
        )

    @classmethod
    def _validar_estado(
        cls,
        estado: dict[str, Any],
    ) -> None:
        if not isinstance(estado, dict):
            raise ValueError(
                "estado_observador_invalido"
            )

        if estado.get("versao") != cls.VERSAO:
            raise ValueError(
                "versao_estado_observador_invalida"
            )

        branch = cls._validar_texto(
            estado.get("branch"),
            "branch",
        )

        commit_observado = cls._validar_sha(
            estado.get("ultimo_commit_observado"),
            "ultimo_commit_observado",
        )

        estado_atual = estado.get("estado")
        if estado_atual not in cls.ESTADOS:
            raise ValueError(
                "estado_observador_invalido"
            )

        historico = estado.get(
            "historico_ciclos"
        )
        if not isinstance(historico, list):
            raise ValueError(
                "historico_ciclos_invalido"
            )

        for indice, ciclo in enumerate(historico):
            if not isinstance(ciclo, dict):
                raise ValueError(
                    f"ciclo_invalido:{indice}"
                )

            if ciclo.get("branch") != branch:
                raise ValueError(
                    f"ciclo_branch_invalida:{indice}"
                )

            cls._validar_sha(
                ciclo.get("commit_anterior"),
                f"ciclo_commit_anterior:{indice}",
            )
            cls._validar_sha(
                ciclo.get("commit_novo"),
                f"ciclo_commit_novo:{indice}",
            )

            if ciclo.get("estado") != "alteracao_detectada":
                raise ValueError(
                    f"ciclo_estado_invalido:{indice}"
                )

            ciclo_id = cls._ciclo_id(
                branch=branch,
                commit_anterior=ciclo[
                    "commit_anterior"
                ],
                commit_novo=ciclo[
                    "commit_novo"
                ],
            )
            if ciclo.get("ciclo_id") != ciclo_id:
                raise ValueError(
                    f"ciclo_id_invalido:{indice}"
                )

        if historico:
            ultimo_ciclo = historico[-1]
            if (
                ultimo_ciclo["commit_novo"]
                != commit_observado
            ):
                raise ValueError(
                    "ultimo_commit_inconsistente"
                )

        if estado_atual == "alteracao_detectada":
            if not historico:
                raise ValueError(
                    "alteracao_sem_ciclo"
                )

        if estado_atual == "observado":
            if historico:
                raise ValueError(
                    "estado_observado_com_historico"
                )

        ciclo_atual = estado.get(
            "ciclo_atual"
        )
        if ciclo_atual is not None:
            if not isinstance(ciclo_atual, dict):
                raise ValueError(
                    "ciclo_atual_invalido"
                )
            if (
                not historico
                or ciclo_atual.get("ciclo_id")
                != historico[-1].get("ciclo_id")
            ):
                raise ValueError(
                    "ciclo_atual_invalido"
                )

    def observar(self) -> dict[str, Any]:
        commit_atual = self._commit_atual()
        estado = self._carregar_estado()

        if estado is None:
            agora = self._timestamp()
            estado = {
                "versao": self.VERSAO,
                "fonte": self.FONTE,
                "branch": self.branch,
                "estado": "observado",
                "criado_em": agora,
                "atualizado_em": agora,
                "ultimo_commit_observado": commit_atual,
                "historico_ciclos": [],
                "ciclo_atual": None,
            }
            self._salvar_estado(estado)
            return deepcopy({
                "estado": "observado",
                "alteracao_detectada": False,
                "branch": self.branch,
                "commit_observado": commit_atual,
                "ciclo": None,
                "estado_path": str(self.estado_path),
            })

        branch_registrada = self._validar_texto(
            estado.get("branch"),
            "branch",
        )
        if branch_registrada != self.branch:
            raise ValueError(
                "branch_do_estado_diferente"
            )

        anterior = self._validar_sha(
            estado.get("ultimo_commit_observado"),
            "ultimo_commit_observado",
        )

        if commit_atual == anterior:
            return deepcopy({
                "estado": estado["estado"],
                "alteracao_detectada": False,
                "branch": self.branch,
                "commit_observado": commit_atual,
                "ciclo": None,
                "estado_path": str(self.estado_path),
            })

        ciclo_id = self._ciclo_id(
            branch=self.branch,
            commit_anterior=anterior,
            commit_novo=commit_atual,
        )

        ciclo = {
            "ciclo_id": ciclo_id,
            "branch": self.branch,
            "commit_anterior": anterior,
            "commit_novo": commit_atual,
            "estado": "alteracao_detectada",
            "detectado_em": self._timestamp(),
        }

        historico = estado.setdefault(
            "historico_ciclos",
            [],
        )
        if not isinstance(historico, list):
            raise ValueError(
                "historico_ciclos_invalido"
            )

        if any(
            isinstance(item, dict)
            and item.get("ciclo_id") == ciclo_id
            for item in historico
        ):
            raise ValueError(
                "ciclo_duplicado_no_historico"
            )

        historico.append(ciclo)
        estado["estado"] = "alteracao_detectada"
        estado["ultimo_commit_observado"] = commit_atual
        estado["ciclo_atual"] = deepcopy(ciclo)
        estado["atualizado_em"] = self._timestamp()

        self._salvar_estado(estado)

        return deepcopy({
            "estado": "alteracao_detectada",
            "alteracao_detectada": True,
            "branch": self.branch,
            "commit_anterior": anterior,
            "commit_novo": commit_atual,
            "ciclo": deepcopy(ciclo),
            "estado_path": str(self.estado_path),
        })


if __name__ == "__main__":
    print("ObservadorDesenvolvimentoNixal OK")
