#!/usr/bin/env python3
"""
NYXAL — CICLO DE EVOLUÇÃO REMOTA

M4 / Nível 9 — integração operacional de:
    Evolução Controlada + Laboratório Remoto.

Responsabilidade:
    transformar uma hipótese experimental já formulada em um ciclo
    completo de evidência remota, comparação e proposta.

Fluxo:
    limitação → hipótese → objetivo → baseline
        → publicação experimental
        → laboratório remoto
        → resultado
        → comparação
        → candidato
        → proposta

Garantias:
- não executa o artefato experimental localmente;
- usa o LaboratorioRemotoNixal para execução remota;
- não modifica stable;
- não concede autorização de integração;
- trata resultado experimental como evidência;
- remove a branch experimental apenas depois de obter resultado;
- falhas de execução remota não viram candidato automaticamente.
"""

from __future__ import annotations

import copy
import json
import math
import shutil
from pathlib import Path
from typing import Any

from nixal_evolucao_controlada import EvolucaoControladaNixal
from nixal_laboratorio_remoto import LaboratorioRemotoNixal
from nixal_aprendizado_persistente import AprendizadoPersistenteNixal


class CicloEvolucaoRemotaNixal:
    """Orquestra um ciclo completo de evolução experimental remota."""

    VERSAO = "9.1.0"
    FONTE = "ciclo_evolucao_remota_nixal"

    def __init__(
        self,
        *,
        evolucao: EvolucaoControladaNixal | None = None,
        laboratorio: LaboratorioRemotoNixal | None = None,
        memoria_aprendizado: AprendizadoPersistenteNixal | None = None,
        repositorio: str | Path | None = None,
    ) -> None:
        raiz = Path(
            repositorio or Path(__file__).resolve().parent
        ).resolve()

        self.evolucao = evolucao or EvolucaoControladaNixal(
            repositorio=raiz
        )
        self.laboratorio = laboratorio or LaboratorioRemotoNixal(
            repositorio=raiz
        )
        self.memoria_aprendizado = (
            memoria_aprendizado
            or AprendizadoPersistenteNixal(
                raiz.parent / "memoria_aprendizado_evolucao_nixal.json"
            )
        )

    @staticmethod
    def _numero(valor: Any, nome: str) -> float:
        if isinstance(valor, bool):
            raise ValueError(f"{nome}_invalido")

        try:
            numero = float(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"{nome}_invalido") from erro

        if not math.isfinite(numero):
            raise ValueError(f"{nome}_invalido")

        return numero

    @staticmethod
    def _validar_nome_arquivo(nome: str) -> str:
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("arquivo_destino_invalido")

        caminho = Path(nome)

        if (
            caminho.is_absolute()
            or ".." in caminho.parts
            or len(caminho.parts) != 1
            or caminho.suffix != ".py"
        ):
            raise ValueError("arquivo_destino_invalido")

        return caminho.name

    @staticmethod
    def _manifesto_evolucao(
        *,
        experimento_id: str,
        metrica: str,
        baseline: float,
        arquivo: str,
        descricao: str,
    ) -> str:
        manifesto = {
            "versao": 1,
            "experimento_id": experimento_id,
            "tipo": "evolucao_controlada_remota",
            "metrica": metrica,
            "baseline": baseline,
            "arquivo": arquivo,
            "descricao": descricao,
            "execucao_local": False,
            "stable_modificada": False,
            "autorizacao_explicita": False,
        }
        return json.dumps(
            manifesto,
            ensure_ascii=False,
            indent=2,
        )

    def _preparar_artefato_evolucao(
        self,
        *,
        experimento_id: str,
        origem: Path,
        nome_arquivo: str,
        manifesto: str,
    ) -> tuple[Path, Path]:
        raiz = self.evolucao.experimentos / experimento_id
        raiz.mkdir(parents=True, exist_ok=True)

        destino = raiz / nome_arquivo
        shutil.copy2(origem, destino)

        manifesto_path = raiz / "manifesto_evolucao.json"
        manifesto_path.write_text(
            manifesto,
            encoding="utf-8",
        )

        return destino, manifesto_path

    def executar(
        self,
        *,
        limitacao: str,
        hipotese: str,
        objetivo: str,
        metrica: str,
        direcao_melhor: str,
        baseline: Any,
        artefato_origem: str | Path,
        arquivo_destino: str = "experimento.py",
        descricao: str = "",
        timeout_seconds: int = 60,
        timeout_resultado_segundos: int = 300,
        intervalo_resultado_segundos: int = 5,
    ) -> dict[str, Any]:
        baseline_numero = self._numero(
            baseline,
            "baseline",
        )
        nome_arquivo = self._validar_nome_arquivo(
            arquivo_destino
        )

        origem = Path(artefato_origem).resolve()

        if not origem.is_file():
            raise FileNotFoundError(
                "artefato_origem_nao_encontrado"
            )

        estado = self.evolucao.iniciar(
            limitacao=limitacao,
            hipotese=hipotese,
            objetivo=objetivo,
            metrica=metrica,
            direcao_melhor=direcao_melhor,
        )
        experimento_id = estado["experimento_id"]

        manifesto = self._manifesto_evolucao(
            experimento_id=experimento_id,
            metrica=metrica,
            baseline=baseline_numero,
            arquivo=nome_arquivo,
            descricao=descricao,
        )

        arquivo_experimental, manifesto_path = (
            self._preparar_artefato_evolucao(
                experimento_id=experimento_id,
                origem=origem,
                nome_arquivo=nome_arquivo,
                manifesto=manifesto,
            )
        )

        self.evolucao.registrar_baseline(
            experimento_id,
            baseline_numero,
            evidencias=[
                {
                    "fonte": "ciclo_evolucao_remota",
                    "tipo": "baseline",
                    "metrica": metrica,
                }
            ],
        )

        publicado = self.laboratorio.publicar_experimento(
            experimento_id=experimento_id,
            arquivo_origem=origem,
            descricao=descricao,
            timeout_seconds=timeout_seconds,
        )

        branch = publicado["branch"]
        commit_sha = publicado["commit_sha"]

        disparo = self.laboratorio.disparar_workflow(
            experimento_id=experimento_id,
            experiment_ref=branch,
            expected_sha=commit_sha,
        )

        resultado_remoto = self.laboratorio.aguardar_resultado(
            experimento_id=experimento_id,
            timeout_segundos=timeout_resultado_segundos,
            intervalo_segundos=intervalo_resultado_segundos,
        )

        branch_removida = False

        if (
            resultado_remoto is None
            or resultado_remoto.get("estado")
            != "resultado_recuperado"
        ):
            return {
                "sucesso": False,
                "estado": "resultado_remoto_indisponivel",
                "origem": self.FONTE,
                "experimento_id": experimento_id,
                "branch": branch,
                "commit_sha": commit_sha,
                "publicacao": copy.deepcopy(publicado),
                "disparo": copy.deepcopy(disparo),
                "resultado_remoto": copy.deepcopy(
                    resultado_remoto
                ),
                "candidato": None,
                "proposta": None,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "branch_removida": False,
            }

        try:
            self.laboratorio.remover_branch_experimento(
                branch
            )
            branch_removida = True
        except Exception as erro:
            resultado_remocao = {
                "sucesso": False,
                "estado": "branch_nao_removida",
                "motivo": f"{type(erro).__name__}: {erro}",
            }
        else:
            resultado_remocao = {
                "sucesso": True,
                "estado": "branch_experimental_removida",
                "branch": branch,
            }

        laboratorio_resultado = resultado_remoto.get(
            "resultado"
        )

        if not isinstance(
            laboratorio_resultado,
            dict,
        ):
            return {
                "sucesso": False,
                "estado": "resultado_remoto_invalido",
                "origem": self.FONTE,
                "experimento_id": experimento_id,
                "branch": branch,
                "commit_sha": commit_sha,
                "publicacao": copy.deepcopy(publicado),
                "disparo": copy.deepcopy(disparo),
                "resultado_remoto": copy.deepcopy(
                    resultado_remoto
                ),
                "remocao_branch": resultado_remocao,
                "candidato": None,
                "proposta": None,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "branch_removida": branch_removida,
            }

        if laboratorio_resultado.get("experiment_sha") != commit_sha:
            return {
                "sucesso": False,
                "estado": "sha_experimental_invalido",
                "origem": self.FONTE,
                "experimento_id": experimento_id,
                "branch": branch,
                "commit_sha": commit_sha,
                "resultado_remoto": copy.deepcopy(
                    resultado_remoto
                ),
                "remocao_branch": resultado_remocao,
                "candidato": None,
                "proposta": None,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "branch_removida": branch_removida,
            }

        if laboratorio_resultado.get("status") != "sucesso":
            return {
                "sucesso": False,
                "estado": "experimento_remoto_falhou",
                "origem": self.FONTE,
                "experimento_id": experimento_id,
                "branch": branch,
                "commit_sha": commit_sha,
                "resultado_remoto": copy.deepcopy(
                    resultado_remoto
                ),
                "remocao_branch": resultado_remocao,
                "candidato": None,
                "proposta": None,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "branch_removida": branch_removida,
            }

        valor_experimental = self._numero(
            laboratorio_resultado.get(metrica),
            "resultado_experimental",
        )

        self.evolucao.registrar_resultado_experimental(
            experimento_id,
            valor_experimental,
            evidencias=[
                {
                    "fonte": "nyxal_remote_lab",
                    "tipo": "resultado_experimental",
                    "experiment_sha": commit_sha,
                    "status": laboratorio_resultado.get(
                        "status"
                    ),
                    "metrica": metrica,
                }
            ],
        )

        comparacao = self.evolucao.comparar(
            experimento_id
        )

        experiencia = {
            "tipo": "evolucao_controlada_remota",
            "experimento_id": experimento_id,
            "metrica": metrica,
            "baseline": baseline_numero,
            "experimental": valor_experimental,
            "melhoria_absoluta": comparacao.get("melhoria_absoluta"),
            "melhoria_relativa": comparacao.get("melhoria_relativa"),
            "aprovado": comparacao.get("aprovado") is True,
            "experiment_sha": commit_sha,
            "resultado_status": laboratorio_resultado.get("status"),
        }

        avaliacao = {
            "avaliacao": (
                "sucesso"
                if comparacao.get("aprovado") is True
                else "falha"
            ),
            "criterio": "experimental_melhor_que_baseline",
            "metrica": metrica,
        }

        aprendizado = self.memoria_aprendizado.registrar(
            ciclo_id=experimento_id,
            experiencia=experiencia,
            avaliacao=avaliacao,
        )

        if aprendizado.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "aprendizado_falhou",
                "origem": self.FONTE,
                "experimento_id": experimento_id,
                "comparacao": copy.deepcopy(comparacao),
                "aprendizado": copy.deepcopy(aprendizado),
                "candidato": None,
                "proposta": None,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "branch_removida": branch_removida,
            }

        if comparacao.get("aprovado") is not True:
            return {
                "sucesso": False,
                "estado": "evolucao_rejeitada",
                "origem": self.FONTE,
                "experimento_id": experimento_id,
                "branch": branch,
                "commit_sha": commit_sha,
                "resultado_remoto": copy.deepcopy(
                    resultado_remoto
                ),
                "comparacao": copy.deepcopy(
                    comparacao
                ),
                "aprendizado": copy.deepcopy(aprendizado),
                "candidato": None,
                "proposta": None,
                "remocao_branch": resultado_remocao,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "branch_removida": branch_removida,
            }

        candidato = self.evolucao.criar_candidato(
            experimento_id,
            arquivo=nome_arquivo,
            manifesto="manifesto_evolucao.json",
        )

        proposta = self.evolucao.criar_proposta(
            experimento_id
        )

        return {
            "sucesso": True,
            "estado": "proposta_criada",
            "origem": self.FONTE,
            "experimento_id": experimento_id,
            "branch": branch,
            "commit_sha": commit_sha,
            "arquivo_experimental": str(
                arquivo_experimental
            ),
            "manifesto": str(manifesto_path),
            "publicacao": copy.deepcopy(publicado),
            "disparo": copy.deepcopy(disparo),
            "resultado_remoto": copy.deepcopy(
                resultado_remoto
            ),
            "comparacao": copy.deepcopy(comparacao),
            "experiencia": copy.deepcopy(experiencia),
            "avaliacao": copy.deepcopy(avaliacao),
            "aprendizado": copy.deepcopy(aprendizado),
            "candidato": copy.deepcopy(candidato),
            "proposta": copy.deepcopy(proposta),
            "remocao_branch": resultado_remocao,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "branch_removida": branch_removida,
        }


__all__ = [
    "CicloEvolucaoRemotaNixal",
]


if __name__ == "__main__":
    print("CicloEvolucaoRemotaNixal OK")
