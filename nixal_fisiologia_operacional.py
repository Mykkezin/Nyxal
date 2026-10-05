#!/usr/bin/env python3
"""NYXOS — M5.13 fisiologia operacional do residente."""

from __future__ import annotations

import copy
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any

from nixal_corpo_termico import avaliar_corpo_termico
from nixal_delta import RegistroDeltaNixOS


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_PADRAO = BASE_DIR / "fisiologia_operacional_nyxos.json"

MAX_HISTORICO = 20
TOLERANCIA_HEARTBEAT_SEGUNDOS = 2.0
AMOSTRAS_FEBRE = 3
AMOSTRAS_RECUPERACAO = 3


class FisiologiaOperacionalNixOS:
    """Deriva presença, heartbeat e estados térmicos compactos."""

    FONTE = "fisiologia_operacional_nyxos"
    VERSAO = "5.13.0"

    def __init__(
        self,
        *,
        intervalo_esperado_segundos: float = 5.0,
        arquivo: str | Path = ARQUIVO_PADRAO,
        delta_nyxos: RegistroDeltaNixOS | None = None,
    ) -> None:
        if intervalo_esperado_segundos <= 0:
            raise ValueError(
                "intervalo_esperado_precisa_ser_positivo"
            )

        self.intervalo_esperado_segundos = float(
            intervalo_esperado_segundos
        )
        self.arquivo = Path(arquivo)
        self.delta_nyxos = delta_nyxos
        self._historico = deque(
            self._carregar_historico(),
            maxlen=MAX_HISTORICO,
        )
        self._estado_fisiologico = "inicializando"
        self._amostras_muito_quente = 0
        self._amostras_recuperacao = 0
        self._reconstruir_estado_persistido()

    def _carregar_historico(self) -> list[dict[str, Any]]:
        if not self.arquivo.is_file():
            return []

        try:
            dados = json.loads(
                self.arquivo.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return []

        if not isinstance(dados, dict):
            return []

        historico = dados.get("historico", [])
        if not isinstance(historico, list):
            return []

        return [
            copy.deepcopy(item)
            for item in historico
            if isinstance(item, dict)
        ][-MAX_HISTORICO:]

    def _salvar(self) -> None:
        self.arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporario = self.arquivo.with_name(
            self.arquivo.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                {
                    "versao": self.VERSAO,
                    "origem": self.FONTE,
                    "historico": list(
                        self._historico
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(
            temporario,
            self.arquivo,
        )

    def _reconstruir_estado_persistido(
        self,
    ) -> None:
        if not self._historico:
            return

        estados = [
            item.get("termico", {}).get("estado_termico")
            for item in self._historico
            if isinstance(item, dict)
        ]

        consecutivas_muito_quente = 0
        for estado in reversed(estados):
            if estado == "muito_quente":
                consecutivas_muito_quente += 1
            else:
                break

        if consecutivas_muito_quente >= AMOSTRAS_FEBRE:
            self._estado_fisiologico = "febre"
            self._amostras_muito_quente = consecutivas_muito_quente
            return

        ultimo_estado = estados[-1] if estados else None
        if ultimo_estado in {"quente", "muito_quente"}:
            self._estado_fisiologico = "estresse_termico"
            self._amostras_muito_quente = consecutivas_muito_quente
        elif ultimo_estado in {"normal", "fria"}:
            ultimo_fisiologico = self._historico[-1].get(
                "estado_fisiologico"
            )
            if ultimo_fisiologico == "febre":
                self._estado_fisiologico = "recuperacao"
                self._amostras_recuperacao = 1
            else:
                self._estado_fisiologico = "normal"

    def _heartbeat(
        self,
        agora: float,
    ) -> dict[str, Any]:
        anterior = (
            self._historico[-1]
            if self._historico
            else None
        )
        timestamp_anterior = (
            anterior.get("timestamp")
            if isinstance(anterior, dict)
            else None
        )

        if not isinstance(
            timestamp_anterior,
            (int, float),
        ):
            return {
                "estado": "inicializando",
                "intervalo_segundos": None,
                "desvio_segundos": None,
            }

        intervalo = max(
            0.0,
            agora - float(timestamp_anterior),
        )
        desvio = round(
            intervalo
            - self.intervalo_esperado_segundos,
            3,
        )
        regular = intervalo <= (
            self.intervalo_esperado_segundos
            + TOLERANCIA_HEARTBEAT_SEGUNDOS
        )

        return {
            "estado": (
                "regular"
                if regular
                else "atrasado"
            ),
            "intervalo_segundos": round(
                intervalo,
                3,
            ),
            "desvio_segundos": desvio,
        }

    def _atualizar_estado_febre(
        self,
        estado_termico: str,
    ) -> str:
        if estado_termico == "muito_quente":
            self._amostras_muito_quente += 1
            self._amostras_recuperacao = 0
        elif estado_termico in {
            "quente",
            "normal",
            "fria",
        }:
            self._amostras_muito_quente = 0

        if self._estado_fisiologico == "febre":
            if estado_termico in {
                "normal",
                "fria",
            }:
                self._amostras_recuperacao += 1
            else:
                self._amostras_recuperacao = 0

            if (
                self._amostras_recuperacao
                >= AMOSTRAS_RECUPERACAO
            ):
                self._estado_fisiologico = "normal"
                self._amostras_recuperacao = 0
            else:
                self._estado_fisiologico = "recuperacao"

            return self._estado_fisiologico

        if (
            self._amostras_muito_quente
            >= AMOSTRAS_FEBRE
        ):
            self._estado_fisiologico = "febre"
            return self._estado_fisiologico

        if estado_termico == "muito_quente":
            self._estado_fisiologico = "estresse_termico"
        elif estado_termico == "quente":
            self._estado_fisiologico = "estresse_termico"
        elif estado_termico in {
            "normal",
            "fria",
        }:
            self._estado_fisiologico = "normal"
        else:
            self._estado_fisiologico = "sem_sinal"

        return self._estado_fisiologico

    def registrar_ciclo(
        self,
        *,
        estado_corpo: dict[str, Any] | None = None,
        timestamp: float | None = None,
        sucesso: bool = True,
    ) -> dict[str, Any]:
        agora = (
            time.time()
            if timestamp is None
            else float(timestamp)
        )

        heartbeat = self._heartbeat(
            agora
        )

        if isinstance(
            estado_corpo,
            dict,
        ):
            termico = avaliar_corpo_termico(
                estado_corpo
            )
        else:
            termico = {
                "sucesso": False,
                "estado": (
                    "sensores_termicos_indisponiveis"
                ),
                "estado_termico": "indisponivel",
                "temperatura_maxima_c": None,
            }

        estado_termico = str(
            termico.get(
                "estado_termico",
                "indisponivel",
            )
        )

        estado_anterior = (
            self._estado_fisiologico
        )

        estado_atual = (
            self._atualizar_estado_febre(
                estado_termico
            )
        )

        registro = {
            "timestamp": agora,
            "sucesso_ciclo": bool(sucesso),
            "heartbeat": heartbeat,
            "termico": {
                "sucesso": bool(
                    termico.get("sucesso")
                ),
                "estado": termico.get(
                    "estado"
                ),
                "temperatura_maxima_c": (
                    termico.get(
                        "temperatura_maxima_c"
                    )
                ),
                "estado_termico": (
                    estado_termico
                ),
            },
            "estado_fisiologico": (
                estado_atual
            ),
            "presenca_ativa": bool(
                sucesso
            ),
        }

        self._historico.append(
            copy.deepcopy(
                registro
            )
        )
        self._salvar()

        if (
            estado_atual
            != estado_anterior
            and self.delta_nyxos
            is not None
        ):
            try:
                delta = (
                    RegistroDeltaNixOS.criar_evento(
                        tipo="sistema",
                        estado_anterior={
                            "fisiologia": (
                                estado_anterior
                            )
                        },
                        estado_novo={
                            "fisiologia": (
                                estado_atual
                            )
                        },
                        causa=(
                            "transicao_fisiologica_observada"
                        ),
                        evidencias=[
                            {
                                "estado_termico": (
                                    estado_termico
                                ),
                                "heartbeat": (
                                    heartbeat.get(
                                        "estado"
                                    )
                                ),
                                "temperatura_maxima_c": (
                                    termico.get(
                                        "temperatura_maxima_c"
                                    )
                                ),
                            }
                        ],
                        resultado={
                            "presenca_ativa": (
                                bool(sucesso)
                            )
                        },
                    )
                )
                self.delta_nyxos.registrar(
                    delta
                )
            except Exception:
                pass

        return {
            "sucesso": True,
            "estado": "fisiologia_observada",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "heartbeat": heartbeat,
            "termico": registro["termico"],
            "estado_fisiologico": (
                estado_atual
            ),
            "presenca_ativa": bool(
                sucesso
            ),
            "historico_ciclos": len(
                self._historico
            ),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }

    def contexto(self) -> dict[str, Any]:
        ultimo = (
            copy.deepcopy(
                self._historico[-1]
            )
            if self._historico
            else None
        )

        return {
            "sucesso": True,
            "estado": "fisiologia_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado_fisiologico": (
                self._estado_fisiologico
            ),
            "historico_limitado": True,
            "historico_maximo": MAX_HISTORICO,
            "historico_ciclos": len(
                self._historico
            ),
            "ultimo": ultimo,
            "presenca_ativa": bool(
                ultimo
                and ultimo.get(
                    "presenca_ativa"
                )
            ),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = [
    "FisiologiaOperacionalNixOS"
]
