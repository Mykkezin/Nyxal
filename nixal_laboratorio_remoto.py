#!/usr/bin/env python3
"""
NYXAL — CONTROLADOR DO LABORATÓRIO REMOTO

M4 / Nível 9 — ponte local entre Evolução Controlada e GitHub Actions.

Responsabilidade:
    publicar um experimento em branch isolada, disparar o workflow
    confiável do laboratório e recuperar resultado/logs.

Princípios:
- não usa force push;
- nunca escreve em stable;
- nunca executa o experimento localmente;
- publica somente a árvore experimento/;
- exige token separado para a API do GitHub;
- o workflow é disparado a partir da branch confiável;
- resultado experimental é evidência, não autorização de integração.

Observação:
    esta camada depende da infraestrutura .github/workflows/nyxal-remote-lab.yml
    estar disponível na branch padrão do repositório.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib import error, parse, request


class LaboratorioRemotoNixal:
    VERSAO = "1.0"
    FONTE = "nyxal_laboratorio_remoto"
    WORKFLOW = "nyxal-remote-lab.yml"

    def __init__(
        self,
        repositorio: str | Path | None = None,
        github_repo: str = "Mykkezin/Nyxal",
        remote: str = "origin",
        token_env: str = "NYXAL_GITHUB_TOKEN",
        workflow_ref: str = "main",
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        ).resolve()
        self.github_repo = github_repo
        self.remote = remote
        self.token_env = token_env
        self.workflow_ref = workflow_ref

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    @staticmethod
    def validar_experimento_id(experimento_id: str) -> str:
        if (
            not isinstance(experimento_id, str)
            or not experimento_id.strip()
        ):
            raise ValueError("experimento_id_invalido")

        valor = experimento_id.strip()

        if not re.fullmatch(
            r"[A-Za-z0-9._-]{1,80}",
            valor,
        ):
            raise ValueError("experimento_id_invalido")

        return valor

    @classmethod
    def branch_experimento(
        cls,
        experimento_id: str,
    ) -> str:
        return "experimento/" + cls.validar_experimento_id(
            experimento_id
        )

    @staticmethod
    def validar_arquivo_origem(
        arquivo_origem: str | Path,
    ) -> Path:
        origem = Path(arquivo_origem).resolve()

        if not origem.is_file():
            raise FileNotFoundError(
                "artefato_origem_nao_encontrado"
            )

        if origem.suffix != ".py":
            raise ValueError(
                "artefato_experimental_precisa_ser_python"
            )

        return origem

    # ==========================================================
    # GIT
    # ==========================================================

    def _git(
        self,
        *args: str,
        cwd: Path | None = None,
    ) -> str:
        resultado = subprocess.run(
            ["git", *args],
            cwd=cwd or self.repositorio,
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
                "git "
                + " ".join(args)
                + " falhou: "
                + resultado.stderr.strip()
            )

        return resultado.stdout.strip()

    def _ref_remota_existe(
        self,
        branch: str,
    ) -> bool:
        linhas = self._git(
            "ls-remote",
            "--heads",
            self.remote,
            f"refs/heads/{branch}",
        )
        return bool(linhas.strip())

    # ==========================================================
    # MANIFESTO
    # ==========================================================

    @classmethod
    def construir_manifesto(
        cls,
        *,
        experimento_id: str,
        entrypoint: str,
        timeout_seconds: int = 60,
        descricao: str = "",
    ) -> dict[str, Any]:
        experimento_id = cls.validar_experimento_id(
            experimento_id
        )

        entrada = Path(entrypoint)

        if (
            entrada.is_absolute()
            or ".." in entrada.parts
            or len(entrada.parts) < 2
            or entrada.parts[0] != "experimento"
            or entrada.suffix != ".py"
        ):
            raise ValueError(
                "entrypoint_invalido"
            )

        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or not 1 <= timeout_seconds <= 120
        ):
            raise ValueError(
                "timeout_seconds_invalido"
            )

        if not isinstance(descricao, str):
            raise ValueError(
                "descricao_invalida"
            )

        return {
            "versao": 1,
            "experimento_id": experimento_id,
            "entrypoint": entrypoint.replace("\\", "/"),
            "timeout_seconds": timeout_seconds,
            "descricao": descricao,
        }

    # ==========================================================
    # PUBLICAÇÃO
    # ==========================================================

    def publicar_experimento(
        self,
        *,
        experimento_id: str,
        arquivo_origem: str | Path,
        base_ref: str | None = None,
        descricao: str = "",
        timeout_seconds: int = 60,
        branch: str | None = None,
    ) -> dict[str, Any]:
        experimento_id = self.validar_experimento_id(
            experimento_id
        )
        origem = self.validar_arquivo_origem(
            arquivo_origem
        )

        branch = (
            branch
            if branch is not None
            else self.branch_experimento(
                experimento_id
            )
        )

        if not re.fullmatch(
            r"experimento/[A-Za-z0-9._/-]+",
            branch,
        ):
            raise ValueError(
                "branch_experimental_invalida"
            )

        if self._ref_remota_existe(branch):
            raise FileExistsError(
                "branch_experimental_ja_existe"
            )

        if base_ref is None:
            self._git(
                "fetch",
                self.remote,
                self.workflow_ref,
            )
            base = f"{self.remote}/{self.workflow_ref}"
        else:
            base = base_ref

        with tempfile.TemporaryDirectory(
            prefix="nyxal-lab-worktree-"
        ) as temporario:
            worktree = Path(temporario)

            self._git(
                "worktree",
                "add",
                "--detach",
                str(worktree),
                base,
            )

            try:
                self._git(
                    "switch",
                    "-c",
                    branch,
                    cwd=worktree,
                )

                destino = (
                    worktree
                    / "experimento"
                    / origem.name
                )
                destino.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                destino.write_bytes(
                    origem.read_bytes()
                )

                manifesto = self.construir_manifesto(
                    experimento_id=experimento_id,
                    entrypoint=f"experimento/{origem.name}",
                    timeout_seconds=timeout_seconds,
                    descricao=descricao,
                )

                manifesto_path = (
                    worktree
                    / "experimento"
                    / "manifesto.json"
                )
                manifesto_path.write_text(
                    json.dumps(
                        manifesto,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                self._git(
                    "add",
                    "--",
                    "experimento/",
                    cwd=worktree,
                )

                staged = self._git(
                    "diff",
                    "--cached",
                    "--name-only",
                    cwd=worktree,
                ).splitlines()

                permitidos = {
                    f"experimento/{origem.name}",
                    "experimento/manifesto.json",
                }

                if set(staged) != permitidos:
                    raise RuntimeError(
                        "diff_experimental_inesperado"
                    )

                self._git(
                    "commit",
                    "-m",
                    f"experiment: {experimento_id}",
                    cwd=worktree,
                )

                commit_sha = self._git(
                    "rev-parse",
                    "HEAD",
                    cwd=worktree,
                )

                self._git(
                    "push",
                    "-u",
                    self.remote,
                    branch,
                    cwd=worktree,
                )

            finally:
                self._git(
                    "worktree",
                    "remove",
                    "--force",
                    str(worktree),
                )

        return {
            "sucesso": True,
            "estado": "experimento_publicado",
            "origem": self.FONTE,
            "experimento_id": experimento_id,
            "branch": branch,
            "commit_sha": commit_sha,
            "workflow_ref": base,
            "stable_modificada": False,
            "integracao_executada": False,
            "autorizacao_explicita": False,
        }

    # ==========================================================
    # GITHUB API
    # ==========================================================

    def _token(self) -> str:
        token = os.environ.get(
            self.token_env,
            "",
        ).strip()

        if not token:
            raise RuntimeError(
                f"token_github_ausente:{self.token_env}"
            )

        return token

    def _api_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, str]:
        token = self._token()

        url = (
            "https://api.github.com"
            "/repos/"
            + self.github_repo
            + path
        )

        data = None

        if payload is not None:
            data = json.dumps(
                payload,
                ensure_ascii=False,
            ).encode("utf-8")

        req = request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "Nyxal-Laboratorio-Remoto",
                **(
                    {
                        "Content-Type": "application/json",
                    }
                    if payload is not None
                    else {}
                ),
            },
        )

        # O endpoint de logs do GitHub responde com 302 para uma URL
        # temporária em outro domínio. O Authorization não pode ser
        # propagado para esse redirecionamento, pois o destino não é
        # a API do GitHub. add_unredirected_header mantém o token na
        # requisição inicial, mas não no request redirecionado.
        req.add_unredirected_header(
            "Authorization",
            f"Bearer {token}",
        )

        try:
            with request.urlopen(
                req,
                timeout=30,
            ) as resposta:
                corpo = resposta.read().decode(
                    "utf-8"
                )
                return resposta.status, corpo

        except error.HTTPError as exc:
            corpo = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise RuntimeError(
                f"github_api_http_{exc.code}:{corpo}"
            ) from exc

    def remover_branch_experimento(
        self,
        branch: str,
    ) -> dict[str, Any]:
        if not re.fullmatch(
            r"experimento/[A-Za-z0-9._/-]+",
            branch,
        ):
            raise ValueError(
                "branch_experimental_invalida"
            )

        self._git(
            "push",
            self.remote,
            "--delete",
            branch,
        )

        return {
            "sucesso": True,
            "estado": "branch_experimental_removida",
            "origem": self.FONTE,
            "branch": branch,
            "stable_modificada": False,
        }

    # ==========================================================
    # GITHUB API
    # ==========================================================

    def disparar_workflow(
        self,
        *,
        experimento_id: str,
        experiment_ref: str,
        expected_sha: str,
    ) -> dict[str, Any]:
        experimento_id = self.validar_experimento_id(
            experimento_id
        )

        if not re.fullmatch(
            r"experimento/[A-Za-z0-9._/-]+",
            experiment_ref,
        ):
            raise ValueError(
                "experiment_ref_invalida"
            )

        if not re.fullmatch(
            r"[0-9a-f]{40}",
            expected_sha,
        ):
            raise ValueError(
                "expected_sha_invalido"
            )

        status, corpo = self._api_request(
            "POST",
            "/actions/workflows/"
            + parse.quote(
                self.WORKFLOW,
                safe="",
            )
            + "/dispatches?return_run_details=true",
            {
                "ref": self.workflow_ref,
                "inputs": {
                    "experiment_ref": experiment_ref,
                    "experiment_id": experimento_id,
                    "expected_sha": expected_sha,
                },
            },
        )

        if status not in {200, 204}:
            raise RuntimeError(
                f"workflow_dispatch_status_inesperado:{status}"
            )

        detalhes: dict[str, Any] = {}

        if corpo.strip():
            try:
                dados = json.loads(corpo)
            except json.JSONDecodeError as erro:
                raise RuntimeError(
                    "workflow_dispatch_resposta_invalida"
                ) from erro

            if isinstance(dados, dict):
                detalhes = {
                    "workflow_run_id": dados.get(
                        "workflow_run_id"
                    ),
                    "run_url": dados.get(
                        "run_url"
                    ),
                    "html_url": dados.get(
                        "html_url"
                    ),
                }

        return {
            "sucesso": True,
            "estado": "workflow_disparado",
            "origem": self.FONTE,
            "experimento_id": experimento_id,
            "experiment_ref": experiment_ref,
            "expected_sha": expected_sha,
            "workflow": self.WORKFLOW,
            "workflow_ref": self.workflow_ref,
            **{
                chave: valor
                for chave, valor in detalhes.items()
                if valor is not None
            },
        }

    def listar_execucoes(
        self,
        *,
        experimento_id: str,
        per_page: int = 20,
    ) -> list[dict[str, Any]]:
        experimento_id = self.validar_experimento_id(
            experimento_id
        )

        if not 1 <= per_page <= 100:
            raise ValueError(
                "per_page_invalido"
            )

        query = parse.urlencode(
            {
                "event": "workflow_dispatch",
                "per_page": per_page,
            }
        )

        _, corpo = self._api_request(
            "GET",
            "/actions/workflows/"
            + parse.quote(
                self.WORKFLOW,
                safe="",
            )
            + "/runs?"
            + query,
        )

        dados = json.loads(corpo)

        if not isinstance(
            dados,
            dict,
        ):
            return []

        runs = dados.get(
            "workflow_runs",
            [],
        )

        if not isinstance(
            runs,
            list,
        ):
            return []

        encontrados = []

        for run in runs:
            if not isinstance(run, dict):
                continue

            campos = " ".join(
                str(run.get(nome, ""))
                for nome in (
                    "display_title",
                    "name",
                    "path",
                )
            )

            if experimento_id in campos:
                encontrados.append(
                    deepcopy(run)
                )

        return encontrados

    def consultar_execucao(
        self,
        *,
        experimento_id: str,
    ) -> dict[str, Any] | None:
        runs = self.listar_execucoes(
            experimento_id=experimento_id,
        )

        if not runs:
            return None

        runs.sort(
            key=lambda item: str(
                item.get(
                    "created_at",
                    "",
                )
            ),
            reverse=True,
        )

        return runs[0]

    def listar_jobs(
        self,
        run_id: int,
    ) -> list[dict[str, Any]]:
        if not isinstance(
            run_id,
            int,
        ):
            raise ValueError(
                "run_id_invalido"
            )

        _, corpo = self._api_request(
            "GET",
            f"/actions/runs/{run_id}/jobs?per_page=100",
        )

        dados = json.loads(corpo)

        jobs = (
            dados.get("jobs", [])
            if isinstance(dados, dict)
            else []
        )

        return (
            [deepcopy(item) for item in jobs]
            if isinstance(jobs, list)
            else []
        )

    def baixar_logs_job(
        self,
        job_id: int,
        max_tentativas: int = 5,
        atraso_inicial: float = 3.0,
    ) -> str:
        if not isinstance(
            job_id,
            int,
        ):
            raise ValueError(
                "job_id_invalido"
            )

        if (
            not isinstance(max_tentativas, int)
            or max_tentativas < 1
        ):
            raise ValueError(
                "max_tentativas_invalido"
            )

        if (
            not isinstance(atraso_inicial, (int, float))
            or atraso_inicial < 0
        ):
            raise ValueError(
                "atraso_inicial_invalido"
            )

        for tentativa in range(max_tentativas):
            try:
                _, corpo = self._api_request(
                    "GET",
                    f"/actions/jobs/{job_id}/logs",
                )
                return corpo

            except RuntimeError as erro:
                mensagem = str(erro)

                blob_nao_disponivel = (
                    "github_api_http_404:" in mensagem
                    and "BlobNotFound" in mensagem
                )

                if (
                    not blob_nao_disponivel
                    or tentativa >= max_tentativas - 1
                ):
                    raise

                atraso = min(
                    float(atraso_inicial) * (2 ** tentativa),
                    30.0,
                )

                if atraso > 0:
                    time.sleep(atraso)

        raise RuntimeError(
            "falha_inesperada_ao_baixar_logs"
        )

    @staticmethod
    def extrair_resultado_dos_logs(
        logs: str,
    ) -> dict[str, Any] | None:
        if not isinstance(
            logs,
            str,
        ):
            return None

        marcador = "NYXAL_RESULT_JSON="

        for linha in reversed(
            logs.splitlines()
        ):
            linha = linha.strip()

            if not linha.startswith(
                marcador
            ):
                continue

            conteudo = linha[
                len(marcador):
            ]

            try:
                resultado = json.loads(
                    conteudo
                )
            except json.JSONDecodeError:
                return None

            if not isinstance(
                resultado,
                dict,
            ):
                return None

            return resultado

        return None

    def consultar_resultado(
        self,
        *,
        experimento_id: str,
    ) -> dict[str, Any] | None:
        run = self.consultar_execucao(
            experimento_id=experimento_id,
        )

        if run is None:
            return None

        run_id = run.get("id")

        if not isinstance(
            run_id,
            int,
        ):
            return {
                "sucesso": False,
                "estado": "run_id_invalido",
                "run": deepcopy(run),
            }

        jobs = self.listar_jobs(
            run_id
        )

        for job in jobs:
            job_id = job.get("id")

            if not isinstance(
                job_id,
                int,
            ):
                continue

            # Enquanto o job ainda estiver rodando, o endpoint de logs
            # pode redirecionar para um blob temporário que ainda não
            # existe. Não tentamos baixá-lo antes da conclusão.
            status_job = job.get("status")
            conclusion_job = job.get("conclusion")

            if status_job != "completed":
                return {
                    "sucesso": False,
                    "estado": "resultado_ainda_nao_disponivel",
                    "origem": self.FONTE,
                    "experimento_id": experimento_id,
                    "run": deepcopy(run),
                    "job": deepcopy(job),
                    "motivo": "job_ainda_em_execucao",
                }

            if conclusion_job is None:
                return {
                    "sucesso": False,
                    "estado": "resultado_ainda_nao_disponivel",
                    "origem": self.FONTE,
                    "experimento_id": experimento_id,
                    "run": deepcopy(run),
                    "job": deepcopy(job),
                    "motivo": "job_sem_conclusao",
                }

            try:
                logs = self.baixar_logs_job(
                    job_id
                )
            except RuntimeError as erro:
                # Logs podem demorar alguns instantes para ficar
                # disponíveis mesmo depois do job concluir.
                mensagem = str(erro)
                if (
                    "github_api_http_404:" in mensagem
                    or "BlobNotFound" in mensagem
                ):
                    return {
                        "sucesso": False,
                        "estado": "resultado_ainda_nao_disponivel",
                        "origem": self.FONTE,
                        "experimento_id": experimento_id,
                        "run": deepcopy(run),
                        "job": deepcopy(job),
                        "motivo": "logs_ainda_nao_disponiveis",
                    }
                raise

            resultado = self.extrair_resultado_dos_logs(
                logs
            )

            if resultado is not None:
                return {
                    "sucesso": True,
                    "estado": "resultado_recuperado",
                    "origem": self.FONTE,
                    "experimento_id": experimento_id,
                    "run": deepcopy(run),
                    "job": deepcopy(job),
                    "resultado": resultado,
                }

        return {
            "sucesso": False,
            "estado": "resultado_ainda_nao_disponivel",
            "origem": self.FONTE,
            "experimento_id": experimento_id,
            "run": deepcopy(run),
        }

    def aguardar_resultado(
        self,
        *,
        experimento_id: str,
        timeout_segundos: int = 300,
        intervalo_segundos: int = 5,
    ) -> dict[str, Any] | None:
        if (
            not isinstance(timeout_segundos, int)
            or timeout_segundos < 1
        ):
            raise ValueError(
                "timeout_segundos_invalido"
            )

        if (
            not isinstance(intervalo_segundos, int)
            or intervalo_segundos < 1
        ):
            raise ValueError(
                "intervalo_segundos_invalido"
            )

        limite = time.monotonic() + timeout_segundos

        while time.monotonic() < limite:
            resultado = self.consultar_resultado(
                experimento_id=experimento_id
            )

            if (
                resultado is not None
                and resultado.get("estado")
                == "resultado_recuperado"
            ):
                return resultado

            time.sleep(
                intervalo_segundos
            )

        return self.consultar_resultado(
            experimento_id=experimento_id
        )


__all__ = [
    "LaboratorioRemotoNixal",
]
