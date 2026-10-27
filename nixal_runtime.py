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
import tempfile
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
from nixal_evolucao_remota import CicloEvolucaoRemotaNixal
from nixal_solicitacao_evolucao import SolicitacaoEvolucaoNixal
from nixal_persistencia_operacional import PersistenciaOperacionalNixOS
from nixal_delta import RegistroDeltaNixOS
from nixal_learning_loop_causal import LearningLoopCausalNixal


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_ESTADO_RUNTIME = BASE_DIR / "estado_nyxal_runtime.json"
ARQUIVO_LOG_RUNTIME = BASE_DIR / "log_nyxal_runtime.json"
ARQUIVO_MEMORIA_INVESTIGACAO_RUNTIME = (
    BASE_DIR / "memoria_investigacao_nixal.json"
)
ARQUIVO_MEMORIA_APRENDIZADO_RUNTIME = (
    BASE_DIR / "memoria_aprendizado_nixal.json"
)

# Limite absoluto para manter o log operacional sob controle.
MAX_TAMANHO_LOG_RUNTIME = 512 * 1024


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
        "observar_sem_atuar",
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
        arquivo_memoria_aprendizado: Path | None = None,
        memoria_aprendizado: AprendizadoPersistenteNixal | None = None,
        evolucao_remota: CicloEvolucaoRemotaNixal | None = None,
        solicitacao_evolucao: SolicitacaoEvolucaoNixal | None = None,
        persistencia_operacional: PersistenciaOperacionalNixOS | None = None,
        delta_nyxos: RegistroDeltaNixOS | None = None,
        *,
        modo_residente: bool = False,
        aprendizado_habilitado: bool = True,
        learning_loop_causal: LearningLoopCausalNixal | None = None,
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

        if memoria_aprendizado is not None and not isinstance(
            memoria_aprendizado,
            AprendizadoPersistenteNixal,
        ):
            raise TypeError(
                "memoria_aprendizado deve ser uma instância de "
                "AprendizadoPersistenteNixal"
            )

        if evolucao_remota is not None and not isinstance(
            evolucao_remota,
            CicloEvolucaoRemotaNixal,
        ):
            raise TypeError(
                "evolucao_remota deve ser uma instância de "
                "CicloEvolucaoRemotaNixal"
            )

        if solicitacao_evolucao is not None and not isinstance(
            solicitacao_evolucao,
            SolicitacaoEvolucaoNixal,
        ):
            raise TypeError(
                "solicitacao_evolucao deve ser uma instância de "
                "SolicitacaoEvolucaoNixal"
            )

        if learning_loop_causal is not None and not isinstance(
            learning_loop_causal,
            LearningLoopCausalNixal,
        ):
            raise TypeError(
                "learning_loop_causal deve ser uma instância de "
                "LearningLoopCausalNixal"
            )

        self.perceber_corpo = perceber_corpo
        self.aprendizado_habilitado = bool(aprendizado_habilitado)
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
        self.modo_residente = bool(modo_residente)
        self.arquivo_log = Path(arquivo_log)
        if (
            self.modo_residente
            and self.arquivo_log == ARQUIVO_LOG_RUNTIME
        ):
            self.arquivo_log = BASE_DIR / "log_nyxal_residente.json"

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

        self.arquivo_memoria_aprendizado = (
            Path(arquivo_memoria_aprendizado)
            if arquivo_memoria_aprendizado is not None
            else self.arquivo_estado.parent
            / "memoria_aprendizado_nixal.json"
        )

        self.memoria_aprendizado = (
            memoria_aprendizado
            if memoria_aprendizado is not None
            else AprendizadoPersistenteNixal(
                self.arquivo_memoria_aprendizado
            )
        )

        # A evolução remota é criada sob demanda para evitar
        # qualquer efeito colateral de laboratório durante a inicialização
        # normal do Runtime.
        self.evolucao_remota = evolucao_remota

        self.solicitacao_evolucao = solicitacao_evolucao
        self.persistencia_operacional = (
            persistencia_operacional
            if persistencia_operacional is not None
            else PersistenciaOperacionalNixOS(
                self.arquivo_estado.parent / "estado_nyxos_operacional.json"
            )
        )
        self.delta_nyxos = (
            delta_nyxos
            if delta_nyxos is not None
            else RegistroDeltaNixOS(
                self.arquivo_estado.parent / "eventos_delta_nyxos.json"
            )
        )

        self.learning_loop_causal = learning_loop_causal

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
        self._ultima_hipotese_investigada: dict[str, Any] | None = None

    # ============================================================
    # SOLICITAÇÃO FORMAL DE EVOLUÇÃO
    # ============================================================

    def _capturar_hipotese_provisoria(
        self,
        ciclo: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Captura a hipótese exatamente no estágio provisório da
        investigação, antes de teste e avaliação.
        """
        if not isinstance(ciclo, dict):
            raise TypeError("ciclo_hipotese_investigada_invalido")

        if ciclo.get("estado_atual") != "provisoria":
            raise ValueError("hipotese_investigada_nao_provisoria")

        if ciclo.get("confirmada", False) is not False:
            raise ValueError(
                "hipotese_investigada_nao_pode_estar_confirmada"
            )

        if ciclo.get("testada", False) is not False:
            raise ValueError(
                "hipotese_investigada_nao_pode_estar_testada"
            )

        self._ultima_hipotese_investigada = deepcopy(ciclo)
        return deepcopy(self._ultima_hipotese_investigada)

    def criar_solicitacao_evolucao(
        self,
        *,
        objetivo: str,
        metrica: str,
        direcao_melhor: str,
        baseline: Any,
        artefato_origem: str | Path | None = None,
        observacao: str = "",
    ) -> dict[str, Any]:
        """
        Converte a hipótese provisória produzida pela investigação do
        Runtime em uma solicitação formal de evolução.

        A solicitação não executa o experimento. Ela apenas estrutura
        a intenção, preserva a hipótese/evidências e registra os gates
        para uma futura evolução controlada.
        """
        if self.solicitacao_evolucao is None:
            self.solicitacao_evolucao = SolicitacaoEvolucaoNixal(
                repositorio=BASE_DIR,
            )

        hipotese = self._ultima_hipotese_investigada
        if not isinstance(hipotese, dict):
            return {
                "sucesso": False,
                "estado": "solicitacao_indisponivel",
                "origem": self.FONTE,
                "motivo": "Ainda não existe hipótese provisória capturada pela investigação.",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        try:
            solicitacao = self.solicitacao_evolucao.criar(
                ciclo_hipotese=deepcopy(hipotese),
                objetivo=objetivo,
                metrica=metrica,
                direcao_melhor=direcao_melhor,
                baseline=baseline,
                artefato_origem=artefato_origem,
                observacao=observacao,
            )
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "solicitacao_evolucao_falhou",
                "origem": self.FONTE,
                "motivo": f"{type(erro).__name__}: {erro}",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        return {
            "sucesso": True,
            "estado": "solicitacao_evolucao_criada",
            "origem": self.FONTE,
            "valor": deepcopy(solicitacao),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

    # ============================================================
    # EVOLUÇÃO REMOTA
    # ============================================================

    def executar_evolucao_remota(
        self,
        *,
        limitacao: str,
        hipotese: str,
        objetivo: str,
        metrica: str,
        direcao_melhor: str,
        baseline: Any,
        artefato_origem: str | Path,
        arquivo_destino: str = "experimento.py",
        descricao: str = "",
        timeout_seconds: int = 60,
        timeout_resultado_segundos: int = 300,
        intervalo_resultado_segundos: int = 5,
    ) -> dict[str, Any]:
        """
        Delega explicitamente uma evolução experimental ao ciclo remoto.

        Esta ponte NÃO é chamada automaticamente pelo ciclo Runtime.
        A execução remota só acontece quando este método é invocado de forma
        explícita por uma camada de decisão/coordenação superior.
        """
        if self.evolucao_remota is None:
            self.evolucao_remota = CicloEvolucaoRemotaNixal(
                repositorio=BASE_DIR,
                memoria_aprendizado=self.memoria_aprendizado,
            )

        resultado = self.evolucao_remota.executar(
            limitacao=limitacao,
            hipotese=hipotese,
            objetivo=objetivo,
            metrica=metrica,
            direcao_melhor=direcao_melhor,
            baseline=baseline,
            artefato_origem=artefato_origem,
            arquivo_destino=arquivo_destino,
            descricao=descricao,
            timeout_seconds=timeout_seconds,
            timeout_resultado_segundos=timeout_resultado_segundos,
            intervalo_resultado_segundos=intervalo_resultado_segundos,
        )

        return {
            "sucesso": bool(
                isinstance(resultado, dict)
                and resultado.get("sucesso") is True
            ),
            "estado": "evolucao_remota_executada",
            "origem": self.FONTE,
            "valor": deepcopy(resultado),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }


    def executar_solicitacao_evolucao_remota(
        self,
        solicitacao_id: str,
        *,
        arquivo_destino: str = "experimento.py",
        descricao: str = "",
        timeout_seconds: int = 60,
        timeout_resultado_segundos: int = 300,
        intervalo_resultado_segundos: int = 5,
    ) -> dict[str, Any]:
        """
        Delega explicitamente uma solicitação formal pronta ao ciclo
        de evolução remota.

        A solicitação precisa existir, estar pronta para experimento e
        conter um artefato válido. O Runtime não executa localmente,
        não concede autorização de integração e não modifica stable.
        """
        if self.solicitacao_evolucao is None:
            self.solicitacao_evolucao = SolicitacaoEvolucaoNixal(
                repositorio=BASE_DIR,
            )

        if self.evolucao_remota is None:
            self.evolucao_remota = CicloEvolucaoRemotaNixal(
                repositorio=BASE_DIR,
                memoria_aprendizado=self.memoria_aprendizado,
            )

        try:
            solicitacao = self.solicitacao_evolucao.consultar(
                solicitacao_id
            )
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "solicitacao_evolucao_indisponivel",
                "origem": self.FONTE,
                "solicitacao_id": solicitacao_id,
                "motivo": f"{type(erro).__name__}: {erro}",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        try:
            resultado = self.evolucao_remota.executar_solicitacao(
                solicitacao,
                arquivo_destino=arquivo_destino,
                descricao=descricao,
                timeout_seconds=timeout_seconds,
                timeout_resultado_segundos=timeout_resultado_segundos,
                intervalo_resultado_segundos=intervalo_resultado_segundos,
            )
        except Exception as erro:
            falha = {
                "sucesso": False,
                "estado": "solicitacao_experimentada",
                "origem": self.FONTE,
                "solicitacao_id": solicitacao_id,
                "valor": {
                    "sucesso": False,
                    "estado": "experimento_falhou",
                    "motivo": f"{type(erro).__name__}: {erro}",
                },
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

            try:
                persistencia_falha = (
                    self.solicitacao_evolucao.registrar_resultado_experimento(
                        solicitacao_id,
                        falha,
                    )
                )
            except Exception as erro_persistencia:
                return {
                    "sucesso": False,
                    "estado": "persistencia_solicitacao_falhou",
                    "origem": self.FONTE,
                    "solicitacao_id": solicitacao_id,
                    "motivo": (
                        f"{type(erro).__name__}: {erro}; "
                        f"persistencia: "
                        f"{type(erro_persistencia).__name__}: "
                        f"{erro_persistencia}"
                    ),
                    "autorizacao_explicita": False,
                    "integracao_executada": False,
                    "stable_modificada": False,
                }

            return {
                "sucesso": False,
                "estado": "evolucao_remota_falhou",
                "origem": self.FONTE,
                "solicitacao_id": solicitacao_id,
                "motivo": f"{type(erro).__name__}: {erro}",
                "persistencia_solicitacao": deepcopy(
                    persistencia_falha
                ),
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        sucesso = bool(
            isinstance(resultado, dict)
            and resultado.get("sucesso") is True
        )
        estado_runtime = (
            "solicitacao_evolucao_remota_executada"
            if sucesso
            else "solicitacao_evolucao_remota_falhou"
        )

        registro_resultado = {
            "sucesso": sucesso,
            "estado": (
                "solicitacao_executada"
                if sucesso
                else "solicitacao_experimentada"
            ),
            "origem": self.FONTE,
            "solicitacao_id": solicitacao_id,
            "valor": deepcopy(resultado),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

        try:
            persistencia = (
                self.solicitacao_evolucao.registrar_resultado_experimento(
                    solicitacao_id,
                    registro_resultado,
                )
            )
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "persistencia_solicitacao_falhou",
                "origem": self.FONTE,
                "solicitacao_id": solicitacao_id,
                "valor": deepcopy(resultado),
                "motivo": f"{type(erro).__name__}: {erro}",
                "autorizacao_explicita": False,
                "integracao_executada": False,
                "stable_modificada": False,
            }

        return {
            "sucesso": sucesso,
            "estado": estado_runtime,
            "origem": self.FONTE,
            "solicitacao_id": solicitacao_id,
            "valor": deepcopy(resultado),
            "persistencia_solicitacao": deepcopy(
                persistencia
            ),
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

    # ============================================================
    # CICLO
    # ============================================================

    def executar_ciclo(self) -> dict[str, Any]:
        ciclo_id = self._gerar_id_ciclo()
        iniciado_em = self._agora_iso()
        etapas: list[dict[str, Any]] = []

        aprendizado_anterior = (
            self.memoria_aprendizado.contexto_para_proximo_ciclo()
            if self.aprendizado_habilitado
            else {
                "disponivel": False,
                "fonte": self.FONTE,
                "motivo": "aprendizado_desabilitado_para_o_ciclo_residente",
                "aplicado_no_ciclo_atual": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            }
        )
        persistencia_anterior = self.persistencia_operacional.contexto()

        self._registrar_etapa(
            etapas,
            "iniciado",
            {
                "ciclo_id": ciclo_id,
                "aprendizado_anterior_disponivel": bool(
                    aprendizado_anterior.get("disponivel")
                ),
                "persistencia_operacional_disponivel": bool(
                    persistencia_anterior.get("sucesso")
                ),
                "ultimo_ciclo_persistido": (
                    persistencia_anterior.get("ultimo_ciclo") or {}
                ).get("ciclo_id")
                if isinstance(
                    persistencia_anterior.get("ultimo_ciclo"),
                    dict,
                )
                else None,
            },
        )

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

            if self.modo_residente:
                investigacao_resultado = {
                    "sucesso": True,
                    "estado": "investigacao_profunda_adiada_no_perfil_residente",
                    "origem": self.FONTE,
                    "valor": {
                        "executada": False,
                        "motivo": (
                            "A investigação profunda não é executada "
                            "em cada ciclo residente de alta frequência."
                        ),
                        "proxima_acao": "investigacao_sob_demanda",
                        "conhecimento_permanente": False,
                        "arquitetura_modificada": False,
                    },
                }
            else:
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

            if aprendizado_anterior.get("disponivel") is True:
                aprendizado_anterior["aplicado_no_ciclo_atual"] = True

            decisao = self._decidir(
                estado_corpo=estado_corpo,
                prioridades=prioridade,
                aprendizado_anterior=aprendizado_anterior,
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
                decisao=decisao,
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

            if self.aprendizado_habilitado:
                aprendizado = self.memoria_aprendizado.registrar(
                    ciclo_id=ciclo_id,
                    experiencia=experiencia,
                    avaliacao=avaliacao,
                )
            else:
                aprendizado = {
                    "sucesso": True,
                    "estado": "aprendizado_desabilitado",
                    "origem": self.FONTE,
                    "novo": False,
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                }

            if aprendizado.get("sucesso") is not True:
                return self._encerrar_com_erro(
                    ciclo_id,
                    iniciado_em,
                    etapas,
                    aprendizado.get(
                        "motivo",
                        "O registro do aprendizado falhou.",
                    ),
                )

            etapas.append(
                {
                    "etapa": "aprendizado",
                    "sucesso": True,
                    "resultado": deepcopy(aprendizado),
                }
            )

            transicao_llc2 = None
            if self.learning_loop_causal is not None:
                transicao_llc2 = self.learning_loop_causal.fechar_transicao(
                    aprendizado_anterior=aprendizado_anterior,
                    decisao=decisao,
                    acao_resultado=acao_resultado,
                    resultado_observado=resultado_observado,
                    avaliacao=avaliacao,
                    aprendizado_novo=aprendizado,
                )
                etapas.append(
                    {
                        "etapa": "llc2",
                        "sucesso": bool(transicao_llc2.get("ciclo_fechado")),
                        "resultado": deepcopy(transicao_llc2),
                    }
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
                    "aprendizado": deepcopy(aprendizado),
                    "llc2": deepcopy(transicao_llc2),
                    "aprendizado_anterior": deepcopy(
                        aprendizado_anterior
                    ),
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

            try:
                persistencia_operacional = self.persistencia_operacional.registrar(
                    ciclo=ciclo,
                    habitat={
                        "estado": "habitat_observado",
                        "origem": "nyxal_runtime",
                        "versao": self.VERSAO,
                        "host": {
                            "modo": "somente_leitura",
                        },
                        "recursos": estado_corpo.get("corpo", {}),
                        "timestamp": estado_corpo.get("percepcao", {}).get(
                            "timestamp"
                        ),
                    },
                    estado=ciclo.get("estado"),
                )
            except Exception as erro_persistencia:
                persistencia_operacional = {
                    "sucesso": False,
                    "estado": "persistencia_operacional_falhou",
                    "origem": "nyxal_runtime",
                    "motivo": (
                        f"{type(erro_persistencia).__name__}: "
                        f"{erro_persistencia}"
                    ),
                    "conhecimento_permanente": False,
                    "arquitetura_modificada": False,
                }

            ciclo["valor"]["persistencia_operacional"] = deepcopy(
                persistencia_operacional
            )

            try:
                ultimo_ciclo_anterior = persistencia_anterior.get(
                    "ultimo_ciclo"
                )
                estado_anterior_delta = (
                    ultimo_ciclo_anterior.get("estado")
                    if isinstance(ultimo_ciclo_anterior, dict)
                    else "inicial"
                ) or "inicial"

                delta_evento = self.delta_nyxos.criar_evento(
                    tipo="ciclo",
                    estado_anterior=estado_anterior_delta,
                    estado_novo=ciclo.get("estado"),
                    causa="ciclo_runtime_concluido",
                    evidencias=[
                        {
                            "ciclo_id": ciclo.get("ciclo_id"),
                            "persistencia_operacional": (
                                persistencia_operacional.get("estado")
                            ),
                        }
                    ],
                    ciclo=ciclo.get("ciclo_id"),
                    resultado={
                        "sucesso": ciclo.get("sucesso"),
                        "avaliacao": avaliacao.get("avaliacao"),
                    },
                )
                registro_delta = self.delta_nyxos.registrar(delta_evento)
            except Exception as erro_delta:
                registro_delta = {
                    "sucesso": False,
                    "estado": "delta_registro_falhou",
                    "origem": self.FONTE,
                    "motivo": f"{type(erro_delta).__name__}: {erro_delta}",
                    "autorizacao_explicita": False,
                    "integracao_executada": False,
                    "arquitetura_modificada": False,
                }

            ciclo["valor"]["delta"] = deepcopy(registro_delta)
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

        # Captura a hipótese no ponto exato em que o ciclo formal
        # a recebe ainda provisória, antes de teste e avaliação.
        self._capturar_hipotese_provisoria(ciclo)

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

        consolidacao_conhecimento = (
            self.consolidacao_conhecimento.consolidar_candidato(
                ciclo_final
            )
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
                    self.memoria_conhecimento.registrar(candidato)
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
        aprendizado_anterior: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(estado_corpo, dict):
            return {
                "sucesso": False,
                "acao": None,
                "motivo": "Estado corporal inválido.",
            }

        contexto_aprendizado = (
            deepcopy(aprendizado_anterior)
            if isinstance(aprendizado_anterior, dict)
            else {
                "disponivel": False,
                "fonte": "aprendizado_persistente_nixal",
                "aplicado_no_ciclo_atual": False,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            }
        )

        if self.learning_loop_causal is not None:
            return self.learning_loop_causal.selecionar(
                estado_corpo=estado_corpo,
                prioridades=prioridades,
                aprendizado_anterior=aprendizado_anterior,
            )

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
            "aprendizado_considerado": contexto_aprendizado,
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

        if acao == "observar_sem_atuar":
            return {
                "sucesso": True,
                "estado": "observacao_sem_atuacao",
                "acao": acao,
                "executada": False,
                "motivo": (
                    "A politica LLC selecionou observacao sem atuacao "
                    "com base em evidencia de aprendizado."
                ),
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

    def _avaliar_resultado(
        self,
        acao_resultado: dict[str, Any],
        resultado_observado: dict[str, Any],
        decisao: dict[str, Any] | None = None,
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

        feedback_llc2 = None
        if self.learning_loop_causal is not None and isinstance(decisao, dict):
            feedback_llc2 = self.learning_loop_causal.avaliar_resultado(
                decisao=decisao,
                acao_resultado=acao_resultado,
                resultado_observado=resultado_observado,
            )

        if not acao_sucesso or not observacao_sucesso:
            return {
                "sucesso": True,
                "estado": "resultado_avaliado",
                "avaliacao": "falha",
                "motivo": (
                    "A ação executada ou a observação do resultado "
                    "não foi considerada bem-sucedida."
                ),
                "llc2": deepcopy(feedback_llc2)
                if feedback_llc2 is not None
                else None,
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
            "llc2": deepcopy(feedback_llc2)
            if feedback_llc2 is not None
            else None,
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

        # Não seguir links simbólicos nem substituir registros que não possam ser
        # lidos/validados; logs operacionais são evidência de recuperação.
        if self.arquivo_log.is_symlink():
            return
        if self.arquivo_log.exists():
            try:
                with self.arquivo_log.open("rb") as arquivo_existente:
                    conteudo_existente = arquivo_existente.read(
                        MAX_TAMANHO_LOG_RUNTIME + 1
                    )
                if len(conteudo_existente) > MAX_TAMANHO_LOG_RUNTIME:
                    backup = self.arquivo_log.with_name(
                        f"{self.arquivo_log.name}.oversized-{time.time_ns()}"
                    )
                    # Não substitua uma evidência que já exista com o mesmo nome.
                    if backup.exists() or backup.is_symlink():
                        return
                    try:
                        os.replace(self.arquivo_log, backup)
                        if backup.is_symlink():
                            os.replace(backup, self.arquivo_log)
                            return
                        try:
                            os.chmod(backup, 0o600)
                        except OSError:
                            # Se o backup não puder ser protegido, restaure o nome
                            # original e falhe fechado.
                            try:
                                os.replace(backup, self.arquivo_log)
                            except OSError:
                                pass
                            return
                    except OSError:
                        return
                else:
                    carregado = json.loads(conteudo_existente.decode("utf-8"))
                    if not isinstance(carregado, list):
                        return
                    dados = carregado
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                # Não apague automaticamente um arquivo ilegível ou corrompido.
                return

        registro = deepcopy(ciclo)
        tamanho_registro = len(
            json.dumps(
                registro,
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
        )

        # Ciclos podem conter etapas/resultados muito grandes. Preserve
        # os identificadores do ciclo, mas resuma o payload volumoso.
        if tamanho_registro > MAX_TAMANHO_LOG_RUNTIME // 2:
            registro = {
                "sucesso": bool(ciclo.get("sucesso", False)),
                "estado": str(ciclo.get("estado", "desconhecido"))[:64],
                "origem": str(ciclo.get("origem", self.FONTE))[:128],
                "versao_runtime": str(
                    ciclo.get("versao_runtime", self.VERSAO)
                )[:64],
                "ciclo_id": str(ciclo.get("ciclo_id", ""))[:128],
                "iniciado_em": str(ciclo.get("iniciado_em", ""))[:128],
                "concluido_em": str(ciclo.get("concluido_em", ""))[:128],
                "valor": {
                    "resumo_truncado": True,
                    "tamanho_original_bytes": tamanho_registro,
                },
                "erro": (
                    str(ciclo.get("erro"))[:2048]
                    if ciclo.get("erro") is not None
                    else None
                ),
            }

        dados.append(registro)
        dados = dados[-100:]

        payload = json.dumps(
            dados,
            ensure_ascii=False,
            indent=2,
        )

        # O teto é definido por bytes serializados, não pelo número
        # de ciclos, porque uma única etapa pode conter saída extensa.
        while (
            len(payload.encode("utf-8")) > MAX_TAMANHO_LOG_RUNTIME
            and len(dados) > 1
        ):
            dados.pop(0)
            payload = json.dumps(
                dados,
                ensure_ascii=False,
                indent=2,
            )

        if len(payload.encode("utf-8")) > MAX_TAMANHO_LOG_RUNTIME:
            dados = [
                {
                    "sucesso": bool(registro.get("sucesso", False)),
                    "estado": str(registro.get("estado", "desconhecido"))[:64],
                    "origem": str(registro.get("origem", self.FONTE))[:128],
                    "versao_runtime": str(
                        registro.get("versao_runtime", self.VERSAO)
                    )[:64],
                    "ciclo_id": str(registro.get("ciclo_id", ""))[:128],
                    "valor": {
                        "resumo_truncado": True,
                        "tamanho_original_bytes": tamanho_registro,
                    },
                }
            ]
            payload = json.dumps(
                dados,
                ensure_ascii=False,
                indent=2,
            )

        if len(payload.encode("utf-8")) > MAX_TAMANHO_LOG_RUNTIME:
            dados = []

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
        payload = json.dumps(dados, ensure_ascii=False, indent=2)
        descritor, temporario = tempfile.mkstemp(
            prefix=f".{caminho.name}.",
            suffix=".tmp",
            dir=str(caminho.parent),
        )
        try:
            # Transfer the descriptor immediately so failures still close it.
            with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
                os.fchmod(arquivo.fileno(), 0o600)
                arquivo.write(payload)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, caminho)
            os.chmod(caminho, 0o600)
            diretorio_fd = os.open(
                caminho.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(diretorio_fd)
            finally:
                os.close(diretorio_fd)
        finally:
            try:
                os.unlink(temporario)
            except FileNotFoundError:
                pass


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
