#!/usr/bin/env python3
"""
NYXAL — PROPOSTA DE INTEGRAÇÃO CONTROLADA

Mantém a proposta separada do candidato e da árvore Git.

A proposta nasce aguardando autorização e só pode avançar por uma
autorização externa e explícita. A mudança para stable é responsabilidade
do integrador controlado, nunca da criação da proposta.

Estados:
    aguardando_autorizacao
        -> autorizada_para_integracao
        -> integracao_em_execucao
        -> integrada | integracao_falhou
"""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PropostaIntegracaoDesenvolvimentoNixal:
    VERSAO = 2

    ESTADOS = {
        "aguardando_autorizacao",
        "autorizada_para_integracao",
        "integracao_em_execucao",
        "integrada",
        "integracao_falhou",
    }

    TRANSICOES = {
        "aguardando_autorizacao": {"autorizada_para_integracao"},
        "autorizada_para_integracao": {"integracao_em_execucao"},
        "integracao_em_execucao": {"integrada", "integracao_falhou"},
        "integrada": set(),
        "integracao_falhou": set(),
    }

    def __init__(
        self,
        repositorio: str | Path | None = None,
        propostas: str | Path | None = None,
    ) -> None:
        self.repositorio = Path(
            repositorio or Path(__file__).resolve().parent
        )

        base_externa = self.repositorio.parent

        self.propostas = Path(
            propostas
            or base_externa
            / "Nyxal-integration-proposals"
        )

        self.propostas.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _texto(valor: Any, nome: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    def _timestamp(self) -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _caminho(self, proposta_id: str) -> Path:
        return self.propostas / f"{self._texto(proposta_id, 'proposta_id')}.json"

    def _carregar(self, proposta_id: str) -> dict[str, Any]:
        caminho = self._caminho(proposta_id)

        if not caminho.is_file():
            raise FileNotFoundError(
                "proposta_nao_encontrada"
            )

        try:
            dados = json.loads(
                caminho.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError(
                "proposta_invalida"
            ) from erro

        if not isinstance(dados, dict):
            raise ValueError("proposta_invalida")

        estado = dados.get("estado")
        if estado not in self.ESTADOS:
            raise ValueError("estado_da_proposta_invalido")

        return dados

    def _salvar(self, proposta: dict[str, Any]) -> None:
        proposta_id = self._texto(
            proposta.get("proposta_id"),
            "proposta_id",
        )
        caminho = self._caminho(proposta_id)
        temporario = caminho.with_name(
            caminho.name + ".tmp"
        )
        temporario.write_text(
            json.dumps(
                proposta,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(
            temporario,
            caminho,
        )

    def _transicionar(
        self,
        proposta: dict[str, Any],
        novo_estado: str,
        *,
        evento: str,
    ) -> None:
        estado_atual = proposta.get("estado")

        if estado_atual not in self.ESTADOS:
            raise ValueError("estado_da_proposta_invalido")

        if novo_estado not in self.ESTADOS:
            raise ValueError("novo_estado_invalido")

        if novo_estado not in self.TRANSICOES.get(
            estado_atual,
            set(),
        ):
            raise ValueError(
                "transicao_proposta_nao_permitida:"
                f"{estado_atual}->{novo_estado}"
            )

        evento = self._texto(evento, "evento")
        agora = self._timestamp()

        historico = proposta.setdefault(
            "historico_estados",
            [],
        )
        if not isinstance(historico, list):
            raise ValueError("historico_estados_invalido")

        historico.append(
            {
                "de": estado_atual,
                "para": novo_estado,
                "evento": evento,
                "em": agora,
            }
        )

        proposta["estado_anterior"] = estado_atual
        proposta["estado"] = novo_estado
        proposta["estado_atualizado_em"] = agora

    def criar(
        self,
        *,
        candidato_dir: str | Path,
        destino: str = "main",
    ) -> dict[str, Any]:
        origem = Path(candidato_dir)

        if not origem.exists():
            raise FileNotFoundError(
                "candidato_nao_encontrado"
            )

        registro_path = origem / "candidato.json"

        if not registro_path.exists():
            raise FileNotFoundError(
                "registro_do_candidato_nao_encontrado"
            )

        try:
            registro = json.loads(
                registro_path.read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError) as erro:
            raise ValueError(
                "registro_do_candidato_invalido"
            ) from erro

        if registro.get("estado") != "candidato":
            raise ValueError(
                "estado_do_candidato_invalido"
            )

        avaliacao = registro.get("avaliacao", {})
        if not isinstance(avaliacao, dict):
            raise ValueError("avaliacao_do_candidato_invalida")

        if avaliacao.get("aprovado") is not True:
            raise ValueError(
                "candidato_sem_avaliacao_aprovada"
            )

        candidato_id = registro.get("candidato_id")
        if not isinstance(candidato_id, str) or not candidato_id:
            raise ValueError("candidato_id_invalido")

        destino = self._texto(destino, "destino")
        proposta_id = f"integracao-{candidato_id}"
        caminho = self._caminho(proposta_id)

        if caminho.exists():
            raise FileExistsError(
                "proposta_ja_existente"
            )

        criada_em = self._timestamp()

        proposta = {
            "versao_proposta": self.VERSAO,
            "proposta_id": proposta_id,
            "estado": "aguardando_autorizacao",
            "estado_anterior": None,
            "historico_estados": [
                {
                    "de": None,
                    "para": "aguardando_autorizacao",
                    "evento": "proposta_criada",
                    "em": criada_em,
                }
            ],
            "criada_em": criada_em,
            "candidato_id": candidato_id,
            "candidato_dir": str(origem.resolve()),
            "arquivo": registro.get("arquivo"),
            "manifesto": registro.get("manifesto"),
            "fingerprint": registro.get("fingerprint"),
            "avaliacao": avaliacao,
            "destino_sugerido": destino,
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
        }

        self._salvar(proposta)
        proposta["arquivo_proposta"] = str(caminho)

        return copy.deepcopy(proposta)

    def consultar(
        self,
        proposta_id: str,
    ) -> dict[str, Any]:
        return copy.deepcopy(
            self._carregar(proposta_id)
        )

    def registrar_autorizacao(
        self,
        proposta_id: str,
        autorizacao: dict[str, Any],
    ) -> dict[str, Any]:
        proposta = self._carregar(proposta_id)

        if proposta.get("estado") != "aguardando_autorizacao":
            raise ValueError(
                "proposta_nao_aguardando_autorizacao"
            )

        if not isinstance(autorizacao, dict):
            raise ValueError("autorizacao_invalida")

        autorizacao_id = self._texto(
            autorizacao.get("autorizacao_id"),
            "autorizacao_id",
        )
        autorizador = self._texto(
            autorizacao.get("autorizador"),
            "autorizador",
        )
        motivo = self._texto(
            autorizacao.get("motivo"),
            "motivo_autorizacao",
        )
        proposta_autorizada = self._texto(
            autorizacao.get("proposta_id"),
            "proposta_id",
        )
        fingerprint = self._texto(
            autorizacao.get("fingerprint"),
            "fingerprint_autorizacao",
        )
        destino = self._texto(
            autorizacao.get("destino"),
            "destino_autorizacao",
        )
        confirmacao = self._texto(
            autorizacao.get("confirmacao_explicita"),
            "confirmacao_explicita",
        )

        if proposta_autorizada != proposta_id:
            raise ValueError("proposta_autorizada_inconsistente")

        if fingerprint != proposta.get("fingerprint"):
            raise ValueError("fingerprint_autorizacao_inconsistente")

        if destino != proposta.get("destino_sugerido"):
            raise ValueError("destino_autorizacao_inconsistente")

        if confirmacao != "AUTORIZAR_INTEGRACAO":
            raise ValueError("confirmacao_explicita_invalida")

        origem = autorizacao.get(
            "origem",
            "autorizacao_externa",
        )
        origem = self._texto(
            origem,
            "origem_autorizacao",
        )

        registro_autorizacao = {
            "autorizacao_id": autorizacao_id,
            "proposta_id": proposta_id,
            "autorizador": autorizador,
            "motivo": motivo,
            "fingerprint": fingerprint,
            "destino": destino,
            "confirmacao_explicita": confirmacao,
            "origem": origem,
            "registrada_em": autorizacao.get(
                "registrada_em",
                self._timestamp(),
            ),
        }

        self._transicionar(
            proposta,
            "autorizada_para_integracao",
            evento="autorizacao_explicita_registrada",
        )
        proposta["autorizacao"] = registro_autorizacao
        proposta["autorizacao_explicita"] = True
        proposta["integracao_executada"] = False
        proposta["stable_modificada"] = False

        self._salvar(proposta)
        return copy.deepcopy(proposta)

    def iniciar_integracao(
        self,
        proposta_id: str,
    ) -> dict[str, Any]:
        proposta = self._carregar(proposta_id)

        if proposta.get("estado") != "autorizada_para_integracao":
            raise ValueError(
                "proposta_nao_autorizada_para_integracao"
            )

        if proposta.get("autorizacao_explicita") is not True:
            raise ValueError(
                "autorizacao_explicita_ausente"
            )

        autorizacao = proposta.get("autorizacao")
        if not isinstance(autorizacao, dict):
            raise ValueError("registro_de_autorizacao_ausente")

        self._transicionar(
            proposta,
            "integracao_em_execucao",
            evento="integracao_iniciada",
        )
        proposta["integracao_executada"] = False
        proposta["stable_modificada"] = False

        self._salvar(proposta)
        return copy.deepcopy(proposta)

    def registrar_resultado_integracao(
        self,
        proposta_id: str,
        *,
        sucesso: bool,
        commit_sha: str | None = None,
        stable_modificada: bool = False,
        erro: str | None = None,
    ) -> dict[str, Any]:
        proposta = self._carregar(proposta_id)

        if proposta.get("estado") != "integracao_em_execucao":
            raise ValueError(
                "proposta_nao_em_integracao"
            )

        if not isinstance(sucesso, bool):
            raise ValueError("sucesso_invalido")

        if sucesso:
            commit_sha = self._texto(
                commit_sha,
                "commit_sha",
            )
            novo_estado = "integrada"
        else:
            commit_sha = (
                self._texto(commit_sha, "commit_sha")
                if commit_sha is not None
                else None
            )
            novo_estado = "integracao_falhou"

        self._transicionar(
            proposta,
            novo_estado,
            evento=(
                "integracao_concluida"
                if sucesso
                else "integracao_falhou"
            ),
        )

        proposta["integracao_executada"] = sucesso
        proposta["stable_modificada"] = bool(
            stable_modificada
        )

        if commit_sha is not None:
            proposta["commit_integracao"] = commit_sha

        if erro is not None:
            proposta["erro_integracao"] = str(erro)

        self._salvar(proposta)
        return copy.deepcopy(proposta)


if __name__ == "__main__":
    print(
        "PropostaIntegracaoDesenvolvimentoNixal OK"
    )
