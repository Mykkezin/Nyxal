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
from nixal_auto_avaliacao_ae3 import AutoAvaliacaoAE3
from nixal_ciclo_evolucao_ae4 import CicloEvolucaoResidenteAE4
from nixal_descoberta_continua_ae5 import DescobertaContinuaGovernadaAE5
from nixal_fisiologia_operacional import FisiologiaOperacionalNixOS
from nixal_presenca_maquina import PresencaMaquinaNixOS


class CicloResidenteNixOS:
    """Orquestra a residência controlada do ciclo operacional."""

    FONTE = "ciclo_residente_nyxos"
    VERSAO = "5.7.2"

    def __init__(
        self,
        runtime: Any,
        persistencia: Any | None = None,
        auto_evolucao: AutoEvolucaoGovernadaNixOS | None = None,
        auto_experimento: AutoExperimentoIsoladoAE2 | None = None,
        auto_avaliacao: AutoAvaliacaoAE3 | None = None,
        ciclo_evolucao_ae4: CicloEvolucaoResidenteAE4 | None = None,
        descoberta_continua_ae5: DescobertaContinuaGovernadaAE5 | None = None,
        fisiologia_operacional: FisiologiaOperacionalNixOS | None = None,
        presenca_maquina: PresencaMaquinaNixOS | None = None,
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
        self.auto_avaliacao = auto_avaliacao
        self.ciclo_evolucao_ae4 = ciclo_evolucao_ae4
        self.descoberta_continua_ae5 = descoberta_continua_ae5
        self.fisiologia_operacional = fisiologia_operacional
        self.presenca_maquina = presenca_maquina
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
            "auto_avaliacao_ae3_habilitada": self.auto_avaliacao is not None,
            "ciclo_evolucao_ae4_habilitado": bool(
                self.ciclo_evolucao_ae4 is not None
                and self.ciclo_evolucao_ae4.habilitada
            ),
            "descoberta_continua_ae5_habilitada": bool(
                self.descoberta_continua_ae5 is not None
                and self.descoberta_continua_ae5.habilitada
            ),
            "fisiologia_operacional_habilitada": (
                self.fisiologia_operacional is not None
            ),
            "presenca_maquina_habilitada": (
                self.presenca_maquina is not None
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

    @staticmethod
    def _extrair_estado_corpo(
        resultado: dict[str, Any],
    ) -> dict[str, Any] | None:
        valor = resultado.get("valor")
        if not isinstance(valor, dict):
            return None

        etapas = valor.get("etapas")
        if not isinstance(etapas, list):
            return None

        for etapa in etapas:
            if not isinstance(etapa, dict):
                continue
            if etapa.get("etapa") != "percepcao":
                continue
            estado = etapa.get("estado")
            if isinstance(estado, dict):
                return estado

        return None
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

        if self.presenca_maquina is not None:
            try:
                self.presenca_maquina.iniciar()
            except Exception:
                pass

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
            if self.presenca_maquina is not None:
                try:
                    presenca = self.presenca_maquina.heartbeat(
                        estado_residente=self._estado,
                    )
                except Exception as erro:
                    presenca = {
                        "sucesso": False,
                        "estado": "presenca_maquina_falhou",
                        "origem": self.presenca_maquina.FONTE,
                        "motivo": f"{type(erro).__name__}: {erro}",
                    }
                resultado["presenca_maquina"] = copy.deepcopy(presenca)

            if self.fisiologia_operacional is not None:
                try:
                    fisiologia = self.fisiologia_operacional.registrar_ciclo(
                        estado_corpo=self._extrair_estado_corpo(resultado),
                        sucesso=resultado.get("sucesso") is True,
                    )
                except Exception as erro:
                    fisiologia = {
                        "sucesso": False,
                        "estado": "fisiologia_falhou",
                        "origem": self.fisiologia_operacional.FONTE,
                        "motivo": f"{type(erro).__name__}: {erro}",
                        "autorizacao_explicita": False,
                        "integracao_executada": False,
                        "arquitetura_modificada": False,
                        "conhecimento_permanente": False,
                    }
                resultado["fisiologia"] = copy.deepcopy(fisiologia)
            if self.ciclo_evolucao_ae4 is not None:
                try:
                    auto_evolucao_ae4_resultado = (
                        self.ciclo_evolucao_ae4.processar_ciclo(resultado)
                    )
                except Exception as erro:
                    auto_evolucao_ae4_resultado = {
                        "sucesso": False,
                        "estado": "auto_evolucao_ae4_falhou",
                        "origem": self.ciclo_evolucao_ae4.FONTE,
                        "motivo": f"{type(erro).__name__}: {erro}",
                        "autorizacao_explicita": False,
                        "integracao_executada": False,
                        "stable_modificada": False,
                        "arquitetura_modificada": False,
                        "conhecimento_permanente": False,
                    }

                resultado["auto_evolucao_ae4"] = copy.deepcopy(
                    auto_evolucao_ae4_resultado
                )

                if self.descoberta_continua_ae5 is not None:
                    try:
                        auto_descoberta_ae5_resultado = (
                            self.descoberta_continua_ae5.processar(
                                auto_evolucao_ae4_resultado
                            )
                        )
                    except Exception as erro:
                        auto_descoberta_ae5_resultado = {
                            "sucesso": False,
                            "estado": "descoberta_continua_ae5_falhou",
                            "origem": self.descoberta_continua_ae5.FONTE,
                            "motivo": f"{type(erro).__name__}: {erro}",
                            "autorizacao_explicita": False,
                            "integracao_executada": False,
                            "stable_modificada": False,
                            "arquitetura_modificada": False,
                            "conhecimento_permanente": False,
                        }

                    resultado["auto_descoberta_ae5"] = copy.deepcopy(
                        auto_descoberta_ae5_resultado
                    )
            else:
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
                            "motivo": f"{type(erro).__name__}: {erro}",
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
                            "motivo": f"{type(erro).__name__}: {erro}",
                            "processada": False,
                            "autorizacao_explicita": False,
                            "integracao_executada": False,
                            "stable_modificada": False,
                            "arquitetura_modificada": False,
                        }

                    resultado["auto_experimento_ae2"] = copy.deepcopy(
                        auto_experimento_resultado
                    )

                if self.auto_avaliacao is not None:
                    try:
                        if (
                            isinstance(resultado.get("auto_experimento_ae2"), dict)
                            and resultado["auto_experimento_ae2"].get("processada") is True
                        ):
                            auto_avaliacao_resultado = self.auto_avaliacao.avaliar(
                                resultado["auto_experimento_ae2"]
                            )
                        else:
                            auto_avaliacao_resultado = {
                                "sucesso": True,
                                "estado": "sem_experimento_para_avaliar",
                                "origem": self.auto_avaliacao.FONTE,
                                "versao": self.auto_avaliacao.VERSAO,
                                "autorizacao_explicita": False,
                                "integracao_executada": False,
                                "stable_modificada": False,
                                "arquitetura_modificada": False,
                                "conhecimento_permanente": False,
                            }
                    except Exception as erro:
                        auto_avaliacao_resultado = {
                            "sucesso": False,
                            "estado": "auto_avaliacao_ae3_falhou",
                            "origem": self.auto_avaliacao.FONTE,
                            "motivo": f"{type(erro).__name__}: {erro}",
                            "autorizacao_explicita": False,
                            "integracao_executada": False,
                            "stable_modificada": False,
                            "arquitetura_modificada": False,
                            "conhecimento_permanente": False,
                        }

                    resultado["auto_avaliacao_ae3"] = copy.deepcopy(
                        auto_avaliacao_resultado
                    )

            # O modo residente contínuo não pode acumular resultados em RAM.
            # O executor nunca retorna enquanto max_ciclos=None; manter somente
            # o último ciclo preserva observabilidade sem crescimento ilimitado.
            self._ultimo_resultado = resultado

            if max_ciclos is None:
                resultados.clear()

            resultados.append(self._ultimo_resultado)

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

        if self.presenca_maquina is not None:
            try:
                self.presenca_maquina.encerrar(
                    motivo=f"residente_{self._estado}",
                )
            except Exception:
                pass

        return resultados


__all__ = ["CicloResidenteNixOS"]
