#!/usr/bin/env python3

"""
NIXAL — COMPOSIÇÃO DE CAPACIDADES

Microetapa 56.3

Objetivo:
Permitir que uma etapa posterior receba o resultado de
uma ou mais etapas anteriores.

Arquitetura:

necessidade complexa
        ↓
planejamento
        ↓
etapa 1
        ↓
resultado da etapa 1
        ↓
contexto
        ↓
etapa 2 + contexto
        ↓
Agente 55.3
        ↓
capacidade
        ↓
execução

Princípio:

O planejador define O QUE precisa ser feito.

O agente 55.3 continua responsável por descobrir
QUAL capacidade atende cada necessidade.

A composição apenas transporta contexto entre etapas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import ollama

from nixal_agente_qwen import AgenteNixalQwen


MODELO = "qwen2:7b"

MAX_PASSOS = 3

MAX_CONTEXTO_CHARS = 5000

ARQUIVO_CAPACIDADES = Path(
    "capacidades_nixal.json"
)


class CompositorNixal:

    def __init__(self) -> None:

        self.agente = AgenteNixalQwen()

        self.catalogo = (
            self._carregar_catalogo()
        )

    # ============================================================
    # CARREGAR CATÁLOGO
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
    # CATÁLOGO PARA O QWEN
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
    # PROMPT DE PLANEJAMENTO
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

Transforme uma necessidade complexa em uma sequência de
no máximo {MAX_PASSOS} necessidades menores.

O catálogo abaixo mostra as capacidades existentes.

Você NÃO escolhe a capacidade final.
O agente 55.3 fará essa escolha posteriormente.

Seu trabalho é definir O QUE precisa acontecer.

CATÁLOGO:

{catalogo}

NECESSIDADE:

{necessidade}

REGRAS:

1. Gere no máximo {MAX_PASSOS} passos.

2. Cada passo deve representar uma necessidade concreta.

3. Não escreva código.

4. Não invente funções.

5. Não invente sensores.

6. Não invente capacidades.

7. Não crie etapas artificiais.

8. Uma etapa pode depender do resultado de uma etapa anterior.

9. Quando isso acontecer, informe os números das etapas
   anteriores no campo "depende_de".

10. Use apenas dependências anteriores ao próprio passo.

11. O primeiro passo normalmente terá "depende_de": [].

12. Se a necessidade não puder ser atendida pelas capacidades
    disponíveis, retorne "possivel": false.

13. Retorne somente JSON válido.

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

CASO IMPOSSÍVEL:

{{
  "possivel": false,
  "passos": []
}}
""".strip()

    # ============================================================
    # CONSULTAR QWEN
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

        # --------------------------------------------------------
        # Remove markdown acidental.
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # JSON
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # IMPOSSÍVEL
        # --------------------------------------------------------

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
                    "Nenhuma composição executável "
                    "foi encontrada nas capacidades atuais."
                ),
            }

        # --------------------------------------------------------
        # POSSÍVEL
        # --------------------------------------------------------

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
                    "Plano possível sem nenhum passo."
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

        passos_validados = []

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

            necessidade_passo = passo.get(
                "necessidade"
            )

            dependencias = passo.get(
                "depende_de",
                [],
            )

            if not isinstance(
                necessidade_passo,
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

            necessidade_passo = (
                necessidade_passo.strip()
            )

            if not necessidade_passo:

                return {
                    "valido": False,
                    "passos": [],
                    "erro": (
                        f"O passo {indice} "
                        "possui necessidade vazia."
                    ),
                }

            # ----------------------------------------------------
            # Dependências
            # ----------------------------------------------------

            if not isinstance(
                dependencias,
                list,
            ):

                return {
                    "valido": False,
                    "passos": [],
                    "erro": (
                        f"As dependências do passo "
                        f"{indice} precisam ser uma lista."
                    ),
                }

            dependencias_normalizadas = []

            for dependencia in dependencias:

                if not isinstance(
                    dependencia,
                    int,
                ):

                    return {
                        "valido": False,
                        "passos": [],
                        "erro": (
                            f"A dependência '{dependencia}' "
                            f"do passo {indice} não é inteira."
                        ),
                    }

                if dependencia < 1:

                    return {
                        "valido": False,
                        "passos": [],
                        "erro": (
                            f"A dependência {dependencia} "
                            f"do passo {indice} é inválida."
                        ),
                    }

                if dependencia >= indice:

                    return {
                        "valido": False,
                        "passos": [],
                        "erro": (
                            f"O passo {indice} depende de "
                            f"{dependencia}, mas uma etapa só "
                            "pode depender de etapas anteriores."
                        ),
                    }

                if dependencia not in (
                    dependencias_normalizadas
                ):

                    dependencias_normalizadas.append(
                        dependencia
                    )

            passos_validados.append(
                {
                    "ordem": indice,
                    "necessidade": necessidade_passo,
                    "depende_de": (
                        dependencias_normalizadas
                    ),
                }
            )

        # --------------------------------------------------------
        # Duplicatas
        # --------------------------------------------------------

        necessidades = [
            passo["necessidade"].lower()
            for passo in passos_validados
        ]

        if len(
            necessidades
        ) != len(
            set(necessidades)
        ):

            return {
                "valido": False,
                "passos": [],
                "erro": (
                    "Qwen retornou passos duplicados."
                ),
            }

        return {
            "valido": True,
            "possivel": True,
            "passos": passos_validados,
            "erro": None,
        }

    # ============================================================
    # PLANEJAR
    # ============================================================

    def planejar(
        self,
        necessidade: str,
    ) -> dict[str, Any]:

        prompt = self.construir_prompt(
            necessidade
        )

        resposta = self.consultar_qwen(
            prompt
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
                "motivo": validacao.get(
                    "motivo",
                    "Capacidade insuficiente.",
                ),
                "resposta_bruta": resposta.get(
                    "resposta_bruta"
                ),
            }

        return {
            "sucesso": True,
            "possivel": True,
            "passos": validacao["passos"],
            "erro": None,
            "resposta_bruta": resposta.get(
                "resposta_bruta"
            ),
        }

    # ============================================================
    # RESUMIR RESULTADO PARA CONTEXTO
    # ============================================================

    def resumir_resultado(
        self,
        resultado: Any,
    ) -> str:

        try:

            texto = json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2,
            )

        except TypeError:

            texto = str(
                resultado
            )

        if len(texto) > MAX_CONTEXTO_CHARS:

            texto = (
                texto[:MAX_CONTEXTO_CHARS]
                + "\n...[CONTEXTO TRUNCADO]"
            )

        return texto

    # ============================================================
    # CONSTRUIR NECESSIDADE COM CONTEXTO
    # ============================================================

    def construir_necessidade_com_contexto(
        self,
        necessidade: str,
        dependencias: list[int],
        resultados: dict[int, dict[str, Any]],
    ) -> tuple[str, dict[int, Any]]:

        if not dependencias:

            return (
                necessidade,
                {},
            )

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
                "capacidade": registro.get(
                    "capacidade_resolvida"
                ),
                "atendida": registro.get(
                    "atendida"
                ),
                "resultado": registro.get(
                    "resultado"
                ),
            }

        if not contexto:

            return (
                necessidade,
                {},
            )

        contexto_texto = (
            json.dumps(
                contexto,
                ensure_ascii=False,
                indent=2,
            )
        )

        if len(contexto_texto) > MAX_CONTEXTO_CHARS:

            contexto_texto = (
                contexto_texto[:MAX_CONTEXTO_CHARS]
                + "\n...[CONTEXTO TRUNCADO]"
            )

        necessidade_expandida = f"""
NECESSIDADE PRINCIPAL DO PASSO:

{necessidade}

CONTEXTO PRODUZIDO POR ETAPAS ANTERIORES:

{contexto_texto}

Use o contexto acima para interpretar a necessidade
deste passo.

O contexto é informação produzida pela própria Nixal.
Não invente informações que não estejam nele.
""".strip()

        return (
            necessidade_expandida,
            contexto,
        )

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
                    "com as capacidades atuais."
                ),
            }

        resultados = {}

        for passo in plano["passos"]:

            numero = passo["ordem"]

            necessidade_original = passo[
                "necessidade"
            ]

            dependencias = passo[
                "depende_de"
            ]

            necessidade_execucao, contexto = (
                self.construir_necessidade_com_contexto(
                    necessidade_original,
                    dependencias,
                    resultados,
                )
            )

            resultado = self.agente.atender(
                necessidade_execucao
            )

            registro = {
                "ordem": numero,
                "necessidade": necessidade_original,
                "depende_de": dependencias,
                "contexto_utilizado": contexto,
                "capacidade_resolvida": resultado.get(
                    "capacidade_escolhida"
                ),
                "argumentos": resultado.get(
                    "argumentos",
                    {},
                ),
                "atendida": resultado[
                    "atendida"
                ],
                "resultado": resultado.get(
                    "resultado"
                ),
            }

            resultados[numero] = registro

            if not resultado["atendida"]:

                return {
                    "sucesso": False,
                    "necessidade": necessidade,
                    "plano": plano,
                    "passos_executados": list(
                        resultados.values()
                    ),
                    "erro": (
                        "A composição foi interrompida "
                        f"no passo {numero} porque o agente "
                        "não encontrou uma capacidade adequada."
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
    print("NIXAL — COMPOSIÇÃO DE CAPACIDADES 56.3")
    print("=" * 60)

    # ------------------------------------------------------------
    # TESTE 1 — dependência real entre etapas
    # ------------------------------------------------------------

    compositor.testar(
        "Quero listar os arquivos do projeto e depois ler "
        "o arquivo JSON de configuração da Nixal que estiver "
        "presente nessa lista."
    )

    # ------------------------------------------------------------
    # TESTE 2 — contexto corporal
    # ------------------------------------------------------------

    compositor.testar(
        "Quero saber como está meu corpo e depois consultar "
        "os eventos registrados na memória corporal levando "
        "em consideração o estado observado anteriormente."
    )

    # ------------------------------------------------------------
    # TESTE 3 — capacidade inexistente
    # ------------------------------------------------------------

    compositor.testar(
        "Preciso descobrir a temperatura do mundo."
    )

    print()
    print("=" * 60)
    print("MICROETAPA 56.3 FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
