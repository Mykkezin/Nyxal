#!/usr/bin/env python3
"""Gate de preparação para a defesa governada da Nyxal.

Esta etapa valida, deduplica e registra planos exclusivamente em memória.
Não contém executor real, não toca rede/firewall/systemd/arquivos, não chama
shell e não transforma uma recomendação em autorização. Mesmo quando um
verificador externo confirma uma aprovação, o resultado permanece simulado.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from ipaddress import ip_address
from threading import Lock
from time import monotonic
from typing import Any, Callable

from nixal_defesa_autonoma import SERVICOS_CONTROLADOS, _identificador_seguro, _ip_canonico


VERSAO_EXECUTOR = "0.1"
MAX_TTL_SEGUNDOS = 3600
MAX_REGISTROS = 256
MAX_CHAVES_IDEMPOTENCIA = 2048
MAX_MOTIVO_CHARS = 240

TIPOS_RECOMENDACAO = frozenset({
    "alertar_operador",
    "preservar_evidencia",
    "solicitar_revisao_de_incidente",
    "limitar_taxa_origem",
    "bloqueio_temporario_origem",
    "isolar_servico",
    "propor_reinicio_controlado",
    "revogar_credencial",
    "quarentenar_artefato",
    "encaminhar_para_enganacao_isolada",
})

# Todas as intenções que não são mero alerta exigem aprovação humana, mesmo
# que uma recomendação recebida indique o contrário. Ainda assim, não executam.
TIPOS_QUE_EXIGEM_APROVACAO = TIPOS_RECOMENDACAO - {"alertar_operador"}
TIPOS_COM_DURACAO = frozenset({
    "limitar_taxa_origem",
    "bloqueio_temporario_origem",
    "encaminhar_para_enganacao_isolada",
})


def _texto_limitado(valor: Any, limite: int) -> str | None:
    if not isinstance(valor, str):
        return None
    normalizado = " ".join(valor.split())[:limite]
    return normalizado or None


def _motivo_sem_segredos(valor: Any) -> str | None:
    """Redige credenciais óbvias e não ecoa metadados arbitrários da entrada."""
    texto = _texto_limitado(valor, MAX_MOTIVO_CHARS)
    if texto is None:
        return None
    import re

    texto = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [redigido]", texto)
    texto = re.sub(
        r"(?i)\b(token|api[_ -]?key|password|secret|senha)\s*[:=]\s*\S+",
        r"\1=[redigido]",
        texto,
    )
    return texto


def _escopo_validado(tipo: str, escopo: Any) -> str | None:
    if not isinstance(escopo, str) or not 1 <= len(escopo) <= 128:
        return None

    if tipo in {"limitar_taxa_origem", "bloqueio_temporario_origem"}:
        ip = _ip_canonico(escopo)
        if ip is None:
            return None
        try:
            endereco = ip_address(ip)
        except ValueError:
            return None
        # Não preparar contenção para o próprio host, mesmo em dry-run.
        return ip if not endereco.is_loopback else None

    if tipo in {"isolar_servico", "propor_reinicio_controlado"}:
        return escopo if escopo in SERVICOS_CONTROLADOS else None

    if tipo == "revogar_credencial":
        if not _identificador_seguro(escopo) or escopo in {".", ".."}:
            return None
        return escopo

    if tipo == "quarentenar_artefato":
        if (
            not _identificador_seguro(escopo)
            or escopo in {".", ".."}
            or "/" in escopo
            or "\\" in escopo
        ):
            return None
        return escopo

    if tipo == "encaminhar_para_enganacao_isolada":
        return "decoy-service-interno" if escopo == "decoy-service-interno" else None

    if tipo == "preservar_evidencia":
        if escopo == "evento-local" or _identificador_seguro(escopo):
            return escopo
        return None

    if tipo == "solicitar_revisao_de_incidente":
        if escopo == "incidente-local" or _identificador_seguro(escopo):
            return escopo
        return None

    if tipo == "alertar_operador":
        if escopo == "defesa-nyxal" or escopo in SERVICOS_CONTROLADOS:
            return escopo
        return None

    return None


class ExecutorDefesaGovernada:
    """Prepara propostas controladas sem nunca realizar efeitos.

    O verificador de aprovação, se injetado pela camada de confiança superior,
    só valida a evidência de aprovação. Ele nunca habilita execução: este módulo
    não implementa uma operação de execução física.
    """

    def __init__(
        self,
        *,
        ttl_segundos: int = 300,
        janela_idempotencia_segundos: int = 300,
        max_registros: int = MAX_REGISTROS,
        relogio: Callable[[], float] = monotonic,
        verificador_aprovacao: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        for nome, valor, minimo, maximo in (
            ("ttl_segundos", ttl_segundos, 1, MAX_TTL_SEGUNDOS),
            ("janela_idempotencia_segundos", janela_idempotencia_segundos, 1, MAX_TTL_SEGUNDOS),
            ("max_registros", max_registros, 1, MAX_REGISTROS),
        ):
            if isinstance(valor, bool) or not isinstance(valor, int) or not minimo <= valor <= maximo:
                raise ValueError(f"{nome}_fora_dos_limites")
        if not callable(relogio):
            raise ValueError("relogio_precisa_ser_chamavel")
        if verificador_aprovacao is not None and not callable(verificador_aprovacao):
            raise ValueError("verificador_aprovacao_precisa_ser_chamavel")

        self._ttl = ttl_segundos
        self._janela_idempotencia = janela_idempotencia_segundos
        self._relogio = relogio
        self._verificador_aprovacao = verificador_aprovacao
        self._registros: deque[dict[str, Any]] = deque(maxlen=max_registros)
        self._idempotencia: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._lock = Lock()

    @staticmethod
    def _utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _chave_idempotencia(tipo: str, escopo: str, duracao: int | None, motivo: str) -> str:
        canonico = "|".join((tipo, escopo, str(duracao or ""), motivo))
        return sha256(canonico.encode("utf-8")).hexdigest()

    def _validar_recomendacao(self, recomendacao: Any) -> dict[str, Any] | None:
        if not isinstance(recomendacao, dict):
            return None
        tipo = recomendacao.get("tipo")
        if not isinstance(tipo, str) or tipo not in TIPOS_RECOMENDACAO:
            return None
        escopo = _escopo_validado(tipo, recomendacao.get("escopo"))
        motivo = _motivo_sem_segredos(recomendacao.get("motivo"))
        if escopo is None or motivo is None:
            return None

        duracao: int | None = None
        valor_duracao = recomendacao.get("duracao_segundos")
        if tipo in TIPOS_COM_DURACAO:
            if (
                isinstance(valor_duracao, bool)
                or not isinstance(valor_duracao, int)
                or not 1 <= valor_duracao <= MAX_TTL_SEGUNDOS
            ):
                return None
            duracao = valor_duracao
        elif valor_duracao is not None:
            if (
                isinstance(valor_duracao, bool)
                or not isinstance(valor_duracao, int)
                or not 1 <= valor_duracao <= MAX_TTL_SEGUNDOS
            ):
                return None
            duracao = valor_duracao

        exige_aprovacao = (
            True
            if tipo in TIPOS_QUE_EXIGEM_APROVACAO
            else bool(recomendacao.get("exige_aprovacao_humana", False))
        )
        return {
            "tipo": tipo,
            "escopo": escopo,
            "motivo": motivo,
            "duracao_segundos": duracao,
            "exige_aprovacao_humana": exige_aprovacao,
        }

    def _verificar_aprovacao(self, aprovacao: Any) -> bool:
        if not isinstance(aprovacao, dict) or self._verificador_aprovacao is None:
            return False
        try:
            return self._verificador_aprovacao(deepcopy(aprovacao)) is True
        except Exception:
            # Aprovação inválida ou serviço indisponível: falhar fechado.
            return False

    def _expirar_idempotencia(self, agora: float) -> None:
        expiradas = [
            chave for chave, (expira_em, _) in self._idempotencia.items()
            if expira_em <= agora
        ]
        for chave in expiradas:
            self._idempotencia.pop(chave, None)
        while len(self._idempotencia) > MAX_CHAVES_IDEMPOTENCIA:
            self._idempotencia.popitem(last=False)

    def preparar(
        self,
        recomendacao: Any,
        *,
        aprovacao: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Cria uma proposta em memória; jamais executa a operação recomendada."""
        validada = self._validar_recomendacao(recomendacao)
        if validada is None:
            return {
                "sucesso": False,
                "estado": "recomendacao_rejeitada",
                "motivo": "Recomendação malformada, fora da allowlist ou com escopo/duração inválidos.",
                "executor_ativo": False,
                "executor_autorizado": False,
                "efeito_executado": False,
            }

        aprovacao_verificada = self._verificar_aprovacao(aprovacao)
        chave = self._chave_idempotencia(
            validada["tipo"],
            validada["escopo"],
            validada["duracao_segundos"],
            validada["motivo"],
        )
        agora = self._relogio()
        with self._lock:
            self._expirar_idempotencia(agora)
            existente = self._idempotencia.get(chave)
            if existente is not None:
                _, plano_id = existente
                return {
                    "sucesso": True,
                    "estado": "duplicado_idempotente",
                    "plano_id": plano_id,
                    "executor_ativo": False,
                    "executor_autorizado": False,
                    "efeito_executado": False,
                }

            criado = self._utc()
            expira = criado + timedelta(seconds=self._ttl)
            plano_id = "plano-" + sha256(
                f"{chave}|{agora:.9f}".encode("utf-8")
            ).hexdigest()[:24]
            exige_aprovacao = validada["exige_aprovacao_humana"]
            estado = (
                "aguardando_aprovacao"
                if exige_aprovacao and not aprovacao_verificada
                else "simulacao_preparada"
            )
            registro = {
                "plano_id": plano_id,
                "versao": VERSAO_EXECUTOR,
                "estado": estado,
                "criado_em": criado.isoformat(),
                "expira_em": expira.isoformat(),
                "ttl_segundos": self._ttl,
                "acao": deepcopy(validada),
                "aprovacao_verificada": aprovacao_verificada,
                "exige_aprovacao_humana": exige_aprovacao,
                "modo": "dry_run",
                "executor_ativo": False,
                "executor_autorizado": False,
                "efeito_executado": False,
            }
            self._registros.append(registro)
            self._idempotencia[chave] = (
                agora + max(self._ttl, self._janela_idempotencia),
                plano_id,
            )
            self._idempotencia.move_to_end(chave)
            self._expirar_idempotencia(agora)

            return {
                "sucesso": True,
                "estado": estado,
                "plano_id": plano_id,
                "plano": deepcopy(registro),
                "executor_ativo": False,
                "executor_autorizado": False,
                "efeito_executado": False,
            }

    def listar_registros(self, limite: int = 20) -> list[dict[str, Any]]:
        if isinstance(limite, bool) or not isinstance(limite, int) or not 1 <= limite <= MAX_REGISTROS:
            raise ValueError("limite_invalido")
        with self._lock:
            return [deepcopy(item) for item in list(self._registros)[-limite:]]

    def contexto(self) -> dict[str, Any]:
        with self._lock:
            quantidade = len(self._registros)
        return {
            "sucesso": True,
            "estado": "executor_defesa_dry_run_disponivel",
            "versao": VERSAO_EXECUTOR,
            "modo": "dry_run",
            "quantidade_registros_em_memoria": quantidade,
            "limite_registros": self._registros.maxlen,
            "executor_ativo": False,
            "execucao_fisica_implementada": False,
            "persistencia_duravel": False,
            "aprovacao_humana_concede_execucao": False,
        }


__all__ = ["ExecutorDefesaGovernada", "TIPOS_RECOMENDACAO", "VERSAO_EXECUTOR"]
