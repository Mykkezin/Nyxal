#!/usr/bin/env python3

"""
NYXAL — PIPELINE CONTROLADO DE DESENVOLVIMENTO

Fluxo:
    incoming
      ↓
    contrato
      ↓
    análise
      ↓
    workspace isolado
      ↓
    validação estrutural/sintaxe
      ↓
    avaliação
      ↓
    candidato ou rejeitado
      ↓
    relatório

Limites:
- não executa código recebido;
- não instala dependências;
- não altera a branch atual;
- não faz merge;
- não publica;
- não promove para stable;
- não executa testes arbitrários recebidos;
- candidato somente após avaliação explícita.

O contrato do artefato é um arquivo *.nyxal.json declarativo.
Artefatos sem contrato são ignorados e registrados.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from nixal_avaliador_desenvolvimento import (
    AvaliacaoDesenvolvimentoNixal,
)
from nixal_contrato_artefato import (
    ContratoArtefatoNixal,
)


class PipelineDesenvolvimentoNixal:
    VERSAO_ESTADO = 2

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

    def _fingerprint(
        self,
        artefato: Path,
        manifesto: Path,
    ) -> str:
        digest = hashlib.sha256()

        for caminho in (
            artefato,
            manifesto,
        ):
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
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return {
                "versao": self.VERSAO_ESTADO,
                "processados": {},
            }

        processados = estado.get(
            "processados",
            {},
        )

        if not isinstance(
            processados,
            dict,
        ):
            processados = {}

        return {
            "versao": self.VERSAO_ESTADO,
            "processados": processados,
        }

    def _salvar_estado(
        self,
        estado: dict,
    ) -> None:
        self.estado_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporario = (
            self.estado_path.with_suffix(".tmp")
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
        fingerprint: str,
        estado: dict,
    ) -> bool:
        return fingerprint in estado[
            "processados"
        ]

    def _registrar_processado(
        self,
        fingerprint: str,
        artefato: str,
        manifesto: str,
        sha256_artefato: str,
        sha256_manifesto: str,
        ciclo_id: str,
        decisao: str,
    ) -> None:
        estado = self._carregar_estado()

        estado["processados"][
            fingerprint
        ] = {
            "artefato": artefato,
            "manifesto": manifesto,
            "sha256_artefato": sha256_artefato,
            "sha256_manifesto": sha256_manifesto,
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
                and not caminho.name.endswith(
                    ".nyxal.json"
                )
            ),
            key=lambda item: str(
                item.relative_to(
                    self.entrada
                )
            ),
        )

    def _manifesto_do_arquivo(
        self,
        arquivo: Path,
    ) -> Path:
        relativo = arquivo.relative_to(
            self.entrada
        )

        return (
            arquivo.parent
            / f"{relativo.name}.nyxal.json"
        )

    def _copiar(
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

    def _validar_contrato(
        self,
        arquivo: Path,
        manifesto: Path,
    ) -> tuple[
        ContratoArtefatoNixal | None,
        str | None,
    ]:
        try:
            contrato = (
                ContratoArtefatoNixal.carregar(
                    manifesto
                )
            )
        except ValueError as erro:
            return (
                None,
                str(erro),
            )

        arquivo_relativo = str(
            arquivo.relative_to(
                self.entrada
            )
        )

        if contrato.arquivo != arquivo_relativo:
            return (
                None,
                "arquivo_do_contrato_nao_corresponde",
            )

        extensao_esperada = (
            ".py"
            if contrato.tipo == "python"
            else None
        )

        if (
            extensao_esperada
            and arquivo.suffix
            != extensao_esperada
        ):
            return (
                None,
                "tipo_do_contrato_nao_corresponde",
            )

        return (
            contrato,
            None,
        )

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
        manifesto: Path,
        contrato: ContratoArtefatoNixal,
        fingerprint: str,
        ciclo_id: str,
    ) -> dict:
        sha_artefato = self._hash_arquivo(
            arquivo
        )

        sha_manifesto = self._hash_arquivo(
            manifesto
        )

        workspace_arquivo = self._copiar(
            arquivo,
            self.workspace / ciclo_id,
        )

        workspace_manifesto = self._copiar(
            manifesto,
            self.workspace / ciclo_id,
        )

        resultado = {
            "arquivo": str(
                arquivo.relative_to(
                    self.entrada
                )
            ),
            "manifesto": str(
                manifesto.relative_to(
                    self.entrada
                )
            ),
            "sha256": sha_artefato,
            "sha256_manifesto": sha_manifesto,
            "fingerprint": fingerprint,
            "contrato": {
                "versao_contrato": contrato.versao_contrato,
                "nome": contrato.nome,
                "objetivo": contrato.objetivo,
                "tipo": contrato.tipo,
                "operacoes_permitidas": list(
                    contrato.operacoes_permitidas
                ),
                "executar": contrato.executar,
            },
            "workspace": str(
                workspace_arquivo.relative_to(
                    self.workspace
                )
            ),
            "workspace_manifesto": str(
                workspace_manifesto.relative_to(
                    self.workspace
                )
            ),
            "validacao_python": None,
            "decisao": "rejeitado",
        }

        if contrato.tipo == "python":
            if (
                "py_compile"
                not in contrato.operacoes_permitidas
            ):
                resultado["motivo"] = (
                    "py_compile_nao_autorizado_pelo_contrato"
                )

                self._registrar_processado(
                    fingerprint,
                    resultado["arquivo"],
                    resultado["manifesto"],
                    sha_artefato,
                    sha_manifesto,
                    ciclo_id,
                    "rejeitado",
                )

                return resultado

            validacao = self.validar_python(
                workspace_arquivo
            )

            resultado[
                "validacao_python"
            ] = validacao

            if not validacao["sucesso"]:
                resultado["motivo"] = (
                    validacao["erro"]
                    or "falha_na_sintaxe_python"
                )

                self._registrar_processado(
                    fingerprint,
                    resultado["arquivo"],
                    resultado["manifesto"],
                    sha_artefato,
                    sha_manifesto,
                    ciclo_id,
                    "rejeitado",
                )

                return resultado

        if "analise" not in contrato.operacoes_permitidas:
            resultado["motivo"] = (
                "analise_nao_autorizada_pelo_contrato"
            )

            self._registrar_processado(
                fingerprint,
                resultado["arquivo"],
                resultado["manifesto"],
                sha_artefato,
                sha_manifesto,
                ciclo_id,
                "rejeitado",
            )

            return resultado

        avaliacao = (
            AvaliacaoDesenvolvimentoNixal.avaliar(
                contrato={
                    "executar": contrato.executar,
                    "operacoes_permitidas": list(
                        contrato.operacoes_permitidas
                    ),
                    "tipo": contrato.tipo,
                },
                validacao_python=resultado[
                    "validacao_python"
                ],
            )
        )

        resultado["avaliacao"] = (
            avaliacao.como_dict()
        )

        if not avaliacao.aprovado:
            resultado["motivo"] = (
                "avaliacao_reprovada"
            )

            self._registrar_processado(
                fingerprint,
                resultado["arquivo"],
                resultado["manifesto"],
                sha_artefato,
                sha_manifesto,
                ciclo_id,
                "rejeitado",
            )

            return resultado

        experimento_arquivo = self._copiar(
            arquivo,
            self.experimentos / ciclo_id,
        )

        experimento_manifesto = self._copiar(
            manifesto,
            self.experimentos / ciclo_id,
        )

        resultado["experimento"] = str(
            experimento_arquivo.relative_to(
                self.experimentos
            )
        )

        resultado["experimento_manifesto"] = str(
            experimento_manifesto.relative_to(
                self.experimentos
            )
        )

        resultado["decisao"] = "candidato"
        resultado["motivo"] = (
            "contrato_analise_e_validacao_concluidas"
        )

        self._registrar_processado(
            fingerprint,
            resultado["arquivo"],
            resultado["manifesto"],
            sha_artefato,
            sha_manifesto,
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
            manifesto = (
                self._manifesto_do_arquivo(
                    arquivo
                )
            )

            if not manifesto.exists():
                ignorados.append(
                    {
                        "arquivo": str(
                            arquivo.relative_to(
                                self.entrada
                            )
                        ),
                        "motivo": "contrato_ausente",
                    }
                )
                continue

            contrato, erro_contrato = (
                self._validar_contrato(
                    arquivo,
                    manifesto,
                )
            )

            if erro_contrato:
                ignorados.append(
                    {
                        "arquivo": str(
                            arquivo.relative_to(
                                self.entrada
                            )
                        ),
                        "manifesto": str(
                            manifesto.relative_to(
                                self.entrada
                            )
                        ),
                        "motivo": "contrato_invalido",
                        "erro": erro_contrato,
                    }
                )
                continue

            fingerprint = self._fingerprint(
                arquivo,
                manifesto,
            )

            if self._eh_processado(
                fingerprint,
                estado,
            ):
                ignorados.append(
                    {
                        "arquivo": str(
                            arquivo.relative_to(
                                self.entrada
                            )
                        ),
                        "manifesto": str(
                            manifesto.relative_to(
                                self.entrada
                            )
                        ),
                        "fingerprint": fingerprint,
                        "motivo": "artefato_ja_processado",
                    }
                )
                continue

            resultado = self.processar_arquivo(
                arquivo,
                manifesto,
                contrato,
                fingerprint,
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
            "versao_pipeline": 2,
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
