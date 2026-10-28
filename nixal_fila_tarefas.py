#!/usr/bin/env python3
"""Fila persistente governada da Nyxal.

A fila é at-most-once por padrão: uma tarefa interrompida em estado "executando"
vira "resultado_indeterminado" e nunca é repetida automaticamente. Apenas
capacidades registradas como somente_leitura podem entrar ou ser executadas.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import re
import socket
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from nixal_capacidades import GerenciadorCapacidades


ARQUIVO_FILA_PADRAO = Path(__file__).resolve().parent / "fila_tarefas_nixal.json"
VERSAO_FILA = "1.0"
MAX_TAREFAS = 500
MAX_FILA_BYTES = 2_000_000
MAX_ARGUMENTOS_BYTES = 16_000
MAX_RESULTADO_BYTES = 8_000
MAX_ERRO_CHARS = 500
MAX_DEPTH_JSON = 12
MAX_EXECUCAO_VIVA_SEGUNDOS = 6 * 60 * 60
ESTADOS_TAREFA = {
    "pendente", "executando", "concluida", "falhou",
    "negada", "resultado_indeterminado",
}
_CHAVES_SENSIVEIS = re.compile(
    r"(?i)(?:^|[_-])(?:api[_-]?key|token|secret|password|passwd|senha|"
    r"credential|authorization|client_secret|private[_-]?key|ssh[_-]?key|"
    r"signing[_-]?key|access[_-]?key)(?:$|[_-])"
)


class FilaTarefasErro(RuntimeError):
    """Falha fechada na persistência ou no contrato da fila."""


class FilaTarefasNixal:
    """Fila persistente com lock interprocesso, validação e checkpoints seguros."""

    FONTE = "fila_tarefas_nixal"

    def __init__(
        self,
        caminho: str | Path = ARQUIVO_FILA_PADRAO,
        capacidades: GerenciadorCapacidades | None = None,
    ) -> None:
        self.caminho = Path(caminho).expanduser().absolute()
        self.capacidades = capacidades if capacidades is not None else GerenciadorCapacidades()
        self._dados = self._estrutura_vazia()
        self._erro_carregamento: str | None = None
        self._recuperacao_pendente = False
        self.recarregar()

    def _estrutura_vazia(self) -> dict[str, Any]:
        return {"versao": VERSAO_FILA, "tarefas": []}

    @staticmethod
    def _agora() -> float:
        return time.time()

    @staticmethod
    def _numero_finito(valor: Any) -> int | float | None:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None
        return valor if math.isfinite(valor) else None

    @staticmethod
    def _json_bytes(dados: Any) -> bytes:
        try:
            return json.dumps(
                dados, ensure_ascii=False, allow_nan=False,
                sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError, RecursionError) as erro:
            raise FilaTarefasErro("json_da_fila_invalido") from erro

    @staticmethod
    def _redigir_texto(texto: str) -> str:
        texto = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", texto)
        texto = re.sub(
            r"(?i)\b(api[_ -]?key|api[_ -]?token|access[_ -]?token|"
            r"refresh[_ -]?token|session[_ -]?token|id[_ -]?token|token|"
            r"authorization|password|passwd|senha|secret|credential)\b"
            r"\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+",
            r"\1=[REDACTED]",
            texto,
        )
        return texto

    @classmethod
    def _redigir_valor(cls, valor: Any, chave: str = "", profundidade: int = 0) -> Any:
        if profundidade > MAX_DEPTH_JSON:
            return "[LIMITE_PROFUNDIDADE]"
        if chave and _CHAVES_SENSIVEIS.search(chave):
            return "[REDACTED]"
        if isinstance(valor, dict):
            return {
                str(k): cls._redigir_valor(v, str(k), profundidade + 1)
                for k, v in list(valor.items())[:500]
                if isinstance(k, str)
            }
        if isinstance(valor, list):
            return [cls._redigir_valor(v, "", profundidade + 1) for v in valor[:500]]
        if isinstance(valor, str):
            return cls._redigir_texto(valor[:4000])
        if valor is None or isinstance(valor, (bool, int)):
            return valor
        if isinstance(valor, float) and math.isfinite(valor):
            return valor
        return f"[TIPO_NAO_SERIALIZAVEL:{type(valor).__name__}]"

    @classmethod
    def _validar_json_limitado(cls, valor: Any, profundidade: int = 0) -> tuple[bool, str | None]:
        if profundidade > MAX_DEPTH_JSON:
            return False, "argumentos_excedem_limite_de_profundidade"
        if isinstance(valor, dict):
            for chave, item in valor.items():
                if not isinstance(chave, str):
                    return False, "chave_de_argumento_invalida"
                if _CHAVES_SENSIVEIS.search(chave):
                    return False, "argumento_com_campo_sensivel_bloqueado"
                valido, erro = cls._validar_json_limitado(item, profundidade + 1)
                if not valido:
                    return False, erro
            return True, None
        if isinstance(valor, list):
            if len(valor) > 500:
                return False, "lista_de_argumentos_excede_limite"
            for item in valor:
                valido, erro = cls._validar_json_limitado(item, profundidade + 1)
                if not valido:
                    return False, erro
            return True, None
        if valor is None or isinstance(valor, (str, bool, int)):
            return True, None
        if isinstance(valor, float) and math.isfinite(valor):
            return True, None
        return False, "argumento_nao_e_json_finito"

    @staticmethod
    def _verificar_caminho_sem_symlink(caminho: Path) -> None:
        caminho = caminho.absolute()
        for componente in list(reversed(caminho.parents)) + [caminho]:
            try:
                if componente.is_symlink():
                    raise FilaTarefasErro("caminho_da_fila_com_symlink")
            except OSError as erro:
                raise FilaTarefasErro("falha_ao_validar_caminho_da_fila") from erro

    @contextmanager
    def _bloquear_diretorio(self) -> Iterator[None]:
        """Lock interprocesso no diretório da fila; não cria sidecar no repositório."""
        parent = self.caminho.parent
        self._verificar_caminho_sem_symlink(parent)
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._verificar_caminho_sem_symlink(parent)
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(parent, flags)
        except OSError as erro:
            raise FilaTarefasErro("diretorio_da_fila_inseguro") from erro
        try:
            stat_fd = os.fstat(fd)
            stat_path = os.stat(parent, follow_symlinks=False)
            if not stat.S_ISDIR(stat_fd.st_mode) or (
                stat_fd.st_ino != stat_path.st_ino or stat_fd.st_dev != stat_path.st_dev
            ):
                raise FilaTarefasErro("diretorio_da_fila_mudou")
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _validar_registro_tarefa(self, tarefa: Any) -> tuple[bool, str | None]:
        if not isinstance(tarefa, dict):
            return False, "registro_de_tarefa_invalido"
        if not isinstance(tarefa.get("id"), str) or not tarefa["id"].strip():
            return False, "id_de_tarefa_invalido"
        if not isinstance(tarefa.get("capacidade"), str) or not tarefa["capacidade"].strip():
            return False, "capacidade_de_tarefa_invalida"
        if not isinstance(tarefa.get("argumentos"), dict):
            return False, "argumentos_de_tarefa_invalidos"
        if tarefa.get("estado") not in ESTADOS_TAREFA:
            return False, "estado_de_tarefa_desconhecido"
        criado = tarefa.get("criado_em")
        if isinstance(criado, bool) or not isinstance(criado, (int, float)) or not math.isfinite(criado):
            return False, "timestamp_de_tarefa_invalido"
        if tarefa.get("resultado") is not None and not isinstance(tarefa.get("resultado"), dict):
            return False, "resultado_de_tarefa_invalido"
        if tarefa.get("erro") is not None and not isinstance(tarefa.get("erro"), str):
            return False, "erro_de_tarefa_invalido"
        try:
            args_bytes = self._json_bytes(tarefa["argumentos"])
        except FilaTarefasErro:
            return False, "argumentos_de_tarefa_nao_serializaveis"
        if len(args_bytes) > MAX_ARGUMENTOS_BYTES:
            return False, "argumentos_de_tarefa_excedem_limite"
        return True, None

    def _validar_estrutura(self, dados: Any) -> tuple[bool, str | None]:
        if not isinstance(dados, dict) or dados.get("versao") != VERSAO_FILA:
            return False, "versao_ou_raiz_de_fila_desconhecida"
        tarefas = dados.get("tarefas")
        if not isinstance(tarefas, list) or len(tarefas) > MAX_TAREFAS:
            return False, "lista_de_tarefas_invalida_ou_excessiva"
        vistos: set[str] = set()
        for tarefa in tarefas:
            valido, erro = self._validar_registro_tarefa(tarefa)
            if not valido:
                return False, erro
            if tarefa["id"] in vistos:
                return False, "id_de_tarefa_duplicado"
            vistos.add(tarefa["id"])
        return True, None

    @staticmethod
    def _processo_vivo(pid: Any) -> bool:
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _recuperar_tarefas_interrompidas(self) -> None:
        host_atual = socket.gethostname()
        for tarefa in self._dados["tarefas"]:
            if tarefa.get("estado") != "executando":
                continue
            dono = tarefa.get("execucao_dono")
            host = dono.get("host") if isinstance(dono, dict) else None
            pid = dono.get("pid") if isinstance(dono, dict) else None
            iniciado = dono.get("iniciado_em") if isinstance(dono, dict) else None
            mesma_maquina = host == host_atual
            vivo = mesma_maquina and self._processo_vivo(pid)
            duracao = self._agora() - iniciado if isinstance(iniciado, (int, float)) else float("inf")
            if vivo and duracao < MAX_EXECUCAO_VIVA_SEGUNDOS:
                continue
            # Não repetir uma capacidade que pode ter produzido efeito antes da interrupção.
            tarefa["estado"] = "resultado_indeterminado"
            tarefa["erro"] = (
                "A execução anterior foi interrompida ou não pode ser verificada; "
                "a tarefa não será repetida automaticamente."
            )
            tarefa["resultado"] = {
                "sucesso": False,
                "estado": "resultado_indeterminado",
                "repeticao_automatica": False,
            }
            tarefa.pop("execucao_dono", None)
            self._recuperacao_pendente = True

    def _carregar_unlocked(self) -> bool:
        self._erro_carregamento = None
        self._recuperacao_pendente = False
        try:
            self._verificar_caminho_sem_symlink(self.caminho)
            if not self.caminho.exists():
                self._dados = self._estrutura_vazia()
                return True
            info = self.caminho.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                raise FilaTarefasErro("arquivo_da_fila_nao_regular")
            if info.st_size > MAX_FILA_BYTES:
                raise FilaTarefasErro("arquivo_da_fila_excede_limite")
            bruto = self.caminho.read_bytes()
            def constante_invalida(_: str) -> None:
                raise ValueError("constante_json_nao_finita")
            dados = json.loads(bruto.decode("utf-8"), parse_constant=constante_invalida)
            valido, motivo = self._validar_estrutura(dados)
            if not valido:
                raise FilaTarefasErro(motivo or "estrutura_de_fila_invalida")
            self._dados = copy.deepcopy(dados)
            self._recuperar_tarefas_interrompidas()
            return True
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError, FilaTarefasErro) as erro:
            self._dados = self._estrutura_vazia()
            self._erro_carregamento = (str(erro) or type(erro).__name__)[:160]
            return False

    def _salvar_unlocked(self) -> None:
        self._verificar_caminho_sem_symlink(self.caminho)
        parent = self.caminho.parent
        payload = self._json_bytes(self._dados)
        if len(payload) > MAX_FILA_BYTES:
            raise FilaTarefasErro("fila_excede_limite_de_tamanho")
        fd, temporario = tempfile.mkstemp(prefix=f".{self.caminho.name}.", suffix=".tmp", dir=parent)
        try:
            with os.fdopen(fd, "wb") as arquivo:
                os.fchmod(arquivo.fileno(), 0o600)
                arquivo.write(payload)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            self._verificar_caminho_sem_symlink(self.caminho)
            os.replace(temporario, self.caminho)
            try:
                descritor_pasta = os.open(
                    parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
                )
                try:
                    os.fsync(descritor_pasta)
                finally:
                    os.close(descritor_pasta)
            except OSError:
                # Depois de os.replace, o commit de dados já ocorreu. Não reverter a fila
                # em memória por uma falha secundária de fsync do diretório.
                pass
        finally:
            if os.path.exists(temporario):
                os.unlink(temporario)
        self._recuperacao_pendente = False

    def _carregar_e_recuperar_unlocked(self) -> bool:
        if not self._carregar_unlocked():
            return False
        if self._recuperacao_pendente:
            try:
                self._salvar_unlocked()
            except (OSError, ValueError, FilaTarefasErro):
                self._erro_carregamento = "falha_ao_persistir_recuperacao_de_tarefas"
                return False
        return True

    def _validar_capacidade(self, nome: str, argumentos: dict[str, Any]) -> tuple[bool, str | None]:
        capacidades = getattr(self.capacidades, "capacidades", None)
        if not isinstance(capacidades, dict) or nome not in capacidades:
            return False, "capacidade_nao_registrada"
        capacidade = capacidades[nome]
        politica = getattr(capacidade, "politica", None)
        if politica != "somente_leitura":
            return False, "fila_nao_aceita_capacidade_mutavel"
        if not hasattr(self.capacidades, "validar_argumentos"):
            return False, "validador_de_argumentos_indisponivel"
        try:
            valido, erro = self.capacidades.validar_argumentos(nome, argumentos)
        except Exception:
            return False, "validacao_de_argumentos_falhou"
        if valido is not True:
            return False, str(erro or "argumentos_de_capacidade_invalidos")[:180]
        return True, None

    @staticmethod
    def _resumir_resultado(valor: Any, limite: int = MAX_RESULTADO_BYTES) -> Any:
        redigido = FilaTarefasNixal._redigir_valor(valor)
        try:
            bruto = json.dumps(redigido, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        except (TypeError, ValueError, RecursionError):
            return {"resultado": "nao_serializavel", "tipo": type(valor).__name__}
        if len(bruto.encode("utf-8")) <= limite:
            return redigido
        return {
            "resultado_truncado": True,
            "tipo": type(valor).__name__,
            "resumo": FilaTarefasNixal._redigir_texto(bruto[: limite // 2]),
        }

    @staticmethod
    def _negado(estado: str, motivo: str) -> dict[str, Any]:
        return {"sucesso": False, "estado": estado, "origem": FilaTarefasNixal.FONTE, "motivo": motivo}

    @staticmethod
    def _falha_persistencia(erro: Exception) -> dict[str, Any]:
        return FilaTarefasNixal._negado(
            "falha_persistencia",
            (str(erro) or type(erro).__name__)[:160],
        )

    def adicionar(
        self,
        capacidade: str,
        argumentos: dict[str, Any] | None = None,
        *,
        chave_idempotencia: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(capacidade, str) or not capacidade.strip():
            return self._negado("entrada_invalida", "Nome da capacidade inválido.")
        capacidade = capacidade.strip()
        if argumentos is None:
            argumentos = {}
        if not isinstance(argumentos, dict):
            return self._negado("entrada_invalida", "Argumentos precisam ser um objeto.")
        argumentos_copia = copy.deepcopy(argumentos)
        valido, erro = self._validar_json_limitado(argumentos_copia)
        if not valido:
            return self._negado("argumentos_invalidos", erro or "Argumentos inválidos.")
        try:
            args_bytes = self._json_bytes(argumentos_copia)
        except FilaTarefasErro:
            return self._negado("argumentos_invalidos", "Argumentos não são JSON finito.")
        if len(args_bytes) > MAX_ARGUMENTOS_BYTES:
            return self._negado("argumentos_excedem_limite", f"Limite: {MAX_ARGUMENTOS_BYTES} bytes.")
        if chave_idempotencia is not None and (
            not isinstance(chave_idempotencia, str)
            or not chave_idempotencia.strip()
            or len(chave_idempotencia) > 160
        ):
            return self._negado("chave_idempotencia_invalida", "Chave precisa ter de 1 a 160 caracteres.")
        valido, erro = self._validar_capacidade(capacidade, argumentos_copia)
        if not valido:
            return self._negado("capacidade_nao_enfileiravel", erro or "Capacidade recusada.")

        with self._bloquear_diretorio():
            if not self._carregar_e_recuperar_unlocked():
                return self._negado(
                    "fila_indisponivel_preservada",
                    f"Fila não foi alterada: {self._erro_carregamento or 'erro_de_carga'}.",
                )
            if chave_idempotencia is not None:
                existente = next(
                    (t for t in self._dados["tarefas"] if t.get("chave_idempotencia") == chave_idempotencia),
                    None,
                )
                if existente is not None:
                    return {
                        "sucesso": True,
                        "estado": "ja_existente",
                        "origem": self.FONTE,
                        "valor": copy.deepcopy(existente),
                    }
            if len(self._dados["tarefas"]) >= MAX_TAREFAS:
                return self._negado("fila_cheia", f"Limite de {MAX_TAREFAS} tarefas atingido.")
            agora = self._agora()
            id_base = {
                "capacidade": capacidade,
                "argumentos": argumentos_copia,
                "criado_em": agora,
                "nonce": uuid.uuid4().hex,
            }
            tarefa = {
                "id": hashlib.sha256(self._json_bytes(id_base)).hexdigest(),
                "capacidade": capacidade,
                "argumentos": argumentos_copia,
                "estado": "pendente",
                "criado_em": agora,
                "resultado": None,
                "erro": None,
            }
            if chave_idempotencia is not None:
                tarefa["chave_idempotencia"] = chave_idempotencia
            self._dados["tarefas"].append(tarefa)
            try:
                self._salvar_unlocked()
            except (OSError, ValueError, FilaTarefasErro) as erro_salvar:
                self._dados["tarefas"].pop()
                return self._falha_persistencia(erro_salvar)
            return {
                "sucesso": True,
                "estado": "pendente",
                "origem": self.FONTE,
                "valor": copy.deepcopy(tarefa),
            }

    def executar_proxima(self) -> dict[str, Any]:
        """Executa uma só capacidade de leitura; claim e finalização são checkpoints atômicos."""
        tarefa_id: str | None = None
        execucao_id = uuid.uuid4().hex
        with self._bloquear_diretorio():
            if not self._carregar_e_recuperar_unlocked():
                return self._negado(
                    "fila_indisponivel_preservada",
                    f"Fila não foi alterada: {self._erro_carregamento or 'erro_de_carga'}.",
                )
            tarefa_em_execucao = next(
                (t for t in self._dados["tarefas"] if t.get("estado") == "executando"),
                None,
            )
            if tarefa_em_execucao is not None:
                return {
                    "sucesso": False,
                    "estado": "tarefa_em_execucao",
                    "origem": self.FONTE,
                    "valor": {
                        "id": tarefa_em_execucao.get("id"),
                        "estado": "executando",
                        "nao_repetir": True,
                    },
                }
            tarefa = next((t for t in self._dados["tarefas"] if t.get("estado") == "pendente"), None)
            if tarefa is None:
                return {"sucesso": True, "estado": "fila_vazia", "origem": self.FONTE, "valor": None}
            valido, erro = self._validar_capacidade(tarefa["capacidade"], tarefa["argumentos"])
            if not valido:
                tarefa["estado"] = "negada"
                tarefa["erro"] = (erro or "capacidade_recusada")[:MAX_ERRO_CHARS]
                tarefa["resultado"] = {"sucesso": False, "estado": "negada", "executada": False}
                try:
                    self._salvar_unlocked()
                except (OSError, ValueError, FilaTarefasErro) as erro_salvar:
                    return self._falha_persistencia(erro_salvar)
                return {
                    "sucesso": False,
                    "estado": "negada",
                    "origem": self.FONTE,
                    "valor": copy.deepcopy(tarefa),
                }
            tarefa_id = tarefa["id"]
            tarefa["estado"] = "executando"
            tarefa["execucao_dono"] = {
                "host": socket.gethostname(),
                "pid": os.getpid(),
                "iniciado_em": self._agora(),
                "execucao_id": execucao_id,
            }
            tarefa.pop("erro", None)
            try:
                self._salvar_unlocked()
            except (OSError, ValueError, FilaTarefasErro) as erro_salvar:
                tarefa["estado"] = "pendente"
                tarefa.pop("execucao_dono", None)
                return self._falha_persistencia(erro_salvar)
            tarefa_para_executar = copy.deepcopy(tarefa)

        # Não manter o lock interprocesso durante uma capacidade potencialmente lenta.
        try:
            resultado_capacidade = self.capacidades.executar(
                tarefa_para_executar["capacidade"],
                **tarefa_para_executar["argumentos"],
            )
            sucesso = getattr(resultado_capacidade, "sucesso", None) is True
            retorno = self._resumir_resultado(getattr(resultado_capacidade, "resultado", None))
            erro_original = getattr(resultado_capacidade, "erro", None)
            erro = self._redigir_texto(erro_original)[:MAX_ERRO_CHARS] if isinstance(erro_original, str) else None
            resultado = {
                "sucesso": sucesso,
                "capacidade": str(getattr(resultado_capacidade, "capacidade", tarefa_para_executar["capacidade"]))[:120],
                "resultado": retorno,
                "timestamp": self._numero_finito(getattr(resultado_capacidade, "timestamp", None)),
                "duracao_ms": self._numero_finito(getattr(resultado_capacidade, "duracao_ms", None)),
            }
        except Exception as erro_execucao:
            sucesso = False
            resultado = {
                "sucesso": False,
                "tipo_erro": type(erro_execucao).__name__,
                "execucao_indeterminada": False,
            }
            erro = f"excecao_na_capacidade:{type(erro_execucao).__name__}"[:MAX_ERRO_CHARS]

        with self._bloquear_diretorio():
            if not self._carregar_e_recuperar_unlocked():
                return self._negado(
                    "resultado_nao_persistido",
                    "A execução terminou, mas a fila não pode ser recarregada. Não repita automaticamente.",
                )
            tarefa_atual = next((t for t in self._dados["tarefas"] if t.get("id") == tarefa_id), None)
            dono_atual = tarefa_atual.get("execucao_dono", {}) if isinstance(tarefa_atual, dict) else {}
            if (
                not isinstance(tarefa_atual, dict)
                or tarefa_atual.get("estado") != "executando"
                or dono_atual.get("execucao_id") != execucao_id
            ):
                return self._negado(
                    "resultado_nao_persistido",
                    "O checkpoint mudou durante a execução. O resultado é indeterminado e não será repetido.",
                )
            tarefa_atual["estado"] = "concluida" if sucesso else "falhou"
            tarefa_atual["resultado"] = resultado
            tarefa_atual["erro"] = erro
            tarefa_atual.pop("execucao_dono", None)
            try:
                self._salvar_unlocked()
            except (OSError, ValueError, FilaTarefasErro) as erro_salvar:
                return self._negado(
                    "resultado_nao_persistido",
                    f"A capacidade terminou, mas o checkpoint não foi gravado ({type(erro_salvar).__name__}). Não repita automaticamente.",
                )
            return {
                "sucesso": sucesso,
                "estado": tarefa_atual["estado"],
                "origem": self.FONTE,
                "valor": copy.deepcopy(tarefa_atual),
            }

    def listar(self) -> list[dict[str, Any]]:
        with self._bloquear_diretorio():
            if not self._carregar_e_recuperar_unlocked():
                return []
            return copy.deepcopy(self._dados["tarefas"])

    def quantidade(self) -> int:
        return len(self.listar())

    def quantidade_pendentes(self) -> int:
        return sum(1 for tarefa in self.listar() if tarefa.get("estado") == "pendente")

    def recarregar(self) -> dict[str, Any]:
        with self._bloquear_diretorio():
            if not self._carregar_e_recuperar_unlocked():
                return self._negado(
                    "fila_corrompida_preservada",
                    f"Arquivo original preservado: {self._erro_carregamento or 'falha_de_leitura'}.",
                )
            return {
                "sucesso": True,
                "estado": "recarregado",
                "origem": self.FONTE,
                "valor": {
                    "quantidade": len(self._dados["tarefas"]),
                    "pendentes": sum(1 for t in self._dados["tarefas"] if t.get("estado") == "pendente"),
                    "indeterminadas": sum(1 for t in self._dados["tarefas"] if t.get("estado") == "resultado_indeterminado"),
                    "erro_carregamento": None,
                },
            }

    def contexto(self) -> dict[str, Any]:
        resultado = self.recarregar()
        if resultado.get("sucesso") is not True:
            return {"sucesso": False, "estado": resultado.get("estado"), "origem": self.FONTE}
        return {"sucesso": True, "estado": "observado", "origem": self.FONTE, **resultado.get("valor", {})}


if __name__ == "__main__":
    fila = FilaTarefasNixal()
    print(json.dumps(fila.recarregar(), ensure_ascii=False, indent=2))
