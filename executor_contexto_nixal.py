#!/usr/bin/env python3

"""
NIXAL — EXECUTOR DE OPERAÇÕES SOBRE CONTEXTO

Microetapa 56.3.10

Objetivos:

1. Executar operações declaradas no catálogo de contexto.
2. Separar execução de operação de registro de operação.
3. Nunca executar capacidades.
4. Operar somente sobre informação já presente no contexto.
5. Recusar informação ausente.
6. Recusar seleção ambígua.
7. Preservar o contexto original sem modificá-lo.
8. Permitir seleção de informação estruturada, não apenas arquivos.
9. Manter seleção explícita de arquivos como caso especializado.
10. Nunca criar informação nova durante uma operação de contexto.

Operação implementada nesta etapa:

    selecionar
"""

from __future__ import annotations

import json
import re
from typing import Any

from nixal_operacoes_contexto import (
    OperacoesContextoNixal,
)


STOPWORDS = {
    "a",
    "o",
    "os",
    "as",
    "um",
    "uma",
    "uns",
    "umas",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "ou",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "que",
    "qual",
    "quais",
    "me",
    "minha",
    "meu",
    "minhas",
    "meus",
    "para",
    "por",
    "com",
    "como",
    "está",
    "esta",
    "estao",
    "estão",
    "quero",
    "preciso",
    "saber",
    "descobrir",
    "isso",
    "nessa",
    "nesse",
    "do",
    "da",
    "ao",
    "aos",
    "às",
    "foi",
    "ser",
    "ter",
    "vai",
    "vou",
}


class ExecutorContextoNixal:

    def __init__(self) -> None:

        self.registro = (
            OperacoesContextoNixal()
        )

        self.implementacoes = {
            "selecionar": (
                self._executar_selecionar
            ),
        }

    # ============================================================
    # NORMALIZAÇÃO
    # ============================================================

    @staticmethod
    def _normalizar_texto(
        texto: str,
    ) -> str:

        texto = texto.lower()

        substituicoes = {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }

        for origem, destino in (
            substituicoes.items()
        ):

            texto = texto.replace(
                origem,
                destino,
            )

        texto = re.sub(
            r"[^a-z0-9_.-]+",
            " ",
            texto,
        )

        return texto.strip()

    @classmethod
    def _tokens(
        cls,
        texto: str,
    ) -> set[str]:

        normalizado = cls._normalizar_texto(
            texto
        )

        tokens: set[str] = set()

        for token in normalizado.split():

            token = token.strip(
                ".,;:!?\"'()[]{}"
            )

            if not token:
                continue

            if token in STOPWORDS:
                continue

            if len(token) < 3:
                continue

            if token.endswith("ões"):
                token = token[:-3]

            elif (
                token.endswith("s")
                and len(token) > 5
            ):
                token = token[:-1]

            tokens.add(token)

        return tokens

    # ============================================================
    # EXTRAÇÃO DE ARQUIVOS
    # ============================================================

    def _extrair_arquivos(
        self,
        valor: Any,
    ) -> list[str]:

        encontrados: list[str] = []

        def visitar(
            item: Any,
        ) -> None:

            if isinstance(
                item,
                dict,
            ):

                for valor_interno in item.values():

                    visitar(
                        valor_interno
                    )

                return

            if isinstance(
                item,
                list,
            ):

                for valor_interno in item:

                    visitar(
                        valor_interno
                    )

                return

            if isinstance(
                item,
                str,
            ):

                candidato = item.strip()

                if re.fullmatch(
                    r"[^/\n]+",
                    candidato,
                ) and "." in candidato:

                    if candidato not in encontrados:

                        encontrados.append(
                            candidato
                        )

        visitar(
            valor
        )

        return encontrados

    # ============================================================
    # CANDIDATOS DE INFORMAÇÃO
    # ============================================================

    def _serializar_candidato(
        self,
        valor: Any,
    ) -> str:

        if isinstance(
            valor,
            str,
        ):
            return valor

        try:

            return json.dumps(
                valor,
                ensure_ascii=False,
                sort_keys=True,
            )

        except (
            TypeError,
            ValueError,
        ):

            return str(valor)

    def _extrair_candidatos_informacao(
        self,
        contexto: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:

        candidatos: list[dict[str, Any]] = []

        def adicionar(
            *,
            etapa: int,
            valor: Any,
            caminho: str,
            tipo: str,
            prioridade: int,
        ) -> None:

            texto = self._serializar_candidato(
                valor
            )

            candidato = {
                "etapa": etapa,
                "valor": valor,
                "caminho": caminho,
                "tipo": tipo,
                "prioridade": prioridade,
                "texto": texto,
            }

            candidatos.append(
                candidato
            )

        for numero_etapa, registro in contexto.items():

            if not isinstance(
                numero_etapa,
                int,
            ):
                continue

            if not isinstance(
                registro,
                dict,
            ):
                continue

            if registro.get(
                "atendida"
            ) is not True:
                continue

            if registro.get(
                "sucesso_operacao"
            ) is not True:
                continue

            resultado = registro.get(
                "resultado"
            )

            if not isinstance(
                resultado,
                dict,
            ):
                continue

            if resultado.get(
                "sucesso"
            ) is not True:
                continue

            if "resultado" not in resultado:
                continue

            valor = resultado.get(
                "resultado"
            )

            adicionar(
                etapa=numero_etapa,
                valor=valor,
                caminho=(
                    f"etapa.{numero_etapa}"
                    ".resultado"
                    ".resultado"
                ),
                tipo=(
                    "informacao_estruturada"
                    if isinstance(
                        valor,
                        (dict, list),
                    )
                    else "informacao"
                ),
                prioridade=3,
            )

            # Um resultado em lista pode conter itens nomeáveis,
            # como arquivos. Esses itens são candidatos individuais
            # sem remover o candidato estrutural original.
            if isinstance(
                valor,
                list,
            ):

                for indice, item in enumerate(
                    valor
                ):

                    if isinstance(
                        item,
                        (str, int, float, bool),
                    ):

                        adicionar(
                            etapa=numero_etapa,
                            valor=item,
                            caminho=(
                                f"etapa.{numero_etapa}"
                                ".resultado.resultado"
                                f"[{indice}]"
                            ),
                            tipo="item",
                            prioridade=4,
                        )

        return candidatos

    # ============================================================
    # SELEÇÃO EXPLÍCITA DE ARQUIVO
    # ============================================================

    def _selecionar_arquivo_explicitamente(
        self,
        consulta: str,
        contexto: dict[int, dict[str, Any]],
    ) -> dict[str, Any] | None:

        arquivos = []

        for arquivo in self._extrair_arquivos(
            contexto
        ):

            if arquivo.lower().endswith(
                ".json"
            ):

                if arquivo not in arquivos:

                    arquivos.append(
                        arquivo
                    )

        if not arquivos:
            return None

        consulta_normalizada = (
            self._normalizar_texto(
                consulta
            )
        )

        nomes_mencionados = re.findall(
            r"[\w.-]+\.json",
            consulta_normalizada,
            re.IGNORECASE,
        )

        if not nomes_mencionados:
            return None

        nomes_encontrados = []

        for nome in nomes_mencionados:

            for arquivo in arquivos:

                if (
                    nome.lower()
                    == arquivo.lower()
                ):

                    if (
                        arquivo
                        not in nomes_encontrados
                    ):

                        nomes_encontrados.append(
                            arquivo
                        )

        # Um único nome explícito.
        if len(
            nomes_mencionados
        ) == 1:

            if len(
                nomes_encontrados
            ) == 1:

                return {
                    "sucesso": True,
                    "tipo": "contexto",
                    "operacao": "selecionar",
                    "valor": (
                        nomes_encontrados[0]
                    ),
                    "origem": "contexto",
                    "candidatos": arquivos,
                    "erro": None,
                }

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": None,
                "origem": "contexto",
                "candidatos": arquivos,
                "erro": (
                    "A informação solicitada "
                    "não existe no contexto."
                ),
            }

        # Mais de um nome explícito.
        if len(
            nomes_mencionados
        ) > 1:

            if len(
                nomes_encontrados
            ) == 1:

                return {
                    "sucesso": True,
                    "tipo": "contexto",
                    "operacao": "selecionar",
                    "valor": (
                        nomes_encontrados[0]
                    ),
                    "origem": "contexto",
                    "candidatos": arquivos,
                    "erro": None,
                }

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": None,
                "candidatos": arquivos,
                "erro": (
                    "A seleção explícita não pode "
                    "ser resolvida com segurança."
                ),
            }

        return None

    # ============================================================
    # SELEÇÃO DE INFORMAÇÃO GERAL
    # ============================================================

    def _pontuar_candidato(
        self,
        consulta: str,
        candidato: dict[str, Any],
    ) -> tuple[int, list[str]]:

        tokens_consulta = self._tokens(
            consulta
        )

        tokens_candidato = self._tokens(
            candidato["texto"]
        )

        intersecao = sorted(
            tokens_consulta
            & tokens_candidato
        )

        score = len(
            intersecao
        )

        # Informação estruturada ganha uma pequena prioridade
        # quando há empate com nomes de arquivo ou itens simples.
        if (
            candidato["tipo"]
            == "informacao_estruturada"
            and score > 0
        ):
            score += 1

        # A prioridade é apenas um desempate estrutural.
        score += max(
            0,
            5 - candidato["prioridade"],
        )

        return (
            score,
            intersecao,
        )

    def _executar_selecionar_informacao(
        self,
        consulta: str,
        contexto: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:

        candidatos = (
            self._extrair_candidatos_informacao(
                contexto
            )
        )

        if not candidatos:

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": None,
                "origem": "contexto",
                "candidatos": [],
                "erro": (
                    "Nenhuma informação produzida "
                    "por etapas anteriores foi encontrada "
                    "no contexto."
                ),
            }

        avaliados = []

        for candidato in candidatos:

            score, evidencias = (
                self._pontuar_candidato(
                    consulta,
                    candidato,
                )
            )

            avaliados.append(
                {
                    **candidato,
                    "score": score,
                    "evidencias": evidencias,
                }
            )

        melhor_score = max(
            item["score"]
            for item in avaliados
        )

        if melhor_score <= 0:

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": None,
                "origem": "contexto",
                "candidatos": [
                    {
                        "etapa": item["etapa"],
                        "caminho": item["caminho"],
                        "tipo": item["tipo"],
                        "evidencias": item["evidencias"],
                    }
                    for item in avaliados
                ],
                "erro": (
                    "Nenhuma informação compatível "
                    "foi encontrada no contexto."
                ),
            }

        melhores = [
            item
            for item in avaliados
            if item["score"]
            == melhor_score
        ]

        # Mesma informação física pode aparecer duplicada
        # no contexto. Deduplicamos por representação exata.
        unicos: dict[str, dict[str, Any]] = {}

        for item in melhores:

            assinatura = item["texto"]

            if assinatura not in unicos:

                unicos[assinatura] = item

        melhores = list(
            unicos.values()
        )

        if len(melhores) != 1:

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": None,
                "origem": "contexto",
                "candidatos": [
                    {
                        "etapa": item["etapa"],
                        "caminho": item["caminho"],
                        "tipo": item["tipo"],
                        "score": item["score"],
                        "evidencias": item["evidencias"],
                    }
                    for item in melhores
                ],
                "erro": (
                    "A seleção é ambígua: "
                    "mais de uma informação do contexto "
                    "possui evidência equivalente."
                ),
            }

        escolhido = melhores[0]

        return {
            "sucesso": True,
            "tipo": "contexto",
            "operacao": "selecionar",
            "valor": escolhido["valor"],
            "origem": "contexto",
            "etapa_origem": escolhido["etapa"],
            "caminho_origem": escolhido["caminho"],
            "tipo_informacao": escolhido["tipo"],
            "evidencias": escolhido["evidencias"],
            "candidatos": [
                {
                    "etapa": item["etapa"],
                    "caminho": item["caminho"],
                    "tipo": item["tipo"],
                    "score": item["score"],
                    "evidencias": item["evidencias"],
                }
                for item in avaliados
            ],
            "erro": None,
        }

    # ============================================================
    # SELECIONAR
    # ============================================================

    def _executar_selecionar(
        self,
        argumentos: dict[str, Any],
        contexto: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:

        consulta = argumentos.get(
            "consulta"
        )

        if not isinstance(
            consulta,
            str,
        ):

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": None,
                "erro": (
                    "O argumento 'consulta' "
                    "precisa ser uma string."
                ),
            }

        consulta = consulta.strip()

        if not consulta:

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": "selecionar",
                "valor": None,
                "erro": (
                    "A consulta de seleção "
                    "não pode ser vazia."
                ),
            }

        resultado_arquivo = (
            self._selecionar_arquivo_explicitamente(
                consulta,
                contexto,
            )
        )

        if resultado_arquivo is not None:
            return resultado_arquivo

        return (
            self._executar_selecionar_informacao(
                consulta,
                contexto,
            )
        )

    # ============================================================
    # EXECUÇÃO GENÉRICA
    # ============================================================

    def executar(
        self,
        nome: str,
        argumentos: dict[str, Any],
        contexto: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:

        especificacao = (
            self.registro.obter_especificacao(
                nome
            )
        )

        if especificacao is None:

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": nome,
                "valor": None,
                "erro": (
                    f"Operação de contexto "
                    f"'{nome}' não existe."
                ),
            }

        validacao = (
            self.registro.validar_argumentos(
                nome,
                argumentos,
            )
        )

        if not validacao["valido"]:

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": nome,
                "valor": None,
                "erro": validacao[
                    "erro"
                ],
            }

        implementacao = (
            self.implementacoes.get(
                nome
            )
        )

        if implementacao is None:

            return {
                "sucesso": False,
                "tipo": "contexto",
                "operacao": nome,
                "valor": None,
                "erro": (
                    f"A operação '{nome}' "
                    "está registrada, mas ainda "
                    "não possui implementação."
                ),
            }

        return implementacao(
            argumentos,
            contexto,
        )


# ================================================================
# MAIN
# ================================================================

def main() -> None:

    executor = (
        ExecutorContextoNixal()
    )

    contexto_arquivos = {
        1: {
            "necessidade": (
                "Listar os arquivos do projeto"
            ),
            "atendida": True,
            "sucesso_operacao": True,
            "resultado": {
                "sucesso": True,
                "capacidade": "listar_arquivos",
                "resultado": [
                    "nixal.py",
                    "capacidades_nixal.json",
                    "estado_corpo_nixal.json",
                    "memoria_corporal_nixal.json",
                ],
            },
        }
    }

    contexto_corpo = {
        1: {
            "necessidade": (
                "Consultar o estado atual "
                "do corpo computacional da Nixal"
            ),
            "atendida": True,
            "sucesso_operacao": True,
            "resultado": {
                "sucesso": True,
                "capacidade": "ler_estado_corpo",
                "resultado": {
                    "identidade": {
                        "nome": "Nixal"
                    },
                    "corpo": {
                        "cpu": {
                            "uso_percentual": 1.5
                        },
                        "memoria": {
                            "uso_percentual": 23.0
                        },
                        "gpu": [
                            {
                                "temperatura_c": 30.0
                            }
                        ],
                    },
                    "percepcao": {
                        "origem": (
                            "corpo_computacional"
                        )
                    },
                },
            },
        }
    }

    print()
    print("=" * 60)
    print(
        "NIXAL — EXECUTOR DE OPERAÇÕES SOBRE CONTEXTO"
    )
    print("=" * 60)

    print()
    print(
        "TESTE 1 — SELEÇÃO EXPLÍCITA DE ARQUIVO"
    )

    resultado_1 = (
        executor.executar(
            "selecionar",
            {
                "consulta": (
                    "Selecionar o arquivo "
                    "capacidades_nixal.json da lista."
                )
            },
            contexto_arquivos,
        )
    )

    print(
        json.dumps(
            resultado_1,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(
        "TESTE 2 — SELEÇÃO DE INFORMAÇÃO ESTRUTURADA"
    )

    resultado_2 = (
        executor.executar(
            "selecionar",
            {
                "consulta": (
                    "Selecionar o estado atual "
                    "do corpo computacional da Nixal."
                )
            },
            contexto_corpo,
        )
    )

    print(
        json.dumps(
            resultado_2,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(
        "TESTE 3 — AUSÊNCIA"
    )

    resultado_3 = (
        executor.executar(
            "selecionar",
            {
                "consulta": (
                    "Selecionar o arquivo "
                    "configuracao.json da lista."
                )
            },
            contexto_arquivos,
        )
    )

    print(
        json.dumps(
            resultado_3,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(
        "TESTE 4 — OPERAÇÃO INEXISTENTE"
    )

    resultado_4 = (
        executor.executar(
            "operacao_inexistente",
            {},
            contexto_arquivos,
        )
    )

    print(
        json.dumps(
            resultado_4,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("=" * 60)
    print(
        "EXECUTOR FINALIZADO"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
