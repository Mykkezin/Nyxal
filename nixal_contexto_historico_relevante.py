#!/usr/bin/env python3

"""
NIXAL — CONTEXTO HISTÓRICO RELEVANTE

Microetapa 56.4.21

Responsabilidade:
    Integrar a relevância do histórico (56.4.20) com a construção
    de contexto histórico (56.4.19), produzindo somente o contexto
    histórico relacionado a uma nova necessidade ou hipótese.

Princípios:
1. Histórico relacionado é contexto, não verdade.
2. O histórico não encerra uma nova investigação.
3. Necessidade exata tem prioridade de classificação.
4. Registros duplicados entre critérios aparecem uma única vez.
5. A ordem cronológica da memória é preservada.
6. Um limite explícito controla quanto histórico é entregue.
7. Nenhum registro persistido é alterado.
8. A camada não executa capacidades.
9. A camada não modifica a arquitetura.
10. A camada não promove conhecimento permanente.
"""

from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any

from nixal_contexto_historico_investigacao import (
    ContextoHistoricoInvestigacaoNixal,
)
from nixal_memoria_investigacao import (
    MemoriaInvestigacaoNixal,
)
from nixal_relevancia_historico_investigacao import (
    RelevanciaHistoricoInvestigacaoNixal,
)


class ContextoHistoricoRelevanteNixal:
    """Entrega somente histórico relevante como contexto explícito."""

    FONTE = "contexto_historico_relevante_nixal"

    def __init__(
        self,
        memoria: MemoriaInvestigacaoNixal,
    ) -> None:
        if not isinstance(
            memoria,
            MemoriaInvestigacaoNixal,
        ):
            raise TypeError(
                "memoria deve ser uma instância de "
                "MemoriaInvestigacaoNixal"
            )

        self._memoria = memoria
        self._relevancia = (
            RelevanciaHistoricoInvestigacaoNixal(
                memoria
            )
        )
        self._contexto = (
            ContextoHistoricoInvestigacaoNixal(
                memoria
            )
        )

    def analisar(
        self,
        necessidade: str | None = None,
        hipotese: str | None = None,
        limite: int = 5,
    ) -> dict[str, Any]:
        if not self._possui_entrada(
            necessidade,
            hipotese,
        ):
            return self._negado(
                "É necessário fornecer necessidade, hipótese ou ambos."
            )

        if not isinstance(
            limite,
            int,
        ) or isinstance(
            limite,
            bool,
        ):
            return self._negado(
                "Limite precisa ser um inteiro."
            )

        if limite <= 0:
            return self._negado(
                "Limite precisa ser maior que zero."
            )

        resultado_relevancia = (
            self._relevancia.analisar(
                necessidade=necessidade,
                hipotese=hipotese,
            )
        )

        if resultado_relevancia.get(
            "sucesso"
        ) is not True:
            return deepcopy(
                resultado_relevancia
            )

        valor_relevancia = resultado_relevancia.get(
            "valor"
        )

        if not isinstance(
            valor_relevancia,
            dict,
        ):
            return self._negado(
                "A relevância do histórico não retornou dados válidos."
            )

        registros = self._selecionar_unicos(
            valor_relevancia,
            limite,
        )

        contextos: list[dict[str, Any]] = []

        for registro in registros:
            registro_id = registro.get(
                "id"
            )

            if not isinstance(
                registro_id,
                str,
            ):
                continue

            resultado_contexto = (
                self._contexto.obter(
                    registro_id
                )
            )

            if resultado_contexto.get(
                "sucesso"
            ) is not True:
                continue

            contexto = resultado_contexto.get(
                "valor"
            )

            if isinstance(
                contexto,
                dict,
            ):
                contextos.append(
                    deepcopy(
                        contexto
                    )
                )

        return {
            "sucesso": True,
            "estado": "contexto_relevante",
            "origem": self.FONTE,
            "valor": {
                "entrada": {
                    "necessidade": necessidade,
                    "hipotese": hipotese,
                },
                "historico_encontrado": bool(
                    contextos
                ),
                "quantidade": len(
                    contextos
                ),
                "limite": limite,
                "contextos": contextos,
                "interpretacao": (
                    "O histórico relevante foi recuperado como "
                    "contexto. Ele não determina a verdade da "
                    "hipótese atual e não encerra a investigação."
                    if contextos
                    else
                    "Nenhum histórico relevante foi recuperado. "
                    "Isso não prova que o tema nunca foi investigado."
                ),
            },
        }

    @staticmethod
    def _tokens_consulta(texto: str) -> list[str]:
        normalizado = unicodedata.normalize("NFKD", texto.casefold())
        normalizado = "".join(
            caractere
            for caractere in normalizado
            if unicodedata.category(caractere) != "Mn"
        )
        tokens = re.findall(r"[a-z0-9]+", normalizado)
        stopwords = {
            "a", "as", "o", "os", "um", "uma", "uns", "umas",
            "de", "da", "das", "do", "dos", "e", "em", "no", "na",
            "nos", "nas", "por", "para", "com", "sem", "que", "qual",
            "quais", "quando", "onde", "como", "foi", "sao", "ser",
            "esta", "estao", "isso", "esse", "essa", "esses", "essas",
            "eu", "meu", "minha", "meus", "minhas", "voce", "voces",
            "nos", "ja", "ainda", "agora", "sobre", "historico",
            "historica", "investigacao", "contexto", "memoria",
            "recupera", "recuperar", "anterior", "anteriores",
            "nyxal", "nyxos",
        }
        termos_curtos_validos = {"ci", "ae", "api", "pr", "llm", "ia"}
        return [
            token
            for token in tokens
            if token not in stopwords
            and (len(token) >= 3 or token in termos_curtos_validos)
        ]

    def analisar_consulta(
        self,
        consulta: str,
        limite: int = 3,
    ) -> dict[str, Any]:
        """Busca investigações persistidas por necessidade, hipótese e termos relacionados.

        A busca é local, lexical e limitada. Ela não grava memória, não promove
        conhecimento e retorna sempre a proveniência/status epistemológico dos registros.
        """
        if (
            not isinstance(consulta, str)
            or not consulta.strip()
            or len(consulta) > 2000
        ):
            return self._negado(
                "Consulta inválida ou maior que 2.000 caracteres."
            )

        if (
            not isinstance(limite, int)
            or isinstance(limite, bool)
            or not 1 <= limite <= 5
        ):
            return self._negado("Limite precisa estar entre 1 e 5.")

        termos_consulta = set(self._tokens_consulta(consulta))
        if not termos_consulta:
            return {
                "sucesso": True,
                "estado": "consulta_historica_sem_termos",
                "origem": self.FONTE,
                "valor": {
                    "consulta": consulta.strip(),
                    "historico_encontrado": False,
                    "quantidade": 0,
                    "limite": limite,
                    "contextos": [],
                },
            }

        consulta_normalizada = " ".join(self._tokens_consulta(consulta))
        registros = self._memoria.listar()[-500:]
        candidatos: list[tuple[float, int, dict[str, Any]]] = []

        for indice, registro in enumerate(registros):
            if not isinstance(registro, dict):
                continue
            registro_id = registro.get("id")
            ciclo = self._ciclo(registro)
            if not isinstance(registro_id, str) or not isinstance(ciclo, dict):
                continue

            campos = [
                ciclo.get("necessidade"),
                ciclo.get("hipotese"),
                ciclo.get("pergunta"),
                ciclo.get("estado_atual"),
                ciclo.get("historico", []),
                ciclo.get("testes", []),
                ciclo.get("avaliacoes", []),
            ]
            textos = [
                valor if isinstance(valor, str)
                else json.dumps(valor, ensure_ascii=False, sort_keys=True)
                for valor in campos
                if isinstance(valor, (str, list, dict))
            ]
            texto_candidato = " ".join(textos)
            termos_candidato = set(self._tokens_consulta(texto_candidato))
            compartilhados = termos_consulta & termos_candidato

            necessidade = ciclo.get("necessidade")
            necessidade_normalizada = (
                " ".join(self._tokens_consulta(necessidade))
                if isinstance(necessidade, str)
                else ""
            )
            correspondencia_direta = (
                len(consulta_normalizada) >= 8
                and any(
                    consulta_normalizada in " ".join(self._tokens_consulta(texto))
                    for texto in textos
                )
            )
            if necessidade_normalizada and necessidade_normalizada == consulta_normalizada:
                pontuacao = 1.0
            elif correspondencia_direta:
                pontuacao = 0.95
            elif len(compartilhados) >= 2:
                pontuacao = len(compartilhados) / max(1, len(termos_consulta))
                if pontuacao < 0.25:
                    continue
            elif (
                len(compartilhados) == 1
                and len(termos_consulta) <= 3
                and len(next(iter(compartilhados))) >= 6
            ):
                pontuacao = 0.35
            else:
                continue

            contexto_bruto = self._contexto.obter(registro_id)
            if contexto_bruto.get("sucesso") is not True:
                continue
            valor_contexto = contexto_bruto.get("valor")
            if not isinstance(valor_contexto, dict):
                continue
            contexto = deepcopy(valor_contexto)
            contexto["relevancia_lexical"] = round(pontuacao, 3)
            candidatos.append((pontuacao, indice, contexto))

        # Primeiro escolhe por relevância; a saída final volta à ordem cronológica.
        escolhidos = sorted(
            candidatos,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )[:limite]
        escolhidos.sort(key=lambda item: item[1])
        contextos = [item[2] for item in escolhidos]

        return {
            "sucesso": True,
            "estado": (
                "contexto_historico_encontrado"
                if contextos
                else "contexto_historico_nao_encontrado"
            ),
            "origem": self.FONTE,
            "valor": {
                "consulta": consulta.strip(),
                "historico_encontrado": bool(contextos),
                "quantidade": len(contextos),
                "limite": limite,
                "contextos": contextos,
                "interpretacao": (
                    "Os registros são contexto histórico não confiável; "
                    "não provam o estado atual nem encerram uma investigação."
                    if contextos
                    else "Nenhum registro lexicalmente relacionado foi encontrado; "
                    "isso não prova que o tema nunca foi investigado."
                ),
            },
        }

    def executar_capacidade(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoRelevanteNixal não executa capacidades"
        )

    def modificar_arquitetura(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoRelevanteNixal não modifica a arquitetura"
        )

    def promover_conhecimento(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        raise PermissionError(
            "ContextoHistoricoRelevanteNixal não promove conhecimento permanente"
        )

    @staticmethod
    def _selecionar_unicos(
        valor_relevancia: dict[str, Any],
        limite: int,
    ) -> list[dict[str, Any]]:
        diretos = valor_relevancia.get(
            "historico_direto",
            [],
        )

        relacionados = valor_relevancia.get(
            "historico_relacionado",
            [],
        )

        candidatos: list[dict[str, Any]] = []

        if isinstance(
            diretos,
            list,
        ):
            candidatos.extend(
                diretos
            )

        if isinstance(
            relacionados,
            list,
        ):
            candidatos.extend(
                relacionados
            )

        unicos: list[dict[str, Any]] = []
        ids_vistos: set[str] = set()

        for registro in candidatos:
            if not isinstance(
                registro,
                dict,
            ):
                continue

            registro_id = registro.get(
                "id"
            )

            if not isinstance(
                registro_id,
                str,
            ):
                continue

            if registro_id in ids_vistos:
                continue

            ids_vistos.add(
                registro_id
            )
            unicos.append(
                deepcopy(registro)
            )

        # A memória é cronológica. O corte deve ocorrer sobre o
        # final da sequência para recuperar os registros mais recentes.
        return unicos[-limite:]

    @staticmethod
    def _possui_entrada(
        necessidade: str | None,
        hipotese: str | None,
    ) -> bool:
        return (
            (
                isinstance(
                    necessidade,
                    str,
                )
                and bool(
                    necessidade.strip()
                )
            )
            or
            (
                isinstance(
                    hipotese,
                    str,
                )
                and bool(
                    hipotese.strip()
                )
            )
        )

    @staticmethod
    def _negado(
        motivo: str,
    ) -> dict[str, Any]:
        return {
            "sucesso": False,
            "estado": "negado",
            "origem": "contexto_historico_relevante_nixal",
            "valor": None,
            "motivo": motivo,
        }


__all__ = [
    "ContextoHistoricoRelevanteNixal",
]
