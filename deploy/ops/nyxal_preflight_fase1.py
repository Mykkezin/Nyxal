#!/usr/bin/env python3
"""Preflight Nyxal Fase 1: diagnóstico estritamente somente-leitura.

Não importa módulos de runtime, não inicia/paralisa serviços, não escreve estado,
não faz reparos/quarentena e não acessa a rede. Exit code 2 indica bloqueios
encontrados; o relatório completo continua sendo impresso.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import pwd
import re
import shlex
import stat
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


GENESIS_HASH = "0" * 64
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_AUDIT_BYTES = 1_048_576
MAX_AUDIT_LINE_BYTES = 4096
AUDIT_KEYS = {
    "schema", "id", "observado_em", "tipo", "fonte_sinal", "origem_ip",
    "estado", "severidade", "recomendacoes", "planos_dry_run",
    "executor_ativo", "executor_autorizado", "efeito_executado",
    "previous_hash", "entry_hash",
}
APPROVAL_TYPES = {
    "aprovacao_registrada", "aprovacao_consumida",
    "aprovacao_revogada", "aprovacao_recusada",
}


class PreflightError(Exception):
    """Erro de validação sem incluir conteúdo dos arquivos no relatório."""


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreflightError("chave_json_duplicada")
        result[key] = value
    return result


def reject_json_constant(_value: str) -> None:
    raise PreflightError("constante_json_nao_padrao")


def strict_json(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_json_constant,
        )
    except PreflightError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise PreflightError("json_ilegivel") from None


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest_stream(stream: Any) -> str:
    digest = hashlib.sha256()
    while True:
        block = stream.read(1024 * 1024)
        if not block:
            break
        digest.update(block)
    return digest.hexdigest()

def hash_regular_file(path: Path, max_bytes: int) -> tuple[str, int]:
    ensure_no_symlink_components(path)
    try:
        with path.open("rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise PreflightError("nao_e_arquivo_regular")
            if info.st_size > max_bytes:
                raise PreflightError("limite_bytes_excedido")
            return digest_stream(stream), info.st_size
    except FileNotFoundError:
        raise PreflightError("arquivo_ausente") from None
    except OSError:
        raise PreflightError("arquivo_ilegivel") from None


def ensure_no_symlink_components(path: Path) -> None:
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise PreflightError("caminho_contem_symlink")


def read_regular(path: Path, max_bytes: int) -> bytes:
    ensure_no_symlink_components(path)
    try:
        with path.open("rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise PreflightError("nao_e_arquivo_regular")
            if info.st_size > max_bytes:
                raise PreflightError("limite_bytes_excedido")
            raw = stream.read(max_bytes + 1)
    except FileNotFoundError:
        raise PreflightError("arquivo_ausente") from None
    except OSError:
        raise PreflightError("arquivo_ilegivel") from None
    if len(raw) > max_bytes:
        raise PreflightError("limite_bytes_excedido")
    return raw


def parse_crystal(raw: bytes) -> dict[str, int]:
    """Valida formato NXCM sem importar o gerenciador que também sabe gravar."""
    if len(raw) < 5 or raw[:4] != b"NXCM":
        raise PreflightError("cristal_magic_invalido")
    version = raw[4]
    if version == 1:
        width = 1
    elif version == 2:
        width = 2
    else:
        raise PreflightError("cristal_versao_desconhecida")

    pos = 5
    concepts: dict[str, int] = {}
    relations: dict[str, int] = {}
    blocks = 0
    triples = 0

    def read_int(at: int) -> tuple[int, int]:
        end = at + width
        if end > len(raw):
            raise PreflightError("cristal_campo_truncado")
        return int.from_bytes(raw[at:end], "little"), end

    while pos < len(raw):
        record_type = raw[pos]
        pos += 1
        if record_type in (1, 2):
            size, pos = read_int(pos)
            end = pos + size
            if end > len(raw):
                raise PreflightError("cristal_string_truncada")
            try:
                name = raw[pos:end].decode("utf-8")
            except UnicodeDecodeError:
                raise PreflightError("cristal_utf8_invalido") from None
            pos = end
            target = concepts if record_type == 1 else relations
            if name in target:
                raise PreflightError("cristal_nome_duplicado")
            target[name] = len(target)
        elif record_type == 3:
            count, pos = read_int(pos)
            required = count * 3 * width
            if pos + required > len(raw):
                raise PreflightError("cristal_bloco_truncado")
            for _ in range(count):
                subject, pos = read_int(pos)
                relation, pos = read_int(pos)
                obj, pos = read_int(pos)
                if subject >= len(concepts) or obj >= len(concepts):
                    raise PreflightError("cristal_referencia_conceito_invalida")
                if relation >= len(relations):
                    raise PreflightError("cristal_referencia_relacao_invalida")
            blocks += 1
            triples += count
        else:
            raise PreflightError("cristal_tipo_de_registro_desconhecido")

    return {
        "versao": version,
        "conceitos": len(concepts),
        "relacoes": len(relations),
        "blocos": blocks,
        "triplas": triples,
        "bytes": len(raw),
    }


def verify_backup(backup_dir: Path) -> dict[str, int]:
    archive = backup_dir / "estado_vivo.tar.gz"
    checksum_file = backup_dir / "estado_vivo.tar.gz.sha256"
    manifest_file = backup_dir / "manifesto_hashes.txt"

    checksum_text = read_regular(checksum_file, 4096).decode("utf-8").strip()
    match = re.fullmatch(
        r"([0-9a-f]{64})\s+\*?estado_vivo\.tar\.gz", checksum_text
    )
    if not match:
        raise PreflightError("checksum_sidecar_invalido")
    archive_hash_expected = match.group(1)
    archive_raw_hash, archive_size = hash_regular_file(archive, 4 * 1024 * 1024 * 1024)
    if archive_raw_hash != archive_hash_expected:
        raise PreflightError("hash_do_archive_nao_confere")

    manifest_text = read_regular(manifest_file, 16 * 1024 * 1024).decode("utf-8")
    manifest: dict[str, str] = {}
    for line in manifest_text.splitlines():
        entry = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not entry:
            raise PreflightError("linha_do_manifesto_invalida")
        expected, name = entry.groups()
        rel = PurePosixPath(name)
        if (
            not name.startswith("payload/")
            or rel.is_absolute()
            or any(part in ("", ".", "..") for part in rel.parts)
            or name in manifest
        ):
            raise PreflightError("caminho_do_manifesto_invalido")
        manifest[name] = expected
    if not manifest:
        raise PreflightError("manifesto_vazio")

    archived: dict[str, str] = {}
    try:
        with tarfile.open(archive, mode="r:gz") as tar:
            for member in tar.getmembers():
                rel = PurePosixPath(member.name)
                if (
                    rel.is_absolute()
                    or any(part == ".." for part in rel.parts)
                    or not (member.name == "payload" or member.name.startswith("payload/"))
                ):
                    raise PreflightError("caminho_no_archive_invalido")
                if member.isdir():
                    continue
                if not member.isfile() or member.name in archived:
                    raise PreflightError("tipo_ou_duplicacao_no_archive")
                stream = tar.extractfile(member)
                if stream is None:
                    raise PreflightError("membro_do_archive_ilegivel")
                with stream:
                    archived[member.name] = digest_stream(stream)
    except PreflightError:
        raise
    except (OSError, tarfile.TarError, EOFError):
        raise PreflightError("archive_ilegivel") from None

    if set(archived) != set(manifest):
        raise PreflightError("conteudo_do_archive_diverge_do_manifesto")
    for name, expected in manifest.items():
        if archived[name] != expected:
            raise PreflightError("hash_de_payload_nao_confere")
    return {"arquivos": len(manifest), "bytes_archive": archive_size}


def check_hash_chain(path: Path, mode: str, owner_uid: int) -> dict[str, int]:
    raw = read_regular(path, MAX_AUDIT_BYTES)
    try:
        info = path.stat()
    except OSError:
        raise PreflightError("metadados_do_diario_indisponiveis") from None
    if info.st_uid != owner_uid:
        raise PreflightError("proprietario_do_diario_invalido")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise PreflightError("permissoes_do_diario_nao_privadas")
    if not raw:
        return {"registros": 0, "bytes": 0}
    if not raw.endswith(b"\n"):
        raise PreflightError("ultima_linha_do_diario_incompleta")

    previous = GENESIS_HASH
    count = 0
    for line in raw.splitlines():
        if len(line) > MAX_AUDIT_LINE_BYTES:
            raise PreflightError("linha_do_diario_excede_limite")
        item = strict_json(line)
        if not isinstance(item, dict):
            raise PreflightError("registro_do_diario_invalido")
        if item.get("previous_hash") != previous:
            raise PreflightError("cadeia_de_hash_invalida")
        entry_hash = item.get("entry_hash")
        if not isinstance(entry_hash, str) or not HASH_RE.fullmatch(entry_hash):
            raise PreflightError("hash_de_registro_invalido")
        unsigned = dict(item)
        unsigned.pop("entry_hash", None)
        expected = hashlib.sha256(canonical_json(unsigned)).hexdigest()
        if expected != entry_hash:
            raise PreflightError("hash_de_registro_nao_confere")
        if mode == "audit" and (
            set(item) != AUDIT_KEYS or item.get("schema") != 1
        ):
            raise PreflightError("schema_de_auditoria_invalido")
        if mode == "approval" and item.get("tipo") not in APPROVAL_TYPES:
            raise PreflightError("tipo_de_aprovacao_invalido")
        previous = entry_hash
        count += 1
        if count > 2048:
            raise PreflightError("quantidade_de_registros_excede_limite")
    return {"registros": count, "bytes": len(raw)}


def check_generic_jsonl(path: Path) -> int:
    raw = read_regular(path, MAX_AUDIT_BYTES)
    if raw and not raw.endswith(b"\n"):
        raise PreflightError("ultima_linha_incompleta")
    count = 0
    for line in raw.splitlines():
        if len(line) > MAX_AUDIT_LINE_BYTES:
            raise PreflightError("linha_excede_limite")
        item = strict_json(line)
        if not isinstance(item, dict):
            raise PreflightError("registro_nao_e_objeto")
        count += 1
    return count


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def active_user_unit(user: str, home: Path, uid: int, unit: str) -> str | None:
    runtime = Path("/run/user") / str(uid)
    socket_path = runtime / "bus"
    if not socket_path.exists():
        return None
    base_env = {
        "HOME": str(home),
        "USER": user,
        "LOGNAME": user,
        "XDG_RUNTIME_DIR": str(runtime),
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={socket_path}",
    }
    command = ["systemctl", "--user", "show", "--property=ActiveState", "--value", unit]
    process_env = os.environ.copy()
    process_env.update(base_env)
    if os.geteuid() == 0:
        command = [
            "runuser", "-u", user, "--", "env",
            *(f"{key}={value}" for key, value in base_env.items()),
            *command,
        ]
    try:
        result = subprocess.run(
            command, env=process_env, capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


class Reporter:
    def __init__(self) -> None:
        self.findings: list[tuple[str, str, str, str]] = []

    def add(self, level: str, code: str, message: str, path: Path | None = None) -> None:
        path_text = str(path) if path is not None else "-"
        self.findings.append((level, code, path_text, message))
        print(f"[{level}] {code} | {path_text} | {message}")

    def check_json(self, path: Path, required: bool = True) -> Any | None:
        try:
            raw = read_regular(path, MAX_JSON_BYTES)
            value = strict_json(raw)
            if not isinstance(value, (dict, list)):
                raise PreflightError("raiz_json_invalida")
            self.add("OK", "json_legivel", f"JSON válido; raiz={type(value).__name__}; bytes={len(raw)}", path)
            return value
        except PreflightError as exc:
            if str(exc) == "arquivo_ausente" and not required:
                self.add("INFO", "estado_opcional_ausente", "Arquivo opcional ausente; nenhum arquivo foi criado.", path)
            else:
                self.add("BLOQUEIO" if required else "ALERTA", "json_nao_validado", str(exc), path)
            return None

    def check_crystal(self, path: Path, required: bool = True) -> dict[str, int] | None:
        try:
            raw = read_regular(path, MAX_JSON_BYTES)
            summary = parse_crystal(raw)
            self.add(
                "OK", "cristal_integro",
                f"NXCM v{summary['versao']}; conceitos={summary['conceitos']}; "
                f"relações={summary['relacoes']}; blocos={summary['blocos']}; "
                f"triplas={summary['triplas']}; bytes={summary['bytes']}",
                path,
            )
            return summary
        except PreflightError as exc:
            if str(exc) == "arquivo_ausente" and not required:
                self.add("INFO", "cristal_opcional_ausente", "Cristal opcional ausente; nenhum arquivo foi criado.", path)
            else:
                self.add("BLOQUEIO" if required else "ALERTA", "cristal_nao_validado", str(exc), path)
            return None

    def check_delta(self, path: Path) -> None:
        value = self.check_json(path, required=True)
        if value is None:
            return
        if (
            not isinstance(value, dict)
            or value.get("versao") != "5.4.0"
            or value.get("origem") != "delta_nyxos"
            or not isinstance(value.get("eventos"), list)
            or len(value["eventos"]) > 200
            or any(
                not isinstance(event, dict)
                or not isinstance(event.get("delta_id"), str)
                or not event["delta_id"].strip()
                for event in value.get("eventos", [])
            )
        ):
            self.add(
                "BLOQUEIO", "delta_schema_invalido",
                "Delta não atende ao contrato esperado; os dados foram preservados sem normalização.",
                path,
            )
            return
        self.add("OK", "delta_schema_validado", f"versão=5.4.0; eventos={len(value['eventos'])}", path)

    def check_operational_state(self, path: Path) -> None:
        value = self.check_json(path, required=True)
        if value is None:
            return
        valid = (
            isinstance(value, dict)
            and value.get("versao") == "5.3.0"
            and value.get("origem") == "persistencia_operacional_nyxos"
            and isinstance(value.get("inicializacoes"), int)
            and not isinstance(value.get("inicializacoes"), bool)
            and value.get("inicializacoes", -1) >= 0
            and isinstance(value.get("historico"), list)
            and len(value["historico"]) <= 50
        )
        if not valid:
            self.add(
                "BLOQUEIO", "estado_operacional_schema_invalido",
                "Estado operacional não atende ao contrato 5.3.0; nenhum reparo foi tentado.",
                path,
            )
        else:
            self.add(
                "OK", "estado_operacional_validado",
                f"versão=5.3.0; inicializações={value['inicializacoes']}; histórico={len(value['historico'])}",
                path,
            )

    def check_memory(self, path: Path) -> None:
        try:
            raw = read_regular(path, MAX_JSON_BYTES)
            value = strict_json(raw)
            if not isinstance(value, dict) or value.get("versao") != 1:
                raise PreflightError("versao_ou_raiz_de_memoria_invalida")
            sessions = value.get("sessoes")
            if not isinstance(sessions, dict) or len(sessions) > 200:
                raise PreflightError("mapa_de_sessoes_invalido")
            messages_total = 0
            for session, messages in sessions.items():
                if (
                    not isinstance(session, str) or not session.strip()
                    or len(session) > 200 or not isinstance(messages, list)
                    or len(messages) > 12
                ):
                    raise PreflightError("sessao_ou_historico_invalido")
                for message in messages:
                    if (
                        not isinstance(message, dict)
                        or message.get("papel") not in {"user", "assistant"}
                        or not isinstance(message.get("texto"), str)
                        or not message["texto"].strip()
                        or len(message["texto"]) > 12000
                    ):
                        raise PreflightError("mensagem_de_conversa_invalida")
                    messages_total += 1
            self.add(
                "OK", "memoria_conversacional_validada",
                f"sessoes={len(sessions)}; mensagens={messages_total}; bytes={len(raw)}; conteúdo não exibido",
                path,
            )
        except PreflightError as exc:
            self.add("BLOQUEIO", "memoria_conversacional_nao_validada", str(exc), path)

    def check_journal(self, path: Path, mode: str, owner_uid: int) -> None:
        try:
            summary = check_hash_chain(path, mode, owner_uid)
            self.add(
                "OK", "diario_encadeado_valido",
                f"tipo={mode}; registros={summary['registros']}; bytes={summary['bytes']}",
                path,
            )
        except PreflightError as exc:
            if str(exc) == "arquivo_ausente":
                self.add("INFO", "diario_ainda_ausente", "Diário ausente; nada foi criado. Confirmar se a ausência é esperada antes de habilitar o recurso.", path)
            else:
                self.add("BLOQUEIO", "diario_nao_confiavel", str(exc), path)

    def has_blockers(self) -> bool:
        return any(finding[0] == "BLOQUEIO" for finding in self.findings)


def resolve_identity(user_arg: str | None, home_arg: str | None) -> tuple[str, Path, int]:
    user = user_arg or os.environ.get("SUDO_USER") or getpass.getuser()
    try:
        entry = pwd.getpwnam(user)
    except KeyError:
        raise PreflightError("conta_operacional_nao_encontrada") from None
    home = Path(home_arg) if home_arg else Path(entry.pw_dir)
    ensure_no_symlink_components(home)
    if not home.is_dir():
        raise PreflightError("home_operacional_ausente")
    return user, home, entry.pw_uid


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight Nyxal Fase 1 somente-leitura; não migra nem altera serviços."
    )
    parser.add_argument("--user", help="Conta Unix da instalação; padrão: SUDO_USER ou usuário atual.")
    parser.add_argument("--home", help="HOME real da conta Nyxal.")
    parser.add_argument("--repo", help="Checkout que será inspecionado; padrão: HOME/Nyxal.")
    parser.add_argument("--backup-dir", required=True, help="Diretório Fase 0 que contém archive, checksum e manifesto.")
    parser.add_argument("--memory-path", help="Caminho efetivo de conversas.json, se diferente do padrão.")
    parser.add_argument("--state-dir", help="Diretório de estado XDG efetivo, se diferente do padrão.")
    parser.add_argument("--delta-path", help="Caminho efetivo de eventos_delta_nyxos.json.")
    parser.add_argument("--crystal-path", help="Caminho efetivo do cristal autoritativo.")
    parser.add_argument("--checkpoint-path", help="Caminho efetivo do checkpoint do cristal.")
    parser.add_argument("--manager-crystal-path", help="Caminho efetivo do cristal experimental do gerenciador.")
    args = parser.parse_args()

    reporter = Reporter()
    try:
        user, home, uid = resolve_identity(args.user, args.home)
        repo = Path(args.repo) if args.repo else home / "Nyxal"
        backup = Path(args.backup_dir)
        ensure_no_symlink_components(repo)
        ensure_no_symlink_components(backup)
        print("=== NYXAL FASE 1 — PREFLIGHT SOMENTE-LEITURA ===")
        print(f"Conta inspecionada: {user} (uid={uid})")
        print(f"Checkout: {repo}")
        print(f"Backup Fase 0: {backup}")
        print("Modo: leitura; sem imports de runtime; sem reparos; sem alterações de serviços.")
        print()

        try:
            summary = verify_backup(backup)
            reporter.add(
                "OK", "backup_fase0_verificado",
                f"archive SHA-256, manifesto e payload conferem; arquivos={summary['arquivos']}; bytes_archive={summary['bytes_archive']}",
                backup,
            )
        except (PreflightError, OSError, UnicodeDecodeError):
            reporter.add(
                "BLOQUEIO", "backup_fase0_nao_verificado",
                "Não foi possível confirmar archive + checksum + hashes internos; não avançar para migração.",
                backup,
            )

        if not repo.is_dir():
            reporter.add("BLOQUEIO", "checkout_ausente", "Diretório de checkout não encontrado.", repo)
        else:
            head_result = run_git(repo, "rev-parse", "--verify", "HEAD")
            branch_result = run_git(repo, "branch", "--show-current")
            main_result = run_git(repo, "rev-parse", "--verify", "origin/main")
            status_result = run_git(repo, "status", "--porcelain=v1", "--untracked-files=all")
            if any(result.returncode != 0 for result in (head_result, branch_result, main_result, status_result)):
                reporter.add("BLOQUEIO", "git_inspecao_indisponivel", "Git não pôde ser inspecionado em modo somente-leitura.", repo)
            else:
                head = head_result.stdout.strip()
                branch = branch_result.stdout.strip() or "(detached HEAD)"
                main_sha = main_result.stdout.strip()
                changes = [line for line in status_result.stdout.splitlines() if line]
                reporter.add("INFO", "git_referencias", f"branch={branch}; HEAD={head}; origin/main local={main_sha} (sem fetch/rede).", repo)
                if head != main_sha:
                    reporter.add("BLOQUEIO", "checkout_nao_corresponde_a_origin_main", "Não usar este checkout como release Green; preparar uma cópia isolada a partir de uma referência revisada.", repo)
                if changes:
                    reporter.add("BLOQUEIO", "checkout_com_alteracoes_locais", f"{len(changes)} entradas modificadas/não rastreadas; nenhuma será descartada.", repo)

            for module in (
                "gerenciador_cristal.py",
                "nixal_delta.py",
                "nixal_aprovacao_defesa.py",
                "nixal_auditoria_defesa.py",
                "nixal_memoria_conversacional.py",
                "nixal_runtime.py",
                "nyxal_web_api.py",
            ):
                module_path = repo / module
                try:
                    ensure_no_symlink_components(module_path)
                    if not module_path.is_file():
                        reporter.add("BLOQUEIO", "modulo_critico_ausente", "Módulo necessário para a validação/release não encontrado.", module_path)
                except PreflightError:
                    reporter.add("BLOQUEIO", "modulo_critico_caminho_inseguro", "Caminho do módulo contém link simbólico.", module_path)

        repo_json = (
            "capacidades_nixal.json",
            "estado_corpo_nixal.json",
            "estado_nyxal_runtime.json",
            "fisiologia_operacional_nyxos.json",
            "gateway_atuacao_nyxos.json",
            "log_nyxal_residente.json",
            "memoria_aprendizado_nixal.json",
            "plano_central_controle_nyxos.json",
            "presenca_maquina_nyxos.json",
            "memoria/cristalizacao.json",
            "memoria/cristal_atual.json",
        )
        for relative in repo_json:
            reporter.check_json(repo / relative, required=True)

        delta_path = Path(args.delta_path) if args.delta_path else repo / "eventos_delta_nyxos.json"
        reporter.check_delta(delta_path)
        reporter.check_operational_state(repo / "estado_nyxos_operacional.json")

        memory_path = Path(args.memory_path) if args.memory_path else home / ".local/share/nyxal/conversas.json"
        reporter.check_memory(memory_path)

        crystal_path = Path(args.crystal_path) if args.crystal_path else repo / "memoria/cristal/cristal.bin"
        checkpoint_path = Path(args.checkpoint_path) if args.checkpoint_path else repo / "memoria/backups/cristal_ultimo_bom.bin"
        manager_crystal_path = Path(args.manager_crystal_path) if args.manager_crystal_path else repo / "experimentos/cristal_gerenciador.bin"
        current_summary = reporter.check_crystal(crystal_path, required=True)
        checkpoint_summary = reporter.check_crystal(checkpoint_path, required=True)
        reporter.check_crystal(manager_crystal_path, required=True)
        if current_summary and checkpoint_summary:
            try:
                current_hash = hashlib.sha256(read_regular(crystal_path, MAX_JSON_BYTES)).hexdigest()
                checkpoint_hash = hashlib.sha256(read_regular(checkpoint_path, MAX_JSON_BYTES)).hexdigest()
                if current_hash != checkpoint_hash:
                    reporter.add(
                        "ALERTA", "cristal_checkpoint_divergente",
                        "Cristal autoritativo e checkpoint são diferentes; ambos foram preservados. Não restaurar automaticamente.",
                        crystal_path,
                    )
                else:
                    reporter.add("OK", "cristal_checkpoint_igual", "Cristal autoritativo e checkpoint têm bytes idênticos.", crystal_path)
            except PreflightError:
                reporter.add("ALERTA", "comparacao_cristal_indisponivel", "Não foi possível comparar os hashes dos cristais.", crystal_path)

        state_dir = Path(args.state_dir) if args.state_dir else home / ".local/state/nyxal"
        reporter.check_journal(state_dir / "defesa-auditoria/eventos.jsonl", "audit", uid)
        reporter.check_journal(state_dir / "defesa-aprovacoes/aprovacoes.jsonl", "approval", uid)

        legacy_audit = repo / "auditoria_atuacao_nyxos.jsonl"
        try:
            count = check_generic_jsonl(legacy_audit)
            reporter.add(
                "ALERTA", "auditoria_legada_precisa_de_validacao_semantica",
                f"JSONL legível; registros={count}; cadeia específica não foi atestada por este preflight.",
                legacy_audit,
            )
        except PreflightError as exc:
            reporter.add("BLOQUEIO", "auditoria_legada_nao_validada", str(exc), legacy_audit)

        quarantine_files = sorted(repo.glob("auditoria_atuacao_nyxos.jsonl.corrompido-cadeia-*"))
        if quarantine_files:
            reporter.add(
                "ALERTA", "artefato_de_corrupcao_preservado",
                f"{len(quarantine_files)} artefato(s) histórico(s) com nome de corrupção encontrados; preservar e investigar, sem excluir ou reutilizar como fonte ativa.",
                repo,
            )

        for unit in ("nyxal-api.service", "nyxos-residente.service"):
            state = active_user_unit(user, home, uid, unit)
            if state is None:
                reporter.add("BLOQUEIO", "estado_systemd_indisponivel", "Não foi possível confirmar o estado atual da unit systemd --user.", Path(unit))
            elif state != "active":
                reporter.add("BLOQUEIO", "servico_esperado_inativo", f"Estado atual={state}; não executar cutover enquanto não houver diagnóstico.", Path(unit))
            else:
                reporter.add("OK", "servico_ativo", "Unit systemd --user está ativa; nenhum comando de controle foi emitido.", Path(unit))

        blockers = sum(1 for item in reporter.findings if item[0] == "BLOQUEIO")
        alerts = sum(1 for item in reporter.findings if item[0] == "ALERTA")
        print()
        print("=== RESUMO ===")
        print(f"Bloqueios: {blockers}")
        print(f"Alertas: {alerts}")
        print("Nenhum arquivo operacional foi escrito, corrigido, movido ou removido.")
        if blockers:
            print("RESULTADO: BLOQUEADO — não migrar estado nem fazer cutover.")
            return 2
        if alerts:
            print("RESULTADO: REVISÃO NECESSÁRIA — resolver alertas antes do cutover.")
        else:
            print("RESULTADO: PREFLIGHT PASSOU — isso não autoriza sozinho um cutover.")
        return 0
    except (PreflightError, OSError, KeyError, ValueError) as exc:
        # Mensagem limitada a códigos que não incluem bytes ou segredos.
        print(f"[BLOQUEIO] preflight_nao_concluido | - | {str(exc) or type(exc).__name__}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
