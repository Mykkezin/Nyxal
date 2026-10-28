#!/usr/bin/env python3
"""Trilha append-only e verificável para observações e propostas dry-run da defesa Nyxal.

Não armazena tokens, cabeçalhos, corpos HTTP ou motivos livres. Não executa ações.
A trilha tem limite rígido e falha fechada: nunca trunca nem corrige automaticamente
um registro inválido, nem segue symlinks para diretórios, arquivo ou lock.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import ipaddress
import json
import os
import re
import stat
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - NyxOS é Linux, não degradar silenciosamente.
    fcntl = None


class TrilhaDefesaError(RuntimeError):
    """Erro seguro da persistência da trilha, sem conteúdo privado no texto."""


class RegistroTrilhaDefesa:
    FONTE = "trilha_defesa_nyxal"
    VERSAO = 1
    MAX_BYTES_PADRAO = 2_000_000
    MAX_REGISTROS_PADRAO = 4096

    EVENTOS_VALIDOS = frozenset({
        "sinal_observado",
        "plano_preparado",
        "plano_aprovado",
        "plano_expirado",
    })
    CAMPOS_VALIDOS = frozenset({
        "tipo_evento",
        "fonte_sinal",
        "origem_ip",
        "severidade",
        "plano_id",
        "tipo",
        "escopo",
        "estado",
        "duracao_segundos",
        "aprovacao_verificada",
        "modo",
    })
    CAMPOS_OBRIGATORIOS = {
        "sinal_observado": frozenset({"tipo_evento", "fonte_sinal"}),
        "plano_preparado": frozenset({
            "plano_id", "tipo", "escopo", "estado", "modo", "aprovacao_verificada",
        }),
        "plano_aprovado": frozenset({
            "plano_id", "tipo", "escopo", "estado", "modo", "aprovacao_verificada",
        }),
        "plano_expirado": frozenset({
            "plano_id", "tipo", "escopo", "estado", "modo", "aprovacao_verificada",
        }),
    }
    _HASH_VAZIO = "GENESIS"

    def __init__(
        self,
        arquivo: str | Path,
        *,
        max_bytes: int = MAX_BYTES_PADRAO,
        max_registros: int = MAX_REGISTROS_PADRAO,
    ) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1024:
            raise ValueError("max_bytes_deve_ser_maior_ou_igual_a_1024")
        if (
            not isinstance(max_registros, int)
            or isinstance(max_registros, bool)
            or not 1 <= max_registros <= self.MAX_REGISTROS_PADRAO
        ):
            raise ValueError("max_registros_fora_dos_limites")
        if fcntl is None or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
            raise ValueError("bloqueio_seguro_de_arquivo_indisponivel")
        if not isinstance(arquivo, (str, Path)) or not str(arquivo).strip():
            raise ValueError("caminho_de_auditoria_invalido")

        caminho_absoluto = os.path.abspath(os.path.expanduser(str(arquivo)))
        self.arquivo = Path(caminho_absoluto)
        if self.arquivo.name in {"", ".", ".."}:
            raise ValueError("nome_de_auditoria_invalido")
        if self.arquivo.parent == Path(os.sep):
            raise ValueError("diretorio_raiz_nao_permitido_para_auditoria")
        self.max_bytes = max_bytes
        self.max_registros = max_registros
        self._lock_thread = threading.RLock()
        self._degradada = False
        self._motivo_degradacao: str | None = None
        self._validada = False
        self._quantidade = 0
        self._ultimo_hash = self._HASH_VAZIO

    @property
    def _nome_lock(self) -> str:
        return self.arquivo.name + ".lock"

    @staticmethod
    def _regex(valor: Any, padrao: str, limite: int) -> str:
        if not isinstance(valor, str) or not 1 <= len(valor) <= limite:
            raise TrilhaDefesaError("campo_auditoria_invalido")
        if re.fullmatch(padrao, valor) is None:
            raise TrilhaDefesaError("campo_auditoria_invalido")
        return valor

    def _sanitizar_dados(self, dados: Any) -> dict[str, Any]:
        if not isinstance(dados, dict) or any(chave not in self.CAMPOS_VALIDOS for chave in dados):
            raise TrilhaDefesaError("campos_de_auditoria_nao_permitidos")

        resultado: dict[str, Any] = {}
        for chave, valor in dados.items():
            if valor is None:
                continue
            if chave == "tipo_evento":
                resultado[chave] = self._regex(valor, r"[a-z][a-z0-9_]{0,63}", 64)
            elif chave == "fonte_sinal":
                if valor != "api-auth":
                    raise TrilhaDefesaError("fonte_de_sinal_nao_permitida")
                resultado[chave] = valor
            elif chave == "origem_ip":
                if not isinstance(valor, str) or len(valor) > 64:
                    raise TrilhaDefesaError("ip_de_auditoria_invalido")
                try:
                    resultado[chave] = ipaddress.ip_address(valor).compressed
                except ValueError:
                    raise TrilhaDefesaError("ip_de_auditoria_invalido") from None
            elif chave == "severidade":
                if valor not in {"informativa", "baixa", "media", "alta", "critica"}:
                    raise TrilhaDefesaError("severidade_de_auditoria_invalida")
                resultado[chave] = valor
            elif chave == "plano_id":
                resultado[chave] = self._regex(valor, r"plano-[0-9a-f]{24}", 30)
            elif chave == "tipo":
                resultado[chave] = self._regex(valor, r"[a-z][a-z0-9_]{0,79}", 80)
            elif chave == "escopo":
                resultado[chave] = self._regex(valor, r"[A-Za-z0-9_.:-]{1,128}", 128)
            elif chave == "estado":
                if valor not in {"aguardando_aprovacao", "simulacao_preparada", "expirado"}:
                    raise TrilhaDefesaError("estado_de_auditoria_invalido")
                resultado[chave] = valor
            elif chave == "duracao_segundos":
                if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 3600:
                    raise TrilhaDefesaError("duracao_de_auditoria_invalida")
                resultado[chave] = valor
            elif chave == "aprovacao_verificada":
                if not isinstance(valor, bool):
                    raise TrilhaDefesaError("aprovacao_de_auditoria_invalida")
                resultado[chave] = valor
            elif chave == "modo":
                if valor != "dry_run":
                    raise TrilhaDefesaError("modo_de_auditoria_invalido")
                resultado[chave] = valor

        return resultado

    def _abrir_diretorio_pai(self, *, criar: bool) -> int:
        """Abre cada componente por dirfd + O_NOFOLLOW, sem resolver links."""
        flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        atual_fd = os.open(os.sep, flags_dir)
        componentes = self.arquivo.parent.parts[1:]
        try:
            for indice, componente in enumerate(componentes):
                try:
                    proximo_fd = os.open(componente, flags_dir, dir_fd=atual_fd)
                except FileNotFoundError:
                    if not criar:
                        raise TrilhaDefesaError("diretorio_de_auditoria_ausente") from None
                    try:
                        os.mkdir(componente, mode=0o700, dir_fd=atual_fd)
                    except FileExistsError:
                        pass
                    proximo_fd = os.open(componente, flags_dir, dir_fd=atual_fd)

                info = os.fstat(proximo_fd)
                if not stat.S_ISDIR(info.st_mode):
                    os.close(proximo_fd)
                    raise TrilhaDefesaError("componente_de_auditoria_nao_e_diretorio")
                if indice == len(componentes) - 1:
                    if info.st_uid != os.geteuid() or info.st_mode & 0o022:
                        os.close(proximo_fd)
                        raise TrilhaDefesaError("diretorio_de_auditoria_nao_privado")
                os.close(atual_fd)
                atual_fd = proximo_fd
            return atual_fd
        except TrilhaDefesaError:
            os.close(atual_fd)
            raise
        except OSError:
            os.close(atual_fd)
            raise TrilhaDefesaError("caminho_de_auditoria_inseguro") from None

    @contextlib.contextmanager
    def _bloquear_arquivo(self) -> Iterator[int]:
        diretorio_fd = self._abrir_diretorio_pai(criar=True)
        lock_fd: int | None = None
        try:
            flags = (
                os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW
                | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
            )
            lock_fd = os.open(
                self._nome_lock, flags, 0o600, dir_fd=diretorio_fd
            )
            info = os.fstat(lock_fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_nlink != 1
                or info.st_mode & 0o077
            ):
                raise TrilhaDefesaError("arquivo_lock_de_auditoria_inseguro")
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield diretorio_fd
        except TrilhaDefesaError:
            raise
        except OSError:
            raise TrilhaDefesaError("lock_de_auditoria_indisponivel") from None
        finally:
            if lock_fd is not None:
                try:
                    if fcntl is not None:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
                os.close(lock_fd)
            os.close(diretorio_fd)

    def _ler_bytes(self, diretorio_fd: int) -> bytes:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
        try:
            arquivo_fd = os.open(self.arquivo.name, flags, dir_fd=diretorio_fd)
        except FileNotFoundError:
            return b""
        except OSError:
            raise TrilhaDefesaError("arquivo_de_auditoria_inseguro_ou_ilegivel") from None

        try:
            info_antes = os.fstat(arquivo_fd)
            if (
                not stat.S_ISREG(info_antes.st_mode)
                or info_antes.st_uid != os.geteuid()
                or info_antes.st_nlink != 1
                or info_antes.st_mode & 0o077
            ):
                raise TrilhaDefesaError("arquivo_de_auditoria_nao_privado")
            if info_antes.st_size > self.max_bytes:
                raise TrilhaDefesaError("limite_de_auditoria_excedido")

            partes: list[bytes] = []
            total = 0
            while True:
                bloco = os.read(arquivo_fd, min(65536, self.max_bytes + 1 - total))
                if not bloco:
                    break
                partes.append(bloco)
                total += len(bloco)
                if total > self.max_bytes:
                    raise TrilhaDefesaError("limite_de_auditoria_excedido")
            if os.fstat(arquivo_fd).st_size != info_antes.st_size or total != info_antes.st_size:
                raise TrilhaDefesaError("arquivo_de_auditoria_mudou_durante_leitura")
            return b"".join(partes)
        finally:
            os.close(arquivo_fd)

    def _validar_bytes(self, bruto: bytes) -> tuple[list[dict[str, Any]], str]:
        if not bruto:
            return [], self._HASH_VAZIO
        if not bruto.endswith(b"\n"):
            raise TrilhaDefesaError("trilha_de_auditoria_incompleta")
        linhas = bruto.splitlines()
        if len(linhas) > self.max_registros:
            raise TrilhaDefesaError("limite_de_registros_de_auditoria_excedido")

        registros: list[dict[str, Any]] = []
        anterior = self._HASH_VAZIO
        chaves_esperadas = {
            "fonte", "versao", "sequencia", "timestamp_utc",
            "evento", "dados", "hash_anterior", "hash",
        }
        for indice, linha in enumerate(linhas, start=1):
            if not linha:
                raise TrilhaDefesaError("linha_vazia_na_trilha_de_auditoria")
            try:
                registro = json.loads(linha.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise TrilhaDefesaError("json_invalido_na_trilha_de_auditoria") from None
            if not isinstance(registro, dict) or set(registro) != chaves_esperadas:
                raise TrilhaDefesaError("esquema_invalido_na_trilha_de_auditoria")
            if (
                registro.get("fonte") != self.FONTE
                or type(registro.get("versao")) is not int
                or registro.get("versao") != self.VERSAO
                or type(registro.get("sequencia")) is not int
                or registro.get("sequencia") != indice
                or not isinstance(registro.get("timestamp_utc"), str)
                or not isinstance(registro.get("evento"), str)
                or registro.get("evento") not in self.EVENTOS_VALIDOS
                or not isinstance(registro.get("hash_anterior"), str)
                or registro.get("hash_anterior") != anterior
                or not isinstance(registro.get("hash"), str)
                or re.fullmatch(r"[0-9a-f]{64}", registro["hash"]) is None
            ):
                raise TrilhaDefesaError("cadeia_de_auditoria_invalida")
            try:
                timestamp = datetime.fromisoformat(registro["timestamp_utc"])
            except ValueError:
                raise TrilhaDefesaError("timestamp_de_auditoria_invalido") from None
            if timestamp.tzinfo is None or timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
                raise TrilhaDefesaError("timestamp_de_auditoria_invalido")
            if json.dumps(registro, ensure_ascii=False, sort_keys=True).encode("utf-8") != linha:
                raise TrilhaDefesaError("serializacao_de_auditoria_nao_canonica")

            dados_sanitizados = self._sanitizar_dados(registro.get("dados"))
            if dados_sanitizados != registro.get("dados"):
                raise TrilhaDefesaError("dados_de_auditoria_invalidos")
            obrigatorios = self.CAMPOS_OBRIGATORIOS[registro["evento"]]
            if not obrigatorios.issubset(dados_sanitizados):
                raise TrilhaDefesaError("campos_obrigatorios_de_auditoria_ausentes")

            base = dict(registro)
            hash_registro = base.pop("hash")
            canonico = json.dumps(
                base, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            esperado = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
            if hash_registro != esperado:
                raise TrilhaDefesaError("hash_de_auditoria_invalido")
            registros.append(registro)
            anterior = hash_registro
        return registros, anterior

    def registrar(self, evento: str, dados: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(evento, str) or evento not in self.EVENTOS_VALIDOS:
            raise TrilhaDefesaError("evento_de_auditoria_nao_permitido")
        dados_sanitizados = self._sanitizar_dados(dados)
        if not self.CAMPOS_OBRIGATORIOS[evento].issubset(dados_sanitizados):
            raise TrilhaDefesaError("campos_obrigatorios_de_auditoria_ausentes")

        with self._lock_thread:
            if self._degradada:
                raise TrilhaDefesaError("trilha_de_auditoria_degradada")
            try:
                with self._bloquear_arquivo() as diretorio_fd:
                    bruto = self._ler_bytes(diretorio_fd)
                    registros, anterior = self._validar_bytes(bruto)
                    if len(registros) >= self.max_registros:
                        raise TrilhaDefesaError("limite_de_registros_de_auditoria_atingido")

                    base = {
                        "fonte": self.FONTE,
                        "versao": self.VERSAO,
                        "sequencia": len(registros) + 1,
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "evento": evento,
                        "dados": dados_sanitizados,
                        "hash_anterior": anterior,
                    }
                    canonico = json.dumps(
                        base, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    )
                    registro = {
                        **base,
                        "hash": hashlib.sha256(canonico.encode("utf-8")).hexdigest(),
                    }
                    linha = (
                        json.dumps(registro, ensure_ascii=False, sort_keys=True) + "\n"
                    ).encode("utf-8")
                    if len(bruto) + len(linha) > self.max_bytes:
                        raise TrilhaDefesaError("limite_de_bytes_de_auditoria_atingido")

                    flags = (
                        os.O_CREAT | os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW
                        | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
                    )
                    try:
                        trilha_fd = os.open(
                            self.arquivo.name, flags, 0o600, dir_fd=diretorio_fd
                        )
                    except OSError:
                        raise TrilhaDefesaError("arquivo_de_auditoria_inseguro_ou_ilegivel") from None
                    try:
                        info = os.fstat(trilha_fd)
                        if (
                            not stat.S_ISREG(info.st_mode)
                            or info.st_uid != os.geteuid()
                            or info.st_nlink != 1
                            or info.st_mode & 0o077
                            or info.st_size != len(bruto)
                        ):
                            raise TrilhaDefesaError("arquivo_de_auditoria_mudou_ou_nao_e_privado")
                        restante = memoryview(linha)
                        while restante:
                            gravados = os.write(trilha_fd, restante)
                            if gravados <= 0:
                                raise TrilhaDefesaError("gravacao_de_auditoria_incompleta")
                            restante = restante[gravados:]
                        os.fsync(trilha_fd)
                        os.fsync(diretorio_fd)
                    finally:
                        os.close(trilha_fd)

                    self._validada = True
                    self._quantidade = len(registros) + 1
                    self._ultimo_hash = registro["hash"]
                    return copy.deepcopy(registro)
            except TrilhaDefesaError as erro:
                # Uma cadeia inválida, caminho inseguro ou limite alcançado
                # deixa a instância degradada; não corrigir nem truncar evidências.
                self._degradada = True
                self._motivo_degradacao = str(erro)
                raise
            except OSError:
                self._degradada = True
                self._motivo_degradacao = "operacao_de_arquivo_falhou"
                raise TrilhaDefesaError("operacao_de_arquivo_falhou") from None

    def validar(self) -> dict[str, Any]:
        with self._lock_thread:
            if self._degradada:
                return {
                    "valido": False,
                    "registros": self._quantidade,
                    "motivo": "trilha_de_auditoria_degradada",
                }
            try:
                with self._bloquear_arquivo() as diretorio_fd:
                    bruto = self._ler_bytes(diretorio_fd)
                    registros, ultimo_hash = self._validar_bytes(bruto)
                    self._validada = True
                    self._quantidade = len(registros)
                    self._ultimo_hash = ultimo_hash
                    return {
                        "valido": True,
                        "registros": self._quantidade,
                        "ultimo_hash": self._ultimo_hash,
                    }
            except (TrilhaDefesaError, OSError) as erro:
                self._degradada = True
                self._motivo_degradacao = (
                    str(erro) if isinstance(erro, TrilhaDefesaError)
                    else "operacao_de_arquivo_falhou"
                )
                return {
                    "valido": False,
                    "registros": self._quantidade,
                    "motivo": self._motivo_degradacao,
                }

    def contexto(self) -> dict[str, Any]:
        with self._lock_thread:
            if self._degradada:
                return {
                    "sucesso": False,
                    "estado": "auditoria_degradada",
                    "auditoria_duravel": False,
                    "motivo": self._motivo_degradacao or "falha_de_auditoria",
                    "registros_confirmados": self._quantidade,
                    "limite_registros": self.max_registros,
                    "limite_bytes": self.max_bytes,
                }
            return {
                "sucesso": True,
                "estado": "auditoria_validada" if self._validada else "auditoria_configurada_nao_validada",
                "auditoria_duravel": self._validada,
                "registros_confirmados": self._quantidade,
                "ultimo_hash": self._ultimo_hash if self._validada else None,
                "limite_registros": self.max_registros,
                "limite_bytes": self.max_bytes,
                "rotacao_automatica": False,
            }


__all__ = ["RegistroTrilhaDefesa", "TrilhaDefesaError"]
