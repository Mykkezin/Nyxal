#!/usr/bin/env python3

"""
NIXAL — COMPOSIÇÃO DE CAPACIDADES

Microetapa 56.3.8

Objetivos:

1. Ler domínios declarados pelas capacidades.
2. Usar evidências de domínio vindas do catálogo, e não listas
   fixas de capacidades dentro do compositor.
3. Diferenciar domínio conhecido, domínio externo e domínio
   desconhecido.
4. Detectar troca de domínio entre necessidade e plano.
5. Manter composição entre etapas.
6. Manter validação real de sucesso.
7. Manter o agente 55.3 como resolvedor final.
8. Preservar o comportamento de segurança da 56.3.7.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import ollama

from nixal_agente_qwen import AgenteNixalQwen


MODELO = "qwen2:7b"

MAX_PASSOS = 3

MAX_CONTEXTO_CHARS = 5000

LIMIAR_COBERTURA_PLANO = 0.55

ARQUIVO_CAPACIDADES = Path(
    "capacidades_nixal.json"
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
    "depois",
    "isso",
    "nessa",
    "nesse",
    "ao",
    "aos",
    "às",
    "foi",
    "ser",
    "ter",
    "vai",
    "vou",
    "levar",
    "levando",
    "em",
    "consideração",
    "anteriormente",
}


class CompositorNixal:

    def __init__(self) -> None:

        self.agente = AgenteNixalQwen()

        self.catalogo = (
            self._carregar_catalogo()
        )

        self.mapa_capacidades = {
            item["nome"]: item
            for item in self.catalogo
        }

    # ============================================================
    # CATÁLOGO
    # ============================================================

    def _carregar_catalogo(
        self,
    ) -> list[dict[str, Any]]:

        if not ARQUIVO_CAPACIDADES.exists():

            raise FileNotFoundError(
                "Arquivo capacidades_nixal.json "
                "não encontrado."
            )

        try:

            with ARQUIVO_CAPACIDADES.open(
                "r",
                encoding="utf-8",
            ) as arquivo:

                dados = json.load(
                    arquivo
                )

        except json.JSONDecodeError as erro:

            raise ValueError(
                "capacidades_nixal.json "
                f"possui JSON inválido: {erro}"
            ) from erro

        if not isinstance(
            dados,
            list,
        ):

            raise ValueError(
                "capacidades_nixal.json "
                "precisa conter uma lista."
            )

        catalogo = []

        for item in dados:

            if not isinstance(
                item,
                dict,
            ):
                continue

            nome = item.get(
                "nome"
            )

            if not isinstance(
                nome,
                str,
            ):
                continue

            nome = nome.strip()

            if not nome:
                continue

            dominios = item.get(
                "dominios",
                [],
            )

            if not isinstance(
                dominios,
                list,
            ):
                dominios = []

            dominios = [
                valor.strip()
                for valor in dominios
                if isinstance(
                    valor,
                    str,
                )
                and valor.strip()
            ]

            evidencias_dominio = item.get(
                "evidencias_dominio",
                [],
            )

            if not isinstance(
                evidencias_dominio,
                list,
            ):
                evidencias_dominio = []

            evidencias_dominio = [
                valor.strip()
                for valor in evidencias_dominio
                if isinstance(
                    valor,
                    str,
                )
                and valor.strip()
            ]

            catalogo.append(
                {
                    "nome": nome,
                    "descricao": item.get(
                        "descricao",
                        "",
                    ),
                    "objetivo": item.get(
                        "objetivo",
                        "",
                    ),
                    "dominios": dominios,
                    "evidencias_dominio": (
                        evidencias_dominio
                    ),
                    "exemplos": item.get(
                        "exemplos",
                        [],
                    ),
                    "argumentos": item.get(
                        "argumentos",
                        {},
                    ),
                }
            )

        if not catalogo:

            raise ValueError(
                "Nenhuma capacidade válida "
                "foi encontrada."
            )

        return catalogo

    # ============================================================
    # NORMALIZAÇÃO TEXTUAL
    # ============================================================

    def _normalizar_texto(
        self,
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

    def _tokens(
        self,
        texto: str,
    ) -> set[str]:

        normalizado = (
            self._normalizar_texto(
                texto
            )
        )

        tokens = set()

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

            if token.endswith(
                "ões"
            ):

                token = token[:-3]

            elif (
                token.endswith("s")
                and len(token) > 5
            ):

                token = token[:-1]

            tokens.add(
                token
            )

        return tokens

    # ============================================================
    # CAPACIDADE POR TEXTO
    # ============================================================

    def _capacidade_por_texto(
        self,
        texto: str,
    ) -> dict[str, Any] | None:

        normalizado = (
            self._normalizar_texto(
                texto
            )
        )

        for nome, capacidade in (
            self.mapa_capacidades.items()
        ):

            nome_normalizado = (
                self._normalizar_texto(
                    nome
                )
            )

            if normalizado == nome_normalizado:

                return capacidade

        return None

    # ============================================================
    # NORMALIZAÇÃO DE ETAPA
    # ============================================================

    def normalizar_necessidade_passo(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        capacidade = (
            self._capacidade_por_texto(
                necessidade
            )
        )

        if capacidade is None:

            return {
                "necessidade": necessidade,
                "foi_convertida": False,
                "capacidade_original": None,
            }

        objetivo = capacidade.get(
            "objetivo"
        )

        if not isinstance(
            objetivo,
            str,
        ):

            objetivo = capacidade.get(
                "descricao",
                necessidade,
            )

        objetivo = objetivo.strip()

        if not objetivo:

            objetivo = necessidade

        return {
            "necessidade": objetivo,
            "foi_convertida": True,
            "capacidade_original": capacidade[
                "nome"
            ],
        }

    def normalizar_plano(
        self,
        passos: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        normalizados = []

        for passo in passos:

            convertido = (
                self.normalizar_necessidade_passo(
                    passo["necessidade"]
                )
            )

            normalizados.append(
                {
                    "ordem": passo["ordem"],
                    "necessidade": convertido[
                        "necessidade"
                    ],
                    "necessidade_original": passo[
                        "necessidade"
                    ],
                    "depende_de": passo[
                        "depende_de"
                    ],
                    "foi_convertida": convertido[
                        "foi_convertida"
                    ],
                    "capacidade_original": convertido[
                        "capacidade_original"
                    ],
                }
            )

        return normalizados

    # ============================================================
    # DEPENDÊNCIAS
    # ============================================================

    def normalizar_dependencias(
        self,
        indice_passo: int,
        dependencias: list[Any],
    ) -> dict[str, Any]:

        if not isinstance(
            dependencias,
            list,
        ):

            return {
                "sucesso": False,
                "dependencias": [],
                "erro": (
                    f"As dependências do passo "
                    f"{indice_passo} precisam ser uma lista."
                ),
            }

        valores = []

        for dependencia in dependencias:

            if not isinstance(
                dependencia,
                int,
            ):

                return {
                    "sucesso": False,
                    "dependencias": [],
                    "erro": (
                        f"A dependência '{dependencia}' "
                        f"do passo {indice_passo} não é inteira."
                    ),
                }

            valores.append(
                dependencia
            )

        if 0 in valores:

            valores = [
                valor + 1
                for valor in valores
            ]

        normalizadas = []

        for valor in valores:

            if valor not in normalizadas:

                normalizadas.append(
                    valor
                )

        for dependencia in normalizadas:

            if dependencia < 1:

                return {
                    "sucesso": False,
                    "dependencias": [],
                    "erro": (
                        f"A dependência {dependencia} "
                        f"do passo {indice_passo} é inválida."
                    ),
                }

            if dependencia >= indice_passo:

                return {
                    "sucesso": False,
                    "dependencias": [],
                    "erro": (
                        f"O passo {indice_passo} depende de "
                        f"{dependencia}, mas só pode depender "
                        "de etapas anteriores."
                    ),
                }

        return {
            "sucesso": True,
            "dependencias": normalizadas,
            "erro": None,
        }

    # ============================================================
    # COBERTURA
    # ============================================================

    def avaliar_cobertura_plano(
        self,
        necessidade: str,
        passos: list[dict[str, Any]],
    ) -> dict[str, Any]:

        tokens_necessidade = self._tokens(
            necessidade
        )

        texto_plano = " ".join(
            passo["necessidade"]
            for passo in passos
        )

        tokens_plano = self._tokens(
            texto_plano
        )

        if not tokens_necessidade:

            return {
                "possivel": True,
                "score": 1.0,
                "tokens_necessidade": [],
                "tokens_cobertos": [],
                "tokens_ausentes": [],
            }

        cobertos = sorted(
            tokens_necessidade
            & tokens_plano
        )

        ausentes = sorted(
            tokens_necessidade
            - tokens_plano
        )

        score = (
            len(cobertos)
            / len(tokens_necessidade)
        )

        return {
            "possivel": (
                score
                >= LIMIAR_COBERTURA_PLANO
            ),
            "score": round(
                score,
                4,
            ),
            "tokens_necessidade": sorted(
                tokens_necessidade
            ),
            "tokens_cobertos": cobertos,
            "tokens_ausentes": ausentes,
        }

    # ============================================================
    # DOMÍNIO — METADADOS DAS CAPACIDADES
    # ============================================================

    def _dominios_catalogo(
        self,
    ) -> list[str]:

        dominios = []

        for capacidade in self.catalogo:

            for dominio in capacidade.get(
                "dominios",
                [],
            ):

                if dominio not in dominios:

                    dominios.append(
                        dominio
                    )

        return sorted(
            dominios
        )

    def _evidencias_por_dominio(
        self,
    ) -> dict[str, set[str]]:

        evidencias = {}

        for capacidade in self.catalogo:

            dominios = capacidade.get(
                "dominios",
                [],
            )

            termos = capacidade.get(
                "evidencias_dominio",
                [],
            )

            termos_normalizados = set()

            for termo in termos:

                termos_normalizados |= self._tokens(
                    termo
                )

            for dominio in dominios:

                if dominio not in evidencias:

                    evidencias[dominio] = set()

                evidencias[dominio] |= (
                    termos_normalizados
                )

        return evidencias

    def _dominios_por_texto(
        self,
        texto: str,
    ) -> dict[str, Any]:

        tokens = self._tokens(
            texto
        )

        evidencias = (
            self._evidencias_por_dominio()
        )

        pontuacoes = {}

        for dominio, termos in (
            evidencias.items()
        ):

            intersecao = sorted(
                tokens
                & termos
            )

            pontuacoes[dominio] = {
                "score": len(intersecao),
                "evidencias": intersecao,
            }

        positivos = {
            dominio: dados
            for dominio, dados in pontuacoes.items()
            if dados["score"] > 0
        }

        if positivos:

            maior_score = max(
                dados["score"]
                for dados in positivos.values()
            )

            selecionados = sorted(
                dominio
                for dominio, dados in positivos.items()
                if dados["score"] == maior_score
            )

        else:

            maior_score = 0
            selecionados = []

        return {
            "tokens": sorted(tokens),
            "dominios": selecionados,
            "melhor_score": maior_score,
            "pontuacoes": pontuacoes,
        }

    def classificar_origem_semantica(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        dominios = self._dominios_catalogo()

        opcoes = (
            json.dumps(
                dominios,
                ensure_ascii=False,
            )
        )

        prompt = f"""
Classifique somente o domínio semântico da necessidade abaixo.

DOMÍNIOS CONHECIDOS PELO SISTEMA:
{opcoes}

NECESSIDADE:
{necessidade}

REGRAS:
1. Escolha exatamente um dos valores abaixo:
   - um domínio da lista
   - externo
   - desconhecido

2. Use um domínio da lista somente quando a necessidade
   realmente pertencer a esse domínio.

3. Use "externo" quando a necessidade estiver claramente
   relacionada ao mundo externo, ambiente físico, cidade,
   rua, clima ou realidade fora do computador da Nixal.

4. Use "desconhecido" quando não houver informação suficiente.

5. Não confunda o corpo computacional da Nixal com o mundo externo.

6. Retorne somente JSON válido.

FORMATO:
{{
  "dominio": "externo"
}}
""".strip()

        resposta = self.consultar_qwen(
            prompt
        )

        if not resposta["sucesso"]:

            return {
                "sucesso": False,
                "dominio": "desconhecido",
                "erro": resposta[
                    "erro"
                ],
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        dominio = resposta[
            "dados"
        ].get(
            "dominio"
        )

        if not isinstance(
            dominio,
            str,
        ):

            return {
                "sucesso": False,
                "dominio": "desconhecido",
                "erro": (
                    "Classificação semântica de domínio inválida."
                ),
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        dominio = dominio.strip()

        permitidos = set(
            dominios
            + [
                "externo",
                "desconhecido",
            ]
        )

        if dominio not in permitidos:

            return {
                "sucesso": False,
                "dominio": "desconhecido",
                "erro": (
                    "Qwen retornou um domínio "
                    "fora do catálogo permitido."
                ),
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        return {
            "sucesso": True,
            "dominio": dominio,
            "erro": None,
            "resposta_bruta": resposta.get(
                "resposta_bruta"
            ),
        }

    def verificar_consistencia_dominio(
        self,
        necessidade: str,
        passos: list[dict[str, Any]],
    ) -> dict[str, Any]:

        origem = self._dominios_por_texto(
            necessidade
        )

        plano_dominios = self._dominios_por_texto(
            " ".join(
                passo["necessidade"]
                for passo in passos
            )
        )

        origem_semantica = None

        if not origem["dominios"]:

            origem_semantica = (
                self.classificar_origem_semantica(
                    necessidade
                )
            )

        dominio_origem = (
            origem_semantica["dominio"]
            if origem_semantica is not None
            else origem["dominios"][0]
        )

        dominios_plano = plano_dominios[
            "dominios"
        ]

        # --------------------------------------------------------
        # Domínio externo -> capacidade conhecida é troca de domínio.
        # --------------------------------------------------------

        if (
            dominio_origem == "externo"
            and dominios_plano
        ):

            return {
                "possivel": False,
                "motivo": (
                    "O plano trocou uma necessidade do "
                    "mundo externo por um domínio conhecido "
                    "do sistema."
                ),
                "dominio_origem": dominio_origem,
                "dominios_origem_catalogo": origem[
                    "dominios"
                ],
                "dominios_plano_catalogo": dominios_plano,
                "origem": origem,
                "plano": plano_dominios,
                "classificacao_semantica": origem_semantica,
            }

        # --------------------------------------------------------
        # Domínio conhecido -> plano deve conter o mesmo domínio.
        # --------------------------------------------------------

        if (
            dominio_origem not in (
                None,
                "externo",
                "desconhecido",
            )
            and dominios_plano
            and dominio_origem not in dominios_plano
        ):

            return {
                "possivel": False,
                "motivo": (
                    "O plano trocou o domínio declarado pela "
                    "necessidade por outro domínio do catálogo."
                ),
                "dominio_origem": dominio_origem,
                "dominios_origem_catalogo": origem[
                    "dominios"
                ],
                "dominios_plano_catalogo": dominios_plano,
                "origem": origem,
                "plano": plano_dominios,
                "classificacao_semantica": origem_semantica,
            }

        return {
            "possivel": True,
            "motivo": None,
            "dominio_origem": dominio_origem,
            "dominios_origem_catalogo": origem[
                "dominios"
            ],
            "dominios_plano_catalogo": dominios_plano,
            "origem": origem,
            "plano": plano_dominios,
            "classificacao_semantica": origem_semantica,
        }

    # ============================================================
    # CATÁLOGO PARA QWEN
    # ============================================================

    def _catalogo_para_prompt(
        self,
    ) -> str:

        linhas = []

        for capacidade in self.catalogo:

            linhas.append(
                f"""
CAPACIDADE DISPONÍVEL: {capacidade["nome"]}
DESCRIÇÃO: {capacidade["descricao"]}
OBJETIVO: {capacidade["objetivo"]}
DOMÍNIOS: {json.dumps(
    capacidade["dominios"],
    ensure_ascii=False,
)}
EVIDÊNCIAS DE DOMÍNIO: {json.dumps(
    capacidade["evidencias_dominio"],
    ensure_ascii=False,
)}
EXEMPLOS: {json.dumps(
    capacidade["exemplos"],
    ensure_ascii=False,
)}
ARGUMENTOS: {json.dumps(
    capacidade["argumentos"],
    ensure_ascii=False,
)}
""".strip()
            )

        return "\n\n".join(
            linhas
        )

    # ============================================================
    # PLANEJAMENTO
    # ============================================================

    def construir_prompt(
        self,
        necessidade: str,
    ) -> str:

        catalogo = (
            self._catalogo_para_prompt()
        )

        return f"""
Você é o módulo de planejamento da Nixal.

Transforme a necessidade abaixo em uma sequência de
no máximo {MAX_PASSOS} passos.

NECESSIDADE:

{necessidade}

CAPACIDADES EXISTENTES:

{catalogo}

REGRAS:

1. Cada passo deve ser uma necessidade em linguagem natural.

2. Não use nomes internos de capacidades.

3. Não invente sensores, funções, APIs ou ferramentas.

4. Não troque o domínio da necessidade.

5. O domínio declarado de uma capacidade descreve o tipo
   de realidade à qual aquela capacidade pertence.

6. Não confunda o mundo externo com o corpo computacional.

7. Não repita uma consulta que já foi realizada.

8. Uma etapa pode depender de uma etapa anterior.

9. Use números de etapas anteriores em "depende_de".

10. O primeiro passo deve usar [].

11. Nunca use zero em uma dependência.

12. Não escolha a capacidade final.

13. O agente 55.3 resolverá a capacidade.

14. Se a necessidade não puder ser atendida:

{{
  "possivel": false,
  "passos": []
}}

15. Retorne somente JSON válido.

FORMATO:

{{
  "possivel": true,
  "passos": [
    {{
      "necessidade": "...",
      "depende_de": []
    }},
    {{
      "necessidade": "...",
      "depende_de": [1]
    }}
  ]
}}
""".strip()

    # ============================================================
    # QWEN
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
                    f"Falha ao consultar Qwen: "
                    f"{type(erro).__name__}: {erro}"
                ),
            }

        texto = (
            resposta["message"][
                "content"
            ].strip()
        )

        if texto.startswith(
            "```"
        ):

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

        try:

            dados = json.loads(
                texto
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
                    "Qwen retornou estrutura "
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
    # VALIDAR PLANO
    # ============================================================

    def validar_plano(
        self,
        dados: dict[str, Any],
    ) -> dict[str, Any]:

        possivel = dados.get(
            "possivel"
        )

        passos = dados.get(
            "passos"
        )

        if possivel is False:

            if passos not in (
                [],
                None,
            ):

                return {
                    "valido": False,
                    "passos": [],
                    "erro": (
                        "Plano impossível contém passos."
                    ),
                }

            return {
                "valido": True,
                "possivel": False,
                "passos": [],
                "erro": None,
                "motivo": (
                    "O planejador marcou a necessidade "
                    "como impossível."
                ),
            }

        if possivel is not True:

            return {
                "valido": False,
                "passos": [],
                "erro": (
                    "O campo 'possivel' precisa ser "
                    "true ou false."
                ),
            }

        if not isinstance(
            passos,
            list,
        ):

            return {
                "valido": False,
                "passos": [],
                "erro": (
                    "O campo 'passos' precisa ser uma lista."
                ),
            }

        if len(passos) == 0:

            return {
                "valido": False,
                "passos": [],
                "erro": (
                    "Plano possível sem passos."
                ),
            }

        if len(passos) > MAX_PASSOS:

            return {
                "valido": False,
                "passos": [],
                "erro": (
                    f"Plano possui {len(passos)} passos; "
                    f"limite = {MAX_PASSOS}."
                ),
            }

        validados = []

        for indice, passo in enumerate(
            passos,
            start=1,
        ):

            if not isinstance(
                passo,
                dict,
            ):

                return {
                    "valido": False,
                    "passos": [],
                    "erro": (
                        f"O passo {indice} "
                        "não é um objeto JSON."
                    ),
                }

            necessidade = passo.get(
                "necessidade"
            )

            if not isinstance(
                necessidade,
                str,
            ):

                return {
                    "valido": False,
                    "passos": [],
                    "erro": (
                        f"O passo {indice} "
                        "não possui necessidade válida."
                    ),
                }

            necessidade = necessidade.strip()

            if not necessidade:

                return {
                    "valido": False,
                    "passos": [],
                    "erro": (
                        f"O passo {indice} "
                        "possui necessidade vazia."
                    ),
                }

            dep_resultado = (
                self.normalizar_dependencias(
                    indice,
                    passo.get(
                        "depende_de",
                        [],
                    ),
                )
            )

            if not dep_resultado[
                "sucesso"
            ]:

                return {
                    "valido": False,
                    "passos": [],
                    "erro": dep_resultado[
                        "erro"
                    ],
                }

            validados.append(
                {
                    "ordem": indice,
                    "necessidade": necessidade,
                    "depende_de": dep_resultado[
                        "dependencias"
                    ],
                }
            )

        validados = (
            self.normalizar_plano(
                validados
            )
        )

        assinaturas = [
            self._normalizar_texto(
                passo["necessidade"]
            )
            for passo in validados
        ]

        if len(
            assinaturas
        ) != len(
            set(assinaturas)
        ):

            return {
                "valido": False,
                "passos": [],
                "erro": (
                    "O plano contém passos duplicados."
                ),
            }

        return {
            "valido": True,
            "possivel": True,
            "passos": validados,
            "erro": None,
        }

    # ============================================================
    # PLANEJAR
    # ============================================================

    def planejar(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        resposta = self.consultar_qwen(
            self.construir_prompt(
                necessidade
            )
        )

        if not resposta["sucesso"]:

            return {
                "sucesso": False,
                "possivel": False,
                "passos": [],
                "erro": resposta["erro"],
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        validacao = self.validar_plano(
            resposta["dados"]
        )

        if not validacao["valido"]:

            return {
                "sucesso": False,
                "possivel": False,
                "passos": [],
                "erro": validacao["erro"],
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        if not validacao["possivel"]:

            return {
                "sucesso": True,
                "possivel": False,
                "passos": [],
                "erro": None,
                "motivo": validacao[
                    "motivo"
                ],
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        dominio = (
            self.verificar_consistencia_dominio(
                necessidade,
                validacao["passos"],
            )
        )

        if not dominio["possivel"]:

            return {
                "sucesso": True,
                "possivel": False,
                "passos": [],
                "erro": None,
                "motivo": dominio[
                    "motivo"
                ],
                "dominio": dominio,
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        cobertura = (
            self.avaliar_cobertura_plano(
                necessidade,
                validacao["passos"],
            )
        )

        if (
            cobertura["score"]
            < LIMIAR_COBERTURA_PLANO
        ):

            return {
                "sucesso": True,
                "possivel": False,
                "passos": [],
                "erro": None,
                "motivo": (
                    "O plano não cobre suficientemente "
                    "a necessidade original."
                ),
                "cobertura": cobertura,
                "dominio": dominio,
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        return {
            "sucesso": True,
            "possivel": True,
            "passos": validacao[
                "passos"
            ],
            "erro": None,
            "cobertura": cobertura,
            "dominio": dominio,
            "resposta_bruta": resposta.get(
                "resposta_bruta"
            ),
        }

    # ============================================================
    # CONTEXTO
    # ============================================================

    def obter_contexto_dependencias(
        self,
        dependencias: list[int],
        resultados: dict[int, dict[str, Any]],
    ) -> dict[int, dict[str, Any]]:

        contexto = {}

        for numero in dependencias:

            registro = resultados.get(
                numero
            )

            if registro is None:
                continue

            contexto[numero] = {
                "necessidade": registro[
                    "necessidade"
                ],
                "atendida": registro.get(
                    "atendida"
                ),
                "sucesso_operacao": registro.get(
                    "sucesso_operacao"
                ),
                "resultado": registro.get(
                    "resultado"
                ),
            }

        return contexto

    # ============================================================
    # EXTRAIR ARQUIVOS
    # ============================================================

    def extrair_arquivos_do_contexto(
        self,
        contexto: dict[int, dict[str, Any]],
    ) -> list[str]:

        encontrados = []

        def visitar(
            valor: Any,
        ) -> None:

            if isinstance(
                valor,
                list,
            ):

                for item in valor:
                    visitar(item)

                return

            if isinstance(
                valor,
                dict,
            ):

                for item in valor.values():
                    visitar(item)

                return

            if isinstance(
                valor,
                str,
            ):

                candidato = valor.strip()

                if re.fullmatch(
                    r"[^/\n]+\.json",
                    candidato,
                    re.IGNORECASE,
                ):

                    if candidato not in encontrados:

                        encontrados.append(
                            candidato
                        )

        visitar(
            contexto
        )

        return encontrados

    # ============================================================
    # MATERIALIZAÇÃO
    # ============================================================

    def precisa_materializacao(
        self,
        necessidade: str,
    ) -> bool:

        texto = self._normalizar_texto(
            necessidade
        )

        return (
            "arquivo" in texto
            and any(
                termo in texto
                for termo in (
                    "lista",
                    "presente",
                    "correspondente",
                    "estiver",
                )
            )
        )

    def materializar_necessidade(
        self,
        necessidade: str,
        contexto: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:

        arquivos = (
            self.extrair_arquivos_do_contexto(
                contexto
            )
        )

        if not arquivos:

            return {
                "sucesso": False,
                "pedido": None,
                "contexto": contexto,
                "erro": (
                    "Nenhum arquivo foi encontrado "
                    "no contexto."
                ),
            }

        prompt = f"""
Você precisa resolver somente uma referência de arquivo.

NECESSIDADE:

{necessidade}

ARQUIVOS DISPONÍVEIS:

{json.dumps(
    arquivos,
    ensure_ascii=False,
    indent=2,
)}

REGRAS:

1. Escolha somente um nome que apareça exatamente
   na lista.

2. Nunca invente nomes.

3. Não mencione capacidades.

4. Não mencione agentes.

5. Se não houver escolha segura:

{{
  "possivel": false,
  "pedido": ""
}}

6. Retorne somente JSON.

FORMATO:

{{
  "possivel": true,
  "pedido": "Leia o arquivo NOME_EXATO.json."
}}
""".strip()

        resposta = self.consultar_qwen(
            prompt
        )

        if not resposta["sucesso"]:

            return {
                "sucesso": False,
                "pedido": None,
                "contexto": contexto,
                "erro": resposta["erro"],
            }

        dados = resposta["dados"]

        if dados.get(
            "possivel"
        ) is not True:

            return {
                "sucesso": False,
                "pedido": None,
                "contexto": contexto,
                "erro": (
                    "Nenhum arquivo pôde ser "
                    "identificado com segurança."
                ),
            }

        pedido = dados.get(
            "pedido"
        )

        if not isinstance(
            pedido,
            str,
        ):

            return {
                "sucesso": False,
                "pedido": None,
                "contexto": contexto,
                "erro": (
                    "Pedido materializado inválido."
                ),
            }

        arquivos_pedido = re.findall(
            r"[\w.-]+\.json",
            pedido,
            re.IGNORECASE,
        )

        if len(
            arquivos_pedido
        ) != 1:

            return {
                "sucesso": False,
                "pedido": None,
                "contexto": contexto,
                "erro": (
                    "O pedido não identificou "
                    "exatamente um arquivo JSON."
                ),
            }

        arquivo = arquivos_pedido[
            0
        ]

        if arquivo not in arquivos:

            return {
                "sucesso": False,
                "pedido": None,
                "contexto": contexto,
                "erro": (
                    f"O arquivo '{arquivo}' "
                    "não existe no contexto."
                ),
            }

        return {
            "sucesso": True,
            "pedido": pedido,
            "contexto": contexto,
            "arquivo_escolhido": arquivo,
            "erro": None,
        }

    # ============================================================
    # SUCESSO REAL
    # ============================================================

    def _existe_falha_recursiva(
        self,
        valor: Any,
    ) -> bool:

        if isinstance(
            valor,
            dict,
        ):

            if valor.get(
                "sucesso"
            ) is False:

                return True

            for item in valor.values():

                if self._existe_falha_recursiva(
                    item
                ):

                    return True

        elif isinstance(
            valor,
            list,
        ):

            for item in valor:

                if self._existe_falha_recursiva(
                    item
                ):

                    return True

        return False

    def avaliar_sucesso_operacao(
        self,
        resultado: dict[str, Any],
    ) -> bool:

        if not isinstance(
            resultado,
            dict,
        ):

            return False

        if resultado.get(
            "atendida"
        ) is not True:

            return False

        if self._existe_falha_recursiva(
            resultado.get(
                "resultado"
            )
        ):

            return False

        return True

    # ============================================================
    # EXECUTAR
    # ============================================================

    def executar(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        plano = self.planejar(
            necessidade
        )

        if not plano["sucesso"]:

            return {
                "sucesso": False,
                "necessidade": necessidade,
                "plano": plano,
                "passos_executados": [],
                "erro": plano["erro"],
            }

        if not plano["possivel"]:

            return {
                "sucesso": False,
                "necessidade": necessidade,
                "plano": plano,
                "passos_executados": [],
                "erro": (
                    "A necessidade não pode ser atendida "
                    "com o plano atual."
                ),
            }

        resultados = {}

        for passo in plano["passos"]:

            numero = passo[
                "ordem"
            ]

            necessidade_original = passo[
                "necessidade"
            ]

            dependencias = passo[
                "depende_de"
            ]

            contexto = (
                self.obter_contexto_dependencias(
                    dependencias,
                    resultados,
                )
            )

            resultado = self.agente.atender(
                necessidade_original
            )

            sucesso_operacao = (
                self.avaliar_sucesso_operacao(
                    resultado
                )
            )

            pedido_final = (
                necessidade_original
            )

            materializacao_utilizada = (
                False
            )

            if (
                not sucesso_operacao
                and contexto
                and self.precisa_materializacao(
                    necessidade_original
                )
            ):

                materializacao = (
                    self.materializar_necessidade(
                        necessidade_original,
                        contexto,
                    )
                )

                if materializacao[
                    "sucesso"
                ]:

                    pedido_final = (
                        materializacao[
                            "pedido"
                        ]
                    )

                    resultado = (
                        self.agente.atender(
                            pedido_final
                        )
                    )

                    sucesso_operacao = (
                        self.avaliar_sucesso_operacao(
                            resultado
                        )
                    )

                    materializacao_utilizada = (
                        True
                    )

            registro = {
                "ordem": numero,
                "necessidade": necessidade_original,
                "necessidade_original_planejada": passo.get(
                    "necessidade_original"
                ),
                "capacidade_original_planejada": passo.get(
                    "capacidade_original"
                ),
                "depende_de": dependencias,
                "contexto_utilizado": contexto,
                "materializacao_utilizada": (
                    materializacao_utilizada
                ),
                "pedido_final": pedido_final,
                "capacidade_resolvida": resultado.get(
                    "capacidade_escolhida"
                ),
                "argumentos": resultado.get(
                    "argumentos",
                    {},
                ),
                "atendida": resultado.get(
                    "atendida"
                ),
                "sucesso_operacao": (
                    sucesso_operacao
                ),
                "resultado": resultado.get(
                    "resultado"
                ),
            }

            resultados[
                numero
            ] = registro

            if not sucesso_operacao:

                return {
                    "sucesso": False,
                    "necessidade": necessidade,
                    "plano": plano,
                    "passos_executados": list(
                        resultados.values()
                    ),
                    "erro": (
                        "A composição foi interrompida "
                        f"no passo {numero}: a operação "
                        "não foi concluída com sucesso."
                    ),
                }

        return {
            "sucesso": True,
            "necessidade": necessidade,
            "plano": plano,
            "passos_executados": list(
                resultados.values()
            ),
            "erro": None,
        }

    # ============================================================
    # TESTE
    # ============================================================

    def testar(
        self,
        necessidade: str,
    ) -> None:

        print()
        print("=" * 60)
        print(
            "NECESSIDADE COMPLEXA:\n"
            f"{necessidade}"
        )
        print("=" * 60)

        resultado = self.executar(
            necessidade
        )

        print()

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

    compositor = CompositorNixal()

    print()
    print("=" * 60)
    print("NIXAL — COMPOSIÇÃO DE CAPACIDADES 56.3.8")
    print("=" * 60)

    compositor.testar(
        "Quero listar os arquivos do projeto e depois ler "
        "o arquivo capacidades_nixal.json que estiver "
        "presente nessa lista."
    )

    compositor.testar(
        "Quero saber como está meu corpo e depois consultar "
        "os eventos registrados na memória corporal."
    )

    compositor.testar(
        "Preciso descobrir a temperatura do mundo."
    )

    print()
    print("=" * 60)
    print("MICROETAPA 56.3.8 FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
