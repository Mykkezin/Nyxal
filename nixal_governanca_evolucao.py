#!/usr/bin/env python3
"""
NYXAL — GOVERNANÇA FINAL DA EVOLUÇÃO

Nível 9 / M4 — última camada de governança entre proposta,
integração preparada e mudança efetivamente registrada em stable.

Princípio:
    proposta → autorização explícita → preparação → revisão externa
        → integração registrada → (opcional) rollback registrado

Este módulo NÃO:
- executa código candidato;
- faz merge em stable;
- concede autorização automaticamente;
- altera stable por conta própria.

A autorização é um registro explícito fornecido pelo chamador humano.
A integração só é considerada concluída quando um merge commit real é
verificado como ancestral de stable. Rollback também é apenas registrado
depois de o commit de rollback já existir em stable.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nixal_integracao_controlada import (
    IntegracaoControladaDesenvolvimentoNixal,
)
from nixal_proposta_integracao import (
    PropostaIntegracaoDesenvolvimentoNixal,
)


class GovernancaEvolucaoNixal:
    VERSAO = "9.5.0"
    FONTE = "governanca_evolucao_nixal"

    ESTADOS = {
        "aguardando_autorizacao",
        "autorizada",
        "integracao_preparada",
        "integrada",
        "rollback_registrado",
        "rejeitada",
    }

    TRANSICOES = {
        "aguardando_autorizacao": {"autorizada", "rejeitada"},
        "autorizada": {"integracao_preparada", "rejeitada"},
        "integracao_preparada": {"integrada", "rejeitada"},
        "integrada": {"rollback_registrado"},
        "rollback_registrado": set(),
        "rejeitada": set(),
    }

    SHA_RE = re.compile(r"^[0-9a-f]{40}$")

    def __init__(
        self,
        *,
        repositorio: str | Path,
        governanca: str | Path | None = None,
        integrador: IntegracaoControladaDesenvolvimentoNixal | None = None,
    ) -> None:
        self.repositorio = Path(repositorio).resolve()
        self.governanca = Path(
            governanca
            or self.repositorio.parent / "Nyxal-evolution-governance"
        ).resolve()
        self.governanca.mkdir(parents=True, exist_ok=True)
        self.propostas = self.repositorio.parent / "Nyxal-integration-proposals"
        self.autorizacoes = self.repositorio.parent / "Nyxal-integration-authorizations"
        self.propostas.mkdir(parents=True, exist_ok=True)
        self.autorizacoes.mkdir(parents=True, exist_ok=True)
        self.integrador = integrador or IntegracaoControladaDesenvolvimentoNixal(
            repositorio=self.repositorio,
            propostas=self.propostas,
            autorizacoes=self.autorizacoes,
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _hash_arquivo(caminho: Path) -> str:
        digest = hashlib.sha256()
        with caminho.open("rb") as arquivo:
            for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
                digest.update(bloco)
        return digest.hexdigest()

    @staticmethod
    def _texto(valor: Any, nome: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    @classmethod
    def _validar_sha(cls, valor: Any, nome: str) -> str:
        texto = cls._texto(valor, nome).lower()
        if not cls.SHA_RE.fullmatch(texto):
            raise ValueError(f"{nome}_invalido")
        return texto

    def _git(self, *args: str) -> str:
        resultado = subprocess.run(
            ["git", *args],
            cwd=self.repositorio,
            text=True,
            capture_output=True,
            check=False,
        )
        if resultado.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} falhou: "
                f"{resultado.stderr.strip()}"
            )
        return resultado.stdout.strip()

    def _caminho(self, proposta_id: str) -> Path:
        return self.governanca / f"{proposta_id}.json"

    def _caminho_autorizacao(self, proposta_id: str) -> Path:
        return self.autorizacoes / f"{proposta_id}.json"

    def _caminho_proposta_formal(self, proposta_id: str) -> Path:
        return self.propostas / f"{proposta_id}.json"

    def _carregar(self, proposta_id: str) -> dict[str, Any]:
        caminho = self._caminho(proposta_id)
        if not caminho.is_file():
            raise FileNotFoundError(
                "registro_governanca_nao_encontrado"
            )
        try:
            registro = json.loads(
                caminho.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError("registro_governanca_invalido") from erro
        self._validar_registro(registro)
        return registro

    def _salvar(self, registro: dict[str, Any]) -> None:
        proposta_id = self._texto(
            registro.get("proposta_id"),
            "proposta_id",
        )
        caminho = self._caminho(proposta_id)
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(
            json.dumps(
                registro,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporario.replace(caminho)

    @classmethod
    def _transicionar(
        cls,
        registro: dict[str, Any],
        novo_estado: str,
        *,
        evento: str,
    ) -> None:
        estado_atual = registro.get("estado")
        if estado_atual not in cls.ESTADOS:
            raise ValueError("estado_governanca_invalido")
        if novo_estado not in cls.ESTADOS:
            raise ValueError("novo_estado_governanca_invalido")
        if novo_estado not in cls.TRANSICOES[estado_atual]:
            raise ValueError(
                f"transicao_governanca_nao_permitida:"
                f"{estado_atual}->{novo_estado}"
            )

        agora = cls._timestamp()
        historico = registro.setdefault("historico_estados", [])
        if not isinstance(historico, list):
            raise ValueError("historico_governanca_invalido")

        historico.append(
            {
                "de": estado_atual,
                "para": novo_estado,
                "evento": cls._texto(evento, "evento"),
                "em": agora,
            }
        )
        registro["estado_anterior"] = estado_atual
        registro["estado"] = novo_estado
        registro["estado_atualizado_em"] = agora

    @classmethod
    def _validar_registro(cls, registro: dict[str, Any]) -> None:
        if not isinstance(registro, dict):
            raise ValueError("registro_governanca_invalido")

        estado = registro.get("estado")
        if estado not in cls.ESTADOS:
            raise ValueError("estado_governanca_invalido")

        historico = registro.get("historico_estados")
        if not isinstance(historico, list) or not historico:
            raise ValueError("historico_governanca_invalido")

        caminho = None
        for indice, transicao in enumerate(historico):
            if not isinstance(transicao, dict):
                raise ValueError(
                    f"historico_governanca_invalido:{indice}"
                )
            de = transicao.get("de")
            para = transicao.get("para")

            if para not in cls.ESTADOS:
                raise ValueError(
                    f"historico_estado_destino_invalido:{indice}"
                )

            if indice == 0:
                if de is not None:
                    raise ValueError(
                        "historico_governanca_primeira_origem_invalida"
                    )
            elif de != caminho:
                raise ValueError(
                    f"historico_governanca_desconectado:{indice}"
                )

            permitidos = (
                cls.ESTADOS
                if de is None
                else cls.TRANSICOES.get(de, set())
            )
            if para not in permitidos:
                raise ValueError(
                    f"historico_governanca_transicao_invalida:{indice}"
                )

            caminho = para

        if caminho != estado:
            raise ValueError("historico_governanca_final_inconsistente")

        if registro.get("estado_anterior") != historico[-1].get("de"):
            raise ValueError("estado_anterior_governanca_inconsistente")

        autorizacao = registro.get("autorizacao")
        if estado in {
            "autorizada",
            "integracao_preparada",
            "integrada",
            "rollback_registrado",
        }:
            if not isinstance(autorizacao, dict):
                raise ValueError("autorizacao_ausente")
            if autorizacao.get("autorizacao_explicita") is not True:
                raise ValueError("autorizacao_explicita_ausente")

        if registro.get("integracao_executada") is True and estado not in {
            "integrada",
            "rollback_registrado",
        }:
            raise ValueError("integracao_fora_de_estado_final")

    @staticmethod
    def _autorizacao_id(
        proposta_id: str,
        autorizador: str,
        motivo: str,
        timestamp: str,
    ) -> str:
        base = "|".join(
            [proposta_id, autorizador, motivo, timestamp]
        )
        return (
            "auth-"
            + hashlib.sha256(base.encode("utf-8")).hexdigest()[:20]
        )

    def autorizar_proposta(
        self,
        *,
        proposta_path: str | Path,
        autorizador: str,
        motivo: str,
    ) -> dict[str, Any]:
        proposta_path = Path(proposta_path).resolve()
        if not proposta_path.is_file():
            raise FileNotFoundError("proposta_nao_encontrada")

        try:
            proposta = json.loads(
                proposta_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError("proposta_invalida") from erro

        if not isinstance(proposta, dict):
            raise ValueError("proposta_invalida")

        proposta_id = self._texto(
            proposta.get("proposta_id"),
            "proposta_id",
        )
        proposta_sha256 = self._hash_arquivo(proposta_path)

        existente = self._caminho(proposta_id)
        if existente.exists():
            registro = self._carregar(proposta_id)
            if registro["estado"] != "aguardando_autorizacao":
                raise ValueError("proposta_ja_processada")
            hash_registrado = registro.get("proposta_sha256")
            if (
                isinstance(hash_registrado, str)
                and hash_registrado
                and hash_registrado != proposta_sha256
            ):
                raise ValueError("proposta_alterada_antes_da_autorizacao")
            registro["proposta_sha256"] = proposta_sha256
        else:
            timestamp = self._timestamp()
            registro = {
                "versao": self.VERSAO,
                "fonte": self.FONTE,
                "proposta_id": proposta_id,
                "criado_em": timestamp,
                "estado": "aguardando_autorizacao",
                "estado_anterior": None,
                "historico_estados": [
                    {
                        "de": None,
                        "para": "aguardando_autorizacao",
                        "evento": "governanca_criada",
                        "em": timestamp,
                    }
                ],
                "autorizacao": None,
                "integracao": None,
                "rollback": None,
                "integracao_executada": False,
                "stable_modificada": False,
                "proposta_sha256": proposta_sha256,
            }
            self._salvar(registro)

        autorizador = self._texto(
            autorizador,
            "autorizador",
        )
        motivo = self._texto(
            motivo,
            "motivo_autorizacao",
        )

        try:
            proposta_formal = json.loads(
                proposta_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError("proposta_invalida") from erro

        if not isinstance(proposta_formal, dict):
            raise ValueError("proposta_invalida")

        fingerprint = self._texto(
            proposta_formal.get("fingerprint"),
            "fingerprint_da_proposta",
        )
        destino = self._texto(
            proposta_formal.get("destino_sugerido"),
            "destino_da_proposta",
        )

        caminho_formal = self._caminho_proposta_formal(proposta_id)
        if caminho_formal.resolve() != proposta_path.resolve():
            caminho_formal.write_text(
                proposta_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

        agora = self._timestamp()
        autorizacao_id = self._autorizacao_id(
            proposta_id,
            autorizador,
            motivo,
            agora,
        )
        registro_autorizacao = {
            "autorizacao_id": autorizacao_id,
            "proposta_id": proposta_id,
            "autorizador": autorizador,
            "motivo": motivo,
            "fingerprint": fingerprint,
            "destino": destino,
            "confirmacao_explicita": "AUTORIZAR_INTEGRACAO",
            "origem": "governanca_externa",
            "registrada_em": agora,
        }
        self._caminho_autorizacao(proposta_id).write_text(
            json.dumps(
                registro_autorizacao,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        registro["autorizacao"] = {
            "autorizacao_id": autorizacao_id,
            "autorizacao_explicita": True,
            "autorizado_por": autorizador,
            "motivo": motivo,
            "autorizado_em": agora,
            "proposta_path": str(proposta_path),
            "autorizacao_path": str(self._caminho_autorizacao(proposta_id)),
        }
        self._transicionar(
            registro,
            "autorizada",
            evento="autorizacao_explicita_registrada",
        )
        self._salvar(registro)
        return copy.deepcopy(registro)

    def preparar_integracao(
        self,
        *,
        proposta_path: str | Path,
        branch_integracao: str | None = None,
    ) -> dict[str, Any]:
        proposta_path = Path(proposta_path).resolve()
        try:
            proposta = json.loads(
                proposta_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError("proposta_invalida") from erro

        proposta_id = self._texto(
            proposta.get("proposta_id"),
            "proposta_id",
        )
        try:
            registro = self._carregar(proposta_id)
        except FileNotFoundError as erro:
            if str(erro) == "registro_governanca_nao_encontrado":
                raise ValueError("autorizacao_nao_registrada") from erro
            raise

        proposta_sha256 = registro.get("proposta_sha256")
        if not isinstance(proposta_sha256, str) or not proposta_sha256:
            raise ValueError("hash_da_proposta_ausente")
        if self._hash_arquivo(proposta_path) != proposta_sha256:
            raise ValueError("proposta_alterada_apos_autorizacao")

        if proposta.get("estado") != "aguardando_autorizacao":
            raise ValueError("estado_da_proposta_invalido")
        if proposta.get("autorizacao_explicita") is not False:
            raise ValueError("autorizacao_da_proposta_invalida")
        if proposta.get("integracao_executada") is not False:
            raise ValueError("integracao_da_proposta_invalida")
        if proposta.get("stable_modificada") is not False:
            raise ValueError("stable_da_proposta_invalida")

        if registro["estado"] != "autorizada":
            raise ValueError("autorizacao_nao_registrada")

        if registro["autorizacao"]["autorizacao_explicita"] is not True:
            raise PermissionError(
                "autorizacao_explicita_obrigatoria"
            )

        baseline_commit = self._git("rev-parse", "main")

        caminho_autorizacao = self._caminho_autorizacao(proposta_id)
        if not caminho_autorizacao.is_file():
            raise ValueError("autorizacao_nao_registrada")

        resultado = self.integrador.preparar(
            proposta_id=proposta_id,
            caminho_autorizacao=caminho_autorizacao,
            stable="main",
            branch_integracao=branch_integracao,
        )

        registro["integracao"] = {
            "baseline_commit": self._validar_sha(
                baseline_commit,
                "baseline_commit",
            ),
            "branch_integracao": resultado["branch_integracao"],
            "commit_integracao": self._validar_sha(
                resultado["commit_integracao"],
                "commit_integracao",
            ),
            "arquivo_integrado": resultado["arquivo_integrado"],
            "preparada_em": self._timestamp(),
        }
        registro["integracao_executada"] = False
        registro["stable_modificada"] = False

        self._transicionar(
            registro,
            "integracao_preparada",
            evento="integracao_preparada_com_autorizacao",
        )
        self._salvar(registro)

        return {
            "governanca": copy.deepcopy(registro),
            "integracao": copy.deepcopy(resultado),
            "stable_modificada": False,
            "integracao_executada": False,
        }

    def registrar_integracao(
        self,
        *,
        proposta_id: str,
        merge_commit: str,
        stable: str = "main",
    ) -> dict[str, Any]:
        proposta_id = self._texto(
            proposta_id,
            "proposta_id",
        )
        merge_commit = self._validar_sha(
            merge_commit,
            "merge_commit",
        )
        stable = self._texto(stable, "stable")

        if stable != "main":
            raise ValueError("branch_stable_nao_permitida")

        registro = self._carregar(proposta_id)
        if registro["estado"] != "integracao_preparada":
            raise ValueError("integracao_nao_preparada")

        branch = registro["integracao"].get("branch_integracao")
        if not isinstance(branch, str) or not branch:
            raise ValueError("branch_integracao_invalida")

        # Não faz merge. Apenas verifica que o merge já existe em stable.
        self._git("merge-base", "--is-ancestor", merge_commit, stable)

        registro["integracao"]["merge_commit"] = merge_commit
        registro["integracao"]["registrada_em"] = self._timestamp()
        registro["integracao"]["stable"] = stable
        registro["integracao_executada"] = True
        registro["stable_modificada"] = True

        self._transicionar(
            registro,
            "integrada",
            evento="integracao_em_stable_registrada",
        )
        self._salvar(registro)
        return copy.deepcopy(registro)

    def registrar_rollback(
        self,
        *,
        proposta_id: str,
        rollback_commit: str,
        motivo: str,
        stable: str = "main",
    ) -> dict[str, Any]:
        proposta_id = self._texto(
            proposta_id,
            "proposta_id",
        )
        rollback_commit = self._validar_sha(
            rollback_commit,
            "rollback_commit",
        )
        motivo = self._texto(motivo, "motivo_rollback")
        stable = self._texto(stable, "stable")

        if stable != "main":
            raise ValueError("branch_stable_nao_permitida")

        registro = self._carregar(proposta_id)
        if registro["estado"] != "integrada":
            raise ValueError("rollback_so_apos_integracao")

        self._git("merge-base", "--is-ancestor", rollback_commit, stable)

        registro["rollback"] = {
            "rollback_commit": rollback_commit,
            "motivo": motivo,
            "stable": stable,
            "registrado_em": self._timestamp(),
        }
        registro["stable_modificada"] = True

        self._transicionar(
            registro,
            "rollback_registrado",
            evento="rollback_em_stable_registrado",
        )
        self._salvar(registro)
        return copy.deepcopy(registro)

    def consultar(
        self,
        proposta_id: str,
    ) -> dict[str, Any]:
        return copy.deepcopy(
            self._carregar(
                self._texto(proposta_id, "proposta_id")
            )
        )


__all__ = ["GovernancaEvolucaoNixal"]


if __name__ == "__main__":
    print("GovernancaEvolucaoNixal OK")
