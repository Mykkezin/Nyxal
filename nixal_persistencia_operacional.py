#!/usr/bin/env python3
"""
NYXOS — PERSISTÊNCIA OPERACIONAL M5.3

Camada durável e mínima para continuidade do habitat NyxOS.

Esta camada:
- restaura estado operacional após reinício;
- grava de forma atômica;
- mantém histórico limitado;
- não executa comandos;
- não persiste conversa;
- não promove conhecimento;
- não modifica arquitetura.
"""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PersistenciaOperacionalNixOS:
    """Persistência durável do estado operacional do NyxOS."""

    FONTE = "persistencia_operacional_nyxos"
    VERSAO = "5.3.0"
    MAX_HISTORICO = 50

    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        self._dados = self._carregar()

        self._dados["inicializacoes"] = (
            int(self._dados.get("inicializacoes", 0)) + 1
        )
        self._dados["ultima_inicializacao"] = self._timestamp()

        # O contador de inicializações é persistido somente quando
        # uma instância é construída; ele representa continuidade
        # operacional e não conhecimento.
        self._salvar()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _estrutura_vazia(cls) -> dict[str, Any]:
        return {
            "versao": cls.VERSAO,
            "origem": cls.FONTE,
            "inicializacoes": 0,
            "ultima_inicializacao": None,
            "ultima_persistencia": None,
            "ultimo_ciclo": None,
            "ultimo_habitat": None,
            "historico": [],
        }

    @classmethod
    def _normalizar(cls, dados: Any) -> dict[str, Any]:
        if not isinstance(dados, dict):
            return cls._estrutura_vazia()

        if dados.get("versao") != cls.VERSAO:
            return cls._estrutura_vazia()

        inicializacoes = dados.get("inicializacoes", 0)
        if not isinstance(inicializacoes, int) or inicializacoes < 0:
            inicializacoes = 0

        historico = dados.get("historico", [])
        if not isinstance(historico, list):
            historico = []

        return {
            "versao": cls.VERSAO,
            "origem": cls.FONTE,
            "inicializacoes": inicializacoes,
            "ultima_inicializacao": dados.get("ultima_inicializacao"),
            "ultima_persistencia": dados.get("ultima_persistencia"),
            "ultimo_ciclo": copy.deepcopy(
                dados.get("ultimo_ciclo")
            ),
            "ultimo_habitat": copy.deepcopy(
                dados.get("ultimo_habitat")
            ),
            "historico": copy.deepcopy(
                historico[-cls.MAX_HISTORICO:]
            ),
        }

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho.is_file():
            return self._estrutura_vazia()

        try:
            dados = json.loads(
                self.caminho.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return self._estrutura_vazia()

        return self._normalizar(dados)

    def _salvar(self) -> None:
        self.caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporario = self.caminho.with_name(
            self.caminho.name + ".tmp"
        )

        temporario.write_text(
            json.dumps(
                self._dados,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        os.replace(
            temporario,
            self.caminho,
        )

    @staticmethod
    def _resumir_ciclo(ciclo: Any) -> dict[str, Any] | None:
        if not isinstance(ciclo, dict):
            return None

        return {
            "ciclo_id": ciclo.get("ciclo_id"),
            "estado": ciclo.get("estado"),
            "sucesso": ciclo.get("sucesso"),
            "iniciado_em": ciclo.get("iniciado_em"),
            "concluido_em": ciclo.get("concluido_em"),
        }

    @classmethod
    def _sanitizar_habitat(
        cls,
        habitat: Any,
    ) -> dict[str, Any] | None:
        if not isinstance(habitat, dict):
            return None

        host = habitat.get("host")
        recursos = habitat.get("recursos")

        host = host if isinstance(host, dict) else {}
        recursos = recursos if isinstance(recursos, dict) else {}

        cpu = recursos.get("cpu")
        memoria = recursos.get("memoria")
        armazenamento = recursos.get("armazenamento")
        processos = recursos.get("processos")

        return {
            "estado": habitat.get("estado"),
            "origem": habitat.get("origem"),
            "versao": habitat.get("versao"),
            "host": {
                "sistema": host.get("sistema"),
                "release": host.get("release"),
                "arquitetura": host.get("arquitetura"),
                "modo": "somente_leitura",
            },
            "recursos": {
                "cpu": {
                    "uso_percentual": (
                        cpu.get("uso_percentual")
                        if isinstance(cpu, dict)
                        else None
                    ),
                    "estado": (
                        cpu.get("estado")
                        if isinstance(cpu, dict)
                        else None
                    ),
                },
                "memoria": {
                    "uso_percentual": (
                        memoria.get("uso_percentual")
                        if isinstance(memoria, dict)
                        else None
                    ),
                    "usado_gb": (
                        memoria.get("usado_gb")
                        if isinstance(memoria, dict)
                        else None
                    ),
                    "total_gb": (
                        memoria.get("total_gb")
                        if isinstance(memoria, dict)
                        else None
                    ),
                },
                "armazenamento": {
                    "uso_percentual": (
                        armazenamento.get("uso_percentual")
                        if isinstance(armazenamento, dict)
                        else None
                    ),
                    "estado": (
                        armazenamento.get("estado")
                        if isinstance(armazenamento, dict)
                        else None
                    ),
                },
                "processos": processos,
                "uptime_segundos": recursos.get("uptime_segundos"),
                "processos_habitat": cls._sanitizar_processos(
                    recursos.get("processos_habitat")
                ),
            },
            "timestamp": habitat.get("timestamp"),
        }

    @staticmethod
    def _sanitizar_processos(
        processos: Any,
    ) -> dict[str, Any] | None:
        if not isinstance(processos, dict):
            return None

        entidades = processos.get("entidades")
        if not isinstance(entidades, list):
            entidades = []

        resumidas = []
        for entidade in entidades[:12]:
            if not isinstance(entidade, dict):
                continue

            resumidas.append(
                {
                    "id": entidade.get("id"),
                    "pid": entidade.get("pid"),
                    "nome": entidade.get("nome"),
                    "estado": entidade.get("estado"),
                    "uso_cpu_percentual": entidade.get(
                        "uso_cpu_percentual"
                    ),
                    "memoria_rss_mb": entidade.get(
                        "memoria_rss_mb"
                    ),
                }
            )

        return {
            "sucesso": processos.get("sucesso"),
            "estado": processos.get("estado"),
            "total": processos.get("total"),
            "limite": processos.get("limite"),
            "entidades": resumidas,
            "modo": "somente_leitura",
        }

    def registrar(
        self,
        *,
        ciclo: dict[str, Any] | None = None,
        habitat: dict[str, Any] | None = None,
        estado: str | None = None,
    ) -> dict[str, Any]:
        ciclo_resumo = self._resumir_ciclo(ciclo)
        habitat_resumo = self._sanitizar_habitat(habitat)

        if estado is None:
            if ciclo_resumo is not None:
                estado = ciclo_resumo.get("estado")
            elif habitat_resumo is not None:
                estado = habitat_resumo.get("estado")
            else:
                estado = "observado"

        agora = self._timestamp()

        self._dados["ultima_persistencia"] = agora

        if ciclo_resumo is not None:
            self._dados["ultimo_ciclo"] = ciclo_resumo

        if habitat_resumo is not None:
            self._dados["ultimo_habitat"] = habitat_resumo

        self._dados["historico"].append(
            {
                "em": agora,
                "estado": estado,
                "ciclo_id": (
                    ciclo_resumo.get("ciclo_id")
                    if ciclo_resumo is not None
                    else None
                ),
                "habitat_observado": habitat_resumo is not None,
            }
        )
        self._dados["historico"] = (
            self._dados["historico"][-self.MAX_HISTORICO:]
        )

        self._salvar()

        return {
            "sucesso": True,
            "estado": "persistencia_operacional_registrada",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "arquivo": str(self.caminho),
            "inicializacoes": self._dados["inicializacoes"],
            "ultima_persistencia": self._dados[
                "ultima_persistencia"
            ],
            "ciclo_id": (
                ciclo_resumo.get("ciclo_id")
                if ciclo_resumo is not None
                else None
            ),
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "persistencia_operacional_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "arquivo": str(self.caminho),
            "inicializacoes": self._dados["inicializacoes"],
            "ultima_inicializacao": self._dados[
                "ultima_inicializacao"
            ],
            "ultima_persistencia": self._dados[
                "ultima_persistencia"
            ],
            "ultimo_ciclo": copy.deepcopy(
                self._dados["ultimo_ciclo"]
            ),
            "ultimo_habitat": copy.deepcopy(
                self._dados["ultimo_habitat"]
            ),
            "quantidade_historico": len(
                self._dados["historico"]
            ),
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def recarregar(self) -> dict[str, Any]:
        self._dados = self._carregar()
        return self.contexto()


__all__ = ["PersistenciaOperacionalNixOS"]
