#!/usr/bin/env python3

"""
NIXAL — INTEGRAÇÃO ENTRE SESSÃO E TRANSPORTE

Microetapa 56.5.4

Responsabilidade:
    Conectar o GerenciadorSessoesNixal ao transporte conversacional
    já existente.

Arquitetura:

    interface
        ↓
    transporte conversacional
        ↓
    integração sessão ↔ transporte
        ↓
    sessão
        ↓
    núcleo

Princípios:
1. A sessão continua sendo somente identidade e estado estrutural.
2. O transporte continua responsável pelo transporte conversacional.
3. Esta camada não cria memória conversacional.
4. Esta camada não armazena mensagens.
5. Esta camada não interpreta mensagens.
6. Esta camada não executa capacidades.
7. Esta camada não formula hipóteses.
8. Esta camada não executa testes.
9. Esta camada não modifica a arquitetura.
10. Uma sessão inexistente pode ser criada automaticamente.
11. Uma sessão existente precisa estar ativa para receber mensagens.
12. O transporte recebe explicitamente o identificador da sessão.
13. A resposta do transporte é preservada por cópia profunda.
14. Estruturas retornadas não expõem referências mutáveis internas.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from nixal_gerenciador_sessoes import (
    GerenciadorSessoesNixal,
)


class IntegracaoSessaoTransporteNixal:
    """
    Camada que integra o transporte conversacional ao
    gerenciamento de sessões.

    O transporte é injetado externamente para manter esta camada
    independente da implementação concreta do transporte.
    """

    FONTE = "integracao_sessao_transporte_nixal"
    VERSAO = "56.5.4"

    def __init__(
        self,
        transporte: Any,
        sessoes: GerenciadorSessoesNixal | None = None,
    ) -> None:
        if not hasattr(
            transporte,
            "processar_mensagem",
        ) or not callable(
            transporte.processar_mensagem
        ):
            raise TypeError(
                "transporte deve fornecer um método "
                "chamado 'processar_mensagem'."
            )

        self.transporte = transporte

        self.sessoes = (
            sessoes
            if sessoes is not None
            else GerenciadorSessoesNixal()
        )

    # ============================================================
    # PROCESSAMENTO DE MENSAGEM
    # ============================================================

    def processar_mensagem(
        self,
        texto: str,
        nucleo: Any,
        sessao_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Processa uma mensagem dentro de uma sessão.

        Quando sessao_id não é fornecido:
            uma nova sessão é criada.

        Quando sessao_id é fornecido:
            a sessão precisa existir e estar ativa.
        """

        if not isinstance(
            texto,
            str,
        ) or not texto.strip():
            return self._negado(
                "A mensagem precisa conter texto válido."
            )

        if nucleo is None:
            return self._negado(
                "Um núcleo conversacional precisa ser fornecido."
            )

        # --------------------------------------------------------
        # OBTENÇÃO OU CRIAÇÃO DA SESSÃO
        # --------------------------------------------------------

        sessao_criada_agora = False

        if sessao_id is None:
            criacao = self.sessoes.criar()

            if criacao.get("sucesso") is not True:
                return self._erro(
                    estado="sessao_nao_criada",
                    mensagem=(
                        "Não foi possível criar uma sessão "
                        "para a mensagem."
                    ),
                    sessao=None,
                )

            sessao_id = criacao.get(
                "sessao"
            )

            if not isinstance(
                sessao_id,
                str,
            ):
                return self._erro(
                    estado="sessao_invalida",
                    mensagem=(
                        "O gerenciador criou uma sessão "
                        "sem identificador válido."
                    ),
                    sessao=None,
                )

            sessao_criada_agora = True

        # --------------------------------------------------------
        # VALIDAÇÃO DA SESSÃO
        # --------------------------------------------------------

        validacao = self.sessoes.validar(
            sessao_id
        )

        if validacao.get("valida") is not True:
            return self._erro(
                estado="sessao_nao_valida",
                mensagem=(
                    "A sessão não pode receber esta mensagem."
                ),
                sessao=sessao_id,
                detalhes=validacao,
            )

        if validacao.get("ativa") is not True:
            return self._erro(
                estado="sessao_inativa",
                mensagem=(
                    "A sessão não está ativa."
                ),
                sessao=sessao_id,
                detalhes=validacao,
            )

        # --------------------------------------------------------
        # CONSULTA DO ESTADO ESTRUTURAL
        # --------------------------------------------------------

        consulta_sessao = self.sessoes.obter(
            sessao_id
        )

        if consulta_sessao.get("sucesso") is not True:
            return self._erro(
                estado="sessao_nao_consultavel",
                mensagem=(
                    "A sessão foi validada, mas não pôde "
                    "ser consultada."
                ),
                sessao=sessao_id,
                detalhes=consulta_sessao,
            )

        sessao = consulta_sessao.get(
            "valor"
        )

        if not isinstance(
            sessao,
            dict,
        ):
            return self._erro(
                estado="estrutura_sessao_invalida",
                mensagem=(
                    "A sessão consultada não possui "
                    "estrutura válida."
                ),
                sessao=sessao_id,
            )

        # --------------------------------------------------------
        # TRANSPORTE
        # --------------------------------------------------------

        try:
            resultado_transporte = (
                self.transporte.processar_mensagem(
                    texto,
                    nucleo,
                    sessao_id,
                )
            )

        except Exception as erro:
            return self._erro(
                estado="transporte_nao_respondeu",
                mensagem=(
                    "O transporte lançou uma exceção "
                    "durante o processamento."
                ),
                sessao=sessao_id,
                detalhes={
                    "tipo": type(erro).__name__,
                    "mensagem": str(erro),
                },
            )

        # --------------------------------------------------------
        # VALIDAR RESPOSTA DO TRANSPORTE
        # --------------------------------------------------------

        if not isinstance(
            resultado_transporte,
            dict,
        ):
            return self._erro(
                estado="resposta_transporte_invalida",
                mensagem=(
                    "O transporte não retornou uma estrutura "
                    "de resposta válida."
                ),
                sessao=sessao_id,
            )

        # --------------------------------------------------------
        # RESULTADO INTEGRADO
        # --------------------------------------------------------

        sucesso_transporte = (
            resultado_transporte.get(
                "sucesso"
            ) is True
        )

        estado = (
            "mensagem_processada_com_sessao"
            if sucesso_transporte
            else "mensagem_nao_processada_com_sessao"
        )

        resposta_integrada = (
            resultado_transporte.get(
                "resposta"
            )
            if isinstance(
                resultado_transporte.get("resposta"),
                dict,
            )
            else {}
        )

        valor_resposta = (
            resposta_integrada.get(
                "valor"
            )
            if isinstance(
                resposta_integrada.get("valor"),
                dict,
            )
            else {}
        )

        mensagem_armazenada = (
            valor_resposta.get(
                "mensagem_armazenada",
                False,
            )
            is True
        )

        memoria_conversacional = (
            valor_resposta.get(
                "memoria_conversacional",
                False,
            )
            is True
        )

        return {
            "sucesso": sucesso_transporte,
            "estado": estado,
            "origem": self.FONTE,
            "sessao": sessao_id,
            "valor": {
                "sessao": deepcopy(
                    sessao
                ),
                "sessao_criada_agora": (
                    sessao_criada_agora
                ),
                "transporte": deepcopy(
                    resultado_transporte
                ),
                "mensagem_armazenada": mensagem_armazenada,
                "memoria_conversacional": memoria_conversacional,
                "conhecimento_permanente": False,
                "arquitetura_modificada": False,
            },
            "erro": (
                None
                if sucesso_transporte
                else resultado_transporte.get(
                    "erro"
                )
            ),
            "versao_integracao": self.VERSAO,
        }

    # ============================================================
    # ENTRADA ESTRUTURADA
    # ============================================================

    def enviar_entrada(
        self,
        entrada: dict[str, Any],
        nucleo: Any,
    ) -> dict[str, Any]:
        """
        Recebe uma entrada estrutural produzida pela interface.

        O formato esperado é compatível com a interface 56.5.1:
            entrada["valor"]["texto"]

        O identificador da sessão pode estar:
            entrada["sessao"]

        ou:

            entrada["valor"]["sessao"]
        """

        if not isinstance(
            entrada,
            dict,
        ):
            return self._negado(
                "A entrada conversacional precisa ser um objeto."
            )

        if entrada.get(
            "sucesso"
        ) is not True:
            return self._negado(
                "A entrada conversacional não está marcada como válida."
            )

        valor = entrada.get(
            "valor"
        )

        if not isinstance(
            valor,
            dict,
        ):
            return self._negado(
                "A entrada não possui um objeto 'valor' válido."
            )

        texto = valor.get(
            "texto"
        )

        if not isinstance(
            texto,
            str,
        ) or not texto.strip():
            return self._negado(
                "A entrada não possui texto válido."
            )

        sessao_id = entrada.get(
            "sessao"
        )

        if sessao_id is None:
            sessao_id = valor.get(
                "sessao"
            )

        if sessao_id is not None and not isinstance(
            sessao_id,
            str,
        ):
            return self._negado(
                "O identificador da sessão é inválido."
            )

        return self.processar_mensagem(
            texto=texto,
            nucleo=nucleo,
            sessao_id=sessao_id,
        )

    # ============================================================
    # SESSÃO
    # ============================================================

    def obter_sessao(
        self,
        sessao_id: str,
    ) -> dict[str, Any]:
        """
        Consulta somente a estrutura da sessão.
        """

        return self.sessoes.obter(
            sessao_id
        )

    def encerrar_sessao(
        self,
        sessao_id: str,
    ) -> dict[str, Any]:
        """
        Encerra uma sessão.

        Nenhum conteúdo conversacional é salvo ou removido aqui.
        """

        return self.sessoes.encerrar(
            sessao_id
        )

    def sessao_ativa(
        self,
        sessao_id: str,
    ) -> bool:
        """
        Retorna somente se a sessão está ativa.
        """

        return self.sessoes.esta_ativa(
            sessao_id
        )

    # ============================================================
    # RESPOSTAS INTERNAS
    # ============================================================

    def _negado(
        self,
        mensagem: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "operacao_negada",
            "origem": self.FONTE,
            "sessao": None,
            "valor": None,
            "erro": mensagem,
            "versao_integracao": self.VERSAO,
        }

    def _erro(
        self,
        estado: str,
        mensagem: str,
        sessao: str | None,
        detalhes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        valor: dict[str, Any] = {}

        if detalhes is not None:
            valor["detalhes"] = deepcopy(
                detalhes
            )

        return {
            "sucesso": False,
            "estado": estado,
            "origem": self.FONTE,
            "sessao": sessao,
            "valor": valor,
            "erro": mensagem,
            "versao_integracao": self.VERSAO,
        }


# ================================================================
# DEMONSTRAÇÃO ISOLADA
# ================================================================

class TransporteDemonstracao:
    """
    Pequeno transporte controlado apenas para demonstrar
    o contrato da integração.

    O transporte real da 56.5.2 continua sendo injetado
    externamente em produção.
    """

    def processar_mensagem(
        self,
        texto: str,
        nucleo: Any,
        sessao: str,
    ) -> dict[str, Any]:
        resposta = nucleo.processar(
            texto
        )

        return {
            "sucesso": True,
            "estado": "mensagem_processada",
            "origem": "transporte_demonstracao",
            "sessao": sessao,
            "resposta": resposta,
        }


class NucleoDemonstracao:
    """
    Núcleo mínimo somente para demonstrar a passagem
    da mensagem pelo transporte.
    """

    def processar(
        self,
        texto: str,
    ) -> str:
        return f"Núcleo recebeu: {texto}"


if __name__ == "__main__":
    print("=" * 60)
    print("NIXAL — INTEGRAÇÃO SESSÃO ↔ TRANSPORTE 56.5.4")
    print("=" * 60)

    transporte = TransporteDemonstracao()
    sessoes = GerenciadorSessoesNixal()

    integracao = IntegracaoSessaoTransporteNixal(
        transporte=transporte,
        sessoes=sessoes,
    )

    nucleo = NucleoDemonstracao()

    print()
    print("MENSAGEM 1 — SEM SESSÃO INFORMADA")

    resultado_1 = integracao.processar_mensagem(
        texto="Olá, Nixal.",
        nucleo=nucleo,
    )

    print(resultado_1)

    sessao_id = resultado_1.get(
        "sessao"
    )

    print()
    print("MENSAGEM 2 — REUTILIZANDO A SESSÃO")

    resultado_2 = integracao.processar_mensagem(
        texto="Como está?",
        nucleo=nucleo,
        sessao_id=sessao_id,
    )

    print(resultado_2)

    print()
    print("ESTADO DA SESSÃO")

    print(
        integracao.obter_sessao(
            sessao_id
        )
    )

    print()
    print("ENCERRAMENTO")

    print(
        integracao.encerrar_sessao(
            sessao_id
        )
    )

    print()
    print("TENTATIVA APÓS ENCERRAMENTO")

    resultado_3 = integracao.processar_mensagem(
        texto="Ainda está aí?",
        nucleo=nucleo,
        sessao_id=sessao_id,
    )

    print(resultado_3)

    print()
    print("=" * 60)
    print("56.5.4 — DEMONSTRAÇÃO FINALIZADA")
    print("=" * 60)
