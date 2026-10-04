#!/usr/bin/env python3

"""
NIXAL — NÚCLEO CONVERSACIONAL

Componente experimental da integração conversacional.

Responsabilidade:

    entrada estruturada 56.5.1
            ↓
        processamento
            ↓
    AgenteNixalQwen 55.3
            ↓
    fallback por domínio
            ↓
      diálogo contextual
            ↓
      resultado interno
            ↓
    resposta estruturada 56.5.1

Princípios:

1. Recebe somente entrada estruturada válida.
2. Acessa somente a memória conversacional volátil injetada.
3. Não promove o contexto conversacional a conhecimento permanente.
4. Não modifica a arquitetura.
5. Não altera o cristal diretamente.
6. Usa o AgenteNixalQwen para seleção e execução.
7. Usa domínio somente como fallback controlado.
8. Só usa fallback automático quando existe exatamente
   uma capacidade prioritária.
9. Não inventa capacidades para domínios externos ou desconhecidos.
10. A resposta final respeita o contrato da InterfaceConversacionalNixal.
"""

from __future__ import annotations

import json
from typing import Any

from nixal_interface import (
    InterfaceConversacionalNixal,
)
from nixal_agente_qwen import (
    AgenteNixalQwen,
)
from nixal_composicao_56_3_9 import (
    CompositorNixal,
)
from nixal_memoria_conversacional import (
    MemoriaConversacionalNixal,
)
from nixal_dialogo_qwen import (
    DialogoQwenNixal,
)


class NucleoConversacionalNixal:

    FONTE = "nucleo_conversacional_nixal"
    VERSAO = "experimental"

    def __init__(
        self,
        interface: InterfaceConversacionalNixal | None = None,
        agente: AgenteNixalQwen | None = None,
        compositor: CompositorNixal | None = None,
        memoria_conversacional: MemoriaConversacionalNixal | None = None,
        dialogo: DialogoQwenNixal | None = None,
    ) -> None:

        if interface is not None and not isinstance(
            interface,
            InterfaceConversacionalNixal,
        ):
            raise TypeError(
                "interface deve ser uma instância de "
                "InterfaceConversacionalNixal"
            )

        if agente is not None and not isinstance(
            agente,
            AgenteNixalQwen,
        ):
            raise TypeError(
                "agente deve ser uma instância de "
                "AgenteNixalQwen"
            )

        if compositor is not None and not isinstance(
            compositor,
            CompositorNixal,
        ):
            raise TypeError(
                "compositor deve ser uma instância de "
                "CompositorNixal"
            )

        if memoria_conversacional is not None and not isinstance(
            memoria_conversacional,
            MemoriaConversacionalNixal,
        ):
            raise TypeError(
                "memoria_conversacional deve ser uma instância de "
                "MemoriaConversacionalNixal"
            )

        if dialogo is not None and not isinstance(
            dialogo,
            DialogoQwenNixal,
        ):
            raise TypeError(
                "dialogo deve ser uma instância de "
                "DialogoQwenNixal"
            )

        self.interface = (
            interface
            if interface is not None
            else InterfaceConversacionalNixal()
        )

        self.agente = (
            agente
            if agente is not None
            else AgenteNixalQwen()
        )

        self.compositor = (
            compositor
            if compositor is not None
            else CompositorNixal()
        )

        self.memoria_conversacional = (
            memoria_conversacional
            if memoria_conversacional is not None
            else MemoriaConversacionalNixal()
        )

        self.dialogo = (
            dialogo
            if dialogo is not None
            else DialogoQwenNixal()
        )

        self.capacidades = {
            capacidade["nome"]: capacidade
            for capacidade
            in self.agente.capacidades.listar_capacidades()
        }

    def processar(
        self,
        entrada: dict[str, Any],
    ) -> dict[str, Any]:

        if not self.interface.validar_entrada(
            entrada
        ):
            return self.interface.criar_resposta(
                "A entrada recebida pelo núcleo é inválida.",
                sessao=(
                    entrada.get("sessao")
                    if isinstance(entrada, dict)
                    else None
                ),
                estado="entrada_invalida",
            )

        texto = entrada["valor"]["texto"]
        sessao = entrada["valor"].get("sessao")

        historico = self._obter_historico(
            sessao
        )

        self._registrar_contexto(
            sessao,
            "user",
            texto,
        )

        resultado = self._atender(
            texto
        )

        if resultado["atendida"]:

            resposta_textual = (
                self._formatar_resultado(
                    resultado
                )
            )

            estado_resposta = "resposta_capacidade"

        else:

            resposta_dialogo = self.dialogo.responder(
                texto,
                historico=historico,
            )

            if resposta_dialogo.get("sucesso") is True:

                resposta_textual = resposta_dialogo["resposta"]
                estado_resposta = "resposta_conversacional"

            else:

                resposta_textual = (
                    "Não consegui responder agora. "
                    "O módulo conversacional não está disponível."
                )
                estado_resposta = "dialogo_indisponivel"

        self._registrar_contexto(
            sessao,
            "assistant",
            resposta_textual,
        )

        resposta = self.interface.criar_resposta(
            resposta_textual,
            sessao=sessao,
            estado=estado_resposta,
        )

        resposta["valor"]["modo"] = estado_resposta
        resposta["valor"]["conhecimento_permanente"] = False
        resposta["valor"]["arquitetura_modificada"] = False

        return resposta

    def _obter_historico(
        self,
        sessao: str | None,
    ) -> list[dict[str, str]]:
        if not isinstance(sessao, str) or not sessao.strip():
            return []

        resultado = self.memoria_conversacional.obter(
            sessao
        )

        if resultado.get("sucesso") is not True:
            return []

        mensagens = resultado.get("mensagens", [])

        return (
            mensagens
            if isinstance(mensagens, list)
            else []
        )

    def _registrar_contexto(
        self,
        sessao: str | None,
        papel: str,
        texto: str,
    ) -> None:
        if not isinstance(sessao, str) or not sessao.strip():
            return

        self.memoria_conversacional.registrar(
            sessao=sessao,
            papel=papel,
            texto=texto,
        )

    def _atender(
        self,
        texto: str,
    ) -> dict[str, Any]:

        resultado_direto = self.agente.atender(
            texto
        )

        if resultado_direto["atendida"]:

            return resultado_direto

        contexto = (
            self.compositor.obter_contexto_dominio(
                texto
            )
        )

        prioritarias = contexto.get(
            "capacidades_prioritarias",
            [],
        )

        if len(prioritarias) != 1:

            return resultado_direto

        origem = contexto.get(
            "origem",
            {}
        )

        melhor_score_origem = (
            origem.get(
                "melhor_score",
                0
            )
            if isinstance(
                origem,
                dict
            )
            else 0
        )

        if (
            not isinstance(
                melhor_score_origem,
                int
            )
            or melhor_score_origem < 2
        ):

            return resultado_direto

        nome_capacidade = prioritarias[0]

        capacidade = self.capacidades.get(
            nome_capacidade
        )

        if capacidade is None:

            return resultado_direto

        objetivo = capacidade.get(
            "objetivo"
        )

        if not isinstance(
            objetivo,
            str,
        ) or not objetivo.strip():

            return resultado_direto

        resultado_fallback = (
            self.agente.atender(
                objetivo
            )
        )

        return resultado_fallback

    def _formatar_resultado(
        self,
        resultado: dict[str, Any],
    ) -> str:

        resultado_capacidade = resultado.get(
            "resultado"
        )

        if not isinstance(
            resultado_capacidade,
            dict,
        ):
            return self._formatar_dado(
                resultado_capacidade
            )

        dado = resultado_capacidade.get(
            "resultado"
        )

        return self._formatar_dado(
            dado
        )

    def _formatar_dado(
        self,
        dado: Any,
    ) -> str:

        if (
            isinstance(dado, dict)
            and all(
                chave in dado
                for chave in (
                    "hora",
                    "minuto",
                    "segundo",
                )
            )
        ):

            return (
                f"Agora são "
                f"{dado['hora']:02d}:"
                f"{dado['minuto']:02d}:"
                f"{dado['segundo']:02d}."
            )

        if isinstance(
            dado,
            list,
        ):

            if not dado:
                return "Não encontrei itens."

            return (
                "Encontrei estes itens:\n"
                + "\n".join(
                    f"- {item}"
                    for item in dado
                )
            )

        if isinstance(
            dado,
            str,
        ):

            return dado

        try:

            return json.dumps(
                dado,
                ensure_ascii=False,
                indent=2,
            )

        except TypeError:

            return str(
                dado
            )

    def interpretar(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:

        raise PermissionError(
            "NucleoConversacionalNixal delega "
            "interpretação ao AgenteNixalQwen."
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:

        raise PermissionError(
            "NucleoConversacionalNixal não modifica a arquitetura."
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:

        raise PermissionError(
            "NucleoConversacionalNixal não promove conhecimento permanente."
        )


__all__ = [
    "NucleoConversacionalNixal",
]
