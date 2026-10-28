#!/usr/bin/env python3

"""
NIXAL — MEMÓRIA PERSISTENTE DE CONHECIMENTO CANDIDATO

Responsabilidade:
    Persistir candidatos de conhecimento produzidos pelo ciclo de
    consolidação, sem promovê-los automaticamente a conhecimento
    permanente e sem modificar a arquitetura.

Princípios:
1. O candidato precisa vir de uma consolidação válida.
2. A memória preserva o candidato sem alterar seu conteúdo.
3. Registros duplicados não são gravados novamente.
4. A identidade do registro é determinística.
5. Persistência não significa conhecimento permanente.
6. A memória não promove conhecimento.
7. A memória não modifica a arquitetura.
8. A memória não executa capacidades.
9. A escrita usa substituição atômica.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any


VERSAO_MEMORIA = "1.0"
MAX_MEMORIA_JSON_BYTES = 32 * 1024 * 1024

ARQUIVO_MEMORIA_PADRAO = (
    Path(__file__).resolve().parent
    / "memoria_conhecimento_nixal.json"
)


def _tem_ancestral_simbolico(caminho: Path) -> bool:
    """Detecta links simbólicos no caminho lexical, inclusive ancestrais ausentes."""
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


class MemoriaConhecimentoNixal:
    """Armazenamento persistente de candidatos de conhecimento."""

    FONTE = "memoria_conhecimento_nixal"

    def __init__(
        self,
        caminho: Path = ARQUIVO_MEMORIA_PADRAO,
    ) -> None:
        self.caminho = Path(caminho)
        self._erro_carregamento: str | None = None
        self._dados = self._carregar()

    @staticmethod
    def _estrutura_vazia() -> dict[str, Any]:
        return {
            "versao": VERSAO_MEMORIA,
            "registros": [],
        }

    def _carregar(self) -> dict[str, Any]:
        """Carrega somente um arquivo íntegro; corrupção nunca vira memória vazia gravável."""
        self._erro_carregamento = None
        if _tem_ancestral_simbolico(self.caminho):
            self._erro_carregamento = "caminho_memoria_com_link_simbolico"
            return self._estrutura_vazia()

        descritor: int | None = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            descritor = os.open(self.caminho, flags)
            if not stat.S_ISREG(os.fstat(descritor).st_mode):
                self._erro_carregamento = "arquivo_memoria_nao_regular"
                return self._estrutura_vazia()
            with os.fdopen(descritor, "rb") as arquivo:
                descritor = None
                bruto = arquivo.read(MAX_MEMORIA_JSON_BYTES + 1)
        except FileNotFoundError:
            return self._estrutura_vazia()
        except OSError:
            self._erro_carregamento = "arquivo_ilegivel_ou_json_corrompido"
            return self._estrutura_vazia()
        finally:
            if descritor is not None:
                try:
                    os.close(descritor)
                except OSError:
                    pass

        if len(bruto) > MAX_MEMORIA_JSON_BYTES:
            self._erro_carregamento = "arquivo_excede_limite_tamanho"
            return self._estrutura_vazia()

        try:
            dados = json.loads(bruto.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            self._erro_carregamento = "arquivo_ilegivel_ou_json_corrompido"
            return self._estrutura_vazia()
        if not isinstance(dados, dict):
            self._erro_carregamento = "estrutura_raiz_invalida"
            return self._estrutura_vazia()
        if dados.get("versao") != VERSAO_MEMORIA:
            self._erro_carregamento = "versao_memoria_nao_suportada"
            return self._estrutura_vazia()
        registros = dados.get("registros")
        if not isinstance(registros, list):
            self._erro_carregamento = "lista_registros_invalida"
            return self._estrutura_vazia()
        for registro in registros:
            if (
                not isinstance(registro, dict)
                or not isinstance(registro.get("registro_id"), str)
                or not isinstance(registro.get("candidato"), dict)
                or registro.get("conhecimento_permanente") is not False
                or registro.get("gravado") is not True
            ):
                self._erro_carregamento = "registro_memoria_invalido"
                return self._estrutura_vazia()
        return {"versao": VERSAO_MEMORIA, "registros": copy.deepcopy(registros)}


    @staticmethod
    def _id_registro(candidato: dict[str, Any]) -> str:
        canonico = json.dumps(
            candidato,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _validar_candidato(
        candidato: Any,
    ) -> tuple[bool, str | None]:
        if not isinstance(candidato, dict):
            return False, "Candidato precisa ser um objeto."

        texto = candidato.get("texto")
        tipo = candidato.get("tipo")
        origem = candidato.get("origem")

        if not isinstance(texto, str) or not texto.strip():
            return False, "Texto do candidato inválido."

        if not isinstance(tipo, str) or not tipo.strip():
            return False, "Tipo do candidato inválido."

        if not isinstance(origem, dict):
            return False, "Origem do candidato inválida."

        if origem.get("estado") != "suportada":
            return (
                False,
                "Somente candidatos provenientes de uma "
                "avaliação suportada podem ser persistidos.",
            )

        if candidato.get("conhecimento_permanente") is not False:
            return (
                False,
                "O candidato não pode marcar conhecimento "
                "permanente como verdadeiro.",
            )

        if candidato.get("gravado") is not False:
            return (
                False,
                "O candidato de entrada precisa estar marcado "
                "como não gravado.",
            )

        return True, None

    def registrar(
        self,
        candidato: dict[str, Any],
    ) -> dict[str, Any]:
        valido, erro = self._validar_candidato(candidato)
        if not valido:
            return self._negado(erro or "Candidato inválido.")
        candidato_copia = copy.deepcopy(candidato)
        registro_id = self._id_registro(candidato_copia)

        try:
            with self._bloquear_escrita():
                self._dados = self._carregar()
                if self._erro_carregamento is not None:
                    return self._negado(
                        f"memoria_degradada:{self._erro_carregamento}; arquivo original preservado."
                    )
                for registro in self._dados["registros"]:
                    if registro.get("registro_id") == registro_id:
                        return {
                            "sucesso": True,
                            "estado": "ja_existente",
                            "origem": self.FONTE,
                            "valor": copy.deepcopy(registro),
                            "conhecimento_permanente": False,
                            "arquitetura_modificada": False,
                        }
                registro = {
                    "registro_id": registro_id,
                    "candidato": candidato_copia,
                    "conhecimento_permanente": False,
                    "gravado": True,
                }
                self._dados["registros"].append(registro)
                try:
                    self._salvar()
                except OSError as erro:
                    self._dados = self._carregar()
                    if str(erro) == "memoria_excede_limite_tamanho":
                        return self._negado(
                            f"memoria_excede_limite_tamanho:{MAX_MEMORIA_JSON_BYTES}; arquivo anterior preservado."
                        )
                    return self._negado(
                        "falha_persistencia; arquivo anterior preservado quando possível."
                    )
        except OSError as erro:
            caminho_inseguro = (
                _tem_ancestral_simbolico(self.caminho)
                or _tem_ancestral_simbolico(self.caminho.with_name(self.caminho.name + ".lock"))
                or "link_simbolico" in str(erro)
            )
            motivo = "caminho_memoria_nao_seguro" if caminho_inseguro else "persistencia_indisponivel"
            self._erro_carregamento = motivo
            self._dados = self._estrutura_vazia()
            return self._negado(
                f"memoria_degradada:{motivo}; arquivo original preservado."
            )
        return {
            "sucesso": True,
            "estado": "persistido",
            "origem": self.FONTE,
            "valor": copy.deepcopy(registro),
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def listar(self) -> list[dict[str, Any]]:
        return copy.deepcopy(
            self._dados.get("registros", [])
        )

    def quantidade(self) -> int:
        return len(
            self._dados.get("registros", [])
        )

    def obter(
        self,
        registro_id: str,
    ) -> dict[str, Any] | None:
        for registro in self._dados.get("registros", []):
            if (
                isinstance(registro, dict)
                and registro.get("registro_id") == registro_id
            ):
                return copy.deepcopy(registro)
        return None

    def recarregar(self) -> dict[str, Any]:
        self._dados = self._carregar()
        if self._erro_carregamento is not None:
            return {
                "sucesso": False, "estado": "memoria_degradada",
                "origem": self.FONTE, "motivo": self._erro_carregamento,
                "arquivo_original_preservado": True, "valor": {"quantidade": 0},
            }
        return {
            "sucesso": True, "estado": "recarregado",
            "origem": self.FONTE, "valor": {"quantidade": self.quantidade()},
        }


    @staticmethod
    def _negado(motivo: str) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "memoria_conhecimento_nixal",
            "valor": None,
            "motivo": motivo,
            "conhecimento_permanente": False,
            "arquitetura_modificada": False,
        }

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória de candidatos não promove "
            "conhecimento permanente."
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória de candidatos não modifica a arquitetura."
        )

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória de candidatos não executa capacidades."
        )

    @contextmanager
    def _bloquear_escrita(self):
        lock_path = self.caminho.with_name(self.caminho.name + ".lock")
        if _tem_ancestral_simbolico(self.caminho) or _tem_ancestral_simbolico(lock_path):
            raise OSError("caminho_memoria_com_link_simbolico")

        self.caminho.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if _tem_ancestral_simbolico(self.caminho) or _tem_ancestral_simbolico(lock_path):
            raise OSError("caminho_memoria_com_link_simbolico")

        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        lock_fd = os.open(lock_path, flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                raise OSError("arquivo_lock_memoria_nao_regular")
            os.fchmod(lock_fd, 0o600)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                if _tem_ancestral_simbolico(self.caminho):
                    raise OSError("caminho_memoria_com_link_simbolico")
                yield
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)

    def _salvar(self) -> None:
        if _tem_ancestral_simbolico(self.caminho):
            raise OSError("caminho_memoria_com_link_simbolico")
        self.caminho.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if _tem_ancestral_simbolico(self.caminho):
            raise OSError("caminho_memoria_com_link_simbolico")

        texto = json.dumps(self._dados, ensure_ascii=False, indent=2)
        if len(texto.encode("utf-8")) > MAX_MEMORIA_JSON_BYTES:
            raise OSError("memoria_excede_limite_tamanho")
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.caminho.name}.", suffix=".tmp", dir=str(self.caminho.parent)
        )
        try:
            os.fchmod(temp_fd, 0o600)
            with os.fdopen(temp_fd, "w", encoding="utf-8") as arquivo:
                temp_fd = -1
                arquivo.write(texto)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            if _tem_ancestral_simbolico(self.caminho):
                raise OSError("caminho_memoria_com_link_simbolico")
            os.replace(temp_name, self.caminho)
            if _tem_ancestral_simbolico(self.caminho.parent):
                raise OSError("caminho_memoria_com_link_simbolico")
            dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
            dir_fd = os.open(self.caminho.parent, dir_flags)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            if temp_fd >= 0:
                os.close(temp_fd)
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
