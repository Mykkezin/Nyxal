#!/usr/bin/env python3

"""
NIXAL — GERENCIADOR DE SESSÕES

Microetapa 56.5.3

Responsabilidade:
    Gerenciar a identidade e o estado estrutural das sessões
    conversacionais da Nixal.

Princípios:
1. Sessão não é memória conversacional.
2. Sessão não armazena mensagens.
3. Sessão não interpreta mensagens.
4. Sessão não executa capacidades.
5. Sessão não acessa o corpo da Nixal.
6. Sessão não cria conhecimento.
7. Sessão não formula hipóteses.
8. Sessão não executa testes.
9. Sessão não avalia hipóteses.
10. Sessão não modifica a arquitetura.
11. O estado de uma sessão pode ser criado, consultado,
    validado e encerrado.
12. Os resultados retornados são cópias isoladas da estrutura
    interna do gerenciador.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID, uuid4


class GerenciadorSessoesNixal:
    """
    Gerencia somente a identidade e o ciclo estrutural
    das sessões conversacionais.

    Nenhum conteúdo de conversa é armazenado nesta camada.
    """

    VERSAO = "56.5.3"
    ORIGEM = "gerenciador_sessoes_nixal"

    ESTADO_ATIVA = "ativa"
    ESTADO_ENCERRADA = "encerrada"

    def __init__(
        self,
        gerador_id: Callable[[], UUID] | None = None,
        relogio: Callable[[], datetime] | None = None,
    ) -> None:
        self._gerador_id = (
            gerador_id
            if gerador_id is not None
            else uuid4
        )

        self._relogio = (
            relogio
            if relogio is not None
            else lambda: datetime.now(timezone.utc)
        )

        self._sessoes: dict[str, dict[str, Any]] = {}

    # ============================================================
    # CRIAÇÃO
    # ============================================================

    def criar(
        self,
        sessao_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Cria uma nova sessão.

        Quando sessao_id não é fornecido, um identificador UUID
        é gerado internamente.

        A sessão criada não contém mensagens nem memória.
        """

        identificador = (
            self._normalizar_id(sessao_id)
            if sessao_id is not None
            else str(self._gerador_id())
        )

        if identificador is None:
            return self._negado(
                "O identificador da sessão é inválido."
            )

        if identificador in self._sessoes:
            return self._negado(
                "Já existe uma sessão com este identificador."
            )

        agora = self._timestamp()

        sessao = {
            "id": identificador,
            "estado": self.ESTADO_ATIVA,
            "criada_em": agora,
            "encerrada_em": None,
        }

        self._sessoes[identificador] = sessao

        return {
            "sucesso": True,
            "estado": "sessao_criada",
            "origem": self.ORIGEM,
            "sessao": identificador,
            "valor": deepcopy(sessao),
            "versao_sessoes": self.VERSAO,
        }

    # ============================================================
    # CONSULTA
    # ============================================================

    def obter(
        self,
        sessao_id: str,
    ) -> dict[str, Any]:
        """
        Consulta uma sessão conhecida.

        Nenhuma informação é criada quando a sessão não existe.
        """

        identificador = self._normalizar_id(sessao_id)

        if identificador is None:
            return self._desconhecida(
                "Identificador de sessão inválido."
            )

        sessao = self._sessoes.get(identificador)

        if sessao is None:
            return self._desconhecida(
                "Sessão desconhecida."
            )

        return {
            "sucesso": True,
            "estado": "sessao_encontrada",
            "origem": self.ORIGEM,
            "sessao": identificador,
            "valor": deepcopy(sessao),
            "versao_sessoes": self.VERSAO,
        }

    # ============================================================
    # VALIDAÇÃO
    # ============================================================

    def validar(
        self,
        sessao_id: str,
    ) -> dict[str, Any]:
        """
        Verifica se uma sessão existe e está ativa.
        """

        identificador = self._normalizar_id(sessao_id)

        if identificador is None:
            return {
                "sucesso": False,
                "estado": "sessao_invalida",
                "origem": self.ORIGEM,
                "sessao": None,
                "valida": False,
                "ativa": False,
                "erro": "Identificador de sessão inválido.",
                "versao_sessoes": self.VERSAO,
            }

        sessao = self._sessoes.get(identificador)

        if sessao is None:
            return {
                "sucesso": True,
                "estado": "sessao_desconhecida",
                "origem": self.ORIGEM,
                "sessao": identificador,
                "valida": False,
                "ativa": False,
                "erro": None,
                "versao_sessoes": self.VERSAO,
            }

        ativa = (
            sessao["estado"] == self.ESTADO_ATIVA
        )

        return {
            "sucesso": True,
            "estado": "sessao_validada",
            "origem": self.ORIGEM,
            "sessao": identificador,
            "valida": True,
            "ativa": ativa,
            "erro": None,
            "versao_sessoes": self.VERSAO,
        }

    # ============================================================
    # ENCERRAMENTO
    # ============================================================

    def encerrar(
        self,
        sessao_id: str,
    ) -> dict[str, Any]:
        """
        Encerra uma sessão existente.

        O encerramento altera somente o estado estrutural da
        sessão. Nenhuma memória conversacional é criada, removida
        ou acessada aqui.
        """

        identificador = self._normalizar_id(sessao_id)

        if identificador is None:
            return self._negado(
                "Identificador de sessão inválido."
            )

        sessao = self._sessoes.get(identificador)

        if sessao is None:
            return self._desconhecida(
                "Sessão desconhecida."
            )

        if sessao["estado"] == self.ESTADO_ENCERRADA:
            return {
                "sucesso": False,
                "estado": "sessao_ja_encerrada",
                "origem": self.ORIGEM,
                "sessao": identificador,
                "valor": deepcopy(sessao),
                "erro": "A sessão já está encerrada.",
                "versao_sessoes": self.VERSAO,
            }

        sessao["estado"] = self.ESTADO_ENCERRADA
        sessao["encerrada_em"] = self._timestamp()

        return {
            "sucesso": True,
            "estado": "sessao_encerrada",
            "origem": self.ORIGEM,
            "sessao": identificador,
            "valor": deepcopy(sessao),
            "erro": None,
            "versao_sessoes": self.VERSAO,
        }

    # ============================================================
    # LISTAGEM
    # ============================================================

    def listar(
        self,
        somente_ativas: bool = False,
    ) -> dict[str, Any]:
        """
        Lista sessões conhecidas.

        A listagem retorna somente estrutura de sessão.
        """

        sessoes = []

        for sessao in self._sessoes.values():
            if (
                somente_ativas
                and sessao["estado"] != self.ESTADO_ATIVA
            ):
                continue

            sessoes.append(
                deepcopy(sessao)
            )

        return {
            "sucesso": True,
            "estado": "sessoes_listadas",
            "origem": self.ORIGEM,
            "quantidade": len(sessoes),
            "somente_ativas": somente_ativas,
            "sessoes": sessoes,
            "versao_sessoes": self.VERSAO,
        }

    # ============================================================
    # ESTADO
    # ============================================================

    def esta_ativa(
        self,
        sessao_id: str,
    ) -> bool:
        """
        Retorna somente o estado ativo/inativo de uma sessão.
        """

        identificador = self._normalizar_id(sessao_id)

        if identificador is None:
            return False

        sessao = self._sessoes.get(identificador)

        if sessao is None:
            return False

        return (
            sessao["estado"] == self.ESTADO_ATIVA
        )

    # ============================================================
    # UTILITÁRIOS INTERNOS
    # ============================================================

    def _timestamp(self) -> str:
        valor = self._relogio()

        if not isinstance(valor, datetime):
            raise TypeError(
                "O relógio da sessão precisa retornar datetime."
            )

        if valor.tzinfo is None:
            valor = valor.replace(
                tzinfo=timezone.utc
            )

        return valor.isoformat()

    @staticmethod
    def _normalizar_id(
        sessao_id: str,
    ) -> str | None:
        if not isinstance(sessao_id, str):
            return None

        identificador = sessao_id.strip()

        if not identificador:
            return None

        return identificador

    def _negado(
        self,
        mensagem: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "operacao_negada",
            "origem": self.ORIGEM,
            "sessao": None,
            "erro": mensagem,
            "versao_sessoes": self.VERSAO,
        }

    def _desconhecida(
        self,
        mensagem: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "sessao_desconhecida",
            "origem": self.ORIGEM,
            "sessao": None,
            "valor": None,
            "erro": mensagem,
            "versao_sessoes": self.VERSAO,
        }


if __name__ == "__main__":
    gerenciador = GerenciadorSessoesNixal()

    criada = gerenciador.criar()

    print("=" * 60)
    print("NIXAL — GERENCIADOR DE SESSÕES 56.5.3")
    print("=" * 60)
    print(criada)

    if criada["sucesso"]:
        sessao = criada["sessao"]

        print()
        print("VALIDAÇÃO:")
        print(gerenciador.validar(sessao))

        print()
        print("CONSULTA:")
        print(gerenciador.obter(sessao))

        print()
        print("LISTAGEM:")
        print(gerenciador.listar())

        print()
        print("ENCERRAMENTO:")
        print(gerenciador.encerrar(sessao))

        print()
        print("VALIDAÇÃO FINAL:")
        print(gerenciador.validar(sessao))
