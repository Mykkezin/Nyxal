#!/usr/bin/env python3
"""
NYXAL — SOLICITAÇÃO FORMAL DE EVOLUÇÃO

M4 / Nível 9 — ponte entre hipótese investigada e evolução controlada.

Responsabilidade:
    transformar uma hipótese provisória já integrada ao ciclo de
    investigação em uma solicitação estruturada para evolução.

A solicitação é um pedido formal, não uma execução.

Gates:
- hipótese precisa estar provisória;
- hipótese não pode estar confirmada nem testada;
- evidências são preservadas como suporte, não como verdade;
- objetivo, métrica, direção e baseline precisam ser explícitos;
- artefato experimental é opcional na criação e gera estado
  "aguardando_artefato" quando ausente;
- nenhuma execução local ou remota acontece aqui;
- nenhuma autorização de integração é concedida;
- stable nunca é modificada.

Persistência:
    solicitações ficam fora da árvore Git, no diretório
    Nyxal-evolution-requests ao lado do repositório.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SolicitacaoEvolucaoNixal:
    VERSAO = "9.3.0"
    FONTE = "solicitacao_evolucao_nixal"

    def __init__(
        self,
        *,
        repositorio: str | Path | None = None,
        solicitacoes: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        ).resolve()

        self.solicitacoes = Path(
            solicitacoes
            or self.repositorio.parent / "Nyxal-evolution-requests"
        ).resolve()

        self.solicitacoes.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _texto(
        valor: Any,
        nome: str,
    ) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    @staticmethod
    def _numero(
        valor: Any,
        nome: str,
    ) -> float:
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
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _extrair_hipotese(
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(ciclo, dict):
            raise ValueError("ciclo_hipotese_invalido")

        estado = ciclo.get("estado_atual")
        if estado != "provisoria":
            raise ValueError("hipotese_nao_provisoria")

        if ciclo.get("confirmada") is not False:
            raise ValueError("hipotese_nao_pode_estar_confirmada")

        if ciclo.get("testada") is not False:
            raise ValueError("hipotese_nao_pode_estar_testada")

        texto = ciclo.get("hipotese")
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError("texto_hipotese_invalido")

        evidencias = ciclo.get("evidencias_de_suporte", [])
        if not isinstance(evidencias, list):
            raise ValueError("evidencias_hipotese_invalidas")

        return {
            "hipotese": texto.strip(),
            "necessidade": ciclo.get("necessidade"),
            "pergunta": ciclo.get("pergunta"),
            "estado": estado,
            "tipo": ciclo.get("tipo"),
            "razao": ciclo.get("razao"),
            "evidencias_de_suporte": copy.deepcopy(evidencias),
            "evidencias_contrarias_conhecidas": copy.deepcopy(
                ciclo.get("evidencias_contrarias_conhecidas", [])
            ),
            "contrarias_avaliadas": bool(
                ciclo.get("contrarias_avaliadas", False)
            ),
            "confianca": ciclo.get("confianca"),
            "confirmada": False,
            "testada": False,
        }

    @staticmethod
    def _validar_arquivo(
        caminho: str | Path | None,
    ) -> str | None:
        if caminho is None:
            return None

        valor = str(caminho).strip()
        if not valor:
            return None

        origem = Path(valor).expanduser().resolve()
        if not origem.is_file():
            raise FileNotFoundError(
                "artefato_experimental_nao_encontrado"
            )

        if origem.suffix != ".py":
            raise ValueError(
                "artefato_experimental_precisa_ser_python"
            )

        return str(origem)

    def _id(
        self,
        *,
        hipotese: dict[str, Any],
        objetivo: str,
        metrica: str,
        direcao_melhor: str,
        baseline: float,
    ) -> str:
        base = {
            "hipotese": hipotese.get("hipotese"),
            "necessidade": hipotese.get("necessidade"),
            "pergunta": hipotese.get("pergunta"),
            "objetivo": objetivo,
            "metrica": metrica,
            "direcao_melhor": direcao_melhor,
            "baseline": baseline,
        }
        canonico = json.dumps(
            base,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()[:20]
        return f"solicitacao-{digest}"

    def criar(
        self,
        *,
        ciclo_hipotese: dict[str, Any],
        objetivo: str,
        metrica: str,
        direcao_melhor: str,
        baseline: Any,
        artefato_origem: str | Path | None = None,
        observacao: str = "",
    ) -> dict[str, Any]:
        hipotese = self._extrair_hipotese(
            ciclo_hipotese
        )

        objetivo = self._texto(
            objetivo,
            "objetivo",
        )
        metrica = self._texto(
            metrica,
            "metrica",
        )

        if direcao_melhor not in {"maior", "menor"}:
            raise ValueError("direcao_melhor_invalida")

        baseline_numero = self._numero(
            baseline,
            "baseline",
        )

        if not isinstance(observacao, str):
            raise ValueError("observacao_invalida")

        artefato = self._validar_arquivo(
            artefato_origem
        )

        solicitacao_id = self._id(
            hipotese=hipotese,
            objetivo=objetivo,
            metrica=metrica,
            direcao_melhor=direcao_melhor,
            baseline=baseline_numero,
        )

        caminho = (
            self.solicitacoes
            / f"{solicitacao_id}.json"
        )

        if caminho.exists():
            return json.loads(
                caminho.read_text(encoding="utf-8")
            )

        estado = (
            "pronta_para_experimento"
            if artefato is not None
            else "aguardando_artefato"
        )

        registro = {
            "versao": self.VERSAO,
            "fonte": self.FONTE,
            "solicitacao_id": solicitacao_id,
            "criada_em": self._timestamp(),
            "estado": estado,
            "necessidade": hipotese.get("necessidade"),
            "pergunta": hipotese.get("pergunta"),
            "hipotese": copy.deepcopy(hipotese),
            "objetivo": objetivo,
            "metrica": metrica,
            "direcao_melhor": direcao_melhor,
            "baseline": baseline_numero,
            "artefato_origem": artefato,
            "observacao": observacao,
            "execucao_solicitada": artefato is not None,
            "execucao_local": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

        temporario = caminho.with_name(
            caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                registro,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(
            temporario,
            caminho,
        )

        return copy.deepcopy(registro)

    def anexar_artefato(
        self,
        solicitacao_id: str,
        artefato_origem: str | Path,
        observacao: str = "",
    ) -> dict[str, Any]:
        """
        Avança uma solicitação já persistida de aguardando_artefato
        para pronta_para_experimento.

        A anexação não executa o artefato e não concede autorização.
        """
        solicitacao_id = self._texto(
            solicitacao_id,
            "solicitacao_id",
        )

        if not isinstance(observacao, str):
            raise ValueError("observacao_invalida")

        caminho = (
            self.solicitacoes
            / f"{solicitacao_id}.json"
        )

        if not caminho.is_file():
            raise FileNotFoundError(
                "solicitacao_nao_encontrada"
            )

        try:
            registro = json.loads(
                caminho.read_text(encoding="utf-8")
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError(
                "solicitacao_invalida"
            ) from erro

        if not isinstance(registro, dict):
            raise ValueError("solicitacao_invalida")

        if registro.get("estado") != "aguardando_artefato":
            raise ValueError(
                "solicitacao_nao_aguarda_artefato"
            )

        artefato = self._validar_arquivo(
            artefato_origem
        )

        if artefato is None:
            raise ValueError(
                "artefato_experimental_nao_encontrado"
            )

        registro["estado"] = "pronta_para_experimento"
        registro["artefato_origem"] = artefato
        registro["observacao_artefato"] = observacao
        registro["artefato_anexado_em"] = self._timestamp()
        registro["execucao_solicitada"] = True
        registro["execucao_local"] = False
        registro["autorizacao_explicita"] = False
        registro["integracao_executada"] = False
        registro["stable_modificada"] = False

        temporario = caminho.with_name(
            caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                registro,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(
            temporario,
            caminho,
        )

        return copy.deepcopy(registro)

    def registrar_resultado_experimento(
        self,
        solicitacao_id: str,
        resultado: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Persiste o resultado da execução remota de uma solicitação.

        A solicitação só pode sair de pronta_para_experimento uma
        vez por este caminho. O resultado é registrado como evidência;
        autorização de integração continua falsa.
        """
        solicitacao_id = self._texto(
            solicitacao_id,
            "solicitacao_id",
        )

        if not isinstance(resultado, dict):
            raise ValueError("resultado_experimento_invalido")

        caminho = (
            self.solicitacoes
            / f"{solicitacao_id}.json"
        )

        if not caminho.is_file():
            raise FileNotFoundError(
                "solicitacao_nao_encontrada"
            )

        try:
            registro = json.loads(
                caminho.read_text(encoding="utf-8")
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError(
                "solicitacao_invalida"
            ) from erro

        if not isinstance(registro, dict):
            raise ValueError("solicitacao_invalida")

        if registro.get("estado") != "pronta_para_experimento":
            raise ValueError(
                "solicitacao_nao_pronta_para_registro"
            )

        valor = resultado.get("valor")
        resultado_interno = (
            valor
            if isinstance(valor, dict)
            else resultado
        )

        if not isinstance(resultado_interno, dict):
            raise ValueError("resultado_experimento_invalido")

        estado_interno = resultado_interno.get("estado")
        estado_externo = resultado.get("estado")

        if (
            resultado.get("sucesso") is True
            and (
                estado_interno == "proposta_criada"
                or estado_externo == "solicitacao_executada"
            )
        ):
            estado_final = "experimento_concluido"
        elif estado_interno == "evolucao_rejeitada":
            estado_final = "evolucao_rejeitada"
        else:
            estado_final = "experimento_falhou"

        registro["estado"] = estado_final
        registro["resultado_experimento"] = copy.deepcopy(
            resultado
        )
        registro["resultado_registrado_em"] = self._timestamp()
        registro["experimento_id"] = (
            resultado_interno.get("experimento_id")
        )
        registro["commit_sha"] = (
            resultado_interno.get("commit_sha")
        )
        registro["comparacao"] = copy.deepcopy(
            resultado_interno.get("comparacao")
        )
        registro["candidato"] = copy.deepcopy(
            resultado_interno.get("candidato")
        )
        registro["proposta"] = copy.deepcopy(
            resultado_interno.get("proposta")
        )
        registro["execucao_solicitada"] = True
        registro["execucao_local"] = False
        registro["autorizacao_explicita"] = False
        registro["integracao_executada"] = False
        registro["stable_modificada"] = False

        temporario = caminho.with_name(
            caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                registro,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(
            temporario,
            caminho,
        )

        return copy.deepcopy(registro)

    def consultar(
        self,
        solicitacao_id: str,
    ) -> dict[str, Any]:
        caminho = (
            self.solicitacoes
            / f"{self._texto(solicitacao_id, 'solicitacao_id')}.json"
        )

        if not caminho.is_file():
            raise FileNotFoundError(
                "solicitacao_nao_encontrada"
            )

        return json.loads(
            caminho.read_text(encoding="utf-8")
        )


__all__ = [
    "SolicitacaoEvolucaoNixal",
]


if __name__ == "__main__":
    print("SolicitacaoEvolucaoNixal OK")
