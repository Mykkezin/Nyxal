"""Motor determinístico de decisão para defesa autônoma governada da Nyxal.

Este módulo apenas produz recomendações tipadas. Não executa bloqueios de rede,
comandos de shell, isolamento de serviços, exclusão de arquivos nem ações contra
sistemas externos. Um executor futuro deverá aplicar allowlists, autorização,
auditoria e mecanismos de reversão separados.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from ipaddress import ip_address
from math import isfinite
from time import monotonic
from threading import Lock
from typing import Callable, Deque, Any


POLICY_VERSION = "1.0"
DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_RATE_LIMIT_THRESHOLD = 3
DEFAULT_BLOCK_THRESHOLD = 8
DEFAULT_BLOCK_SECONDS = 300
MAX_WINDOW_SECONDS = 3600
MAX_BLOCK_SECONDS = 3600
MAX_THRESHOLD = 1_000_000
MAX_TRACKED_ORIGINS = 2048
MAX_FAILURES_PER_ORIGIN = 128

SERVICOS_CONTROLADOS = frozenset({
    "nyxal-api",
    "nyxos-residente",
    "inferencia-local",
    "gateway-atuacao",
    "memoria",
})

EVENTOS_SUPORTADOS = frozenset({
    "falha_autenticacao",
    "origem_suspeita",
    "tentativa_exploracao",
    "violacao_integridade",
    "credencial_comprometida",
    "malware_detectado",
    "servico_indisponivel",
    "recuperacao_verificada",
})

# O adaptador de observabilidade deve preencher essa identidade a partir de uma
# fonte local autenticada; este campo sozinho não autentica uma conexão remota.
FONTES_PADRAO_EVENTO = {
    "falha_autenticacao": "api-auth",
    "origem_suspeita": "api-auth",
    "tentativa_exploracao": "ids",
    "violacao_integridade": "integrity-monitor",
    "credencial_comprometida": "credential-monitor",
    "malware_detectado": "malware-scanner",
    "servico_indisponivel": "health-monitor",
    "recuperacao_verificada": "incident-review",
}
FONTES_POR_EVENTO = {
    "falha_autenticacao": frozenset({"api-auth", "waf"}),
    "origem_suspeita": frozenset({"api-auth", "waf"}),
    "tentativa_exploracao": frozenset({"ids", "waf"}),
    "violacao_integridade": frozenset({"integrity-monitor"}),
    "credencial_comprometida": frozenset({"credential-monitor"}),
    "malware_detectado": frozenset({"malware-scanner"}),
    "servico_indisponivel": frozenset({"health-monitor"}),
    "recuperacao_verificada": frozenset({"incident-review"}),
}
EVENTOS_QUE_EXIGEM_EVIDENCIA = frozenset({
    "tentativa_exploracao",
    "violacao_integridade",
    "credencial_comprometida",
    "malware_detectado",
    "servico_indisponivel",
    "recuperacao_verificada",
})

# Identificadores, nunca segredos, caminhos ou conteúdo arbitrário do evento.
_ID_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-"
)


def _identificador_seguro(valor: Any) -> str | None:
    if not isinstance(valor, str) or not 1 <= len(valor) <= 128:
        return None
    if any(char not in _ID_CHARS for char in valor):
        return None
    return valor


def _ip_canonico(valor: Any) -> str | None:
    if not isinstance(valor, str) or not 1 <= len(valor) <= 64:
        return None
    raw = valor.strip()
    if not raw or "%" in raw:
        return None
    try:
        address = ip_address(raw)
        if getattr(address, "ipv4_mapped", None) is not None:
            address = address.ipv4_mapped
        if address.is_unspecified or address.is_multicast:
            return None
        if address.version == 4:
            numeric_ip = int(address)
            if numeric_ip >> 24 == 0 or numeric_ip == 0xFFFFFFFF:
                return None
        return str(address)
    except ValueError:
        return None


def _origem_remota(ip: str | None) -> bool:
    if ip is None:
        return False
    try:
        address = ip_address(ip)
        mapped = getattr(address, "ipv4_mapped", None)
        if mapped is not None:
            address = mapped
        return not address.is_loopback
    except ValueError:
        return False


def _recomendacao(
    tipo: str,
    escopo: str,
    motivo: str,
    *,
    duracao_segundos: int | None = None,
    exige_aprovacao_humana: bool = True,
) -> dict[str, Any]:
    """Gera uma recomendação limitada, reversível quando aplicável e sem execução."""
    item: dict[str, Any] = {
        "tipo": tipo,
        "escopo": escopo,
        "motivo": motivo,
        "exige_aprovacao_humana": exige_aprovacao_humana,
        "executor_autorizado": False,
        "efeito_executado": False,
    }
    if duracao_segundos is not None:
        item["duracao_segundos"] = duracao_segundos
    return item


class DefesaAutonoma:
    """Avalia eventos normalizados e sugere contenção proporcional.

    A contagem de falhas usa relógio monotônico e uma janela deslizante local.
    A instância não persiste eventos, IPs ou incidentes fora de sua memória.
    """

    def __init__(
        self,
        *,
        relogio: Callable[[], float] = monotonic,
        janela_segundos: float = DEFAULT_WINDOW_SECONDS,
        limiar_rate_limit: int = DEFAULT_RATE_LIMIT_THRESHOLD,
        limiar_bloqueio: int = DEFAULT_BLOCK_THRESHOLD,
        duracao_bloqueio_segundos: int = DEFAULT_BLOCK_SECONDS,
    ) -> None:
        if isinstance(janela_segundos, bool) or not isinstance(janela_segundos, (int, float)):
            raise ValueError("janela_segundos precisa ser um número real")
        try:
            janela_normalizada = float(janela_segundos)
        except (OverflowError, ValueError):
            raise ValueError("janela_segundos precisa ser positiva e finita") from None
        if not isfinite(janela_normalizada) or not 0 < janela_normalizada <= MAX_WINDOW_SECONDS:
            raise ValueError("janela_segundos precisa estar entre 0 e MAX_WINDOW_SECONDS")
        if any(
            isinstance(valor, bool) or not isinstance(valor, int)
            for valor in (limiar_rate_limit, limiar_bloqueio, duracao_bloqueio_segundos)
        ):
            raise ValueError("limiares e duração precisam ser inteiros")
        if (
            limiar_rate_limit < 1
            or limiar_rate_limit > MAX_THRESHOLD
            or limiar_bloqueio <= limiar_rate_limit
            or limiar_bloqueio > MAX_THRESHOLD
        ):
            raise ValueError("limiares fora dos limites ou ordem inválida")
        if not 1 <= duracao_bloqueio_segundos <= MAX_BLOCK_SECONDS:
            raise ValueError("duracao_bloqueio_segundos excede o limite permitido")
        if not callable(relogio):
            raise ValueError("relogio precisa ser uma função chamável")
        self._lock = Lock()
        self._relogio = relogio
        self._janela = janela_normalizada
        self._limiar_rate_limit = limiar_rate_limit
        self._limiar_bloqueio = limiar_bloqueio
        self._duracao_bloqueio = duracao_bloqueio_segundos
        # Capacidade limitada: endereços não confiáveis não podem crescer sem limite.
        self._falhas: OrderedDict[str, Deque[float]] = OrderedDict()

    def avaliar(self, evento: dict[str, Any]) -> dict[str, Any]:
        """Devolve uma decisão auditável sem realizar qualquer efeito colateral."""
        validado = self._validar_evento(evento)
        if "erro" in validado:
            return {
                "versao_politica": POLICY_VERSION,
                "estado": "evento_rejeitado",
                "motivos": [validado["erro"]],
                "recomendacoes": [],
                "efeito_executado": False,
            }

        tipo = validado["tipo"]
        origem_ip = validado.get("origem_ip")
        servico = validado.get("servico")
        evidencia_id = validado.get("evidencia_id")
        confianca = validado["confianca"]
        recomendacoes: list[dict[str, Any]] = []
        motivos: list[str] = []
        severidade = "informativa"

        # Preservar evidência e alertar são recomendações de baixo impacto.
        def preservar_e_alertar(codigo: str) -> None:
            recomendacoes.append(_recomendacao(
                "preservar_evidencia",
                evidencia_id or "evento-local",
                "Preservar metadados mínimos e cadeia de custódia; não coletar segredos.",
            ))
            recomendacoes.append(_recomendacao(
                "alertar_operador",
                servico or "defesa-nyxal",
                codigo,
                exige_aprovacao_humana=False,
            ))

        if tipo == "falha_autenticacao":
            severidade = "baixa"
            assert origem_ip is not None  # validado antes desta etapa
            # A API usa threads concorrentes; proteger a janela deslizante e o LRU.
            with self._lock:
                agora = self._relogio()
                if origem_ip not in self._falhas:
                    if len(self._falhas) >= MAX_TRACKED_ORIGINS:
                        self._falhas.popitem(last=False)
                    self._falhas[origem_ip] = deque(maxlen=MAX_FAILURES_PER_ORIGIN)
                falhas = self._falhas[origem_ip]
                self._falhas.move_to_end(origem_ip)
                while falhas and agora - falhas[0] > self._janela:
                    falhas.popleft()
                falhas.append(agora)
                quantidade = len(falhas)
            motivos.append("falha_autenticacao_observada")

            if _origem_remota(origem_ip):
                if quantidade >= self._limiar_bloqueio:
                    severidade = "alta"
                    recomendacoes.append(_recomendacao(
                        "bloqueio_temporario_origem",
                        origem_ip,
                        "Limiar de falhas de autenticação na janela deslizante atingido.",
                        duracao_segundos=self._duracao_bloqueio,
                        exige_aprovacao_humana=True,
                    ))
                    motivos.append("limiar_bloqueio_atingido")
                    preservar_e_alertar("Pico sustentado de falhas de autenticação; revisar evidências.")
                elif quantidade >= self._limiar_rate_limit:
                    severidade = "media"
                    recomendacoes.append(_recomendacao(
                        "limitar_taxa_origem",
                        origem_ip,
                        "Múltiplas falhas de autenticação dentro da janela deslizante.",
                        duracao_segundos=int(self._janela),
                        exige_aprovacao_humana=True,
                    ))
                    motivos.append("limiar_rate_limit_atingido")
                    preservar_e_alertar("Repetição de falhas de autenticação.")
            else:
                # Não limitar nem bloquear automaticamente loopback: evitar lockout
                # da própria Nyxal. Repetição local gera alerta, não contenção.
                motivos.append("origem_loopback_sem_contencao_automatica")
                if quantidade >= self._limiar_rate_limit:
                    severidade = "media"
                    preservar_e_alertar(
                        "Falhas repetidas em loopback; investigar a origem local sem bloqueá-la."
                    )

        elif tipo == "origem_suspeita":
            severidade = "media" if confianca >= 0.7 else "baixa"
            motivos.append("origem_suspeita_requer_correlacao")
            preservar_e_alertar("Origem sinalizada; correlacionar com outros sinais.")
            if origem_ip and evidencia_id and _origem_remota(origem_ip) and confianca >= 0.7:
                recomendacoes.append(_recomendacao(
                    "limitar_taxa_origem",
                    origem_ip,
                    "Contenção temporária enquanto a origem é investigada.",
                    duracao_segundos=60,
                    exige_aprovacao_humana=True,
                ))

        elif tipo == "tentativa_exploracao":
            severidade = "alta" if confianca >= 0.7 else "media"
            motivos.append("tentativa_exploracao_sinalizada")
            preservar_e_alertar("Validar indicador e correlacionar antes de escalar.")
            if origem_ip and evidencia_id and _origem_remota(origem_ip) and confianca >= 0.9:
                recomendacoes.append(_recomendacao(
                    "bloqueio_temporario_origem",
                    origem_ip,
                    "Indicador de alta confiança; bloqueio curto e reversível para revisão.",
                    duracao_segundos=self._duracao_bloqueio,
                    exige_aprovacao_humana=True,
                ))
            if confianca >= 0.95 and evidencia_id and origem_ip and _origem_remota(origem_ip):
                recomendacoes.append(_recomendacao(
                    "encaminhar_para_enganacao_isolada",
                    "decoy-service-interno",
                    "Usar somente uma honeypot interna isolada, sem encaminhamento externo.",
                    duracao_segundos=300,
                    exige_aprovacao_humana=True,
                ))

        elif tipo == "violacao_integridade":
            severidade = "critica"
            motivos.append("violacao_integridade_requer_isolamento")
            preservar_e_alertar("Possível adulteração; congelar alterações e preservar estado.")
            if servico and evidencia_id:
                recomendacoes.append(_recomendacao(
                    "isolar_servico",
                    servico,
                    "Isolamento disruptivo; validar dependências e preservar evidências.",
                    exige_aprovacao_humana=True,
                ))

        elif tipo == "credencial_comprometida":
            severidade = "critica"
            motivos.append("credencial_comprometida_requer_revogacao")
            preservar_e_alertar("Tratar a credencial como comprometida; não registrar seu valor.")
            credencial_id = validado.get("credencial_id")
            if credencial_id and evidencia_id:
                recomendacoes.append(_recomendacao(
                    "revogar_credencial",
                    credencial_id,
                    "Revogação explícita por identificador; nunca manipular o segredo aqui.",
                    exige_aprovacao_humana=True,
                ))
            if servico and evidencia_id:
                recomendacoes.append(_recomendacao(
                    "isolar_servico",
                    servico,
                    "Conter o componente até a rotação segura das credenciais.",
                    exige_aprovacao_humana=True,
                ))

        elif tipo == "malware_detectado":
            severidade = "critica"
            motivos.append("artefato_sinalizado_para_quarentena")
            preservar_e_alertar("Não executar nem apagar o artefato; preservar evidência.")
            artefato_id = validado.get("artefato_id")
            if artefato_id and evidencia_id:
                recomendacoes.append(_recomendacao(
                    "quarentenar_artefato",
                    artefato_id,
                    "Quarentena requer validação de caminho, hash e autorização fora deste módulo.",
                    exige_aprovacao_humana=True,
                ))

        elif tipo == "servico_indisponivel":
            severidade = "alta"
            motivos.append("falha_de_disponibilidade")
            preservar_e_alertar("Coletar telemetria somente de leitura e verificar dependências.")
            if servico and evidencia_id:
                recomendacoes.append(_recomendacao(
                    "propor_reinicio_controlado",
                    servico,
                    "Reinício pode interromper trabalhos; requer aprovação e verificação de saúde.",
                    exige_aprovacao_humana=True,
                ))

        elif tipo == "recuperacao_verificada":
            severidade = "informativa"
            motivos.append("recuperacao_precisa_de_revisao")
            recomendacoes.append(_recomendacao(
                "solicitar_revisao_de_incidente",
                evidencia_id or "incidente-local",
                "Não limpar evidências nem retirar bloqueios sem revisão e critérios explícitos.",
                exige_aprovacao_humana=True,
            ))

        return {
            "versao_politica": POLICY_VERSION,
            "estado": "avaliado",
            "evento": {
                "tipo": tipo,
                "fonte_sinal": validado["fonte_sinal"],
                "origem_ip": origem_ip,
                "servico": servico,
                "evidencia_id": evidencia_id,
                "confianca": confianca,
            },
            "severidade": severidade,
            "motivos": motivos,
            "recomendacoes": recomendacoes,
            "efeito_executado": False,
        }

    @staticmethod
    def _validar_evento(evento: Any) -> dict[str, Any]:
        if not isinstance(evento, dict):
            return {"erro": "evento_precisa_ser_objeto"}
        tipo = evento.get("tipo")
        if not isinstance(tipo, str) or tipo not in EVENTOS_SUPORTADOS:
            return {"erro": "tipo_evento_nao_suportado"}

        fonte_sinal = evento.get("fonte_sinal")
        if not isinstance(fonte_sinal, str) or fonte_sinal not in FONTES_POR_EVENTO[tipo]:
            return {"erro": "fonte_sinal_nao_autorizada"}

        origem_ip: str | None = None
        if "origem_ip" in evento:
            origem_ip = _ip_canonico(evento.get("origem_ip"))
            if origem_ip is None:
                return {"erro": "origem_ip_invalida"}

        if tipo in {"falha_autenticacao", "origem_suspeita", "tentativa_exploracao"}:
            if origem_ip is None:
                return {"erro": "origem_ip_obrigatoria"}

        servico = evento.get("servico")
        if servico is not None:
            if not isinstance(servico, str) or servico not in SERVICOS_CONTROLADOS:
                return {"erro": "servico_fora_da_allowlist"}

        confianca = evento.get("confianca", 0.5)
        if isinstance(confianca, bool) or not isinstance(confianca, (int, float)):
            return {"erro": "confianca_invalida"}
        try:
            confianca_normalizada = float(confianca)
        except (OverflowError, ValueError):
            return {"erro": "confianca_invalida"}
        if not isfinite(confianca_normalizada):
            return {"erro": "confianca_invalida"}
        if not 0.0 <= confianca_normalizada <= 1.0:
            return {"erro": "confianca_fora_do_intervalo"}

        result: dict[str, Any] = {
            "tipo": tipo,
            "fonte_sinal": fonte_sinal,
            "origem_ip": origem_ip,
            "servico": servico,
            "confianca": confianca_normalizada,
        }
        for campo in ("evidencia_id", "credencial_id", "artefato_id"):
            valor = evento.get(campo)
            if valor is not None:
                normalizado = _identificador_seguro(valor)
                if normalizado is None:
                    return {"erro": f"{campo}_invalido"}
                result[campo] = normalizado
        if tipo in EVENTOS_QUE_EXIGEM_EVIDENCIA and not result.get("evidencia_id"):
            return {"erro": "evidencia_id_obrigatorio"}
        return result
