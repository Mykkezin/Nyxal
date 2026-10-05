#!/usr/bin/env python3
"""
NYXOS — CICLO OPERACIONAL RESIDENTE M5.7

Mantém o Runtime da Nyxal executando ciclos de forma contínua,
interrompível e observável.

Importante:
- não inicia evolução remota por conta própria;
- não autoriza integração;
- não modifica stable;
- não executa comandos externos;
- usa o Runtime e os gates existentes.
"""

from __future__ import annotations

import copy
import threading
import time
from typing import Any

from nixal_auto_evolucao import AutoEvolucaoGovernadaNixOS
from nixal_auto_experimento_ae2 import AutoExperimentoIsoladoAE2


class CicloResidenteNixOS:
    """Orquestra a residência controlada do ciclo operacional."""

    FONTE = "ciclo_residente_nyxos"
    VERSAO = "5.7.0"

    def __init__(
        self,
        runtime: Any,
        persistencia: Any | None = None,
        auto_evolucao: AutoEvolucaoGovernadaNixOS | None = None,
        auto_experimento: AutoExperimentoIsoladoAE2 | None = None,
        *,
        intervalo_segundos: float = 5.0,
        parar_em_erro: bool = True,
    ) -> None:
        if not hasattr(runtime, "executar_ciclo") or not callable(
            runtime.executar_ciclo
        ):
            raise TypeError("runtime_precisa_executar_ciclo")

        if intervalo_segundos < 0:
            raise ValueError("intervalo_segundos_nao_pode_ser_negativo")

        self.runtime = runtime
        self.persistencia = persistencia
        self.auto_evolucao = auto_evolucao
        self.auto_experimento = auto_experimento
        self.intervalo_segundos = float(intervalo_segundos)
        self.parar_em_erro = bool(parar_em_erro)

        self._parar = threading.Event()
        self._estado = "parado"
        self._ultimo_resultado: dict[str, Any] | None = None
        self._quantidade_ciclos = 0
        self._iniciado_em: str | None = None
        self._encerrado_em: str | None = None

    @staticmethod
    def _agora() -> str:
        return time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(),
        )

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "residente_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado_residente": self._estado,
            "ciclos_executados": self._quantidade_ciclos,
            "iniciado_em": self._iniciado_em,
            "encerrado_em": self._encerrado_em,
            "ultimo_resultado": copy.deepcopy(
                self._ultimo_resultado
            ),
            "intervalo_segundos": self.intervalo_segundos,
            "parar_em_erro": self.parar_em_erro,
            "auto_evolution_habilitada": self.auto_evolucao is not None,
            "auto_evolution_execucao_automatica": bool(
                self.auto_experimento is not None
                and self.auto_experimento.habilitada
            ),
            "auto_experimento_ae2_habilitado": bool(
                self.auto_experimento is not None
                and self.auto_experimento.habilitada
            ),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
        }

    def parar(self) -> dict[str, Any]:
        self._parar.set()
        return {
            "sucesso": True,
            "estado": "interrupcao_solicitada",
            "origem": self.FONTE,
            "versao": self.VERSAO,
        }

    def _persistir_estado(
        self,
        estado: str,
        ciclo: dict[str, Any] | None = None,
    ) -> None:
        if self.persistencia is None:
            return

        registrar = getattr(
            self.persistencia,
            "registrar",
            None,
        )
        if not callable(registrar):
            return

        try:
            registrar(
                ciclo=ciclo,
                estado=estado,
            )
        except Exception:
            # Persistência residente não deve ocultar o resultado do
            # Runtime. O status continua observável no contexto local.
            pass

    def executar(
        self,
        max_ciclos: int | None = None,
    ) -> list[dict[str, Any]]:
        if max_ciclos is not None:
            if not isinstance(max_ciclos, int) or max_ciclos < 1:
                raise ValueError("max_ciclos_deve_ser_inteiro_positivo")

        self._parar.clear()
        self._estado = "executando"
        self._iniciado_em = self._agora()
        self._encerrado_em = None
        resultados: list[dict[str, Any]] = []
        ciclos_nesta_execucao = 0

        self._persistir_estado("residente_iniciado")

        while (
            max_ciclos is None
            or ciclos_nesta_execucao < max_ciclos
        ):
            if self._parar.is_set():
                self._estado = "interrompido"
                break

            try:
                resultado = self.runtime.executar_ciclo()
            except Exception as erro:
                resultado = {
                    "sucesso": False,
                    "estado": "erro",
                    "origem": self.FONTE,
                    "motivo": f"{type(erro).__name__}: {erro}",
                    "auto_evolution_habilitada": False,
                    "autorizacao_explicita": False,
                    "integracao_executada": False,
                    "arquitetura_modificada": False,
                }

            resultado = copy.deepcopy(
                resultado
                if isinstance(resultado, dict)
                else {
                    "sucesso": False,
                    "estado": "erro",
                    "origem": self.FONTE,
                    "motivo": "Runtime não retornou um objeto válido.",
                }
            )

            ciclos_nesta_execucao += 1
            self._quantidade_ciclos += 1
            auto_evolucao_resultado = None
            if self.auto_evolucao is not None:
                try:
                    auto_evolucao_resultado = (
                        self.auto_evolucao.avaliar_ciclo(resultado)
                    )
                except Exception as erro:
                    auto_evolucao_resultado = {
                        "sucesso": False,
                        "estado": "auto_evolucao_ae1_falhou",
                        "origem": self.auto_evolucao.FONTE,
                        "motivo": (
                            f"{type(erro).__name__}: {erro}"
                        ),
                        "autorizacao_explicita": False,
                        "integracao_executada": False,
                        "arquitetura_modificada": False,
                    }

                resultado["auto_evolucao_ae1"] = copy.deepcopy(
                    auto_evolucao_resultado
                )

            if self.auto_experimento is not None:
                try:
                    auto_experimento_resultado = (
                        self.auto_experimento.processar_pendentes()
                    )
                except Exception as erro:
                    auto_experimento_resultado = {
                        "sucesso": False,
                        "estado": "auto_experimento_ae2_falhou",
                        "origem": self.auto_experimento.FONTE,
                        "motivo": (
                            f"{type(erro).__name__}: {erro}"
                        ),
                        "processada": False,
                        "autorizacao_explicita": False,
                        "integracao_executada": False,
                        "stable_modificada": False,
                        "arquitetura_modificada": False,
                    }

                resultado["auto_experimento_ae2"] = copy.deepcopy(
                    auto_experimento_resultado
                )

            self._ultimo_resultado = copy.deepcopy(resultado)
            resultados.append(copy.deepcopy(resultado))

            self._persistir_estado(
                resultado.get("estado", "ciclo_processado"),
                resultado,
            )

            if (
                self.parar_em_erro
                and resultado.get("sucesso") is not True
            ):
                self._estado = "erro"
                break

            if (
                max_ciclos is not None
                and ciclos_nesta_execucao >= max_ciclos
            ):
                self._estado = "concluido"
                break

            if self._parar.wait(self.intervalo_segundos):
                self._estado = "interrompido"
                break

        if self._estado == "executando":
            self._estado = "interrompido"

        self._encerrado_em = self._agora()
        self._persistir_estado(
            f"residente_{self._estado}",
            self._ultimo_resultado,
        )

        return resultados


__all__ = ["CicloResidenteNixOS"]
