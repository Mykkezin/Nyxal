#!/usr/bin/env python3

"""
NIXAL — AGENTE COM RECUPERAÇÃO HÍBRIDA + QWEN

Microetapa 55.3

Arquitetura:

necessidade
    ↓
normalização
    ↓
extração de termos relevantes
    ↓
recuperação híbrida
    ├── similaridade textual
    ├── sobreposição de termos
    ├── exemplos
    ├── objetivo
    └── descrição
    ↓
candidatos relevantes
    ↓
Qwen
    ↓
validação
    ↓
execução

Objetivo:
Melhorar a recuperação de capacidades e reduzir falsos candidatos.

O Qwen nunca executa código diretamente.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict
from difflib import SequenceMatcher
from typing import Any

import ollama

from nixal_capacidades import (
    GerenciadorCapacidades,
)


MODELO = "qwen2:7b"

LIMIAR_RECUPERACAO = 0.42
MAX_CANDIDATOS = 3

# Palavras muito comuns que não ajudam a identificar
# a intenção da necessidade.
STOPWORDS = {
    "a",
    "as",
    "o",
    "os",
    "um",
    "uma",
    "uns",
    "umas",
    "de",
    "da",
    "das",
    "do",
    "dos",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "e",
    "ou",
    "que",
    "qual",
    "quais",
    "como",
    "me",
    "meu",
    "minha",
    "meus",
    "minhas",
    "eu",
    "se",
    "para",
    "por",
    "com",
    "sem",
    "ao",
    "aos",
    "isso",
    "isto",
    "isso",
    "preciso",
    "quero",
    "gostaria",
    "pode",
    "poderia",
    "saber",
    "descobrir",
    "conhecer",
    "verificar",
    "mostrar",
    "mostre",
    "dizer",
    "diga",
}


class AgenteNixalQwen:

    def __init__(self) -> None:

        self.capacidades = (
            GerenciadorCapacidades()
        )

    # ============================================================
    # NORMALIZAÇÃO
    # ============================================================

    def normalizar_texto(
        self,
        texto: str,
    ) -> str:

        texto = texto.lower().strip()

        texto = unicodedata.normalize(
            "NFD",
            texto,
        )

        texto = "".join(
            caractere
            for caractere in texto
            if unicodedata.category(
                caractere
            ) != "Mn"
        )

        texto = re.sub(
            r"[^a-z0-9_]+",
            " ",
            texto,
        )

        texto = re.sub(
            r"\s+",
            " ",
            texto,
        )

        return texto.strip()

    # ============================================================
    # TOKENIZAÇÃO RELEVANTE
    # ============================================================

    def normalizar_token(
        self,
        token: str,
    ) -> str:

        token = token.strip().lower()

        if len(token) <= 2:
            return token

        # Singularização simples para aumentar reutilização
        # sem depender de biblioteca externa.
        if token.endswith("oes") and len(token) > 5:

            token = token[:-3] + "ao"

        elif token.endswith("s") and len(token) > 4:

            token = token[:-1]

        return token

    def extrair_termos(
        self,
        texto: str,
    ) -> set[str]:

        normalizado = self.normalizar_texto(
            texto
        )

        termos = set()

        for token in normalizado.split():

            if token in STOPWORDS:
                continue

            token_normalizado = (
                self.normalizar_token(token)
            )

            if not token_normalizado:
                continue

            if token_normalizado in STOPWORDS:
                continue

            termos.add(
                token_normalizado
            )

        return termos

    # ============================================================
    # SIMILARIDADE TEXTUAL
    # ============================================================

    def similaridade(
        self,
        texto_a: str,
        texto_b: str,
    ) -> float:

        a = self.normalizar_texto(
            texto_a
        )

        b = self.normalizar_texto(
            texto_b
        )

        if not a or not b:
            return 0.0

        return SequenceMatcher(
            None,
            a,
            b,
        ).ratio()

    # ============================================================
    # SOBREPOSIÇÃO DE TERMOS
    # ============================================================

    def sobreposicao_termos(
        self,
        texto_a: str,
        texto_b: str,
    ) -> float:

        termos_a = self.extrair_termos(
            texto_a
        )

        termos_b = self.extrair_termos(
            texto_b
        )

        if not termos_a or not termos_b:
            return 0.0

        intersecao = termos_a.intersection(
            termos_b
        )

        # Mede o quanto dos termos relevantes
        # da necessidade aparecem no texto da capacidade.
        return len(intersecao) / len(
            termos_a
        )

    # ============================================================
    # INTERSEÇÃO ABSOLUTA
    # ============================================================

    def quantidade_termos_comuns(
        self,
        texto_a: str,
        texto_b: str,
    ) -> int:

        termos_a = self.extrair_termos(
            texto_a
        )

        termos_b = self.extrair_termos(
            texto_b
        )

        return len(
            termos_a.intersection(
                termos_b
            )
        )

    # ============================================================
    # EVIDÊNCIA DE UMA FONTE
    # ============================================================

    def pontuar_fonte(
        self,
        necessidade: str,
        texto_fonte: str,
    ) -> float:

        if not texto_fonte:
            return 0.0

        textual = self.similaridade(
            necessidade,
            texto_fonte,
        )

        termos = self.sobreposicao_termos(
            necessidade,
            texto_fonte,
        )

        comuns = self.quantidade_termos_comuns(
            necessidade,
            texto_fonte,
        )

        # Coincidência textual ajuda,
        # mas termos relevantes têm mais peso.
        score = (
            textual * 0.35
            + termos * 0.50
        )

        # Pequeno bônus quando existem pelo menos
        # dois conceitos relevantes em comum.
        if comuns >= 2:
            score += 0.15

        return min(
            score,
            1.0,
        )

    # ============================================================
    # EVIDÊNCIA SEMÂNTICA DA CAPACIDADE
    # ============================================================

    def pontuar_capacidade(
        self,
        necessidade: str,
        capacidade: dict[str, Any],
    ) -> float:

        exemplos = capacidade.get(
            "exemplos",
            [],
        )

        objetivo = capacidade.get(
            "objetivo",
            "",
        )

        descricao = capacidade.get(
            "descricao",
            "",
        )

        # --------------------------------------------------------
        # Exemplos
        # --------------------------------------------------------

        melhor_exemplo = 0.0
        melhor_exemplo_comuns = 0

        for exemplo in exemplos:

            score = self.pontuar_fonte(
                necessidade,
                exemplo,
            )

            comuns = (
                self.quantidade_termos_comuns(
                    necessidade,
                    exemplo,
                )
            )

            if score > melhor_exemplo:

                melhor_exemplo = score
                melhor_exemplo_comuns = comuns

        # --------------------------------------------------------
        # Objetivo
        # --------------------------------------------------------

        score_objetivo = self.pontuar_fonte(
            necessidade,
            objetivo,
        )

        # --------------------------------------------------------
        # Descrição
        # --------------------------------------------------------

        score_descricao = self.pontuar_fonte(
            necessidade,
            descricao,
        )

        # --------------------------------------------------------
        # Termos relevantes da necessidade
        # --------------------------------------------------------

        termos_necessidade = (
            self.extrair_termos(
                necessidade
            )
        )

        # --------------------------------------------------------
        # Combinação
        # --------------------------------------------------------

        score_final = (
            melhor_exemplo * 0.60
            + score_objetivo * 0.25
            + score_descricao * 0.15
        )

        # --------------------------------------------------------
        # Penalização de evidência fraca
        # --------------------------------------------------------

        if (
            len(termos_necessidade) >= 2
            and melhor_exemplo_comuns == 0
        ):

            score_final *= 0.45

        elif (
            len(termos_necessidade) >= 3
            and melhor_exemplo_comuns == 1
        ):

            score_final *= 0.75

        return min(
            max(
                score_final,
                0.0,
            ),
            1.0,
        )

    # ============================================================
    # RECUPERAÇÃO
    # ============================================================

    def recuperar_candidatos(
        self,
        necessidade: str,
    ) -> list[dict[str, Any]]:

        capacidades = (
            self.capacidades.listar_capacidades()
        )

        candidatos = []

        for capacidade in capacidades:

            score = (
                self.pontuar_capacidade(
                    necessidade,
                    capacidade,
                )
            )

            candidatos.append(
                {
                    "nome": capacidade["nome"],
                    "descricao": capacidade[
                        "descricao"
                    ],
                    "objetivo": capacidade[
                        "objetivo"
                    ],
                    "exemplos": capacidade[
                        "exemplos"
                    ],
                    "argumentos": capacidade[
                        "argumentos"
                    ],
                    "score_recuperacao": round(
                        score,
                        4,
                    ),
                }
            )

        candidatos.sort(
            key=lambda item: item[
                "score_recuperacao"
            ],
            reverse=True,
        )

        candidatos_validos = [
            candidato
            for candidato in candidatos
            if candidato[
                "score_recuperacao"
            ] >= LIMIAR_RECUPERACAO
        ]

        return candidatos_validos[
            :MAX_CANDIDATOS
        ]

    # ============================================================
    # PROMPT
    # ============================================================

    def construir_prompt(
        self,
        necessidade: str,
        candidatos: list[dict[str, Any]],
    ) -> str:

        candidatos_json = json.dumps(
            candidatos,
            ensure_ascii=False,
            indent=2,
        )

        return f"""
Você é o módulo de decisão de capacidades da Nixal.

NECESSIDADE:
{necessidade}

CANDIDATOS RECUPERADOS:
{candidatos_json}

Sua tarefa é escolher UMA capacidade entre os candidatos.

REGRAS:

1. Só pode escolher uma capacidade presente nos candidatos.
2. Use os exemplos, objetivo e descrição para decidir.
3. A capacidade precisa realmente atender à necessidade.
4. Se a capacidade exigir argumentos, forneça todos os
   argumentos obrigatórios.
5. Nunca invente argumentos.
6. Nunca invente capacidades.
7. Se nenhum candidato atender à necessidade, retorne null.
8. Não escolha uma capacidade apenas por uma palavra isolada.
9. Considere o significado completo da necessidade.
10. Retorne somente JSON válido.
11. Não escreva explicações.
12. Não execute código.

FORMATO:

{{
  "capacidade": "nome_da_capacidade",
  "argumentos": {{}}
}}

OU:

{{
  "capacidade": null,
  "argumentos": {{}}
}}
""".strip()

    # ============================================================
    # LIMPEZA
    # ============================================================

    def limpar_resposta(
        self,
        texto: str,
    ) -> str:

        texto = texto.strip()

        if texto.startswith("```"):

            linhas = texto.splitlines()

            if linhas:
                linhas = linhas[1:]

            if (
                linhas
                and linhas[-1].strip()
                == "```"
            ):
                linhas = linhas[:-1]

            texto = "\n".join(
                linhas
            ).strip()

        return texto

    # ============================================================
    # CONSULTA AO QWEN
    # ============================================================

    def consultar_qwen(
        self,
        prompt: str,
    ) -> dict[str, Any]:

        try:

            resposta = ollama.chat(
                model=MODELO,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                options={
                    "temperature": 0.0,
                },
            )

        except Exception as erro:

            return {
                "sucesso": False,
                "dados": None,
                "erro": (
                    "Falha ao consultar Qwen: "
                    f"{type(erro).__name__}: "
                    f"{erro}"
                ),
            }

        texto = (
            resposta["message"][
                "content"
            ].strip()
        )

        texto_limpo = (
            self.limpar_resposta(
                texto
            )
        )

        try:

            dados = json.loads(
                texto_limpo
            )

        except json.JSONDecodeError as erro:

            return {
                "sucesso": False,
                "dados": None,
                "erro": (
                    "Qwen não retornou JSON válido: "
                    f"{erro}"
                ),
                "resposta_bruta": texto,
            }

        if not isinstance(
            dados,
            dict,
        ):

            return {
                "sucesso": False,
                "dados": None,
                "erro": (
                    "Qwen retornou uma estrutura "
                    "que não é objeto JSON."
                ),
                "resposta_bruta": texto,
            }

        return {
            "sucesso": True,
            "dados": dados,
            "erro": None,
            "resposta_bruta": texto,
        }

    # ============================================================
    # VALIDAÇÃO
    # ============================================================

    def validar_proposta(
        self,
        necessidade: str,
        proposta: dict[str, Any],
        candidatos: list[dict[str, Any]],
    ) -> dict[str, Any]:

        capacidade = proposta.get(
            "capacidade"
        )

        argumentos = proposta.get(
            "argumentos",
            {},
        )

        # --------------------------------------------------------
        # ABSTENÇÃO
        # --------------------------------------------------------

        if capacidade is None:

            return {
                "valida": True,
                "capacidade": None,
                "argumentos": {},
                "motivo": "abstencao",
            }

        # --------------------------------------------------------
        # NOME
        # --------------------------------------------------------

        if not isinstance(
            capacidade,
            str,
        ):

            return {
                "valida": False,
                "capacidade": None,
                "argumentos": {},
                "motivo": (
                    "Nome da capacidade inválido."
                ),
            }

        capacidade = capacidade.strip()

        # --------------------------------------------------------
        # CANDIDATO
        # --------------------------------------------------------

        nomes_candidatos = {
            candidato["nome"]
            for candidato in candidatos
        }

        if capacidade not in nomes_candidatos:

            return {
                "valida": False,
                "capacidade": capacidade,
                "argumentos": argumentos,
                "motivo": (
                    "Capacidade não está entre "
                    "os candidatos recuperados."
                ),
            }

        # --------------------------------------------------------
        # ARGUMENTOS
        # --------------------------------------------------------

        if not isinstance(
            argumentos,
            dict,
        ):

            return {
                "valida": False,
                "capacidade": capacidade,
                "argumentos": {},
                "motivo": (
                    "Argumentos precisam ser "
                    "um objeto JSON."
                ),
            }

        valido, erro = (
            self.capacidades.validar_argumentos(
                capacidade,
                argumentos,
            )
        )

        if not valido:

            return {
                "valida": False,
                "capacidade": capacidade,
                "argumentos": argumentos,
                "motivo": erro,
            }

        # --------------------------------------------------------
        # EVIDÊNCIA SEMÂNTICA
        # --------------------------------------------------------

        candidato = next(
            candidato
            for candidato in candidatos
            if candidato["nome"]
            == capacidade
        )

        score = self.pontuar_capacidade(
            necessidade,
            candidato,
        )

        if score < LIMIAR_RECUPERACAO:

            return {
                "valida": False,
                "capacidade": capacidade,
                "argumentos": argumentos,
                "motivo": (
                    "A capacidade escolhida não "
                    "possui evidência semântica suficiente "
                    f"(score={score:.4f})."
                ),
            }

        return {
            "valida": True,
            "capacidade": capacidade,
            "argumentos": argumentos,
            "motivo": "validada",
            "score_semantico": round(
                score,
                4,
            ),
        }

    # ============================================================
    # CORREÇÃO
    # ============================================================

    def corrigir_proposta(
        self,
        necessidade: str,
        proposta_anterior: dict[str, Any],
        motivo: str,
        candidatos: list[dict[str, Any]],
    ) -> dict[str, Any]:

        candidatos_json = json.dumps(
            candidatos,
            ensure_ascii=False,
            indent=2,
        )

        proposta_json = json.dumps(
            proposta_anterior,
            ensure_ascii=False,
            indent=2,
        )

        prompt = f"""
Você é o verificador de decisão da Nixal.

NECESSIDADE:
{necessidade}

PROPOSTA ANTERIOR:
{proposta_json}

PROBLEMA ENCONTRADO:
{motivo}

CANDIDATOS DISPONÍVEIS:
{candidatos_json}

Reavalie a decisão.

REGRAS:

1. Escolha somente entre os candidatos.
2. A capacidade deve realmente atender à necessidade.
3. Forneça argumentos obrigatórios.
4. Não invente argumentos.
5. Se nenhuma capacidade servir, use null.
6. Considere o significado completo da necessidade.
7. Retorne somente JSON.
8. Não explique sua resposta.

FORMATO:

{{
  "capacidade": "nome_da_capacidade",
  "argumentos": {{}}
}}

OU:

{{
  "capacidade": null,
  "argumentos": {{}}
}}
""".strip()

        return self.consultar_qwen(
            prompt
        )

    # ============================================================
    # SELEÇÃO COMPLETA
    # ============================================================

    def selecionar_capacidade(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        candidatos = (
            self.recuperar_candidatos(
                necessidade
            )
        )

        # --------------------------------------------------------
        # SEM CANDIDATOS
        # --------------------------------------------------------

        if not candidatos:

            return {
                "sucesso": True,
                "capacidade": None,
                "argumentos": {},
                "candidatos": [],
                "tentativa_correcao": False,
                "erro": None,
                "motivo": (
                    "Nenhuma capacidade "
                    "possui evidência suficiente."
                ),
            }

        # --------------------------------------------------------
        # PRIMEIRA DECISÃO
        # --------------------------------------------------------

        prompt = self.construir_prompt(
            necessidade,
            candidatos,
        )

        primeira = self.consultar_qwen(
            prompt
        )

        if not primeira["sucesso"]:

            return {
                "sucesso": False,
                "capacidade": None,
                "argumentos": {},
                "candidatos": candidatos,
                "tentativa_correcao": False,
                "erro": primeira["erro"],
                "resposta_bruta": primeira.get(
                    "resposta_bruta"
                ),
            }

        proposta = primeira["dados"]

        validacao = self.validar_proposta(
            necessidade,
            proposta,
            candidatos,
        )

        if validacao["valida"]:

            return {
                "sucesso": True,
                "capacidade": validacao[
                    "capacidade"
                ],
                "argumentos": validacao[
                    "argumentos"
                ],
                "candidatos": candidatos,
                "tentativa_correcao": False,
                "erro": None,
                "motivo": validacao[
                    "motivo"
                ],
                "score_semantico": validacao.get(
                    "score_semantico"
                ),
                "resposta_bruta": primeira.get(
                    "resposta_bruta"
                ),
            }

        # --------------------------------------------------------
        # SEGUNDA DECISÃO
        # --------------------------------------------------------

        correcao = self.corrigir_proposta(
            necessidade,
            proposta,
            validacao["motivo"],
            candidatos,
        )

        if not correcao["sucesso"]:

            return {
                "sucesso": False,
                "capacidade": None,
                "argumentos": {},
                "candidatos": candidatos,
                "tentativa_correcao": True,
                "erro": correcao["erro"],
                "resposta_bruta": (
                    primeira.get(
                        "resposta_bruta"
                    )
                ),
            }

        proposta_corrigida = (
            correcao["dados"]
        )

        validacao_corrigida = (
            self.validar_proposta(
                necessidade,
                proposta_corrigida,
                candidatos,
            )
        )

        if not validacao_corrigida[
            "valida"
        ]:

            return {
                "sucesso": True,
                "capacidade": None,
                "argumentos": {},
                "candidatos": candidatos,
                "tentativa_correcao": True,
                "erro": None,
                "motivo": (
                    "A proposta inicial e a "
                    "correção foram rejeitadas."
                ),
                "resposta_inicial": primeira.get(
                    "resposta_bruta"
                ),
                "resposta_correcao": (
                    correcao.get(
                        "resposta_bruta"
                    )
                ),
            }

        return {
            "sucesso": True,
            "capacidade": (
                validacao_corrigida[
                    "capacidade"
                ]
            ),
            "argumentos": (
                validacao_corrigida[
                    "argumentos"
                ]
            ),
            "candidatos": candidatos,
            "tentativa_correcao": True,
            "erro": None,
            "motivo": (
                "Decisão corrigida pelo Qwen."
            ),
            "score_semantico": (
                validacao_corrigida.get(
                    "score_semantico"
                )
            ),
            "resposta_inicial": primeira.get(
                "resposta_bruta"
            ),
            "resposta_correcao": (
                correcao.get(
                    "resposta_bruta"
                )
            ),
        }

    # ============================================================
    # ATENDER
    # ============================================================

    def atender(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        selecao = (
            self.selecionar_capacidade(
                necessidade
            )
        )

        if not selecao["sucesso"]:

            return {
                "atendida": False,
                "necessidade": necessidade,
                "capacidade_escolhida": None,
                "argumentos": {},
                "selecao": selecao,
                "resultado": None,
            }

        capacidade = (
            selecao["capacidade"]
        )

        argumentos = (
            selecao["argumentos"]
        )

        if capacidade is None:

            return {
                "atendida": False,
                "necessidade": necessidade,
                "capacidade_escolhida": None,
                "argumentos": {},
                "selecao": selecao,
                "resultado": None,
            }

        resultado = (
            self.capacidades.executar(
                capacidade,
                **argumentos,
            )
        )

        return {
            "atendida": resultado.sucesso,
            "necessidade": necessidade,
            "capacidade_escolhida": capacidade,
            "argumentos": argumentos,
            "selecao": selecao,
            "resultado": asdict(
                resultado
            ),
        }

    # ============================================================
    # TESTE
    # ============================================================

    def testar(
        self,
        necessidade: str,
    ) -> None:

        print()
        print("-" * 60)
        print(
            f"NECESSIDADE: {necessidade}"
        )
        print("-" * 60)

        resultado = self.atender(
            necessidade
        )

        print(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
            )
        )


# ================================================================
# MAIN
# ================================================================

def main() -> None:

    print()
    print("=" * 60)
    print("NIXAL — AGENTE COM RECUPERAÇÃO HÍBRIDA + QWEN")
    print("=" * 60)

    agente = AgenteNixalQwen()

    # ------------------------------------------------------------
    # Teste 1
    # ------------------------------------------------------------

    agente.testar(
        "Preciso saber a hora."
    )

    # ------------------------------------------------------------
    # Teste 2
    # ------------------------------------------------------------

    agente.testar(
        "Preciso verificar como está meu corpo."
    )

    # ------------------------------------------------------------
    # Teste 3
    # ------------------------------------------------------------

    agente.testar(
        "Quero saber quais eventos meu corpo registrou."
    )

    # ------------------------------------------------------------
    # Teste 4
    # ------------------------------------------------------------

    agente.testar(
        "Quero conhecer os arquivos do projeto."
    )

    # ------------------------------------------------------------
    # Teste 5
    # ------------------------------------------------------------

    agente.testar(
        "Leia o arquivo capacidades_nixal.json."
    )

    # ------------------------------------------------------------
    # Teste 6
    # ------------------------------------------------------------

    agente.testar(
        "Leia o arquivo estado_corpo_nixal.json."
    )

    # ------------------------------------------------------------
    # Teste 7
    # ------------------------------------------------------------

    agente.testar(
        "Preciso descobrir a temperatura do mundo."
    )

    print()
    print("=" * 60)
    print("MICROETAPA 55.3 FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
