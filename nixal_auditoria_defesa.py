#!/usr/bin/env python3
"""Trilha de auditoria durável, mínima e somente de observação para a Nyxal.

O arquivo contém apenas metadados allowlisted: nunca guarda cabeçalhos HTTP,
tokens, corpos de pedidos, motivos livres ou conteúdo arbitrário do cliente.
A trilha é append-only, limitada por bytes/registros e encadeada por SHA-256.
O encadeamento detecta corrupção, remoção ou reordenação não acompanhada da
reconstrução da cadeia; não substitui permissões de filesystem nem assinatura.
Nenhuma recomendação é executada por este módulo.
"""
from __future__ import annotations

import fcntl
import hashlib
import ipaddress
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_urlsafe
from typing import Any


GENESIS_HASH = "0" * 64
MAX_BYTES_PADRAO = 1_048_576
MAX_REGISTROS_PADRAO = 2048
MAX_LINHA_BYTES = 4096

_SEVERIDADES = frozenset({"informativa", "baixa", "media", "alta", "critica"})
_TIPOS_EVENTO = frozenset({"falha_autenticacao"})
_FONTES_EVENTO = frozenset({"api-auth"})
_TIPOS_RECOMENDACAO = frozenset({
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
_ESTADOS_PLANO = frozenset({
    "aguardando_aprovacao",
    "simulacao_preparada",
    "duplicado_idempotente",
    "expirado",
    "recomendacao_rejeitada",
    "preparacao_indisponivel",
    "nao_preparado",
})
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_HASH_RE = re.compile(r"^[a-f0-9]{64}$")


def _json_canonico(dados: dict[str, Any]) -> bytes:
    return json.dumps(
        dados, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class RegistroAuditoriaDefesaNixOS:
    """Persiste resumos allowlisted sob um diretório privado do usuário."""

    _CHAVES_REGISTRO = frozenset({
        "schema", "id", "observado_em", "tipo", "fonte_sinal", "origem_ip",
        "estado", "severidade", "recomendacoes", "planos_dry_run",
        "executor_ativo", "executor_autorizado", "efeito_executado",
        "previous_hash", "entry_hash",
    })

    @staticmethod
    def _objeto_sem_chaves_duplicadas(pares: list[tuple[str, Any]]) -> dict[str, Any]:
        resultado: dict[str, Any] = {}
        for chave, valor in pares:
            if chave in resultado:
                raise ValueError("chaves_json_duplicadas")
            resultado[chave] = valor
        return resultado

    VERSAO = 1

    def __init__(
        self,
        caminho: str | Path,
        *,
        max_bytes: int = MAX_BYTES_PADRAO,
        max_registros: int = MAX_REGISTROS_PADRAO,
    ) -> None:
        self.caminho = Path(caminho).expanduser().absolute()
        if not isinstance(max_bytes, int) or not 4096 <= max_bytes <= MAX_BYTES_PADRAO:
            raise ValueError("max_bytes_invalido")
        if not isinstance(max_registros, int) or not 1 <= max_registros <= MAX_REGISTROS_PADRAO:
            raise ValueError("max_registros_invalido")
        self.max_bytes = max_bytes
        self.max_registros = max_registros

    @classmethod
    def do_ambiente(cls) -> "RegistroAuditoriaDefesaNixOS":
        """Resolve XDG_STATE_HOME ou o diretório de estado padrão do usuário."""
        configurado = os.environ.get("XDG_STATE_HOME", "").strip()
        base = Path(configurado).expanduser() if configurado else Path.home() / ".local" / "state"
        return cls(base / "nyxal" / "defesa-auditoria" / "eventos.jsonl")

    def _validar_pasta(self, *, criar: bool) -> None:
        pasta = self.caminho.parent
        if criar:
            pasta.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Não aceite caminhos cujo trajeto atravesse symlinks; isso evita
        # redirecionar o registro privado para outra localização.
        componentes = [pasta, *pasta.parents]
        for componente in componentes:
            if componente.is_symlink():
                raise OSError("diretorio_simbolico_bloqueado")

        if not pasta.exists():
            raise FileNotFoundError("diretorio_auditoria_ausente")
        info = pasta.stat()
        if not stat.S_ISDIR(info.st_mode):
            raise OSError("diretorio_auditoria_invalido")
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
                raise OSError("arquivo_auditoria_nao_regular")
            if info.st_uid != os.geteuid():
                raise PermissionError("proprietario_arquivo_invalido")
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise PermissionError("permissoes_arquivo_nao_privadas")
            fcntl.flock(fd, fcntl.LOCK_EX if escrita else fcntl.LOCK_SH)
            return fd
        except Exception:
            os.close(fd)
            raise

    def _ler_fd(self, fd: int) -> tuple[list[dict[str, Any]], int]:
        info = os.fstat(fd)
        tamanho = info.st_size
        if tamanho > self.max_bytes:
            raise ValueError("limite_bytes_excedido")
        os.lseek(fd, 0, os.SEEK_SET)
        partes: list[bytes] = []
        restante = tamanho
        while restante:
            parte = os.read(fd, min(restante, 65536))
            if not parte:
                raise ValueError("arquivo_auditoria_truncado")
            partes.append(parte)
            restante -= len(parte)
        dados = b"".join(partes)
        if not dados:
            return [], 0
        if not dados.endswith(b"\n"):
            raise ValueError("ultima_linha_incompleta")

        registros: list[dict[str, Any]] = []
        hash_anterior = GENESIS_HASH
        for linha in dados.splitlines():
            if len(linha) > MAX_LINHA_BYTES:
                raise ValueError("linha_auditoria_excede_limite")
            item = json.loads(
                linha.decode("utf-8"),
                object_pairs_hook=self._objeto_sem_chaves_duplicadas,
            )
            if (
                not isinstance(item, dict)
                or set(item) != self._CHAVES_REGISTRO
                or item.get("schema") != self.VERSAO
            ):
                raise ValueError("schema_auditoria_invalido")
            hash_registro = item.get("entry_hash")
            anterior = item.get("previous_hash")
            if (
                not isinstance(hash_registro, str)
                or not _HASH_RE.fullmatch(hash_registro)
                or anterior != hash_anterior
            ):
                raise ValueError("cadeia_auditoria_invalida")
            sem_hash = dict(item)
            sem_hash.pop("entry_hash", None)
            esperado = hashlib.sha256(_json_canonico(sem_hash)).hexdigest()
            if esperado != hash_registro:
                raise ValueError("hash_auditoria_invalido")

            # Mesmo um registro com hash recalculado não pode injetar campos
            # extras ou afirmar execução/autorizações que este módulo proíbe.
            conteudo = dict(item)
            conteudo.pop("entry_hash", None)
            conteudo.pop("previous_hash", None)
            if self._sanitizar(conteudo) != conteudo:
                raise ValueError("metadados_auditoria_nao_allowlisted")
            registros.append(item)
            hash_anterior = hash_registro
            if len(registros) > self.max_registros:
                raise ValueError("limite_registros_excedido")
        return registros, tamanho

    @staticmethod
    def _timestamp(valor: Any) -> str:
        if not isinstance(valor, str) or len(valor) > 64:
            raise ValueError("timestamp_invalido")
        try:
            momento = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp_invalido") from exc
        if momento.tzinfo is None:
            raise ValueError("timestamp_sem_fuso")
        return momento.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _id(valor: Any) -> str:
        if not isinstance(valor, str) or not _ID_RE.fullmatch(valor):
            return token_urlsafe(12)
        return valor

    def _sanitizar(self, evento: Any) -> dict[str, Any]:
        if not isinstance(evento, dict):
            raise ValueError("evento_invalido")
        tipo = evento.get("tipo")
        fonte = evento.get("fonte_sinal")
        estado = evento.get("estado")
        severidade = evento.get("severidade")
        if tipo not in _TIPOS_EVENTO or fonte not in _FONTES_EVENTO:
            raise ValueError("origem_evento_nao_autorizada")
        if estado != "avaliado" or severidade not in _SEVERIDADES:
            raise ValueError("decisao_evento_invalida")

        ip_bruto = evento.get("origem_ip")
        if ip_bruto is None:
            endereco = None
        else:
            if not isinstance(ip_bruto, str) or len(ip_bruto) > 64:
                raise ValueError("origem_ip_invalida")
            endereco = str(ipaddress.ip_address(ip_bruto))

        recomendacoes: list[dict[str, Any]] = []
        valor_recomendacoes = evento.get("recomendacoes", [])
        if not isinstance(valor_recomendacoes, list):
            raise ValueError("recomendacoes_invalidas")
        for recomendacao in valor_recomendacoes[:8]:
            if not isinstance(recomendacao, dict):
                continue
            tipo_rec = recomendacao.get("tipo")
            if tipo_rec not in _TIPOS_RECOMENDACAO:
                continue
            recomendacoes.append({
                "tipo": tipo_rec,
                "exige_aprovacao_humana": (
                    True if tipo_rec != "alertar_operador"
                    else bool(recomendacao.get("exige_aprovacao_humana", False))
                ),
            })

        planos: list[dict[str, Any]] = []
        valor_planos = evento.get("planos_dry_run", [])
        if not isinstance(valor_planos, list):
            raise ValueError("planos_invalidos")
        for plano in valor_planos[:8]:
            if not isinstance(plano, dict):
                continue
            estado_plano = plano.get("estado")
            tipo_plano = plano.get("tipo")
            if estado_plano not in _ESTADOS_PLANO or tipo_plano not in _TIPOS_RECOMENDACAO:
                continue
            plano_id = plano.get("plano_id")
            expira = plano.get("expira_em")
            planos.append({
                "tipo": tipo_plano,
                "estado": estado_plano,
                "plano_id": plano_id if isinstance(plano_id, str) and _ID_RE.fullmatch(plano_id) else None,
                "expira_em": expira[:64] if isinstance(expira, str) else None,
                "exige_aprovacao_humana": bool(plano.get("exige_aprovacao_humana", True)),
                "aprovacao_verificada": bool(plano.get("aprovacao_verificada", False)),
                "executor_ativo": False,
                "executor_autorizado": False,
                "efeito_executado": False,
            })

        return {
            "schema": self.VERSAO,
            "id": self._id(evento.get("id")),
            "observado_em": self._timestamp(evento.get("observado_em")),
            "tipo": tipo,
            "fonte_sinal": fonte,
            "origem_ip": endereco,
            "estado": estado,
            "severidade": severidade,
            "recomendacoes": recomendacoes,
            "planos_dry_run": planos,
            "executor_ativo": False,
            "executor_autorizado": False,
            "efeito_executado": False,
        }

    def registrar(self, evento: Any) -> dict[str, Any]:
        """Acrescenta um evento sanitizado sem substituir registros existentes."""
        try:
            base = self._sanitizar(evento)
            fd = self._abrir(escrita=True, criar=True)
        except (OSError, ValueError, TypeError) as erro:
            # Não devolva a mensagem original da exceção: pode conter caminhos
            # locais ou valores vindos da entrada.
            estado = (
                "evento_invalido"
                if isinstance(erro, (ValueError, TypeError))
                else "auditoria_indisponivel"
            )
            return {"sucesso": False, "estado": estado}

        try:
            try:
                registros, tamanho = self._ler_fd(fd)
            except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as erro:
                return {
                    "sucesso": False,
                    "estado": f"integridade_auditoria_invalida_{type(erro).__name__}"[:64],
                }

            if len(registros) >= self.max_registros:
                return {"sucesso": False, "estado": "limite_registros_atingido"}
            base["previous_hash"] = registros[-1]["entry_hash"] if registros else GENESIS_HASH
            base["entry_hash"] = hashlib.sha256(_json_canonico(base)).hexdigest()
            linha = _json_canonico(base) + b"\n"
            if len(linha) > MAX_LINHA_BYTES:
                return {"sucesso": False, "estado": "linha_auditoria_excede_limite"}
            if tamanho + len(linha) > self.max_bytes:
                return {"sucesso": False, "estado": "limite_bytes_atingido"}
            escrita = os.write(fd, linha)
            if escrita != len(linha):
                return {"sucesso": False, "estado": "gravacao_parcial"}
            os.fsync(fd)
            return {
                "sucesso": True,
                "estado": "auditoria_duravel_registrada",
                "registro_id": base["id"],
                "quantidade_registros": len(registros) + 1,
            }
        except OSError as erro:
            return {"sucesso": False, "estado": f"falha_io_{type(erro).__name__}"[:64]}
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def _snapshot(self) -> tuple[bool, str, list[dict[str, Any]], int]:
        try:
            self._validar_pasta(criar=False)
            fd = self._abrir(escrita=False, criar=False)
        except FileNotFoundError:
            return True, "aguardando_primeiro_evento", [], 0
        except (OSError, ValueError, PermissionError) as erro:
            return False, f"auditoria_indisponivel_{type(erro).__name__}", [], 0
        try:
            try:
                registros, tamanho = self._ler_fd(fd)
            except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as erro:
                return False, f"integridade_auditoria_invalida_{type(erro).__name__}", [], 0
            return True, "auditoria_integridade_verificada", registros, tamanho
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def listar(self, limite: int = 50) -> list[dict[str, Any]]:
        if not isinstance(limite, int) or isinstance(limite, bool):
            return []
        if not 1 <= limite <= 100:
            return []
        sucesso, _estado, registros, _tamanho = self._snapshot()
        if not sucesso:
            return []
        return [dict(item) for item in registros[-limite:]]

    def contexto(self) -> dict[str, Any]:
        sucesso, estado, registros, tamanho = self._snapshot()
        return {
            "sucesso": sucesso,
            "estado": estado,
            "versao": self.VERSAO,
            "persistencia_duravel": True,
            "integridade_verificada": sucesso,
            "quantidade_registros": len(registros),
            "bytes_utilizados": tamanho,
            "limite_bytes": self.max_bytes,
            "limite_registros": self.max_registros,
            "somente_metadados_allowlisted": True,
            "executor_ativo": False,
            "executor_autorizado": False,
            "efeito_executado": False,
        }


__all__ = ["RegistroAuditoriaDefesaNixOS"]
