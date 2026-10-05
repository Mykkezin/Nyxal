#!/usr/bin/env python3
"""
NYXAL — AUTO-EXPERIMENTO AE2

Executa automaticamente somente solicitações formais já prontas,
sob uma política explícita e reutilizando os gates N9 existentes.

Não:
- gera código;
- executa código localmente;
- autoriza integração;
- modifica stable;
- faz merge;
- promove conhecimento permanente;
- faz retry automático.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


class AutoExperimentoIsoladoAE2:
    """Coordena a execução automática e limitada de experimentos N9."""

    FONTE = "auto_experimento_isolado_ae2"
    VERSAO = "AE2.0.0"
    MAX_POR_CICLO = 1

    def __init__(
        self,
        runtime: Any,
        solicitacao_evolucao: Any,
        *,
        habilitada: bool = False,
        max_por_ciclo: int = MAX_POR_CICLO,
    ) -> None:
        if not hasattr(runtime, "executar_solicitacao_evolucao_remota") or not callable(
            runtime.executar_solicitacao_evolucao_remota
        ):
            raise TypeError("runtime_precisa_executar_solicitacao_evolucao_remota")

        if not hasattr(solicitacao_evolucao, "solicitacoes"):
            raise TypeError("solicitacao_precisa_expor_diretorio")

        if (
            not isinstance(max_por_ciclo, int)
            or max_por_ciclo < 1
            or max_por_ciclo > 1
        ):
            raise ValueError("max_por_ciclo_deve_ser_1")

        self.runtime = runtime
        self.solicitacao_evolucao = solicitacao_evolucao
        self.habilitada = bool(habilitada)
        self.max_por_ciclo = max_por_ciclo
        self._ultimo_resultado: dict[str, Any] | None = None

    @staticmethod
    def _carregar(caminho: Path) -> dict[str, Any] | None:
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return dados if isinstance(dados, dict) else None

    def _listar_pendentes(self, limite: int | None = None) -> list[dict[str, Any]]:
        limite_efetivo = self.max_por_ciclo if limite is None else limite
        if not isinstance(limite_efetivo, int) or limite_efetivo < 1:
            raise ValueError("limite_invalido")

        diretorio = Path(self.solicitacao_evolucao.solicitacoes)
        if not diretorio.is_dir():
            return []

        registros: list[dict[str, Any]] = []
        for caminho in diretorio.glob("solicitacao-*.json"):
            registro = self._carregar(caminho)
            if registro is None:
                continue
            if registro.get("estado") != "pronta_para_experimento":
                continue
            registros.append(registro)

        registros.sort(
            key=lambda item: (
                str(item.get("criada_em") or ""),
                str(item.get("solicitacao_id") or ""),
            )
        )
        return registros[:limite_efetivo]

    def _validar_politica(
        self,
        solicitacao: dict[str, Any],
    ) -> str | None:
        if solicitacao.get("estado") != "pronta_para_experimento":
            return "solicitacao_nao_pronta"

        artefato = solicitacao.get("artefato_origem")
        if not isinstance(artefato, str) or not artefato.strip():
            return "artefato_ausente"

        caminho = Path(artefato).expanduser().resolve()
        if not caminho.is_file():
            return "artefato_inexistente"
        if caminho.suffix != ".py":
            return "artefato_nao_python"

        try:
            caminho.relative_to(
                Path(self.solicitacao_evolucao.repositorio).resolve()
            )
        except ValueError:
            return "artefato_fora_do_repositorio"

        if solicitacao.get("execucao_local") is not False:
            return "execucao_local_nao_permitida"

        if solicitacao.get("autorizacao_explicita") is not False:
            return "autorizacao_invalida"

        if solicitacao.get("integracao_executada") is not False:
            return "integracao_nao_permitida"

        if solicitacao.get("stable_modificada") is not False:
            return "stable_modificada_invalida"

        hipotese = solicitacao.get("hipotese")
        if not isinstance(hipotese, dict):
            return "hipotese_formal_invalida"

        if (
            hipotese.get("estado") != "provisoria"
            or hipotese.get("confirmada") is not False
            or hipotese.get("testada") is not False
        ):
            return "hipotese_nao_elegivel"

        objetivo = solicitacao.get("objetivo")
        metrica = solicitacao.get("metrica")
        direcao = solicitacao.get("direcao_melhor")
        if (
            not isinstance(objetivo, str)
            or not objetivo.strip()
            or not isinstance(metrica, str)
            or not metrica.strip()
            or direcao not in {"maior", "menor"}
            or solicitacao.get("baseline") is None
        ):
            return "parametros_formais_incompletos"

        return None

    def processar_pendentes(self) -> dict[str, Any]:
        """Processa no máximo uma solicitação pronta neste ciclo."""
        if not self.habilitada:
            resultado = {
                "sucesso": True,
                "estado": "ae2_desabilitada",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "processada": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        pendentes = self._listar_pendentes()
        if not pendentes:
            resultado = {
                "sucesso": True,
                "estado": "sem_solicitacao_pendente",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "processada": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        solicitacao = pendentes[0]
        motivo = self._validar_politica(solicitacao)
        if motivo is not None:
            resultado = {
                "sucesso": False,
                "estado": "solicitacao_bloqueada_pela_politica",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "solicitacao_id": solicitacao.get("solicitacao_id"),
                "motivo": motivo,
                "processada": False,
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        solicitacao_id = str(solicitacao["solicitacao_id"])
        try:
            remoto = self.runtime.executar_solicitacao_evolucao_remota(
                solicitacao_id
            )
        except Exception as erro:
            remoto = {
                "sucesso": False,
                "estado": "ae2_execucao_nao_concluida",
                "origem": self.FONTE,
                "solicitacao_id": solicitacao_id,
                "motivo": f"{type(erro).__name__}: {erro}",
            }

        sucesso = bool(
            isinstance(remoto, dict)
            and remoto.get("sucesso") is True
        )
        resultado = {
            "sucesso": sucesso,
            "estado": (
                "experimento_processado"
                if sucesso
                else "experimento_processado_com_falha"
            ),
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "solicitacao_id": solicitacao_id,
            "processada": True,
            "valor": copy.deepcopy(remoto),
            "retry_automatico": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }
        self._ultimo_resultado = copy.deepcopy(resultado)
        return resultado

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "ae2_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "execucao_experimental_automatica": self.habilitada,
            "max_por_ciclo": self.max_por_ciclo,
            "ultimo_resultado": copy.deepcopy(self._ultimo_resultado),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = ["AutoExperimentoIsoladoAE2"]
