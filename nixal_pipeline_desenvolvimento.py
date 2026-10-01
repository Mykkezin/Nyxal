#!/usr/bin/env python3

"""
NYXAL — PIPELINE CONTROLADO DE DESENVOLVIMENTO

Recebe artefatos externos fora da árvore Git e os conduz por uma
primeira etapa segura:

    incoming
      ↓
    análise
      ↓
    workspace isolado
      ↓
    validação estrutural/sintaxe
      ↓
    experiments
      ↓
    candidato ou rejeitado
      ↓
    relatório

Limites desta versão:
- não executa código recebido;
- não instala dependências;
- não altera a branch atual;
- não faz merge;
- não publica;
- não promove para stable;
- não executa testes arbitrários recebidos.

A validação Python usa apenas py_compile.

Deduplicação:
- cada artefato é identificado pelo SHA-256;
- artefatos já processados ficam registrados em um estado externo;
- o mesmo conteúdo não é reprocessado enquanto permanecer no incoming;
- conteúdo novo do mesmo arquivo pode voltar ao pipeline.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


class PipelineDesenvolvimentoNixal:
    VERSAO_ESTADO = 1

    def __init__(
        self,
        repositorio: str | Path | None = None,
        entrada: str | Path | None = None,
        workspace: str | Path | None = None,
        experimentos: str | Path | None = None,
        relatorios: str | Path | None = None,
        estado: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )

        base_externa = self.repositorio.parent

        self.entrada = Path(
            entrada or base_externa / "Nyxal-incoming"
        )

        self.workspace = Path(
            workspace or base_externa / "Nyxal-workspace"
        )

        self.experimentos = Path(
            experimentos or base_externa / "Nyxal-experiments"
        )

        self.relatorios = Path(
            relatorios or base_externa / "Nyxal-reports"
        )

        self.estado_path = Path(
            estado or self.relatorios / "estado_pipeline.json"
        )

        self.python = (
            self.repositorio
            / ".venv"
            / "bin"
            / "python"
        )

        for diretorio in (
            self.entrada,
            self.workspace,
            self.experimentos,
            self.relatorios,
        ):
            diretorio.mkdir(
                parents=True,
                exist_ok=True,
            )

    def _hash_arquivo(self, caminho: Path) -> str:
        digest = hashlib.sha256()

        with caminho.open("rb") as arquivo:
            for bloco in iter(
                lambda: arquivo.read(1024 * 1024),
                b"",
            ):
                digest.update(bloco)

        return digest.hexdigest()

    def _timestamp(self) -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _carregar_estado(self) -> dict:
        if not self.estado_path.exists():
            return {
                "versao": self.VERSAO_ESTADO,
                "processados": {},
            }

        try:
            estado = json.loads(
                self.estado_path.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            return {
                "versao": self.VERSAO_ESTADO,
                "processados": {},
            }

        processados = estado.get(
            "processados",
            {},
        )

        if not isinstance(processados, dict):
            processados = {}

        return {
            "versao": self.VERSAO_ESTADO,
            "processados": processados,
        }

    def _salvar_estado(self, estado: dict) -> None:
        self.estado_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporario = self.estado_path.with_suffix(
            ".tmp"
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

    def _eh_processado(
        self,
        sha256: str,
        estado: dict,
    ) -> bool:
        return sha256 in estado["processados"]

    def _registrar_processado(
        self,
        analise: dict,
        ciclo_id: str,
        decisao: str,
    ) -> None:
        estado = self._carregar_estado()

        estado["processados"][
            analise["sha256"]
        ] = {
            "arquivo": analise["arquivo"],
            "processado_em": self._timestamp(),
            "ciclo_id": ciclo_id,
            "decisao": decisao,
        }

        self._salvar_estado(
            estado
        )

    def listar_entrada(self) -> list[Path]:
        return sorted(
            (
                caminho
                for caminho in self.entrada.rglob("*")
                if caminho.is_file()
            ),
            key=lambda item: str(
                item.relative_to(
                    self.entrada
                )
            ),
        )

    def _copiar_workspace(
        self,
        origem: Path,
        destino_raiz: Path,
    ) -> Path:
        relativo = origem.relative_to(
            self.entrada
        )

        destino = (
            destino_raiz
            / relativo
        )

        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            origem,
            destino,
        )

        return destino

    def analisar_arquivo(
        self,
        arquivo: Path,
    ) -> dict:
        relativo = arquivo.relative_to(
            self.entrada
        )

        resultado = {
            "arquivo": str(relativo),
            "tipo": (
                "python"
                if arquivo.suffix == ".py"
                else "arquivo_texto"
            ),
            "tamanho_bytes": arquivo.stat().st_size,
            "sha256": self._hash_arquivo(
                arquivo
            ),
        }

        try:
            arquivo.read_text(
                encoding="utf-8"
            )

            resultado["utf8_valido"] = True

        except UnicodeDecodeError:
            resultado["utf8_valido"] = False
            resultado["estado"] = "rejeitado"

            return resultado

        resultado["estado"] = "analisado"

        return resultado

    def validar_python(
        self,
        arquivo: Path,
    ) -> dict:
        resultado = {
            "arquivo": str(
                arquivo.relative_to(
                    self.workspace
                )
            ),
            "sucesso": False,
            "erro": "",
        }

        if not self.python.exists():
            resultado["erro"] = (
                "python_virtualenv_nao_encontrado"
            )

            return resultado

        execucao = subprocess.run(
            [
                str(self.python),
                "-m",
                "py_compile",
                str(arquivo),
            ],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )

        resultado["sucesso"] = (
            execucao.returncode == 0
        )

        resultado["codigo_saida"] = (
            execucao.returncode
        )

        resultado["erro"] = (
            execucao.stderr.strip()
        )

        return resultado

    def processar_arquivo(
        self,
        arquivo: Path,
        ciclo_id: str,
    ) -> dict:
        analise = self.analisar_arquivo(
            arquivo
        )

        if analise["estado"] == "rejeitado":
            resultado = {
                **analise,
                "decisao": "rejeitado",
                "motivo": "arquivo_nao_utf8",
            }

            self._registrar_processado(
                analise,
                ciclo_id,
                "rejeitado",
            )

            return resultado

        workspace_arquivo = (
            self._copiar_workspace(
                arquivo,
                self.workspace / ciclo_id,
            )
        )

        resultado = {
            **analise,
            "workspace": str(
                workspace_arquivo.relative_to(
                    self.workspace
                )
            ),
            "validacao_python": None,
            "decisao": "rejeitado",
        }

        if arquivo.suffix == ".py":
            validacao = self.validar_python(
                workspace_arquivo
            )

            resultado["validacao_python"] = (
                validacao
            )

            if not validacao["sucesso"]:
                resultado["motivo"] = (
                    validacao["erro"]
                    or "falha_na_sintaxe_python"
                )

                self._registrar_processado(
                    analise,
                    ciclo_id,
                    "rejeitado",
                )

                return resultado

        experimento_arquivo = (
            self._copiar_workspace(
                arquivo,
                self.experimentos / ciclo_id,
            )
        )

        resultado["experimento"] = str(
            experimento_arquivo.relative_to(
                self.experimentos
            )
        )

        resultado["decisao"] = "candidato"
        resultado["motivo"] = (
            "analise_e_validacao_concluidas"
        )

        self._registrar_processado(
            analise,
            ciclo_id,
            "candidato",
        )

        return resultado

    def executar_ciclo(self) -> dict:
        ciclo_id = (
            datetime.now(timezone.utc)
            .strftime("%Y%m%dT%H%M%S%fZ")
        )

        estado = self._carregar_estado()
        arquivos = self.listar_entrada()

        resultados = []
        ignorados = []

        for arquivo in arquivos:
            sha256 = self._hash_arquivo(
                arquivo
            )

            if self._eh_processado(
                sha256,
                estado,
            ):
                ignorados.append(
                    {
                        "arquivo": str(
                            arquivo.relative_to(
                                self.entrada
                            )
                        ),
                        "sha256": sha256,
                        "motivo": "artefato_ja_processado",
                    }
                )
                continue

            resultado = self.processar_arquivo(
                arquivo,
                ciclo_id,
            )

            resultados.append(
                resultado
            )

            estado = self._carregar_estado()

        candidato = sum(
            item["decisao"] == "candidato"
            for item in resultados
        )

        rejeitado = sum(
            item["decisao"] == "rejeitado"
            for item in resultados
        )

        relatorio = {
            "versao_pipeline": 1,
            "ciclo_id": ciclo_id,
            "iniciado_em": self._timestamp(),
            "arquivos_detectados": len(arquivos),
            "arquivos_novos": len(resultados),
            "arquivos_ignorados": ignorados,
            "arquivos_processados": resultados,
            "candidatos": candidato,
            "rejeitados": rejeitado,
            "integracao_stable": False,
            "codigo_executado": False,
            "estado": (
                "nenhum_artefato"
                if not arquivos
                else (
                    "nenhum_artefato_novo"
                    if not resultados
                    else "processamento_concluido"
                )
            ),
        }

        caminho_relatorio = (
            self.relatorios
            / f"{ciclo_id}.json"
        )

        caminho_relatorio.write_text(
            json.dumps(
                relatorio,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        relatorio["relatorio"] = str(
            caminho_relatorio
        )

        return relatorio


if __name__ == "__main__":
    resultado = (
        PipelineDesenvolvimentoNixal()
        .executar_ciclo()
    )

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
        )
    )
