#!/usr/bin/env python3

"""
NIXAL / NYXAL — OBSERVADOR DE DESENVOLVIMENTO

Observa continuamente a branch de desenvolvimento e coordena:
    1. sincronização Git controlada;
    2. validação dos arquivos alterados;
    3. testes alterados;
    4. pipeline de entrada de artefatos externos.

Limites:
    - não faz merge;
    - não altera main;
    - não força refs;
    - não publica;
    - não executa código recebido pelo pipeline de entrada.

Fluxo:
    observação
        ↓
    coordenador Git
        ↓
    validação/testes
        ↓
    pipeline incoming
        ↓
    resultado
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nixal_coordenador_desenvolvimento import (
    CoordenadorDesenvolvimentoNixal,
)
from nixal_pipeline_desenvolvimento import (
    PipelineDesenvolvimentoNixal,
)


class ObservadorDesenvolvimentoNixal:
    VERSAO_NIVEL10 = "10.1.0"
    FONTE_NIVEL10 = "observador_desenvolvimento_nixal"
    ESTADOS_NIVEL10 = {"observado", "alteracao_detectada"}
    SHA_RE_NIVEL10 = re.compile(r"^[0-9a-f]{40}$")

    def __init__(
        self,
        repositorio: str | Path | None = None,
        branch: str = "desenvolvimento/mcp-bridge",
        intervalo: float = 30.0,
        estado_path: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )

        self.branch = branch
        self.intervalo = float(intervalo)

        self.coordenador = (
            CoordenadorDesenvolvimentoNixal(
                repositorio=self.repositorio,
                branch=self.branch,
            )
        )

        self.pipeline = (
            PipelineDesenvolvimentoNixal(
                repositorio=self.repositorio,
            )
        )

        if estado_path is None:
            estado_path = (
                self.repositorio.parent
                / "Nyxal-reports"
                / "nivel10"
                / f"{self._nome_arquivo_branch_nivel10(self.branch)}.json"
            )

        self.estado_path_nivel10 = Path(
            estado_path
        ).resolve()
        self.estado_path_nivel10.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.ativo = True
        self.ultimo_estado: dict | None = None

    @staticmethod
    def _timestamp_nivel10() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _nome_arquivo_branch_nivel10(
        branch: str,
    ) -> str:
        normalizado = []
        for caractere in branch:
            if caractere.isalnum() or caractere in {"-", "_"}:
                normalizado.append(caractere)
            else:
                normalizado.append("_")
        nome = "".join(normalizado).strip("_")
        return nome or "branch"

    @classmethod
    def _validar_sha_nivel10(
        cls,
        valor: Any,
        nome: str,
    ) -> str:
        if not isinstance(valor, str):
            raise ValueError(f"{nome}_invalido")
        valor = valor.strip().lower()
        if not cls.SHA_RE_NIVEL10.fullmatch(valor):
            raise ValueError(f"{nome}_invalido")
        return valor

    @staticmethod
    def _validar_texto_nivel10(
        valor: Any,
        nome: str,
    ) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    def _git_nivel10(self, *args: str) -> str:
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

    def _commit_atual_nivel10(self) -> str:
        saida = self._git_nivel10(
            "rev-parse",
            "--verify",
            f"refs/heads/{self.branch}",
        )
        return self._validar_sha_nivel10(
            saida,
            "commit_atual",
        )

    @staticmethod
    def _ciclo_id_nivel10(
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

    def _carregar_estado_nivel10(
        self,
    ) -> dict[str, Any] | None:
        if not self.estado_path_nivel10.exists():
            return None

        try:
            estado = json.loads(
                self.estado_path_nivel10.read_text(
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

        self._validar_estado_nivel10(estado)
        return estado

    def _salvar_estado_nivel10(
        self,
        estado: dict[str, Any],
    ) -> None:
        self._validar_estado_nivel10(estado)

        temporario = self.estado_path_nivel10.with_name(
            self.estado_path_nivel10.name + ".tmp"
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
            self.estado_path_nivel10
        )

    @classmethod
    def _validar_estado_nivel10(
        cls,
        estado: dict[str, Any],
    ) -> None:
        if not isinstance(estado, dict):
            raise ValueError(
                "estado_observador_invalido"
            )

        if estado.get("versao") != cls.VERSAO_NIVEL10:
            raise ValueError(
                "versao_estado_observador_invalida"
            )

        branch = cls._validar_texto_nivel10(
            estado.get("branch"),
            "branch",
        )
        commit_observado = cls._validar_sha_nivel10(
            estado.get("ultimo_commit_observado"),
            "ultimo_commit_observado",
        )

        estado_atual = estado.get("estado")
        if estado_atual not in cls.ESTADOS_NIVEL10:
            raise ValueError(
                "estado_observador_invalido"
            )

        historico = estado.get("historico_ciclos")
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

            anterior = cls._validar_sha_nivel10(
                ciclo.get("commit_anterior"),
                f"ciclo_commit_anterior:{indice}",
            )
            novo = cls._validar_sha_nivel10(
                ciclo.get("commit_novo"),
                f"ciclo_commit_novo:{indice}",
            )
            if ciclo.get("estado") != "alteracao_detectada":
                raise ValueError(
                    f"ciclo_estado_invalido:{indice}"
                )

            esperado = cls._ciclo_id_nivel10(
                branch=branch,
                commit_anterior=anterior,
                commit_novo=novo,
            )
            if ciclo.get("ciclo_id") != esperado:
                raise ValueError(
                    f"ciclo_id_invalido:{indice}"
                )

        if historico:
            if historico[-1]["commit_novo"] != commit_observado:
                raise ValueError(
                    "ultimo_commit_inconsistente"
                )

        if estado_atual == "alteracao_detectada" and not historico:
            raise ValueError("alteracao_sem_ciclo")

        if estado_atual == "observado" and historico:
            raise ValueError("estado_observado_com_historico")

        ciclo_atual = estado.get("ciclo_atual")
        if ciclo_atual is not None:
            if not isinstance(ciclo_atual, dict):
                raise ValueError("ciclo_atual_invalido")
            if (
                not historico
                or ciclo_atual.get("ciclo_id")
                != historico[-1].get("ciclo_id")
            ):
                raise ValueError("ciclo_atual_invalido")

    def observar_nivel10(self) -> dict[str, Any]:
        """
        Executa somente a detecção formal Nível 10.

        A primeira observação estabelece o ponto de partida. Alterações
        posteriores geram um ciclo auditável. Nenhuma operação altera refs Git.
        """
        commit_atual = self._commit_atual_nivel10()
        estado = self._carregar_estado_nivel10()

        if estado is None:
            agora = self._timestamp_nivel10()
            novo_estado = {
                "versao": self.VERSAO_NIVEL10,
                "fonte": self.FONTE_NIVEL10,
                "branch": self.branch,
                "estado": "observado",
                "criado_em": agora,
                "atualizado_em": agora,
                "ultimo_commit_observado": commit_atual,
                "historico_ciclos": [],
                "ciclo_atual": None,
            }
            self._salvar_estado_nivel10(novo_estado)
            return {
                "estado": "observado",
                "alteracao_detectada": False,
                "branch": self.branch,
                "commit_observado": commit_atual,
                "ciclo": None,
                "estado_path": str(
                    self.estado_path_nivel10
                ),
            }

        branch_registrada = self._validar_texto_nivel10(
            estado.get("branch"),
            "branch",
        )
        if branch_registrada != self.branch:
            raise ValueError(
                "branch_do_estado_diferente"
            )

        anterior = self._validar_sha_nivel10(
            estado.get("ultimo_commit_observado"),
            "ultimo_commit_observado",
        )

        if commit_atual == anterior:
            return {
                "estado": estado["estado"],
                "alteracao_detectada": False,
                "branch": self.branch,
                "commit_observado": commit_atual,
                "ciclo": None,
                "estado_path": str(
                    self.estado_path_nivel10
                ),
            }

        ciclo = {
            "ciclo_id": self._ciclo_id_nivel10(
                branch=self.branch,
                commit_anterior=anterior,
                commit_novo=commit_atual,
            ),
            "branch": self.branch,
            "commit_anterior": anterior,
            "commit_novo": commit_atual,
            "estado": "alteracao_detectada",
            "detectado_em": self._timestamp_nivel10(),
        }

        historico = estado.setdefault(
            "historico_ciclos",
            [],
        )
        if any(
            isinstance(item, dict)
            and item.get("ciclo_id") == ciclo["ciclo_id"]
            for item in historico
        ):
            raise ValueError(
                "ciclo_duplicado_no_historico"
            )

        historico.append(ciclo)
        estado["estado"] = "alteracao_detectada"
        estado["ultimo_commit_observado"] = commit_atual
        estado["ciclo_atual"] = deepcopy(ciclo)
        estado["atualizado_em"] = self._timestamp_nivel10()

        self._salvar_estado_nivel10(estado)

        return {
            "estado": "alteracao_detectada",
            "alteracao_detectada": True,
            "branch": self.branch,
            "commit_anterior": anterior,
            "commit_novo": commit_atual,
            "ciclo": deepcopy(ciclo),
            "estado_path": str(
                self.estado_path_nivel10
            ),
        }

    def observar(self) -> dict[str, Any]:
        """Alias curto para uma observação formal Nível 10."""
        return self.observar_nivel10()

    def parar(self) -> None:
        """Solicita encerramento do observador."""
        self.ativo = False

    def ciclo(self) -> dict:
        """Executa uma única verificação Git + pipeline."""
        desenvolvimento = (
            self.coordenador.executar_ciclo()
        )

        pipeline = (
            self.pipeline.executar_ciclo()
        )

        resultado = {
            "desenvolvimento": desenvolvimento,
            "pipeline": pipeline,
            "ciclo_sucesso": (
                desenvolvimento["ciclo_sucesso"]
                and pipeline["estado"]
                in {
                    "nenhum_artefato",
                    "processamento_concluido",
                }
            ),
        }

        self.ultimo_estado = resultado

        return resultado

    def iniciar(self) -> None:
        """Executa observação contínua."""
        print(
            json.dumps(
                {
                    "estado": "observador_iniciado",
                    "repositorio": str(
                        self.repositorio
                    ),
                    "branch": self.branch,
                    "intervalo_segundos": self.intervalo,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        while self.ativo:
            inicio = time.monotonic()

            try:
                resultado = self.ciclo()

                print(
                    json.dumps(
                        resultado,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    flush=True,
                )

            except Exception as erro:
                erro_resultado = {
                    "estado": "erro_no_observador",
                    "erro": str(erro),
                    "ciclo_sucesso": False,
                }

                self.ultimo_estado = (
                    erro_resultado
                )

                print(
                    json.dumps(
                        erro_resultado,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    flush=True,
                )

            decorrido = (
                time.monotonic() - inicio
            )

            restante = max(
                0.0,
                self.intervalo - decorrido,
            )

            if self.ativo and restante > 0:
                time.sleep(restante)


if __name__ == "__main__":
    observador = (
        ObservadorDesenvolvimentoNixal(
            intervalo=30.0,
        )
    )

    try:
        observador.iniciar()

    except KeyboardInterrupt:
        observador.parar()

        print(
            json.dumps(
                {
                    "estado": "observador_encerrado"
                },
                ensure_ascii=False,
                indent=2,
            )
        )
