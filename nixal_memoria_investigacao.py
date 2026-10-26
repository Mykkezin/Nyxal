#!/usr/bin/env python3

"""
NIXAL — MEMÓRIA PERSISTENTE DE INVESTIGAÇÃO

Microetapa 56.4.15

Responsabilidade:
    Persistir investigações, evidências, hipóteses, testes e
    avaliações em memória durável.

Princípios:
1. A memória é separada da planta arquitetural.
2. A memória pode registrar experiências explicitamente.
3. Um registro persistido não altera a planta.
4. O registro preserva o ciclo completo recebido.
5. Registros duplicados não são gravados novamente.
6. A identidade do registro é determinística.
7. A memória não executa capacidades.
8. A memória não modifica a arquitetura.
9. Um registro salvo não vira automaticamente conhecimento permanente.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any


VERSAO_MEMORIA = "56.4.15"
MAX_MEMORIA_JSON_BYTES = 32 * 1024 * 1024
MAX_REGISTROS_LEITURA_RECENTE = 5000

ARQUIVO_MEMORIA_PADRAO = (
    Path(__file__).resolve().parent
    / "memoria_investigacao_nixal.json"
)


class MemoriaInvestigacaoNixal:
    """Armazenamento persistente de ciclos de investigação."""

    FONTE = "memoria_investigacao_nixal"

    def __init__(
        self,
        caminho: Path = ARQUIVO_MEMORIA_PADRAO,
    ) -> None:
        self.caminho = Path(caminho)
        self._erro_carregamento: str | None = None
        self._dados = self._carregar()

    # ============================================================
    # CARREGAMENTO
    # ============================================================

    def _carregar(self) -> dict[str, Any]:
        """Carrega um arquivo íntegro; corrupção nunca vira memória vazia gravável."""
        self._erro_carregamento = None
        if not self.caminho.exists():
            return self._estrutura_vazia()
        try:
            with self.caminho.open("rb") as arquivo:
                bruto = arquivo.read(MAX_MEMORIA_JSON_BYTES + 1)
        except OSError:
            self._erro_carregamento = "arquivo_ilegivel_ou_json_corrompido"
            return self._estrutura_vazia()

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
            if not isinstance(registro, dict) or not isinstance(registro.get("id"), str) or not isinstance(registro.get("ciclo"), dict):
                self._erro_carregamento = "registro_memoria_invalido"
                return self._estrutura_vazia()
        return {"versao": VERSAO_MEMORIA, "registros": copy.deepcopy(registros)}


    @staticmethod
    def _estrutura_vazia() -> dict[str, Any]:
        return {
            "versao": VERSAO_MEMORIA,
            "registros": [],
        }

    # ============================================================
    # IDENTIDADE DO REGISTRO
    # ============================================================

    @staticmethod
    def _id_registro(
        ciclo: dict[str, Any],
    ) -> str:
        canonico = json.dumps(
            ciclo,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        return hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()

    # ============================================================
    # VALIDAÇÃO
    # ============================================================

    @staticmethod
    def _validar_ciclo(
        ciclo: Any,
    ) -> tuple[bool, str | None]:
        if not isinstance(
            ciclo,
            dict,
        ):
            return False, "Ciclo precisa ser um objeto."

        obrigatorios = (
            "hipotese",
            "estado_atual",
            "historico",
            "testes",
            "avaliacoes",
            "conhecimento_permanente",
        )

        for campo in obrigatorios:
            if campo not in ciclo:
                return (
                    False,
                    f"Campo obrigatório ausente: {campo}",
                )

        if not isinstance(
            ciclo.get("hipotese"),
            str,
        ) or not ciclo.get(
            "hipotese",
            "",
        ).strip():
            return False, "Texto da hipótese inválido."

        if not isinstance(
            ciclo.get("estado_atual"),
            str,
        ):
            return False, "Estado atual inválido."

        if not isinstance(
            ciclo.get("historico"),
            list,
        ):
            return False, "Histórico inválido."

        if not isinstance(
            ciclo.get("testes"),
            list,
        ):
            return False, "Lista de testes inválida."

        if not isinstance(
            ciclo.get("avaliacoes"),
            list,
        ):
            return False, "Lista de avaliações inválida."

        if ciclo.get(
            "conhecimento_permanente"
        ) is not False:
            return (
                False,
                "Memória de investigação não pode marcar "
                "conhecimento permanente como verdadeiro.",
            )

        return True, None

    # ============================================================
    # REGISTRO
    # ============================================================

    def registrar(self, ciclo: dict[str, Any]) -> dict[str, Any]:
        valido, erro = self._validar_ciclo(ciclo)
        if not valido:
            return self._negado(erro or "Ciclo inválido.")
        ciclo_copia = copy.deepcopy(ciclo)
        registro_id = self._id_registro(ciclo_copia)

        # Refresh under an inter-process lock to prevent stale instances overwriting each other.
        with self._bloquear_escrita():
            self._dados = self._carregar()
            if self._erro_carregamento is not None:
                return self._negado(
                    f"memoria_degradada:{self._erro_carregamento}; arquivo original preservado."
                )
            for registro in self._dados["registros"]:
                if registro.get("id") == registro_id:
                    return {
                        "sucesso": True, "estado": "ja_existente",
                        "origem": self.FONTE, "valor": copy.deepcopy(registro),
                    }
            registro = {
                "id": registro_id,
                "versao_memoria": VERSAO_MEMORIA,
                "ciclo": ciclo_copia,
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
        return {
            "sucesso": True, "estado": "persistido",
            "origem": self.FONTE, "valor": copy.deepcopy(registro),
        }


    # ============================================================
    # LEITURA
    # ============================================================

    def listar(
        self,
    ) -> list[dict[str, Any]]:
        """Retorna cópia completa para manter compatibilidade com consumidores existentes."""
        return copy.deepcopy(
            self._dados.get(
                "registros",
                [],
            )
        )

    def listar_recent(
        self,
        limite: int = 500,
    ) -> list[dict[str, Any]]:
        """Copia apenas o sufixo recente, sem duplicar toda a memória em RAM."""
        if (
            isinstance(limite, bool)
            or not isinstance(limite, int)
            or not 1 <= limite <= MAX_REGISTROS_LEITURA_RECENTE
        ):
            raise ValueError(
                "limite precisa ser inteiro entre 1 e "
                f"{MAX_REGISTROS_LEITURA_RECENTE}."
            )
        registros = self._dados.get("registros", [])
        return copy.deepcopy(registros[-limite:])

    def quantidade(self) -> int:
        return len(
            self._dados.get(
                "registros",
                [],
            )
        )

    def obter(
        self,
        registro_id: str,
    ) -> dict[str, Any] | None:
        for registro in self._dados.get(
            "registros",
            [],
        ):
            if (
                isinstance(
                    registro,
                    dict,
                )
                and registro.get("id")
                == registro_id
            ):
                return copy.deepcopy(
                    registro
                )

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


    # ============================================================
    # PROTEÇÕES
    # ============================================================

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória não executa capacidades."
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "A memória não modifica a arquitetura."
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._negado(
            "Persistência de investigação não promove "
            "conhecimento permanente."
        )

    # ============================================================
    # PERSISTÊNCIA ATÔMICA
    # ============================================================

    @contextmanager
    def _bloquear_escrita(self):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.caminho.with_name(self.caminho.name + ".lock")
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(lock_fd, 0o600)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    def _salvar(self) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
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
            os.replace(temp_name, self.caminho)
            dir_fd = os.open(self.caminho.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
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


    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "memoria_investigacao_nixal",
            "valor": None,
            "motivo": motivo,
        }


def main() -> None:
    memoria = MemoriaInvestigacaoNixal()

    exemplo = {
        "hipotese": (
            "Exemplo de hipótese persistível."
        ),
        "estado_atual": "provisoria",
        "historico": [
            {
                "de": None,
                "para": "provisoria",
                "evento": "hipotese_criada",
            }
        ],
        "testes": [],
        "avaliacoes": [],
        "conhecimento_permanente": False,
    }

    print("=" * 60)
    print("NIXAL — MEMÓRIA DE INVESTIGAÇÃO 56.4.15")
    print("=" * 60)
    print()
    print(
        memoria.registrar(
            exemplo
        )
    )
    print()
    print(
        "Registros:",
        memoria.quantidade(),
    )


if __name__ == "__main__":
    main()
