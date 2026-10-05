#!/usr/bin/env python3
"""NYXOS — M5.14 plano central de controle.

Transforma sinais observados do ciclo residente em um plano operacional
determinístico e auditável. Esta camada NÃO executa ações físicas, não
controla processos, não concede autorização e não altera arquitetura.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


class PlanoCentralControleNixOS:
    FONTE = "plano_central_controle_nyxos"
    VERSAO = "5.14.0"

    ACOES_CONHECIDAS = {
        "observar",
        "aguardar",
        "reduzir_carga",
        "preservar_estado",
        "preparar_gateway",
    }

    def __init__(self, *, arquivo: str | Path | None = None) -> None:
        self.arquivo = Path(arquivo) if arquivo is not None else None
        self._ultimo_plano: dict[str, Any] | None = None

    @staticmethod
    def _normalizar(objeto: Any) -> str:
        return json.dumps(
            objeto,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _id_plano(self, plano: dict[str, Any]) -> str:
        base = self._normalizar(plano)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _classificar_acao(
        self,
        *,
        estado_fisiologico: str,
        sucesso_ciclo: bool,
    ) -> str:
        if not sucesso_ciclo:
            return "preservar_estado"

        if estado_fisiologico == "febre":
            return "reduzir_carga"

        if estado_fisiologico == "estresse_termico":
            return "reduzir_carga"

        if estado_fisiologico == "recuperacao":
            return "aguardar"

        if estado_fisiologico in {"inicializando", "sem_sinal"}:
            return "observar"

        return "aguardar"

    def gerar_plano(
        self,
        *,
        ciclo: dict[str, Any],
        fisiologia: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(ciclo, dict):
            raise TypeError("ciclo_invalido")

        fisiologia = (
            fisiologia
            if isinstance(fisiologia, dict)
            else ciclo.get("fisiologia")
        )
        if not isinstance(fisiologia, dict):
            fisiologia = {}

        estado_fisiologico = str(
            fisiologia.get("estado_fisiologico", "sem_sinal")
        )
        sucesso_ciclo = ciclo.get("sucesso") is True
        acao = self._classificar_acao(
            estado_fisiologico=estado_fisiologico,
            sucesso_ciclo=sucesso_ciclo,
        )

        plano = {
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado_observado": {
                "fisiologia": estado_fisiologico,
                "heartbeat": copy.deepcopy(fisiologia.get("heartbeat")),
                "termico": copy.deepcopy(fisiologia.get("termico")),
                "sucesso_ciclo": sucesso_ciclo,
            },
            "decisao": {
                "acao_planejada": acao,
                "motivo": (
                    "estado_fisiologico_observado"
                    if sucesso_ciclo
                    else "falha_do_ciclo_exige_preservacao"
                ),
            },
            "execucao": {
                "planejada": False,
                "executada": False,
                "gateway_atuacao": False,
            },
            "governanca": {
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
                "arquitetura_modificada": False,
                "conhecimento_permanente": False,
            },
        }
        plano["plano_id"] = self._id_plano(plano)

        self._ultimo_plano = copy.deepcopy(plano)
        if self.arquivo is not None:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            self.arquivo.write_text(
                json.dumps(
                    plano,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        return copy.deepcopy(plano)

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "plano_central_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "ultimo_plano": copy.deepcopy(self._ultimo_plano),
            "acoes_conhecidas": sorted(self.ACOES_CONHECIDAS),
            "execucao_fisica_habilitada": False,
            "gateway_atuacao_habilitado": False,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
        }


__all__ = ["PlanoCentralControleNixOS"]
