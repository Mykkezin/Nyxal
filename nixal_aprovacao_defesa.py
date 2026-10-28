#!/usr/bin/env python3
"""Diário durável de aprovações humanas para a defesa governada.

Camada de confiança da issue #103: um booleano no corpo do pedido nunca é uma
aprovação. Aqui a aprovação só existe quando um principal autenticado,
resolvido pela camada HTTP (nunca pelo cliente), a registra contra um escopo
determinado. O verificador devolvido por `para_executor()` é injetável no gate
`ExecutorDefesaGovernada`, que continua sem operação de execução: registrar ou
verificar uma aprovação não habilita efeito algum no host.

O formato é o mesmo da trilha de auditoria de defesa: arquivo privado (0700/0600), append-only,
encadeado por SHA-256, limitado por registros e bytes, com lock entre
processos. Falha de armazenamento, saturation ou trilha corrompida resultam em
negação (fail-closed) e o arquivo original permanece intacto.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from threading import Lock
from time import time
from typing import Any, Callable

VERSAO_APROVACAO = "0.1"
MAX_TTL_APROVACAO_SEGUNDOS = 3600
MAX_BYTES_PADRAO = 1_048_576
MAX_REGISTROS_PADRAO = 4096
MAX_ID_CHARS = 64
MAX_IDENTIDADE_CHARS = 128

# Procedências que a camada de confiança superior pode atestar. Não há valor
# "auto_declarada": o cliente não consegue produzir uma aprovação.
PROCEDENCIAS_CONFIAVEIS = frozenset({"http_autenticado", "cli_local_confirmado"})

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_TIPOS_LINHA = frozenset({
    "aprovacao_registrada",
    "aprovacao_consumida",
    "aprovacao_revogada",
    "aprovacao_recusada",
})


def _agora() -> float:
    return time()


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _hash_escopo(plano: dict[str, Any]) -> str:
    canonico = "|".join(
        (
            str(plano.get("tipo", "")),
            str(plano.get("escopo", "")),
            str(plano.get("duracao_segundos") or ""),
        )
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _json_canonico(dados: dict[str, Any]) -> bytes:
    return json.dumps(
        dados, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class DiarioAprovacaoDefesa:
    """Registra e consome aprovações verificáveis, sempre negando na dúvida."""

    def __init__(
        self,
        caminho: str | Path,
        *,
        max_bytes: int = MAX_BYTES_PADRAO,
        max_registros: int = MAX_REGISTROS_PADRAO,
        relogio: Callable[[], float] = _agora,
    ) -> None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 4096 <= max_bytes <= MAX_BYTES_PADRAO:
            raise ValueError("max_bytes_invalido")
        if isinstance(max_registros, bool) or not isinstance(max_registros, int) or not 1 <= max_registros <= MAX_REGISTROS_PADRAO:
            raise ValueError("max_registros_invalido")
        if not callable(relogio):
            raise ValueError("relogio_precisa_ser_chamavel")
        self.caminho = Path(caminho).expanduser().absolute()
        self.max_bytes = max_bytes
        self.max_registros = max_registros
        self.relogio = relogio
        self._lock = Lock()
        # estado: "ativa" | "consumida" | "revogada" | "expirada"
        self._aprovacoes: dict[str, dict[str, Any]] = {}
        self._linhas = 0
        self._bytes = 0
        self._ultimo_hash = "0" * 64
        self._corrompido = False
        self._recarregado = False

    @classmethod
    def do_ambiente(cls) -> "DiarioAprovacaoDefesa":
        configurado = os.environ.get("XDG_STATE_HOME", "").strip()
        base = Path(configurado).expanduser() if configurado else Path.home() / ".local" / "state"
        return cls(base / "nyxal" / "defesa-aprovacoes" / "aprovacoes.jsonl")

    # ------------------------------------------------------------------
    # armazenamento privado
    # ------------------------------------------------------------------

    def _validar_pasta(self, *, criar: bool) -> None:
        pasta = self.caminho.parent
        if criar:
            pasta.mkdir(parents=True, exist_ok=True, mode=0o700)
        for componente in [pasta, *pasta.parents]:
            if componente.is_symlink():
                raise OSError("diretorio_simbolico_bloqueado")
        if not pasta.exists():
            raise FileNotFoundError("diretorio_aprovacoes_ausente")
        info = pasta.stat()
        if not stat.S_ISDIR(info.st_mode):
            raise OSError("diretorio_aprovacoes_invalido")
        if info.st_uid != os.geteuid():
            raise PermissionError("proprietario_diretorio_invalido")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise PermissionError("permissoes_diretorio_nao_privadas")

    def _abrir(self, *, escrita: bool, criar: bool = False) -> int:
        self._validar_pasta(criar=criar)
        flags = os.O_RDWR if escrita else os.O_RDONLY
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        if not getattr(os, "O_NOFOLLOW", 0):
            raise OSError("O_NOFOLLOW_indisponivel")
        if criar:
            flags |= os.O_CREAT | os.O_APPEND
        fd = os.open(self.caminho, flags, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise OSError("arquivo_aprovacoes_nao_regular")
            if info.st_uid != os.geteuid():
                raise PermissionError("proprietario_arquivo_invalido")
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise PermissionError("permissoes_arquivo_nao_privadas")
            fcntl.flock(fd, fcntl.LOCK_EX if escrita else fcntl.LOCK_SH)
            return fd
        except Exception:
            os.close(fd)
            raise

    def _carregar(self, fd: int) -> None:
        """Reconstrói o índice a partir da trilha; corruption nunca é consertada."""
        dados = os.read(fd, self.max_bytes + 1)
        aprovacoes: dict[str, dict[str, Any]] = {}
        linhas = 0
        anterior = "0" * 64
        self._corrompido = False
        for bruto in dados.splitlines():
            if not bruto.strip():
                continue
            linhas += 1
            try:
                registro = json.loads(
                    bruto.decode("utf-8", errors="strict"),
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._corrompido = True
                break
            if not isinstance(registro, dict):
                self._corrompido = True
                break
            if registro.get("previous_hash") != anterior:
                self._corrompido = True
                break
            corpo = {k: v for k, v in registro.items() if k != "entry_hash"}
            anterior = hashlib.sha256(_json_canonico(corpo)).hexdigest()
            if registro.get("entry_hash") != anterior:
                self._corrompido = True
                break
            tipo = registro.get("tipo")
            aprovacao_id = registro.get("aprovacao_id")
            if tipo not in _TIPOS_LINHA or not isinstance(aprovacao_id, str):
                continue
            if tipo == "aprovacao_registrada":
                if not isinstance(registro.get("valor"), dict):
                    continue
                aprovacoes[aprovacao_id] = {
                    **registro["valor"],
                    "estado": "ativa",
                    "registrada_em": registro.get("observado_em"),
                }
            elif tipo == "aprovacao_consumida":
                if aprovacao_id in aprovacoes:
                    aprovacoes[aprovacao_id]["estado"] = "consumida"
            elif tipo == "aprovacao_revogada":
                if aprovacao_id in aprovacoes:
                    aprovacoes[aprovacao_id]["estado"] = "revogada"
        else:
            self._ultimo_hash = anterior
        if self._corrompido:
            aprovacoes = {}
            self._ultimo_hash = "0" * 64
        self._aprovacoes = aprovacoes
        self._linhas = linhas
        self._bytes = len(dados)
        self._recarregado = True

    def _anexar(self, fd: int, registro: dict[str, Any]) -> None:
        linha = _json_canonico(registro) + b"\n"
        if self._bytes + len(linha) > self.max_bytes:
            raise OSError("diario_saturado")
        os.write(fd, linha)
        os.fsync(fd)
        self._bytes += len(linha)
        self._linhas += 1
        self._ultimo_hash = registro["entry_hash"]

    @contextmanager
    def _transacao(self):
        """Um único fd com LOCK_EX para ler e anexar: sem janela entre processos.

        Ler sob LOCK_SH e anexar depois sob LOCK_EX deixaria dois processos
        reconstruir o mesmo `previous_hash` e gravar duas linhas encadeadas no
        genesis — corrompendo a trilha por concorrência legítima.
        """
        fd = self._abrir(escrita=True, criar=True)
        try:
            self._carregar(fd)
            yield fd
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _linha(self, tipo: str, aprovacao_id: str, valor: dict[str, Any] | None, motivo: str | None) -> dict[str, Any]:
        corpo = {
            "schema": VERSAO_APROVACAO,
            "tipo": tipo,
            "aprovacao_id": aprovacao_id,
            "observado_em": _utc_iso(self.relogio()),
            "previous_hash": self._ultimo_hash,
        }
        if valor is not None:
            corpo["valor"] = valor
        if motivo is not None:
            corpo["motivo"] = motivo[:200]
        corpo["entry_hash"] = hashlib.sha256(_json_canonico(corpo)).hexdigest()
        return corpo

    # ------------------------------------------------------------------
    # API da camada de confiança
    # ------------------------------------------------------------------

    def _negada(self, motivo: str) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "aprovacao_recusada",
            "motivo": motivo,
            "efeito_executado": False,
            "executor_autorizado": False,
        }

    def registrar(
        self,
        *,
        principal: Any,
        plano: Any,
        ttl_segundos: int = 300,
    ) -> dict[str, Any]:
        """Só um principal autenticado, atestado pela camada superior, registra."""
        if not isinstance(plano, dict):
            return self._negada("plano_invalido")
        tipo = plano.get("tipo")
        escopo = plano.get("escopo")
        if not isinstance(tipo, str) or not isinstance(escopo, str) or not tipo or not escopo:
            return self._negada("plano_sem_tipo_ou_escopo")
        if isinstance(ttl_segundos, bool) or not isinstance(ttl_segundos, int) or not 1 <= ttl_segundos <= MAX_TTL_APROVACAO_SEGUNDOS:
            return self._negada("ttl_fora_dos_limites")
        if not isinstance(principal, dict):
            return self._negada("principal_ausente")
        if principal.get("autenticado") is not True:
            return self._negada("principal_nao_autenticado")
        procedencia = principal.get("procedencia")
        if procedencia not in PROCEDENCIAS_CONFIAVEIS:
            return self._negada("procedencia_nao_confiavel")
        identidade = principal.get("identidade")
        if not isinstance(identidade, str) or not identidade.strip():
            return self._negada("identidade_do_aprovador_ausente")
        if len(identidade) > MAX_IDENTIDADE_CHARS:
            return self._negada("identidade_larga_demais")
        if principal.get("auto_declarada") is True:
            return self._negada("aprovacao_auto_declarada")

        agora = self.relogio()
        aprovacao_id = "apr-" + hashlib.sha256(
            f"{agora:.9f}|{os.urandom(16).hex()}".encode("utf-8")
        ).hexdigest()[:24]
        registro = {
            "aprovacao_id": aprovacao_id,
            "tipo_plano": tipo[:80],
            "escopo_hash": _hash_escopo(plano),
            "expira_em": agora + ttl_segundos,
            "aprovador": identidade[:MAX_IDENTIDADE_CHARS],
            "procedencia": procedencia,
        }
        with self._lock:
            try:
                with self._transacao() as fd:
                    if self._corrompido:
                        return self._negada("diario_corrompido")
                    if self._linhas >= self.max_registros:
                        return self._negada("diario_saturado")
                    self._anexar(fd, self._linha("aprovacao_registrada", aprovacao_id, registro, None))
            except (OSError, ValueError) as erro:
                return self._negada(f"armazenamento_indisponivel:{type(erro).__name__}")
            self._aprovacoes[aprovacao_id] = {**registro, "estado": "ativa", "registrada_em": _utc_iso(agora)}
        return {
            "sucesso": True,
            "estado": "aprovacao_registrada",
            "aprovacao_id": aprovacao_id,
            "expira_em": _utc_iso(registro["expira_em"]),
            "efeito_executado": False,
            "executor_autorizado": False,
        }


    def revogar(self, aprovacao_id: Any, *, principal: Any) -> dict[str, Any]:
        if not isinstance(aprovacao_id, str) or not _ID_RE.match(aprovacao_id):
            return self._negada("aprovacao_id_invalido")
        if not isinstance(principal, dict) or principal.get("autenticado") is not True:
            return self._negada("principal_nao_autenticado")
        if principal.get("procedencia") not in PROCEDENCIAS_CONFIAVEIS:
            return self._negada("procedencia_nao_confiavel")
        with self._lock:
            try:
                with self._transacao() as fd:
                    if self._corrompido:
                        return self._negada("diario_corrompido")
                    atual = self._aprovacoes.get(aprovacao_id)
                    if atual is None:
                        return self._negada("aprovacao_inexistente")
                    if atual["estado"] != "ativa":
                        return self._negada(f"aprovacao_ja_{atual['estado']}")
                    self._anexar(
                        fd,
                        self._linha(
                            "aprovacao_revogada",
                            aprovacao_id,
                            {"aprovador": str(principal.get("identidade", ""))[:MAX_IDENTIDADE_CHARS]},
                            None,
                        ),
                    )
            except (OSError, ValueError) as erro:
                return self._negada(f"armazenamento_indisponivel:{type(erro).__name__}")
            self._aprovacoes[aprovacao_id]["estado"] = "revogada"
        return {"sucesso": True, "estado": "aprovacao_revogada", "efeito_executado": False}

    def verificar(self, candidato: Any) -> bool:
        """Verificador para o gate; nunca levanta exceção para o chamador."""
        try:
            return self._verificar(candidato) is True
        except Exception:
            return False

    def _verificar(self, candidato: Any) -> bool:
        if not isinstance(candidato, dict):
            return False
        aprovacao_id = candidato.get("aprovacao_id")
        escopo_hash = candidato.get("escopo_hash")
        if not isinstance(aprovacao_id, str) or not _ID_RE.match(aprovacao_id):
            return False
        if not isinstance(escopo_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", escopo_hash):
            return False
        with self._lock:
            try:
                with self._transacao() as fd:
                    if self._corrompido:
                        return False
                    atual = self._aprovacoes.get(aprovacao_id)
                    if atual is None or atual.get("estado") != "ativa":
                        return False
                    if atual.get("escopo_hash") != escopo_hash:
                        return False
                    agora = self.relogio()
                    if float(atual.get("expira_em") or 0) <= agora:
                        self._anexar(
                            fd, self._linha("aprovacao_recusada", aprovacao_id, None, "expirada")
                        )
                        self._aprovacoes[aprovacao_id]["estado"] = "expirada"
                        return False
                    self._anexar(fd, self._linha("aprovacao_consumida", aprovacao_id, None, None))
                    self._aprovacoes[aprovacao_id]["estado"] = "consumida"
                    return True
            except (OSError, ValueError):
                # Sem escrever o consumo, a aprovação fica não consumida; o
                # resultado seria indeterminado, então a concessão é negada.
                return False

    def para_executor(self) -> Callable[[dict[str, Any]], bool]:
        return self.verificar

    def _recarregar_para_leitura(self) -> bool:
        """Recarrega sem criar o diário; devolve False quando não é confiável."""
        if not self.caminho.exists():
            self._aprovacoes = {}
            self._linhas = 0
            self._bytes = 0
            self._ultimo_hash = "0" * 64
            self._corrompido = False
            self._recarregado = True
            return True
        fd = self._abrir(escrita=False)
        try:
            self._carregar(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        return not self._corrompido

    def contexto(self) -> dict[str, Any]:
        with self._lock:
            try:
                confiavel = self._recarregar_para_leitura()
            except (OSError, ValueError):
                confiavel = False
            ativos = sum(1 for item in self._aprovacoes.values() if item.get("estado") == "ativa")
            return {
                "sucesso": True,
                "versao": VERSAO_APROVACAO,
                "diario_disponivel": confiavel,
                "trilha_corrompida": self._corrompido,
                "aprovacoes_ativas": ativos,
                "aprovacoes_registradas": len(self._aprovacoes),
                "linhas_no_diario": self._linhas,
                "limite_registros": self.max_registros,
                "bytes_no_diario": self._bytes,
                "limite_bytes": self.max_bytes,
                "aprovacao_auto_declarada_aceita": False,
                "executor_ativo": False,
                "efeito_executado": False,
            }


__all__ = ["DiarioAprovacaoDefesa", "PROCEDENCIAS_CONFIAVEIS", "VERSAO_APROVACAO", "_hash_escopo"]
