#!/usr/bin/env python3
"""
NYXAL — EVOLUÇÃO CONTROLADA

M4 / Nível 9 — primeira camada operacional de Controlled Evolution.

Responsabilidade:
    orquestrar uma evolução experimental sem modificar stable,
    usando baseline, resultado experimental, comparação explícita,
    candidato e proposta de integração.

A classe:
- mantém o experimento fora da árvore Git;
- exige baseline antes da comparação;
- exige resultado experimental antes da aprovação;
- só cria candidato quando há melhoria segundo a métrica declarada;
- cria proposta em estado aguardando_autorizacao;
- nunca executa o artefato experimental;
- nunca modifica stable;
- nunca concede autorização implícita.

Esta etapa prova coordenação e governança da evolução.
Ela NÃO prova ainda que a Nyxal descobriu sozinha a limitação,
gerou código autonomamente ou executou uma alteração arquitetural.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nixal_candidatos_desenvolvimento import (
    RegistroCandidatosDesenvolvimentoNixal,
)
from nixal_proposta_integracao import (
    PropostaIntegracaoDesenvolvimentoNixal,
)


class EvolucaoControladaNixal:
    """Coordena um experimento de evolução com gates explícitos."""

    VERSAO = "1.0"
    FONTE = "evolucao_controlada_nixal"
    ESTADOS = {
        "experimento_iniciado",
        "baseline_registrado",
        "resultado_experimental_registrado",
        "comparacao_concluida",
        "candidato_criado",
        "proposta_criada",
        "rejeitado",
    }

    def __init__(
        self,
        repositorio: str | Path | None = None,
        experimentos: str | Path | None = None,
        candidatos: str | Path | None = None,
        propostas: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        ).resolve()

        externo = self.repositorio.parent

        self.experimentos = Path(
            experimentos or externo / "Nyxal-experiments"
        ).resolve()

        self.candidatos = Path(
            candidatos or externo / "Nyxal-candidates"
        ).resolve()

        self.propostas = Path(
            propostas or externo / "Nyxal-integration-proposals"
        ).resolve()

        for diretorio in (
            self.experimentos,
            self.candidatos,
            self.propostas,
        ):
            diretorio.mkdir(parents=True, exist_ok=True)

        self.registro_candidatos = (
            RegistroCandidatosDesenvolvimentoNixal(
                repositorio=self.repositorio,
                candidatos=self.candidatos,
            )
        )

        self.registro_propostas = (
            PropostaIntegracaoDesenvolvimentoNixal(
                repositorio=self.repositorio,
                propostas=self.propostas,
            )
        )

    # ==========================================================
    # UTILITÁRIOS
    # ==========================================================

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _id_experimento(
        limitacao: str,
        hipotese: str,
        objetivo: str,
    ) -> str:
        base = {
            "limitacao": limitacao.strip(),
            "hipotese": hipotese.strip(),
            "objetivo": objetivo.strip(),
        }
        canonico = json.dumps(
            base,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()[:16]
        return f"evolucao-{digest}"

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
    def _validar_texto(valor: Any, nome: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    @staticmethod
    def _validar_numero(valor: Any, nome: str) -> float:
        if isinstance(valor, bool):
            raise ValueError(f"{nome}_invalido")

        try:
            numero = float(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"{nome}_invalido") from erro

        if not math.isfinite(numero):
            raise ValueError(f"{nome}_invalido")

        return numero

    def _caminho_estado(
        self,
        experimento_id: str,
    ) -> Path:
        return self.experimentos / experimento_id / "evolucao.json"

    def _carregar_estado(
        self,
        experimento_id: str,
    ) -> dict[str, Any]:
        caminho = self._caminho_estado(experimento_id)

        if not caminho.exists():
            raise FileNotFoundError("experimento_nao_encontrado")

        try:
            dados = json.loads(
                caminho.read_text(encoding="utf-8")
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError("estado_experimento_invalido") from erro

        if not isinstance(dados, dict):
            raise ValueError("estado_experimento_invalido")

        return dados

    def _salvar_estado(
        self,
        estado: dict[str, Any],
    ) -> None:
        experimento_id = estado.get("experimento_id")

        if not isinstance(experimento_id, str):
            raise ValueError("experimento_id_invalido")

        caminho = self._caminho_estado(experimento_id)
        caminho.parent.mkdir(parents=True, exist_ok=True)

        temporario = caminho.with_name(
            caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                estado,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporario, caminho)

    @staticmethod
    def _validar_arquivo_relativo(
        arquivo: str,
    ) -> Path:
        caminho = Path(arquivo)

        if (
            caminho.is_absolute()
            or ".." in caminho.parts
            or not caminho.name
        ):
            raise ValueError("arquivo_relativo_invalido")

        return caminho

    # ==========================================================
    # EXPERIMENTO
    # ==========================================================

    def iniciar(
        self,
        *,
        limitacao: str,
        hipotese: str,
        objetivo: str,
        metrica: str,
        direcao_melhor: str,
    ) -> dict[str, Any]:
        limitacao = self._validar_texto(
            limitacao,
            "limitacao",
        )
        hipotese = self._validar_texto(
            hipotese,
            "hipotese",
        )
        objetivo = self._validar_texto(
            objetivo,
            "objetivo",
        )
        metrica = self._validar_texto(
            metrica,
            "metrica",
        )

        if direcao_melhor not in {"maior", "menor"}:
            raise ValueError("direcao_melhor_invalida")

        experimento_id = self._id_experimento(
            limitacao,
            hipotese,
            objetivo,
        )

        raiz = self.experimentos / experimento_id
        estado_path = raiz / "evolucao.json"

        if estado_path.exists():
            return self._carregar_estado(
                experimento_id
            )

        raiz.mkdir(
            parents=True,
            exist_ok=True,
        )

        estado = {
            "versao_evolucao": self.VERSAO,
            "fonte": self.FONTE,
            "experimento_id": experimento_id,
            "estado": "experimento_iniciado",
            "criado_em": self._timestamp(),
            "limitacao": limitacao,
            "hipotese": hipotese,
            "objetivo": objetivo,
            "metrica": metrica,
            "direcao_melhor": direcao_melhor,
            "baseline": None,
            "resultado_experimental": None,
            "comparacao": None,
            "candidato": None,
            "proposta": None,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

        self._salvar_estado(estado)
        return copy.deepcopy(estado)

    def registrar_baseline(
        self,
        experimento_id: str,
        valor: Any,
        evidencias: list[Any] | None = None,
    ) -> dict[str, Any]:
        estado = self._carregar_estado(
            experimento_id
        )

        if estado.get("estado") not in {
            "experimento_iniciado",
            "baseline_registrado",
        }:
            raise ValueError("ordem_do_experimento_invalida")

        numero = self._validar_numero(
            valor,
            "baseline",
        )

        estado["baseline"] = {
            "valor": numero,
            "evidencias": copy.deepcopy(
                evidencias or []
            ),
            "registrado_em": self._timestamp(),
        }
        estado["estado"] = "baseline_registrado"

        self._salvar_estado(estado)
        return copy.deepcopy(estado)

    def registrar_resultado_experimental(
        self,
        experimento_id: str,
        valor: Any,
        evidencias: list[Any] | None = None,
    ) -> dict[str, Any]:
        estado = self._carregar_estado(
            experimento_id
        )

        if estado.get("baseline") is None:
            raise ValueError(
                "baseline_obrigatorio_antes_do_experimento"
            )

        if estado.get("estado") not in {
            "baseline_registrado",
            "resultado_experimental_registrado",
        }:
            raise ValueError("ordem_do_experimento_invalida")

        numero = self._validar_numero(
            valor,
            "resultado_experimental",
        )

        estado["resultado_experimental"] = {
            "valor": numero,
            "evidencias": copy.deepcopy(
                evidencias or []
            ),
            "registrado_em": self._timestamp(),
        }
        estado["estado"] = (
            "resultado_experimental_registrado"
        )

        self._salvar_estado(estado)
        return copy.deepcopy(estado)

    # ==========================================================
    # COMPARAÇÃO
    # ==========================================================

    def comparar(
        self,
        experimento_id: str,
    ) -> dict[str, Any]:
        estado = self._carregar_estado(
            experimento_id
        )

        baseline = estado.get("baseline")
        experimental = estado.get(
            "resultado_experimental"
        )

        if not isinstance(baseline, dict):
            raise ValueError(
                "baseline_nao_registrado"
            )

        if not isinstance(experimental, dict):
            raise ValueError(
                "resultado_experimental_nao_registrado"
            )

        base = self._validar_numero(
            baseline.get("valor"),
            "baseline",
        )
        novo = self._validar_numero(
            experimental.get("valor"),
            "resultado_experimental",
        )

        direcao = estado.get("direcao_melhor")

        if direcao == "maior":
            melhoria_absoluta = novo - base
            aprovado = novo > base
        elif direcao == "menor":
            melhoria_absoluta = base - novo
            aprovado = novo < base
        else:
            raise ValueError(
                "direcao_melhor_invalida"
            )

        if base == 0:
            melhoria_relativa = None
        else:
            melhoria_relativa = (
                melhoria_absoluta / abs(base)
            )

        comparacao = {
            "metrica": estado.get("metrica"),
            "baseline": base,
            "experimental": novo,
            "direcao_melhor": direcao,
            "melhoria_absoluta": melhoria_absoluta,
            "melhoria_relativa": melhoria_relativa,
            "aprovado": aprovado,
            "criterio": (
                "experimental_melhor_que_baseline"
            ),
            "avaliacao": (
                "sucesso"
                if aprovado
                else "falha"
            ),
            "comparado_em": self._timestamp(),
        }

        estado["comparacao"] = comparacao
        estado["estado"] = (
            "comparacao_concluida"
            if aprovado
            else "rejeitado"
        )

        self._salvar_estado(estado)

        return copy.deepcopy(comparacao)

    # ==========================================================
    # CANDIDATO
    # ==========================================================

    def criar_candidato(
        self,
        experimento_id: str,
        *,
        arquivo: str,
        manifesto: str = "manifesto_evolucao.json",
    ) -> dict[str, Any]:
        estado = self._carregar_estado(
            experimento_id
        )

        comparacao = estado.get(
            "comparacao"
        )

        if not isinstance(comparacao, dict):
            raise ValueError(
                "comparacao_obrigatoria_antes_do_candidato"
            )

        if comparacao.get("aprovado") is not True:
            raise ValueError(
                "melhoria_nao_aprovada"
            )

        arquivo_relativo = self._validar_arquivo_relativo(
            arquivo
        )
        manifesto_relativo = (
            self._validar_arquivo_relativo(
                manifesto
            )
        )

        raiz = self.experimentos / experimento_id
        origem = raiz / arquivo_relativo
        caminho_manifesto = raiz / manifesto_relativo

        if not origem.is_file():
            raise FileNotFoundError(
                "artefato_experimental_nao_encontrado"
            )

        if not caminho_manifesto.is_file():
            raise FileNotFoundError(
                "manifesto_experimental_nao_encontrado"
            )

        avaliacao = {
            "aprovado": True,
            "tipo": "evolucao_controlada",
            "comparacao": copy.deepcopy(
                comparacao
            ),
            "execucao_codigo": False,
            "stable_modificada": False,
            "autorizacao_explicita": False,
        }

        candidato = (
            self.registro_candidatos.registrar(
                ciclo_id=experimento_id,
                arquivo=str(arquivo_relativo),
                manifesto=str(manifesto_relativo),
                fingerprint=self._hash_arquivo(
                    origem
                ),
                experimento_raiz=raiz,
                avaliacao=avaliacao,
            )
        )

        estado["candidato"] = copy.deepcopy(
            candidato
        )
        estado["estado"] = "candidato_criado"
        self._salvar_estado(estado)

        return copy.deepcopy(candidato)

    # ==========================================================
    # PROPOSTA
    # ==========================================================

    def criar_proposta(
        self,
        experimento_id: str,
        *,
        destino: str = "main",
    ) -> dict[str, Any]:
        estado = self._carregar_estado(
            experimento_id
        )

        if estado.get("estado") != "candidato_criado":
            raise ValueError(
                "candidato_obrigatorio_antes_da_proposta"
            )

        candidato = estado.get("candidato")

        if not isinstance(candidato, dict):
            raise ValueError(
                "candidato_invalido"
            )

        candidato_dir = candidato.get(
            "diretorio_candidato"
        )

        if not isinstance(candidato_dir, str):
            raise ValueError(
                "diretorio_candidato_invalido"
            )

        proposta = self.registro_propostas.criar(
            candidato_dir=candidato_dir,
            destino=destino,
        )

        estado["proposta"] = copy.deepcopy(
            proposta
        )
        estado["estado"] = "proposta_criada"
        estado["autorizacao_explicita"] = False
        estado["integracao_executada"] = False
        estado["stable_modificada"] = False
        self._salvar_estado(estado)

        return copy.deepcopy(proposta)

    def consultar(
        self,
        experimento_id: str,
    ) -> dict[str, Any]:
        return self._carregar_estado(
            experimento_id
        )

    def executar_fluxo_aprovado(
        self,
        *,
        limitacao: str,
        hipotese: str,
        objetivo: str,
        metrica: str,
        direcao_melhor: str,
        baseline: Any,
        experimental: Any,
        arquivo: str,
        manifesto_conteudo: str,
        artefato_origem: str | Path,
    ) -> dict[str, Any]:
        """
        Atalho determinístico para o fluxo completo até proposta.

        O artefato é apenas copiado para o diretório experimental.
        Ele NÃO é executado.
        """
        estado = self.iniciar(
            limitacao=limitacao,
            hipotese=hipotese,
            objetivo=objetivo,
            metrica=metrica,
            direcao_melhor=direcao_melhor,
        )
        experimento_id = estado["experimento_id"]

        raiz = self.experimentos / experimento_id
        arquivo_relativo = self._validar_arquivo_relativo(
            arquivo
        )
        origem = Path(artefato_origem).resolve()

        if not origem.is_file():
            raise FileNotFoundError(
                "artefato_origem_nao_encontrado"
            )

        destino = raiz / arquivo_relativo
        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        shutil.copy2(
            origem,
            destino,
        )

        manifesto_relativo = Path(
            "manifesto_evolucao.json"
        )
        (raiz / manifesto_relativo).write_text(
            manifesto_conteudo,
            encoding="utf-8",
        )

        self.registrar_baseline(
            experimento_id,
            baseline,
            evidencias=[
                {
                    "fonte": "entrada_controlada",
                    "tipo": "baseline",
                }
            ],
        )
        self.registrar_resultado_experimental(
            experimento_id,
            experimental,
            evidencias=[
                {
                    "fonte": "entrada_controlada",
                    "tipo": "resultado_experimental",
                }
            ],
        )
        self.comparar(experimento_id)

        estado_atual = self.consultar(
            experimento_id
        )

        if estado_atual["estado"] == "rejeitado":
            return {
                "sucesso": False,
                "estado": "rejeitado",
                "experimento": estado_atual,
                "comparacao": copy.deepcopy(
                    estado_atual.get("comparacao")
                ),
                "candidato": None,
                "proposta": None,
                "execucao_artefato": False,
                "autorizacao_explicita": False,
                "stable_modificada": False,
            }

        self.criar_candidato(
            experimento_id,
            arquivo=arquivo,
            manifesto=str(
                manifesto_relativo
            ),
        )
        proposta = self.criar_proposta(
            experimento_id
        )

        return {
            "sucesso": True,
            "estado": "proposta_criada",
            "experimento": self.consultar(
                experimento_id
            ),
            "proposta": proposta,
            "execucao_artefato": False,
            "autorizacao_explicita": False,
            "stable_modificada": False,
        }


__all__ = [
    "EvolucaoControladaNixal",
]


if __name__ == "__main__":
    print("EvolucaoControladaNixal OK")
