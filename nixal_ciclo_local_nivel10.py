#!/usr/bin/env python3
"""
NYXAL — CICLO LOCAL DE DESENVOLVIMENTO / NÍVEL 10

Camada formal de estado sobre o observador e o coordenador existentes.

Responsabilidade:
    registrar e validar as transições do ciclo:

    alteracao_detectada
        ↓
    sincronizacao_preparada
        ↓
    validacao_em_execucao
        ↓
    validacao_concluida
        ↓
    aprovado | rejeitado

Esta classe não executa Git, código, testes ou comandos externos.
Ela registra estados e resultados fornecidos por componentes executores.
A aprovação da validação não autoriza integração em stable.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CicloLocalNivel10Nixal:
    VERSAO = "10.2.0"
    FONTE = "ciclo_local_nivel10_nixal"

    ESTADOS = {
        "alteracao_detectada",
        "sincronizacao_preparada",
        "validacao_em_execucao",
        "validacao_concluida",
        "aprovado",
        "rejeitado",
    }

    TRANSICOES = {
        "alteracao_detectada": {
            "sincronizacao_preparada",
        },
        "sincronizacao_preparada": {
            "validacao_em_execucao",
        },
        "validacao_em_execucao": {
            "validacao_concluida",
        },
        "validacao_concluida": {
            "aprovado",
            "rejeitado",
        },
        "aprovado": set(),
        "rejeitado": set(),
    }

    def __init__(
        self,
        *,
        diretorio_registros: str | Path,
    ) -> None:
        self.diretorio_registros = Path(
            diretorio_registros
        ).resolve()
        self.diretorio_registros.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _texto(valor: Any, nome: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{nome}_invalido")
        return valor.strip()

    @staticmethod
    def _sha(valor: Any, nome: str) -> str:
        texto = CicloLocalNivel10Nixal._texto(
            valor,
            nome,
        ).lower()
        if len(texto) != 40 or any(
            caractere not in "0123456789abcdef"
            for caractere in texto
        ):
            raise ValueError(f"{nome}_invalido")
        return texto

    @staticmethod
    def _ciclo_id(
        *,
        branch: str,
        commit_anterior: str,
        commit_novo: str,
    ) -> str:
        base = json.dumps(
            {
                "branch": branch,
                "commit_anterior": commit_anterior,
                "commit_novo": commit_novo,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(
            base.encode("utf-8")
        ).hexdigest()[:20]
        return f"n10-{digest}"

    def _arquivo(self, ciclo_id: str) -> Path:
        ciclo_id = self._texto(
            ciclo_id,
            "ciclo_id",
        )
        return (
            self.diretorio_registros
            / f"{ciclo_id}.json"
        )

    def _carregar(self, ciclo_id: str) -> dict[str, Any]:
        caminho = self._arquivo(ciclo_id)
        if not caminho.is_file():
            raise FileNotFoundError(
                "ciclo_nivel10_nao_encontrado"
            )

        try:
            registro = json.loads(
                caminho.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as erro:
            raise ValueError(
                "ciclo_nivel10_invalido"
            ) from erro

        self._validar(registro)
        return registro

    def _salvar(self, registro: dict[str, Any]) -> None:
        self._validar(registro)

        ciclo_id = self._texto(
            registro.get("ciclo_id"),
            "ciclo_id",
        )
        caminho = self._arquivo(ciclo_id)
        temporario = caminho.with_name(
            caminho.name + ".tmp"
        )

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
    def _validar(
        cls,
        registro: dict[str, Any],
    ) -> None:
        if not isinstance(registro, dict):
            raise ValueError(
                "ciclo_nivel10_invalido"
            )

        if registro.get("versao") != cls.VERSAO:
            raise ValueError(
                "versao_ciclo_nivel10_invalida"
            )

        ciclo_id = cls._texto(
            registro.get("ciclo_id"),
            "ciclo_id",
        )
        branch = cls._texto(
            registro.get("branch"),
            "branch",
        )
        anterior = cls._sha(
            registro.get("commit_anterior"),
            "commit_anterior",
        )
        novo = cls._sha(
            registro.get("commit_novo"),
            "commit_novo",
        )

        esperado = cls._ciclo_id(
            branch=branch,
            commit_anterior=anterior,
            commit_novo=novo,
        )

        tentativa_de = registro.get("tentativa_de")
        tentativa_numero = registro.get("tentativa_numero")

        if tentativa_de is None:
            if ciclo_id != esperado:
                raise ValueError(
                    "ciclo_id_inconsistente"
                )
            if tentativa_numero != 1:
                raise ValueError(
                    "tentativa_numero_inconsistente"
                )
        else:
            if not isinstance(tentativa_de, str) or not tentativa_de:
                raise ValueError(
                    "tentativa_de_invalida"
                )
            if not isinstance(tentativa_numero, int) or tentativa_numero < 2:
                raise ValueError(
                    "tentativa_numero_inconsistente"
                )

        estado = registro.get("estado")
        if estado not in cls.ESTADOS:
            raise ValueError(
                "estado_ciclo_nivel10_invalido"
            )

        historico = registro.get("historico_estados")
        if not isinstance(historico, list) or not historico:
            raise ValueError(
                "historico_ciclo_nivel10_invalido"
            )

        caminho = None
        for indice, transicao in enumerate(historico):
            if not isinstance(transicao, dict):
                raise ValueError(
                    f"transicao_invalida:{indice}"
                )

            de = transicao.get("de")
            para = transicao.get("para")

            if para not in cls.ESTADOS:
                raise ValueError(
                    f"estado_destino_invalido:{indice}"
                )

            if indice == 0:
                if de != "observado":
                    raise ValueError(
                        "origem_inicial_invalida"
                    )
            else:
                if de != caminho:
                    raise ValueError(
                        f"historico_desconectado:{indice}"
                    )

            if de == "observado":
                if para != "alteracao_detectada":
                    raise ValueError(
                        "transicao_inicial_invalida"
                    )
            elif para not in cls.TRANSICOES.get(
                de,
                set(),
            ):
                raise ValueError(
                    f"transicao_nao_permitida:{de}->{para}"
                )

            caminho = para

        if caminho != estado:
            raise ValueError(
                "estado_final_inconsistente"
            )

        if registro.get("autorizacao_explicita") is True:
            raise ValueError(
                "autorizacao_fora_do_escopo_nivel10"
            )

        validacao = registro.get(
            "resultado_validacao"
        )
        if estado in {
            "validacao_concluida",
            "aprovado",
            "rejeitado",
        }:
            if not isinstance(validacao, dict):
                raise ValueError(
                    "resultado_validacao_ausente"
                )

    def abrir_ciclo(
        self,
        observacao: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(observacao, dict):
            raise ValueError(
                "observacao_invalida"
            )

        if observacao.get("alteracao_detectada") is not True:
            raise ValueError(
                "alteracao_nao_detectada"
            )

        ciclo = observacao.get("ciclo")
        if not isinstance(ciclo, dict):
            raise ValueError(
                "ciclo_observado_ausente"
            )

        branch = self._texto(
            ciclo.get("branch"),
            "branch",
        )
        anterior = self._sha(
            ciclo.get("commit_anterior"),
            "commit_anterior",
        )
        novo = self._sha(
            ciclo.get("commit_novo"),
            "commit_novo",
        )

        ciclo_id = self._ciclo_id(
            branch=branch,
            commit_anterior=anterior,
            commit_novo=novo,
        )

        if ciclo.get("ciclo_id") != ciclo_id:
            raise ValueError(
                "ciclo_id_observado_inconsistente"
            )

        caminho = self._arquivo(ciclo_id)
        if caminho.exists():
            return self._carregar(ciclo_id)

        agora = self._timestamp()
        registro = {
            "versao": self.VERSAO,
            "fonte": self.FONTE,
            "ciclo_id": ciclo_id,
            "branch": branch,
            "commit_anterior": anterior,
            "commit_novo": novo,
            "criado_em": agora,
            "atualizado_em": agora,
            "estado": "alteracao_detectada",
            "estado_anterior": "observado",
            "historico_estados": [
                {
                    "de": "observado",
                    "para": "alteracao_detectada",
                    "evento": "alteracao_detectada",
                    "em": agora,
                }
            ],
            "sincronizacao": None,
            "validacao": None,
            "resultado_validacao": None,
            "autorizacao_explicita": False,
            "tentativa_de": None,
            "tentativa_numero": 1,
        }

        self._salvar(registro)
        return copy.deepcopy(registro)

    def _transicionar(
        self,
        registro: dict[str, Any],
        novo_estado: str,
        *,
        evento: str,
    ) -> None:
        atual = registro.get("estado")
        if atual not in self.ESTADOS:
            raise ValueError(
                "estado_ciclo_nivel10_invalido"
            )

        if novo_estado not in self.ESTADOS:
            raise ValueError(
                "novo_estado_ciclo_nivel10_invalido"
            )

        if novo_estado not in self.TRANSICOES.get(
            atual,
            set(),
        ):
            raise ValueError(
                f"transicao_nao_permitida:{atual}->{novo_estado}"
            )

        historico = registro.setdefault(
            "historico_estados",
            [],
        )
        if not isinstance(historico, list):
            raise ValueError(
                "historico_ciclo_nivel10_invalido"
            )

        agora = self._timestamp()
        historico.append(
            {
                "de": atual,
                "para": novo_estado,
                "evento": self._texto(
                    evento,
                    "evento",
                ),
                "em": agora,
            }
        )
        registro["estado_anterior"] = atual
        registro["estado"] = novo_estado
        registro["atualizado_em"] = agora

    def registrar_sincronizacao_preparada(
        self,
        ciclo_id: str,
        *,
        commit_validado: str,
        evidencias: list[Any] | None = None,
    ) -> dict[str, Any]:
        registro = self._carregar(ciclo_id)

        if registro["estado"] != "alteracao_detectada":
            raise ValueError(
                "estado_invalido_para_sincronizacao"
            )

        commit_validado = self._sha(
            commit_validado,
            "commit_validado",
        )
        if commit_validado != registro[
            "commit_novo"
        ]:
            raise ValueError(
                "commit_validado_diferente_do_ciclo"
            )

        registro["sincronizacao"] = {
            "commit_validado": commit_validado,
            "evidencias": copy.deepcopy(
                evidencias or []
            ),
            "preparada_em": self._timestamp(),
        }

        self._transicionar(
            registro,
            "sincronizacao_preparada",
            evento="sincronizacao_preparada",
        )
        self._salvar(registro)
        return copy.deepcopy(registro)

    def iniciar_validacao(
        self,
        ciclo_id: str,
    ) -> dict[str, Any]:
        registro = self._carregar(ciclo_id)

        self._transicionar(
            registro,
            "validacao_em_execucao",
            evento="validacao_iniciada",
        )
        self._salvar(registro)
        return copy.deepcopy(registro)

    def concluir_validacao(
        self,
        ciclo_id: str,
        *,
        sucesso: bool,
        validacoes: list[Any] | None = None,
        diagnostico: str | None = None,
    ) -> dict[str, Any]:
        registro = self._carregar(ciclo_id)

        if registro["estado"] != "validacao_em_execucao":
            raise ValueError(
                "estado_invalido_para_conclusao_validacao"
            )

        if not isinstance(sucesso, bool):
            raise ValueError(
                "sucesso_validacao_invalido"
            )

        registro["resultado_validacao"] = {
            "sucesso": sucesso,
            "validacoes": copy.deepcopy(
                validacoes or []
            ),
            "diagnostico": (
                diagnostico
                if diagnostico is not None
                else ""
            ),
            "concluida_em": self._timestamp(),
        }

        self._transicionar(
            registro,
            "validacao_concluida",
            evento="validacao_concluida",
        )
        self._salvar(registro)
        return copy.deepcopy(registro)

    def classificar_resultado(
        self,
        ciclo_id: str,
    ) -> dict[str, Any]:
        registro = self._carregar(ciclo_id)

        if registro["estado"] != "validacao_concluida":
            raise ValueError(
                "estado_invalido_para_classificacao"
            )

        resultado = registro.get(
            "resultado_validacao"
        )
        if not isinstance(resultado, dict):
            raise ValueError(
                "resultado_validacao_ausente"
            )

        sucesso = resultado.get("sucesso")
        if sucesso is True:
            destino = "aprovado"
        elif sucesso is False:
            destino = "rejeitado"
        else:
            raise ValueError(
                "resultado_validacao_invalido"
            )

        self._transicionar(
            registro,
            destino,
            evento=(
                "validacao_aprovada"
                if destino == "aprovado"
                else "validacao_rejeitada"
            ),
        )
        self._salvar(registro)
        return copy.deepcopy(registro)

    def criar_nova_tentativa(
        self,
        ciclo_id: str,
        *,
        motivo: str,
    ) -> dict[str, Any]:
        """Cria explicitamente uma nova tentativa para um ciclo rejeitado.

        A nova tentativa mantém o mesmo commit-alvo, mas recebe um novo
        identificador de tentativa e aponta para o ciclo anterior.
        """
        registro = self._carregar(ciclo_id)

        if registro["estado"] != "rejeitado":
            raise ValueError(
                "nova_tentativa_exige_ciclo_rejeitado"
            )

        motivo = self._texto(
            motivo,
            "motivo_reexecucao",
        )

        numero = registro.get("tentativa_numero")
        if not isinstance(numero, int) or numero < 1:
            raise ValueError(
                "tentativa_numero_invalido"
            )

        base = json.dumps(
            {
                "ciclo_id": registro["ciclo_id"],
                "commit_novo": registro["commit_novo"],
                "tentativa_numero": numero + 1,
                "motivo": motivo,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(
            base.encode("utf-8")
        ).hexdigest()[:20]
        novo_id = f"n10-r-{digest}"

        novo = {
            "versao": self.VERSAO,
            "fonte": self.FONTE,
            "ciclo_id": novo_id,
            "branch": registro["branch"],
            "commit_anterior": registro["commit_anterior"],
            "commit_novo": registro["commit_novo"],
            "criado_em": self._timestamp(),
            "atualizado_em": self._timestamp(),
            "estado": "alteracao_detectada",
            "estado_anterior": "observado",
            "historico_estados": [
                {
                    "de": "observado",
                    "para": "alteracao_detectada",
                    "evento": "nova_tentativa",
                    "em": self._timestamp(),
                }
            ],
            "sincronizacao": None,
            "validacao": None,
            "resultado_validacao": None,
            "autorizacao_explicita": False,
            "tentativa_de": registro["ciclo_id"],
            "tentativa_numero": numero + 1,
            "motivo_reexecucao": motivo,
        }

        self._salvar(novo)
        return copy.deepcopy(novo)

    def consultar(
        self,
        ciclo_id: str,
    ) -> dict[str, Any]:
        return copy.deepcopy(
            self._carregar(ciclo_id)
        )


if __name__ == "__main__":
    print("CicloLocalNivel10Nixal OK")
