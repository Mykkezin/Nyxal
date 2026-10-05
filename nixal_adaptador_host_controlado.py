#!/usr/bin/env python3
"""NYXOS — M5.16 adaptador controlado de host.

Define a primeira fronteira executável segura para operações sem mutação física.
Ações potencialmente mutáveis permanecem bloqueadas porque nenhum executor
físico de host foi implementado nesta etapa.
"""

from __future__ import annotations

import copy
import json
import os
import platform
import time
from pathlib import Path
from typing import Any


class AdaptadorHostControladoNixOS:
    FONTE = "adaptador_host_controlado_nyxos"
    VERSAO = "5.16.0"

    ACOES_SOMENTE_LEITURA = {
        "observar",
        "aguardar",
        "preparar_gateway",
    }
    ACOES_FISICAS_NAO_IMPLEMENTADAS = {
        "reduzir_carga",
        "preservar_estado",
    }

    def __init__(
        self,
        *,
        arquivo: str | Path | None = None,
    ) -> None:
        self.arquivo = Path(arquivo) if arquivo is not None else None
        self._ultimo_resultado: dict[str, Any] | None = None

    def executar(self, acao: str) -> dict[str, Any]:
        if acao not in (
            self.ACOES_SOMENTE_LEITURA
            | self.ACOES_FISICAS_NAO_IMPLEMENTADAS
        ):
            raise ValueError("acao_nao_conhecida")

        if acao in self.ACOES_FISICAS_NAO_IMPLEMENTADAS:
            return self._bloquear(
                acao,
                "atuacao_fisica_nao_implementada",
            )

        if acao == "observar":
            resultado = {
                "pid": os.getpid(),
                "plataforma": platform.platform(),
                "python": platform.python_version(),
                "diretorio": str(Path.cwd()),
                "timestamp_epoch": time.time(),
            }
        elif acao == "aguardar":
            resultado = {
                "operacao": "aguardar",
                "efeito_fisico": False,
            }
        else:
            resultado = {
                "operacao": "preparar_gateway",
                "efeito_fisico": False,
            }

        saida = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "executado_controlado",
            "acao": acao,
            "executada": True,
            "atuacao_fisica": False,
            "mutacao_host": False,
            "modo": "controlado_somente_leitura",
            "resultado": copy.deepcopy(resultado),
            "governanca": {
                "autorizacao_explicita": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }
        self._ultimo_resultado = copy.deepcopy(saida)
        self._persistir()
        return copy.deepcopy(saida)

    def _bloquear(
        self,
        acao: str,
        motivo: str,
    ) -> dict[str, Any]:
        saida = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "bloqueado",
            "acao": acao,
            "motivo": motivo,
            "executada": False,
            "atuacao_fisica": False,
            "mutacao_host": False,
            "modo": "controlado_somente_leitura",
            "governanca": {
                "autorizacao_explicita": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }
        self._ultimo_resultado = copy.deepcopy(saida)
        self._persistir()
        return copy.deepcopy(saida)

    def __call__(self, acao: str) -> dict[str, Any]:
        return self.executar(acao)

    def _persistir(self) -> None:
        if self.arquivo is None or self._ultimo_resultado is None:
            return
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo.write_text(
            json.dumps(
                self._ultimo_resultado,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "adaptador_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "modo": "controlado_somente_leitura",
            "acoes_somente_leitura": sorted(self.ACOES_SOMENTE_LEITURA),
            "acoes_fisicas_nao_implementadas": sorted(
                self.ACOES_FISICAS_NAO_IMPLEMENTADAS
            ),
            "atuacao_fisica_habilitada": False,
            "mutacao_host_habilitada": False,
            "ultimo_resultado": copy.deepcopy(self._ultimo_resultado),
        }


__all__ = ["AdaptadorHostControladoNixOS"]
