#!/usr/bin/env python3

"""
NIXAL / NYXAL RUNTIME — FASE 01

Objetivo:
    Criar o primeiro coordenador operacional persistente da Nyxal.

Escopo desta fase:
    percepção corporal
        ↓
    estado interno
        ↓
    diagnóstico
        ↓
    necessidade
        ↓
    priorização determinística
        ↓
    decisão controlada
        ↓
    ação autorizada de persistência do estado corporal
        ↓
    observação do resultado
        ↓
    registro do ciclo

Esta fase NÃO:
    - modifica código da arquitetura;
    - modifica planta_nixal/;
    - executa autoalteração;
    - promove conhecimento permanente;
    - usa Qwen para decidir a ação;
    - depende da interface conversacional;
    - guarda memória conversacional.

A finalidade é provar o LOOP operacional em uma implementação mínima,
observável, interrompível e determinística.
"""

from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import corpo_nixal
from nixal_estado_composicao import EstadoCompostoAutorreprentacaoNixal
from nixal_necessidades_internas import NecessidadesInternasNixal


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_ESTADO_RUNTIME = BASE_DIR / "estado_nyxal_runtime.json"
ARQUIVO_LOG_RUNTIME = BASE_DIR / "log_nyxal_runtime.json"


class NyxalRuntime:
    """Coordenador mínimo do ciclo operacional da Nyxal."""

    FONTE = "nyxal_runtime"
    VERSAO = "fase_01"

    ESTADOS = {
        "iniciado",
        "percebido",
        "diagnosticado",
        "necessidade_detectada",
        "decidido",
        "acao_executada",
        "resultado_observado",
        "ciclo_concluido",
        "erro",
    }

    ACOES_AUTORIZADAS = {
        "registrar_estado_corpo",
    }

    def __init__(
        self,
        perceber_corpo: Callable[..., Any] | None = None,
        estado: EstadoCompostoAutorreprentacaoNixal | None = None,
        necessidades: NecessidadesInternasNixal | None = None,
        arquivo_estado: Path = ARQUIVO_ESTADO_RUNTIME,
        arquivo_log: Path = ARQUIVO_LOG_RUNTIME,
    ) -> None:
        if perceber_corpo is None:
            perceber_corpo = corpo_nixal.perceber_corpo

        if not callable(perceber_corpo):
            raise TypeError("perceber_corpo deve ser chamável")

        if estado is not None and not isinstance(
            estado,
            EstadoCompostoAutorreprentacaoNixal,
        ):
            raise TypeError(
                "estado deve ser uma instância de "
                "EstadoCompostoAutorreprentacaoNixal"
            )

        if necessidades is not None and not isinstance(
            necessidades,
            NecessidadesInternasNixal,
        ):
            raise TypeError(
                "necessidades deve ser uma instância de "
                "NecessidadesInternasNixal"
            )

        self.perceber_corpo = perceber_corpo
        self.estado = (
            estado
            if estado is not None
            else EstadoCompostoAutorreprentacaoNixal()
        )
        self.necessidades = (
            necessidades
            if necessidades is not None
            else NecessidadesInternasNixal()
        )
        self.arquivo_estado = Path(arquivo_estado)
        self.arquivo_log = Path(arquivo_log)
        self._cpu_anterior: Any = None
        self._ultimo_ciclo: dict[str, Any] | None = None

    # ============================================================
    # CICLO
    # ============================================================

    def executar_ciclo(self) -> dict[str, Any]:
        ciclo_id = self._gerar_id_ciclo()
        iniciado_em = self._agora_iso()
        etapas: list[dict[str, Any]] = []

        self._registrar_etapa(etapas, "iniciado", {"ciclo_id": ciclo_id})

        try:
            estado_corpo, cpu_atual = self.perceber_corpo(
                self._cpu_anterior
            )
            self._cpu_anterior = cpu_atual
            etapas.append(
                {
                    "etapa": "percepcao",
                    "sucesso": isinstance(estado_corpo, dict),
                    "estado": deepcopy(estado_corpo),
                }
            )

            if not isinstance(estado_corpo, dict):
                return self._encerrar_com_erro(
                    ciclo_id,
                    iniciado_em,
                    etapas,
                    "A percepção corporal não retornou um estado válido.",
                )

            self._registrar_etapa(
                etapas,
                "percebido",
                {"fonte": "corpo_nixal"},
            )

            estado_completo = self.estado.resumo()
            etapas.append(
                {
                    "etapa": "estado_interno",
                    "sucesso": bool(estado_completo.get("sucesso")),
                    "estado": deepcopy(estado_completo),
                }
            )

            diagnostico = self.necessidades.diagnostico.diagnosticar()
            etapas.append(
                {
                    "etapa": "diagnostico",
                    "sucesso": bool(diagnostico.get("sucesso")),
                    "estado": deepcopy(diagnostico),
                }
            )
            self._registrar_etapa(
                etapas,
                "diagnosticado",
                {"estado_diagnostico": diagnostico.get("estado")},
            )

            necessidade_resultado = self.necessidades.analisar()
            valor_necessidades = necessidade_resultado.get("valor")
            lista_necessidades = (
                valor_necessidades.get("necessidades", [])
                if isinstance(valor_necessidades, dict)
                else []
            )

            prioridade = self._priorizar(lista_necessidades)
            etapas.append(
                {
                    "etapa": "necessidades",
                    "sucesso": bool(necessidade_resultado.get("sucesso")),
                    "resultado": deepcopy(necessidade_resultado),
                    "prioridade": deepcopy(prioridade),
                }
            )
            self._registrar_etapa(
                etapas,
                "necessidade_detectada" if lista_necessidades else "diagnosticado",
                {"quantidade": len(lista_necessidades)},
            )

            decisao = self._decidir(
                estado_corpo=estado_corpo,
                prioridades=prioridade,
            )
            etapas.append(
                {
                    "etapa": "decisao",
                    "sucesso": True,
                    "decisao": deepcopy(decisao),
                }
            )
            self._registrar_etapa(etapas, "decidido", deepcopy(decisao))

            acao_resultado = self._agir(
                decisao=decisao,
                estado_corpo=estado_corpo,
            )
            etapas.append(
                {
                    "etapa": "acao",
                    "sucesso": bool(acao_resultado.get("sucesso")),
                    "resultado": deepcopy(acao_resultado),
                }
            )

            if not acao_resultado.get("sucesso"):
                return self._encerrar_com_erro(
                    ciclo_id,
                    iniciado_em,
                    etapas,
                    acao_resultado.get(
                        "motivo",
                        "A ação autorizada falhou.",
                    ),
                )

            self._registrar_etapa(
                etapas,
                "acao_executada",
                {"acao": decisao.get("acao")},
            )

            resultado_observado = self._observar_resultado(
                estado_corpo,
                acao_resultado,
            )
            etapas.append(
                {
                    "etapa": "resultado",
                    "sucesso": bool(resultado_observado.get("sucesso")),
                    "resultado": deepcopy(resultado_observado),
                }
            )
            self._registrar_etapa(
                etapas,
                "resultado_observado",
                {"estado": resultado_observado.get("estado")},
            )

            concluido_em = self._agora_iso()
            ciclo = {
                "sucesso": True,
                "estado": "ciclo_concluido",
                "origem": self.FONTE,
                "versao_runtime": self.VERSAO,
                "ciclo_id": ciclo_id,
                "iniciado_em": iniciado_em,
                "concluido_em": concluido_em,
                "valor": {
                    "etapas": deepcopy(etapas),
                    "necessidade_prioritaria": deepcopy(prioridade),
                    "decisao": deepcopy(decisao),
                    "acao": deepcopy(acao_resultado),
                    "resultado": deepcopy(resultado_observado),
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
            }

            self._persistir_estado(ciclo)
            self._registrar_log(ciclo)
            self._ultimo_ciclo = deepcopy(ciclo)
            return deepcopy(ciclo)

        except Exception as erro:
            return self._encerrar_com_erro(
                ciclo_id,
                iniciado_em,
                etapas,
                f"{type(erro).__name__}: {erro}",
            )

    def executar(
        self,
        max_ciclos: int | None = None,
        intervalo_segundos: float = 2.0,
        parar_em_erro: bool = True,
    ) -> list[dict[str, Any]]:
        if max_ciclos is not None:
            if not isinstance(max_ciclos, int) or max_ciclos < 1:
                raise ValueError("max_ciclos deve ser inteiro >= 1 ou None")

        if intervalo_segundos < 0:
            raise ValueError("intervalo_segundos não pode ser negativo")

        resultados: list[dict[str, Any]] = []
        contador = 0

        while max_ciclos is None or contador < max_ciclos:
            contador += 1
            resultado = self.executar_ciclo()
            resultados.append(deepcopy(resultado))

            if parar_em_erro and not resultado.get("sucesso"):
                break

            if max_ciclos is None or contador < max_ciclos:
                time.sleep(intervalo_segundos)

        return resultados

    # ============================================================
    # PRIORIDADE / DECISÃO
    # ============================================================

    @staticmethod
    def _priorizar(
        necessidades: list[Any],
    ) -> dict[str, Any]:
        validas = [
            item
            for item in necessidades
            if isinstance(item, dict)
        ]

        ordem = {"alta": 0, "media": 1, "baixa": 2, "indeterminada": 3}
        validas.sort(
            key=lambda item: (
                ordem.get(str(item.get("prioridade", "indeterminada")), 3),
                str(item.get("necessidade", "")),
            )
        )

        primeira = validas[0] if validas else None

        return {
            "sucesso": True,
            "quantidade": len(validas),
            "selecionada": deepcopy(primeira),
        }

    def _decidir(
        self,
        estado_corpo: dict[str, Any],
        prioridades: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(estado_corpo, dict):
            return {
                "sucesso": False,
                "acao": None,
                "motivo": "Estado corporal inválido.",
            }

        return {
            "sucesso": True,
            "tipo": "acao_controlada",
            "acao": "registrar_estado_corpo",
            "motivo": (
                "Na Fase 01, a ação segura mínima é persistir o estado "
                "corporal observado para garantir continuidade e rastreabilidade."
            ),
            "necessidade_prioritaria": deepcopy(
                prioridades.get("selecionada")
            ),
        }

    # ============================================================
    # AÇÃO AUTORIZADA
    # ============================================================

    def _agir(
        self,
        decisao: dict[str, Any],
        estado_corpo: dict[str, Any],
    ) -> dict[str, Any]:
        acao = decisao.get("acao")

        if acao not in self.ACOES_AUTORIZADAS:
            return {
                "sucesso": False,
                "estado": "acao_nao_autorizada",
                "acao": acao,
                "motivo": "A ação não está na lista autorizada da Fase 01.",
            }

        if acao == "registrar_estado_corpo":
            caminho = corpo_nixal.ARQUIVO_ESTADO_CORPO
            corpo_nixal.salvar_estado_corpo(estado_corpo)

            return {
                "sucesso": True,
                "estado": "estado_corpo_persistido",
                "acao": acao,
                "arquivo": str(caminho),
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            }

        return {
            "sucesso": False,
            "estado": "acao_desconhecida",
            "acao": acao,
            "motivo": "A ação autorizada não possui executor.",
        }

    # ============================================================
    # RESULTADO
    # ============================================================

    @staticmethod
    def _observar_resultado(
        estado_corpo: dict[str, Any],
        acao_resultado: dict[str, Any],
    ) -> dict[str, Any]:
        if not acao_resultado.get("sucesso"):
            return {
                "sucesso": False,
                "estado": "resultado_inexistente",
                "corpo_observado": False,
            }

        return {
            "sucesso": True,
            "estado": "resultado_observado",
            "arquivo_persistido": acao_resultado.get("arquivo"),
            "corpo_observado": isinstance(estado_corpo, dict),
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    # ============================================================
    # PERSISTÊNCIA DO RUNTIME
    # ============================================================

    def _persistir_estado(
        self,
        ciclo: dict[str, Any],
    ) -> None:
        self._atomic_write_json(
            self.arquivo_estado,
            {
                "origem": self.FONTE,
                "versao_runtime": self.VERSAO,
                "ultimo_ciclo": deepcopy(ciclo),
            },
        )

    def _registrar_log(
        self,
        ciclo: dict[str, Any],
    ) -> None:
        dados: list[Any] = []

        if self.arquivo_log.exists():
            try:
                carregado = json.loads(
                    self.arquivo_log.read_text(encoding="utf-8")
                )
                if isinstance(carregado, list):
                    dados = carregado
            except (OSError, json.JSONDecodeError):
                dados = []

        dados.append(deepcopy(ciclo))
        dados = dados[-100:]
        self._atomic_write_json(self.arquivo_log, dados)

    # ============================================================
    # ERROS / UTILITÁRIOS
    # ============================================================

    def _encerrar_com_erro(
        self,
        ciclo_id: str,
        iniciado_em: str,
        etapas: list[dict[str, Any]],
        motivo: str,
    ) -> dict[str, Any]:
        ciclo = {
            "sucesso": False,
            "estado": "erro",
            "origem": self.FONTE,
            "versao_runtime": self.VERSAO,
            "ciclo_id": ciclo_id,
            "iniciado_em": iniciado_em,
            "concluido_em": self._agora_iso(),
            "valor": {
                "etapas": deepcopy(etapas),
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "erro": motivo,
        }
        self._persistir_estado(ciclo)
        self._registrar_log(ciclo)
        self._ultimo_ciclo = deepcopy(ciclo)
        return deepcopy(ciclo)

    @staticmethod
    def _agora_iso() -> str:
        return datetime.now().astimezone().isoformat()

    @classmethod
    def _gerar_id_ciclo(cls) -> str:
        return f"{cls.VERSAO}_{time.time_ns()}"

    @staticmethod
    def _registrar_etapa(
        etapas: list[dict[str, Any]],
        estado: str,
        dados: dict[str, Any],
    ) -> None:
        etapas.append(
            {
                "etapa": "transicao",
                "estado": estado,
                "dados": deepcopy(dados),
            }
        )

    @staticmethod
    def _atomic_write_json(
        caminho: Path,
        dados: Any,
    ) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporario, caminho)


if __name__ == "__main__":
    runtime = NyxalRuntime()
    resultado = runtime.executar(max_ciclos=1, intervalo_segundos=0.0)
    print(json.dumps(resultado[0], ensure_ascii=False, indent=2))
