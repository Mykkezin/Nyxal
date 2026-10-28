#!/usr/bin/env python3
"""Trilha HTTP estruturada, limitada e sem conteúdo sensível para o Nyxal."""
from __future__ import annotations

import json
import os
import stat
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def _tem_ancestral_simbolico(caminho: Path) -> bool:
    """Detecta links simbólicos no caminho, incluindo ancestrais ainda inexistentes."""
    candidato = Path(caminho)
    while True:
        try:
            if candidato.is_symlink():
                return True
        except OSError:
            return True
        if candidato.parent == candidato:
            return False
        candidato = candidato.parent


class RegistroTrilhaHTTP:
    """Registro JSONL de metadados HTTP; falhas de telemetria nunca derrubam a API."""

    VERSAO = 1
    METODOS_PERMITIDOS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
    MAX_ROUTE_CHARS = 128

    def __init__(self, caminho: str | Path, *, habilitado: bool = True,
                 max_bytes: int = 2_000_000, backups: int = 2) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1024:
            raise ValueError("max_bytes_deve_ser_inteiro_maior_ou_igual_a_1024")
        if not isinstance(backups, int) or isinstance(backups, bool) or backups < 0 or backups > 5:
            raise ValueError("backups_deve_estar_entre_0_e_5")
        self.caminho = Path(caminho).expanduser()
        self.habilitado = bool(habilitado)
        self.max_bytes = max_bytes
        self.backups = backups
        self._lock = threading.Lock()

    @classmethod
    def do_ambiente(cls) -> "RegistroTrilhaHTTP":
        habilitado = os.environ.get("NYXAL_HTTP_TRACE_ENABLED", "true").strip().lower()
        state_home = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
        caminho = os.environ.get("NYXAL_HTTP_TRACE_PATH", str(state_home / "nyxal" / "http-traces.jsonl"))
        try:
            max_bytes = int(os.environ.get("NYXAL_HTTP_TRACE_MAX_BYTES", "2000000"))
        except ValueError:
            max_bytes = 2_000_000
        if max_bytes < 1024:
            max_bytes = 2_000_000
        try:
            backups = int(os.environ.get("NYXAL_HTTP_TRACE_BACKUPS", "2"))
        except ValueError:
            backups = 2
        if not 0 <= backups <= 5:
            backups = 2
        return cls(caminho, habilitado=habilitado not in {"0", "false", "no", "off"},
                   max_bytes=max_bytes, backups=backups)

    @staticmethod
    def _timestamp_utc() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    @classmethod
    def _rota_sem_query(cls, caminho: str) -> str:
        # Query strings may contain keys or user data; never persist them.
        try:
            rota = urlsplit(caminho).path
        except (TypeError, ValueError):
            rota = "/invalid-route"
        rota = "".join(ch for ch in rota if ch.isprintable())
        if not rota.startswith("/"):
            rota = "/" + rota
        return rota[:cls.MAX_ROUTE_CHARS] or "/"

    @staticmethod
    def _resultado(status_code: int | None, error_type: str | None) -> str:
        if error_type:
            return "exception"
        if status_code is None:
            return "no_response"
        if status_code < 400:
            return "success"
        if status_code < 500:
            return "client_error"
        return "server_error"

    def _validar_caminhos_persistencia(self) -> None:
        """Recusa links simbólicos/FIFOs em todos os arquivos de log e backup."""
        if _tem_ancestral_simbolico(self.caminho.parent):
            raise OSError("diretorio_trace_com_link_simbolico")
        caminhos = [self.caminho]
        caminhos.extend(
            self.caminho.with_name(f"{self.caminho.name}.{indice}")
            for indice in range(1, self.backups + 1)
        )
        for caminho in caminhos:
            if _tem_ancestral_simbolico(caminho):
                raise OSError("caminho_trace_com_link_simbolico")
            try:
                info = caminho.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode):
                raise OSError("arquivo_trace_nao_regular")

    def _rotacionar_se_necessario(self, tamanho_novo: int) -> None:
        self._validar_caminhos_persistencia()
        try:
            info = self.caminho.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise OSError("arquivo_trace_nao_regular")
            tamanho_atual = info.st_size
        except FileNotFoundError:
            tamanho_atual = 0
        if tamanho_atual + tamanho_novo <= self.max_bytes:
            return
        if self.backups == 0:
            try:
                self.caminho.unlink()
            except FileNotFoundError:
                pass
            return
        for indice in range(self.backups, 0, -1):
            destino = self.caminho.with_name(f"{self.caminho.name}.{indice}")
            origem = self.caminho if indice == 1 else self.caminho.with_name(f"{self.caminho.name}.{indice - 1}")
            try:
                info_origem = origem.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info_origem.st_mode):
                raise OSError("arquivo_trace_nao_regular")
            try:
                info_destino = destino.lstat()
            except FileNotFoundError:
                info_destino = None
            if info_destino is not None:
                if not stat.S_ISREG(info_destino.st_mode):
                    raise OSError("backup_trace_nao_regular")
                destino.unlink()
            os.replace(origem, destino)

    def registrar(self, *, request_id: str, method: str, path: str,
                  status_code: int | None, duration_ms: float,
                  error_type: str | None = None) -> dict[str, Any] | None:
        """Persiste somente metadados; retorna None se desabilitado/indisponível."""
        if not self.habilitado:
            return None
        metodo = method.upper() if isinstance(method, str) else "UNKNOWN"
        if metodo not in self.METODOS_PERMITIDOS:
            metodo = "OTHER"
        if status_code is not None and (
            not isinstance(status_code, int) or isinstance(status_code, bool)
            or not 100 <= status_code <= 599
        ):
            status_code = None
        try:
            duracao = max(0.0, min(float(duration_ms), 86_400_000.0))
        except (TypeError, ValueError, OverflowError):
            duracao = 0.0
        rid = request_id.strip()[:80] if isinstance(request_id, str) else ""
        if not rid:
            rid = uuid.uuid4().hex
        registro: dict[str, Any] = {
            "schema_version": self.VERSAO,
            "timestamp_utc": self._timestamp_utc(),
            "request_id": rid,
            "method": metodo,
            "route": self._rota_sem_query(path),
            "status_code": status_code,
            "duration_ms": round(duracao, 3),
            "outcome": self._resultado(status_code, error_type),
        }
        if error_type:
            # Type only; exception messages may contain credentials or user text.
            registro["error_type"] = "".join(
                ch for ch in str(error_type) if ch.isalnum() or ch in "_.-"
            )[:80]
        linha = (json.dumps(registro, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")) + "\n").encode("utf-8")
        try:
            with self._lock:
                self._validar_caminhos_persistencia()
                self.caminho.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                self._validar_caminhos_persistencia()
                self._rotacionar_se_necessario(len(linha))
                self._validar_caminhos_persistencia()
                flags = os.O_CREAT | os.O_WRONLY | os.O_APPEND
                flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
                fd = os.open(str(self.caminho), flags, 0o600)
                try:
                    if not stat.S_ISREG(os.fstat(fd).st_mode):
                        raise OSError("arquivo_trace_nao_regular")
                    os.fchmod(fd, 0o600)
                    with os.fdopen(fd, "ab") as arquivo:
                        fd = -1
                        arquivo.write(linha)
                finally:
                    if fd >= 0:
                        os.close(fd)
        except OSError:
            # Observability must never make the API unavailable.
            return None
        return registro


__all__ = ["RegistroTrilhaHTTP"]
