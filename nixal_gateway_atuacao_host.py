#!/usr/bin/env python3
"""
NYXOS — M5.10 GATEWAY DE ATUAÇÃO DO HOST

Franqueia uma única fronteira entre uma solicitação estruturada e
uma ação concreta no host.

Princípios:
- a entrada é contrato estruturado, não linguagem natural;
- somente ações registradas no allowlist podem atravessar o gateway;
- política é validada antes do executor;
- argumentos são validados pelo contrato da ação;
- o gateway não interpreta shell nem recebe comandos arbitrários;
- dry-run permite validar o caminho sem atuar no host;
- resultados e execuções são observáveis;
- integração/evolução permanecem fora desta camada.
"""

from __future__ import annotations

import copy
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nixal_delta import RegistroDeltaNixOS


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_LOG_PADRAO = BASE_DIR / "log_atuacao_host_nixal.json"


@dataclass(frozen=True)
class ContratoAcaoHost:
    """Contrato declarativo de uma ação permitida sobre o host."""

    nome: str
    descricao: str
    objetivo: str
    argumentos: dict[str, dict[str, Any]]
    dominio: str
    nivel_risco: str
    reversivel: bool
    requer_autorizacao_explicita: bool = True

    def especificacao(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "descricao": self.descricao,
            "objetivo": self.objetivo,
            "argumentos": copy.deepcopy(self.argumentos),
            "dominio": self.dominio,
            "nivel_risco": self.nivel_risco,
            "reversivel": self.reversivel,
            "requer_autorizacao_explicita": (
                self.requer_autorizacao_explicita
            ),
        }


class GatewayAtuacaoHostNixOS:
    """
    Ponto único de entrada para atuação controlada no host.

    A lista de ações é injetada por código do sistema. Ela não é derivada
    de texto, Qwen, shell ou arquivos de configuração controlados pela IA.
    M5.10 não registra ações concretas por padrão; M5.11 adicionará as
    primeiras operações de processos/aplicativos.
    """

    FONTE = "gateway_atuacao_host_nyxos"
    VERSAO = "5.10.0"

    TIPOS_VALIDOS = {"string", "integer", "number", "boolean"}
    NIVEIS_RISCO_VALIDOS = {"baixo", "medio", "alto"}
    MAX_EVENTOS_LOG = 100
    MAX_TAMANHO_RESULTADO = 5000

    def __init__(
        self,
        *,
        contratos: dict[str, ContratoAcaoHost] | None = None,
        executores: dict[str, Callable[..., Any]] | None = None,
        arquivo_log: str | Path = ARQUIVO_LOG_PADRAO,
        delta_nyxos: RegistroDeltaNixOS | None = None,
    ) -> None:
        self.arquivo_log = Path(arquivo_log)
        self.delta_nyxos = delta_nyxos
        self.contratos = dict(contratos or {})
        self.executores = dict(executores or {})
        self._validar_catalogo()
        self._dados_log = self._carregar_log()

    def _validar_catalogo(self) -> None:
        for nome, contrato in self.contratos.items():
            if not isinstance(nome, str) or not nome.strip():
                raise ValueError("nome_acao_invalido")

            if not isinstance(contrato, ContratoAcaoHost):
                raise TypeError(
                    f"O contrato {nome} precisa ser ContratoAcaoHost."
                )

            if contrato.nome != nome:
                raise ValueError(
                    f"nome_contrato_inconsistente:{nome}"
                )

            if contrato.nivel_risco not in self.NIVEIS_RISCO_VALIDOS:
                raise ValueError("nivel_risco_invalido")

            self._validar_especificacao_argumentos(
                contrato.argumentos
            )

            executor = self.executores.get(nome)
            if executor is not None and not callable(executor):
                raise TypeError(
                    f"executor_invalido:{nome}"
                )

            if executor is None:
                raise ValueError(
                    f"acao_sem_executor:{nome}"
                )

    @classmethod
    def _validar_especificacao_argumentos(
        cls,
        especificacao: dict[str, dict[str, Any]],
    ) -> None:
        if not isinstance(especificacao, dict):
            raise TypeError(
                "argumentos_contrato_invalidos"
            )

        for nome, regras in especificacao.items():
            if not isinstance(nome, str) or not nome.strip():
                raise ValueError(
                    "nome_argumento_invalido"
                )

            if not isinstance(regras, dict):
                raise TypeError(
                    f"regras_argumento_invalidas:{nome}"
                )

            tipo = regras.get("tipo", "string")
            if tipo not in cls.TIPOS_VALIDOS:
                raise ValueError(
                    f"tipo_argumento_nao_suportado:{nome}"
                )

            obrigatorio = regras.get(
                "obrigatorio",
                False,
            )

            if not isinstance(
                obrigatorio,
                bool,
            ):
                raise TypeError(
                    f"obrigatorio_invalido:{nome}"
                )

            valores = regras.get(
                "valores"
            )

            if valores is not None and not isinstance(
                valores,
                list,
            ):
                raise TypeError(
                    f"valores_invalidos:{nome}"
                )

    @staticmethod
    def _estrutura_log() -> dict[str, Any]:
        return {
            "versao": GatewayAtuacaoHostNixOS.VERSAO,
            "origem": GatewayAtuacaoHostNixOS.FONTE,
            "eventos": [],
        }

    def _carregar_log(self) -> dict[str, Any]:
        if not self.arquivo_log.is_file():
            return self._estrutura_log()

        try:
            dados = json.loads(
                self.arquivo_log.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return self._estrutura_log()

        if (
            not isinstance(dados, dict)
            or dados.get("versao")
            != self.VERSAO
            or not isinstance(
                dados.get("eventos"),
                list,
            )
        ):
            return self._estrutura_log()

        return {
            "versao": self.VERSAO,
            "origem": self.FONTE,
            "eventos": copy.deepcopy(
                dados["eventos"][
                    -self.MAX_EVENTOS_LOG :
                ]
            ),
        }

    def _salvar_log(self) -> None:
        self.arquivo_log.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporario = self.arquivo_log.with_name(
            self.arquivo_log.name
            + ".tmp"
        )

        temporario.write_text(
            json.dumps(
                self._dados_log,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        os.replace(
            temporario,
            self.arquivo_log,
        )

    def _registrar_evento_observabilidade(
        self,
        evento: dict[str, Any],
    ) -> None:
        self._dados_log["eventos"].append(
            copy.deepcopy(evento)
        )

        self._dados_log["eventos"] = (
            self._dados_log["eventos"][
                -self.MAX_EVENTOS_LOG :
            ]
        )

        self._salvar_log()

    @staticmethod
    def _tipo_compativel(
        valor: Any,
        tipo: str,
    ) -> bool:
        if tipo == "string":
            return isinstance(
                valor,
                str,
            )

        if tipo == "integer":
            return (
                isinstance(
                    valor,
                    int,
                )
                and not isinstance(
                    valor,
                    bool,
                )
            )

        if tipo == "number":
            return (
                isinstance(
                    valor,
                    (int, float),
                )
                and not isinstance(
                    valor,
                    bool,
                )
            )

        if tipo == "boolean":
            return isinstance(
                valor,
                bool,
            )

        return False

    @classmethod
    def _validar_argumentos(
        cls,
        contrato: ContratoAcaoHost,
        argumentos: Any,
    ) -> tuple[bool, str | None]:
        if not isinstance(
            argumentos,
            dict,
        ):
            return (
                False,
                "argumentos_precisam_ser_objeto",
            )

        especificacao = contrato.argumentos

        for nome in argumentos:
            if nome not in especificacao:
                return (
                    False,
                    f"argumento_nao_permitido:{nome}",
                )

        for (
            nome,
            regras,
        ) in especificacao.items():
            if (
                regras.get(
                    "obrigatorio",
                    False,
                )
                and nome not in argumentos
            ):
                return (
                    False,
                    f"argumento_obrigatorio_ausente:{nome}",
                )

            if nome not in argumentos:
                continue

            valor = argumentos[nome]
            tipo = regras.get(
                "tipo",
                "string",
            )

            if not cls._tipo_compativel(
                valor,
                tipo,
            ):
                return (
                    False,
                    f"tipo_argumento_invalido:{nome}",
                )

            valores = regras.get(
                "valores"
            )

            if (
                valores is not None
                and valor not in valores
            ):
                return (
                    False,
                    f"valor_argumento_nao_permitido:{nome}",
                )

        return True, None

    def validar_politica(
        self,
        solicitacao: Any,
        *,
        autorizacao_acao: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(
            solicitacao,
            dict,
        ):
            return {
                "permitido": False,
                "estado": "entrada_invalida",
                "motivo": (
                    "A atuação precisa chegar "
                    "como contrato estruturado."
                ),
            }

        campos = {
            "acao",
            "argumentos",
            "metadados",
        }

        desconhecidos = (
            set(solicitacao)
            - campos
        )

        if desconhecidos:
            return {
                "permitido": False,
                "estado": "entrada_invalida",
                "motivo": (
                    "Campos não permitidos: "
                    + ", ".join(
                        sorted(
                            desconhecidos
                        )
                    )
                ),
            }

        acao = solicitacao.get(
            "acao"
        )

        if not isinstance(
            acao,
            str,
        ) or not acao.strip():
            return {
                "permitido": False,
                "estado": "entrada_invalida",
                "motivo": (
                    "A ação precisa possuir nome."
                ),
            }

        acao = acao.strip()
        contrato = self.contratos.get(
            acao
        )

        if contrato is None:
            return {
                "permitido": False,
                "estado": "acao_nao_registrada",
                "acao": acao,
                "motivo": (
                    "A ação não está no allowlist "
                    "do gateway."
                ),
            }

        valido, motivo = (
            self._validar_argumentos(
                contrato,
                solicitacao.get(
                    "argumentos",
                    {},
                ),
            )
        )

        if not valido:
            return {
                "permitido": False,
                "estado": "argumentos_invalidos",
                "acao": acao,
                "motivo": motivo,
            }

        if not isinstance(
            autorizacao_acao,
            bool,
        ):
            return {
                "permitido": False,
                "estado": "entrada_invalida",
                "acao": acao,
                "motivo": (
                    "autorizacao_acao precisa ser bool."
                ),
            }

        if (
            contrato.requer_autorizacao_explicita
            and not autorizacao_acao
        ):
            return {
                "permitido": False,
                "estado": (
                    "autorizacao_acao_necessaria"
                ),
                "acao": acao,
                "motivo": (
                    "A ação exige autorização "
                    "explícita no limite de atuação."
                ),
            }

        return {
            "permitido": True,
            "estado": "politica_aprovada",
            "acao": acao,
            "contrato": (
                contrato.especificacao()
            ),
            "argumentos": copy.deepcopy(
                solicitacao.get(
                    "argumentos",
                    {},
                )
            ),
        }

    def executar(
        self,
        solicitacao: Any,
        *,
        autorizacao_acao: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(
            dry_run,
            bool,
        ):
            raise TypeError(
                "dry_run_precisa_ser_bool"
            )

        politica = (
            self.validar_politica(
                solicitacao,
                autorizacao_acao=autorizacao_acao,
            )
        )

        evento_base = {
            "timestamp": time.time(),
            "solicitacao": (
                copy.deepcopy(
                    solicitacao
                )
                if isinstance(
                    solicitacao,
                    dict,
                )
                else None
            ),
            "politica": copy.deepcopy(
                politica
            ),
            "dry_run": dry_run,
        }

        if not politica.get(
            "permitido"
        ):
            evento = {
                **evento_base,
                "estado": "rejeitada",
                "resultado": None,
            }

            self._registrar_evento_observabilidade(
                evento
            )

            return self._resposta(
                False,
                "acao_rejeitada_pela_politica",
                evento,
            )

        if dry_run:
            evento = {
                **evento_base,
                "estado": "simulacao",
                "resultado": {
                    "executada": False,
                    "motivo": "dry_run",
                },
            }

            self._registrar_evento_observabilidade(
                evento
            )

            return self._resposta(
                True,
                "acao_simulada",
                evento,
            )

        acao = politica["acao"]
        argumentos = politica["argumentos"]
        executor = self.executores[acao]

        inicio = time.perf_counter()

        try:
            resultado = executor(
                **argumentos
            )

            duracao_ms = (
                time.perf_counter()
                - inicio
            ) * 1000

            resultado_seguro = (
                self._limitar_resultado(
                    resultado
                )
            )

            evento = {
                **evento_base,
                "estado": "executada",
                "duracao_ms": duracao_ms,
                "resultado": resultado_seguro,
            }

            self._registrar_evento_observabilidade(
                evento
            )

            self._registrar_delta(
                contrato=self.contratos[
                    acao
                ],
                argumentos=argumentos,
                resultado=resultado_seguro,
            )

            return self._resposta(
                True,
                "acao_executada",
                evento,
            )

        except Exception as erro:
            evento = {
                **evento_base,
                "estado": "falhou",
                "erro": (
                    f"{type(erro).__name__}: "
                    f"{erro}"
                ),
            }

            self._registrar_evento_observabilidade(
                evento
            )

            return self._resposta(
                False,
                "acao_falhou",
                evento,
            )

    @staticmethod
    def _resposta(
        sucesso: bool,
        estado: str,
        valor: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "sucesso": sucesso,
            "estado": estado,
            "origem": (
                GatewayAtuacaoHostNixOS.FONTE
            ),
            "valor": valor,
            "autorizacao_evolucao": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }

    @classmethod
    def _limitar_resultado(
        cls,
        resultado: Any,
    ) -> Any:
        try:
            serializado = json.dumps(
                resultado,
                ensure_ascii=False,
            )
        except (
            TypeError,
            ValueError,
        ):
            return {
                "serializavel": False,
                "tipo": type(
                    resultado
                ).__name__,
            }

        if (
            len(serializado)
            <= cls.MAX_TAMANHO_RESULTADO
        ):
            return copy.deepcopy(
                resultado
            )

        return {
            "serializavel": True,
            "truncado": True,
            "tipo": type(
                resultado
            ).__name__,
            "tamanho_original": len(
                serializado
            ),
            "valor": serializado[
                : cls.MAX_TAMANHO_RESULTADO
            ],
        }

    def _registrar_delta(
        self,
        *,
        contrato: ContratoAcaoHost,
        argumentos: dict[str, Any],
        resultado: Any,
    ) -> None:
        if self.delta_nyxos is None:
            return

        evento = (
            RegistroDeltaNixOS.criar_evento(
                tipo="sistema",
                estado_anterior={
                    "acao": contrato.nome,
                    "estado": "solicitada",
                },
                estado_novo={
                    "acao": contrato.nome,
                    "estado": "executada",
                },
                causa="acao_host_executada",
                evidencias=[
                    {
                        "dominio": contrato.dominio,
                        "nivel_risco": (
                            contrato.nivel_risco
                        ),
                        "reversivel": contrato.reversivel,
                        "argumentos": copy.deepcopy(
                            argumentos
                        ),
                    }
                ],
                resultado=resultado,
            )
        )

        self.delta_nyxos.registrar(
            evento
        )

    def listar_acoes(
        self,
    ) -> list[dict[str, Any]]:
        return [
            self.contratos[nome].especificacao()
            for nome in sorted(
                self.contratos
            )
        ]

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": (
                "gateway_atuacao_disponivel"
            ),
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "allowlist": self.listar_acoes(),
            "quantidade_acoes": len(
                self.contratos
            ),
            "shell_arbitrario": False,
            "entrada_linguagem_natural": False,
            "qwen_executor_direto": False,
            "autorizacao_evolucao": False,
            "integracao_executada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }


__all__ = [
    "ContratoAcaoHost",
    "GatewayAtuacaoHostNixOS",
]
