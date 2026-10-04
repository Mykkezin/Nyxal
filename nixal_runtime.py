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
    avaliação do resultado
        ↓
    registro da experiência
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
from nixal_formulacao_investigacao import FormulacaoInvestigacaoNixal
from nixal_preparacao_investigacao import PreparacaoInvestigacaoNixal
from nixal_analise_lacunas_investigacao import AnaliseLacunasInvestigacaoNixal
from nixal_planejamento_coleta_evidencias import PlanejamentoColetaEvidenciasNixal
from nixal_execucao_plano_investigacao import ExecucaoPlanoInvestigacaoNixal
from nixal_consolidacao_evidencias import ConsolidacaoEvidenciasNixal
from nixal_preparacao_formulacao_hipotese import PreparacaoFormulacaoHipoteseNixal
from nixal_execucao_formulacao_hipotese import ExecucaoFormulacaoHipoteseNixal
from nixal_integracao_formulacao_ciclo_hipotese import (
    IntegracaoFormulacaoCicloHipoteseNixal,
)
from nixal_ciclo_memoria_hipotese import CicloMemoriaHipoteseNixal
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal
from nixal_preparacao_teste_hipotese import PreparacaoTesteHipoteseNixal
from nixal_execucao_teste_hipotese import ExecucaoTesteHipoteseNixal
from nixal_integracao_teste_ciclo_hipotese import (
    IntegracaoTesteCicloHipoteseNixal,
)
from nixal_execucao_avaliacao_hipotese import ExecucaoAvaliacaoHipoteseNixal
from nixal_integracao_avaliacao_ciclo_hipotese import (
    IntegracaoAvaliacaoCicloHipoteseNixal,
)
from nixal_testador_arquitetural import TestadorArquiteturalNixal
from nixal_consolidacao_conhecimento import ConsolidacaoConhecimentoNixal
from nixal_memoria_conhecimento import MemoriaConhecimentoNixal
from nixal_aprendizado_persistente import AprendizadoPersistenteNixal


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_ESTADO_RUNTIME = BASE_DIR / "estado_nyxal_runtime.json"
ARQUIVO_LOG_RUNTIME = BASE_DIR / "log_nyxal_runtime.json"
ARQUIVO_MEMORIA_INVESTIGACAO_RUNTIME = (
    BASE_DIR / "memoria_investigacao_nixal.json"
)


class NyxalRuntime:
    """Coordenador mínimo do ciclo operacional da Nyxal."""

    FONTE = "nyxal_runtime"
    VERSAO = "fase_01"

    ESTADOS = {
        "iniciado",
        "percebido",
        "diagnosticado",
        "necessidade_detectada",
        "investigacao_integrada",
        "decidido",
        "acao_executada",
        "resultado_observado",
        "avaliado",
        "experiencia_registrada",
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
        arquivo_memoria_investigacao: Path | None = None,
        memoria_investigacao: MemoriaInvestigacaoNixal | None = None,
        arquivo_memoria_conhecimento: Path | None = None,
        memoria_conhecimento: MemoriaConhecimentoNixal | None = None,
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

        if memoria_investigacao is not None and not isinstance(
            memoria_investigacao,
            MemoriaInvestigacaoNixal,
        ):
            raise TypeError(
                "memoria_investigacao deve ser uma instância de "
                "MemoriaInvestigacaoNixal"
            )

        if memoria_conhecimento is not None and not isinstance(
            memoria_conhecimento,
            MemoriaConhecimentoNixal,
        ):
            raise TypeError(
                "memoria_conhecimento deve ser uma instância de "
                "MemoriaConhecimentoNixal"
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

        self.arquivo_memoria_investigacao = (
            Path(arquivo_memoria_investigacao)
            if arquivo_memoria_investigacao is not None
            else self.arquivo_estado.parent
            / "memoria_investigacao_nixal.json"
        )

        self.memoria_investigacao = (
            memoria_investigacao
            if memoria_investigacao is not None
            else MemoriaInvestigacaoNixal(
                self.arquivo_memoria_investigacao
            )
        )

        self.arquivo_memoria_conhecimento = (
            Path(arquivo_memoria_conhecimento)
            if arquivo_memoria_conhecimento is not None
            else self.arquivo_estado.parent
            / "memoria_conhecimento_nixal.json"
        )

        self.memoria_conhecimento = (
            memoria_conhecimento
            if memoria_conhecimento is not None
            else MemoriaConhecimentoNixal(
                self.arquivo_memoria_conhecimento
            )
        )

        self.formulacao_investigacao = (
            FormulacaoInvestigacaoNixal(
                necessidades=self.necessidades
            )
        )
        self.preparacao_investigacao = (
            PreparacaoInvestigacaoNixal(
                self.memoria_investigacao
            )
        )
        self.analise_lacunas_investigacao = (
            AnaliseLacunasInvestigacaoNixal()
        )
        self.planejamento_coleta_evidencias = (
            PlanejamentoColetaEvidenciasNixal()
        )
        self.execucao_plano_investigacao = (
            ExecucaoPlanoInvestigacaoNixal()
        )
        self.consolidacao_evidencias = (
            ConsolidacaoEvidenciasNixal()
        )
        self.preparacao_formulacao_hipotese = (
            PreparacaoFormulacaoHipoteseNixal()
        )
        self.execucao_formulacao_hipotese = (
            ExecucaoFormulacaoHipoteseNixal()
        )
        self.preparacao_teste_hipotese = (
            PreparacaoTesteHipoteseNixal()
        )
        self.testador_arquitetural = (
            TestadorArquiteturalNixal(
                base_dir=BASE_DIR,
            )
        )
        self.execucao_teste_hipotese = (
            ExecucaoTesteHipoteseNixal(
                self.testador_arquitetural,
            )
        )
        self.execucao_avaliacao_hipotese = (
            ExecucaoAvaliacaoHipoteseNixal()
        )
        self.consolidacao_conhecimento = (
            ConsolidacaoConhecimentoNixal()
        )

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

            investigacao_resultado = self._executar_investigacao(
                prioridade.get("selecionada")
            )

            etapas.append(
                {
                    "etapa": "investigacao",
                    "sucesso": bool(
                        investigacao_resultado.get("sucesso")
                    ),
                    "resultado": deepcopy(
                        investigacao_resultado
                    ),
                }
            )

            if not investigacao_resultado.get("sucesso"):
                return self._encerrar_com_erro(
                    ciclo_id,
                    iniciado_em,
                    etapas,
                    investigacao_resultado.get(
                        "motivo",
                        "A investigação integrada falhou.",
                    ),
                )

            if investigacao_resultado.get(
                "estado"
            ) == "hipotese_integrada_no_ciclo":
                self._registrar_etapa(
                    etapas,
                    "investigacao_integrada",
                    {
                        "estado": investigacao_resultado.get(
                            "estado"
                        ),
                        "hipotese_estado": (
                            investigacao_resultado.get(
                                "valor",
                                {}
                            ).get(
                                "hipotese",
                                {}
                            ).get(
                                "estado_atual"
                            )
                            if isinstance(
                                investigacao_resultado.get(
                                    "valor"
                                ),
                                dict,
                            )
                            else None
                        ),
                    },
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

            avaliacao = self._avaliar_resultado(
                acao_resultado=acao_resultado,
                resultado_observado=resultado_observado,
            )
            etapas.append(
                {
                    "etapa": "avaliacao",
                    "sucesso": bool(avaliacao.get("sucesso")),
                    "resultado": deepcopy(avaliacao),
                }
            )

            if not avaliacao.get("sucesso"):
                return self._encerrar_com_erro(
                    ciclo_id,
                    iniciado_em,
                    etapas,
                    avaliacao.get(
                        "motivo",
                        "A avaliação do resultado falhou.",
                    ),
                )

            self._registrar_etapa(
                etapas,
                "avaliado",
                {
                    "avaliacao": avaliacao.get("avaliacao"),
                    "estado": avaliacao.get("estado"),
                },
            )

            experiencia = self._registrar_experiencia(
                decisao=decisao,
                acao_resultado=acao_resultado,
                resultado_observado=resultado_observado,
                avaliacao=avaliacao,
            )
            etapas.append(
                {
                    "etapa": "experiencia",
                    "sucesso": bool(experiencia.get("sucesso")),
                    "resultado": deepcopy(experiencia),
                }
            )

            if not experiencia.get("sucesso"):
                return self._encerrar_com_erro(
                    ciclo_id,
                    iniciado_em,
                    etapas,
                    experiencia.get(
                        "motivo",
                        "O registro da experiência falhou.",
                    ),
                )

            self._registrar_etapa(
                etapas,
                "experiencia_registrada",
                {
                    "tipo": experiencia.get("tipo"),
                    "avaliacao": experiencia.get("avaliacao"),
                },
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
                    "avaliacao": deepcopy(avaliacao),
                    "experiencia": deepcopy(experiencia),
                    "investigacao": deepcopy(
                        investigacao_resultado
                    ),
                    "hipotese": deepcopy(
                        investigacao_resultado.get(
                            "valor",
                            {}
                        ).get(
                            "hipotese"
                        )
                        if isinstance(
                            investigacao_resultado.get(
                                "valor"
                            ),
                            dict,
                        )
                        else None
                    ),
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
    # INVESTIGAÇÃO INTEGRADA
    # ============================================================

    def _executar_investigacao(
        self,
        necessidade_prioritaria: Any,
    ) -> dict[str, Any]:
        if necessidade_prioritaria is None:
            return {
                "sucesso": True,
                "estado": "investigacao_nao_aplicavel",
                "origem": self.FONTE,
                "valor": {
                    "motivo": (
                        "Nenhuma necessidade prioritária foi detectada."
                    ),
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
            }

        if not isinstance(
            necessidade_prioritaria,
            dict,
        ):
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": None,
                "motivo": "Necessidade prioritária inválida.",
            }

        nome_necessidade = necessidade_prioritaria.get(
            "necessidade"
        )

        if not isinstance(
            nome_necessidade,
            str,
        ) or not nome_necessidade.strip():
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": None,
                "motivo": (
                    "A necessidade prioritária não possui identificação válida."
                ),
            }

        formulacao = self.formulacao_investigacao.formular()

        if formulacao.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                },
                "motivo": "A formulação da investigação falhou.",
            }

        investigacoes = (
            formulacao.get(
                "valor",
                {}
            ).get(
                "investigacoes",
                []
            )
            if isinstance(
                formulacao.get("valor"),
                dict,
            )
            else []
        )

        investigacao = next(
            (
                item
                for item in investigacoes
                if isinstance(item, dict)
                and item.get("necessidade")
                == nome_necessidade
            ),
            None,
        )

        if investigacao is None:
            return {
                "sucesso": True,
                "estado": "investigacao_nao_aplicavel",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "necessidade": nome_necessidade,
                    "motivo": (
                        "A necessidade prioritária não possui investigação "
                        "declarada para esta arquitetura."
                    ),
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                },
            }

        preparacao = self.preparacao_investigacao.preparar(
            investigacao
        )

        if preparacao.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                },
                "motivo": "A preparação da investigação falhou.",
            }

        investigacao_contextualizada = (
            preparacao.get("valor", {}).get(
                "investigacao_contextualizada"
            )
            if isinstance(
                preparacao.get("valor"),
                dict,
            )
            else None
        )

        analise = self.analise_lacunas_investigacao.analisar(
            investigacao_contextualizada
        )

        if analise.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                },
                "motivo": "A análise de lacunas falhou.",
            }

        planejamento = self.planejamento_coleta_evidencias.planejar(
            analise
        )

        if planejamento.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                },
                "motivo": "O planejamento da coleta falhou.",
            }

        planos = (
            planejamento.get(
                "valor",
                {}
            ).get(
                "planos",
                []
            )
            if isinstance(
                planejamento.get("valor"),
                dict,
            )
            else []
        )

        if not isinstance(planos, list) or len(planos) != 1:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                },
                "motivo": (
                    "A integração inicial do Runtime suporta "
                    "exatamente um plano de coleta."
                ),
            }

        execucao = self.execucao_plano_investigacao.executar(
            deepcopy(planos[0])
        )

        if execucao.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                    "execucao": deepcopy(execucao),
                },
                "motivo": "A execução do plano de investigação falhou.",
            }

        consolidacao = self.consolidacao_evidencias.consolidar(
            execucao
        )

        if consolidacao.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                    "execucao": deepcopy(execucao),
                    "consolidacao": deepcopy(consolidacao),
                },
                "motivo": "A consolidação das evidências falhou.",
            }

        preparacao_hipotese = (
            self.preparacao_formulacao_hipotese.preparar(
                investigacao,
                consolidacao,
            )
        )

        if preparacao_hipotese.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                    "execucao": deepcopy(execucao),
                    "consolidacao": deepcopy(consolidacao),
                    "preparacao_hipotese": deepcopy(
                        preparacao_hipotese
                    ),
                },
                "motivo": (
                    "A preparação da formulação da hipótese falhou."
                ),
            }

        ciclo_memoria = CicloMemoriaHipoteseNixal(
            self.memoria_investigacao
        )

        integracao = IntegracaoFormulacaoCicloHipoteseNixal(
            self.execucao_formulacao_hipotese,
            ciclo_memoria,
        ).executar(
            preparacao_hipotese
        )

        if integracao.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                    "execucao": deepcopy(execucao),
                    "consolidacao": deepcopy(consolidacao),
                    "preparacao_hipotese": deepcopy(
                        preparacao_hipotese
                    ),
                    "integracao": deepcopy(integracao),
                },
                "motivo": (
                    "A integração da hipótese ao ciclo falhou."
                ),
            }

        valor_integracao = integracao.get(
            "valor"
        )

        ciclo = (
            valor_integracao.get("ciclo")
            if isinstance(
                valor_integracao,
                dict,
            )
            else None
        )

        if not isinstance(ciclo, dict):
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "integracao": deepcopy(integracao),
                },
                "motivo": (
                    "A integração não retornou um ciclo de hipótese válido."
                ),
            }

        preparacao_teste = self.preparacao_teste_hipotese.preparar(
            integracao
        )

        if preparacao_teste.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                    "execucao": deepcopy(execucao),
                    "consolidacao": deepcopy(consolidacao),
                    "preparacao_hipotese": deepcopy(
                        preparacao_hipotese
                    ),
                    "integracao": deepcopy(integracao),
                    "hipotese": deepcopy(ciclo),
                    "preparacao_teste": deepcopy(
                        preparacao_teste
                    ),
                },
                "motivo": "A preparação do teste da hipótese falhou.",
            }

        integracao_teste = IntegracaoTesteCicloHipoteseNixal(
            self.execucao_teste_hipotese,
            ciclo_memoria,
        ).executar(
            preparacao_teste
        )

        if integracao_teste.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                    "execucao": deepcopy(execucao),
                    "consolidacao": deepcopy(consolidacao),
                    "preparacao_hipotese": deepcopy(
                        preparacao_hipotese
                    ),
                    "integracao": deepcopy(integracao),
                    "hipotese": deepcopy(ciclo),
                    "preparacao_teste": deepcopy(
                        preparacao_teste
                    ),
                    "integracao_teste": deepcopy(
                        integracao_teste
                    ),
                },
                "motivo": "A integração do teste ao ciclo falhou.",
            }

        integracao_avaliacao = (
            IntegracaoAvaliacaoCicloHipoteseNixal(
                self.execucao_avaliacao_hipotese,
                ciclo_memoria,
            ).executar(
                integracao_teste
            )
        )

        if integracao_avaliacao.get("sucesso") is not True:
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "formulacao": deepcopy(formulacao),
                    "preparacao": deepcopy(preparacao),
                    "analise": deepcopy(analise),
                    "planejamento": deepcopy(planejamento),
                    "execucao": deepcopy(execucao),
                    "consolidacao": deepcopy(consolidacao),
                    "preparacao_hipotese": deepcopy(
                        preparacao_hipotese
                    ),
                    "integracao": deepcopy(integracao),
                    "hipotese": deepcopy(ciclo),
                    "preparacao_teste": deepcopy(
                        preparacao_teste
                    ),
                    "integracao_teste": deepcopy(
                        integracao_teste
                    ),
                    "integracao_avaliacao": deepcopy(
                        integracao_avaliacao
                    ),
                },
                "motivo": "A integração da avaliação ao ciclo falhou.",
            }

        valor_avaliacao = integracao_avaliacao.get(
            "valor"
        )

        ciclo_final = (
            valor_avaliacao.get("ciclo")
            if isinstance(
                valor_avaliacao,
                dict,
            )
            else None
        )

        if not isinstance(ciclo_final, dict):
            return {
                "sucesso": False,
                "estado": "investigacao_falhou",
                "origem": self.FONTE,
                "valor": {
                    "integracao_avaliacao": deepcopy(
                        integracao_avaliacao
                    ),
                },
                "motivo": (
                    "A integração da avaliação não retornou "
                    "um ciclo final válido."
                ),
            }

        consolidacao_conhecimento = self.consolidacao_conhecimento.consolidar_candidato(
            ciclo_final
        )

        memoria_conhecimento = {
            "sucesso": True,
            "estado": "nenhum_candidato",
            "origem": self.FONTE,
            "valor": None,
            "conhecimento_permanente": False,
            "gravado": False,
            "arquitetura_modificada": False,
        }

        if (
            isinstance(consolidacao_conhecimento, dict)
            and consolidacao_conhecimento.get("estado")
            == "candidato_conhecimento_criado"
        ):
            candidato = consolidacao_conhecimento.get("valor")

            if isinstance(candidato, dict):
                memoria_conhecimento = (
                    self.memoria_conhecimento.registrar(
                        candidato
                    )
                )

                if memoria_conhecimento.get("sucesso") is not True:
                    return {
                        "sucesso": False,
                        "estado": "investigacao_falhou",
                        "origem": self.FONTE,
                        "valor": {
                            "consolidacao_conhecimento": deepcopy(
                                consolidacao_conhecimento
                            ),
                            "memoria_conhecimento": deepcopy(
                                memoria_conhecimento
                            ),
                        },
                        "motivo": (
                            "A persistência do candidato de conhecimento "
                            "falhou."
                        ),
                    }

        return {
            "sucesso": True,
            "estado": "avaliacao_integrada_no_ciclo",
            "origem": self.FONTE,
            "valor": {
                "necessidade": nome_necessidade,
                "investigacao_original": deepcopy(
                    investigacao
                ),
                "formulacao": deepcopy(formulacao),
                "preparacao": deepcopy(preparacao),
                "analise": deepcopy(analise),
                "planejamento": deepcopy(planejamento),
                "execucao": deepcopy(execucao),
                "consolidacao": deepcopy(consolidacao),
                "preparacao_hipotese": deepcopy(
                    preparacao_hipotese
                ),
                "integracao": deepcopy(integracao),
                "hipotese_inicial": deepcopy(ciclo),
                "preparacao_teste": deepcopy(
                    preparacao_teste
                ),
                "integracao_teste": deepcopy(
                    integracao_teste
                ),
                "integracao_avaliacao": deepcopy(
                    integracao_avaliacao
                ),
                "consolidacao_conhecimento": deepcopy(
                    consolidacao_conhecimento
                ),
                "memoria_conhecimento": deepcopy(
                    memoria_conhecimento
                ),
                "hipotese": deepcopy(ciclo_final),
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
        }

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
    # AVALIAÇÃO / EXPERIÊNCIA
    # ============================================================

    @staticmethod
    def _avaliar_resultado(
        acao_resultado: dict[str, Any],
        resultado_observado: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(acao_resultado, dict):
            return {
                "sucesso": False,
                "estado": "avaliacao_invalida",
                "avaliacao": "inconclusiva",
                "motivo": "O resultado da ação não é um objeto válido.",
            }

        if not isinstance(resultado_observado, dict):
            return {
                "sucesso": False,
                "estado": "avaliacao_invalida",
                "avaliacao": "inconclusiva",
                "motivo": "O resultado observado não é um objeto válido.",
            }

        acao_sucesso = bool(acao_resultado.get("sucesso"))
        observacao_sucesso = bool(resultado_observado.get("sucesso"))

        if not acao_sucesso or not observacao_sucesso:
            return {
                "sucesso": True,
                "estado": "resultado_avaliado",
                "avaliacao": "falha",
                "motivo": (
                    "A ação executada ou a observação do resultado "
                    "não foi considerada bem-sucedida."
                ),
            }

        return {
            "sucesso": True,
            "estado": "resultado_avaliado",
            "avaliacao": "sucesso",
            "criterio": "acao_e_resultado_sucesso",
            "motivo": (
                "A ação autorizada foi executada com sucesso e "
                "o resultado foi observado corretamente."
            ),
        }

    @staticmethod
    def _registrar_experiencia(
        decisao: dict[str, Any],
        acao_resultado: dict[str, Any],
        resultado_observado: dict[str, Any],
        avaliacao: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "experiencia_registrada",
            "tipo": "ciclo_runtime",
            "acao": decisao.get("acao"),
            "resultado": resultado_observado.get("estado"),
            "avaliacao": avaliacao.get("avaliacao"),
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

    print("NYXAL RUNTIME — MODO PERSISTENTE")
    print("Ciclo contínuo ativo. Pressione Ctrl+C para interromper.")

    try:
        runtime.executar(
            max_ciclos=None,
            intervalo_segundos=2.0,
            parar_em_erro=True,
        )
    except KeyboardInterrupt:
        print("\nNYXAL RUNTIME — EXECUÇÃO INTERROMPIDA.")
