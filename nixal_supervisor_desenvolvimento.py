#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_ESTADO = (
    BASE_DIR / "supervisor_desenvolvimento_estado.json"
)

DIRETORIO_CHECKPOINTS = (
    BASE_DIR / ".nyxal_checkpoints"
)

MODELO = os.getenv(
    "NYXAL_SUPERVISOR_MODEL",
    "gpt-5.6-sol",
)

VERSAO = "1.0"

MAX_ARQUIVO = 1 * 1024 * 1024


INSTRUCOES = """
Você é o Supervisor de Desenvolvimento da Nyxal.

Seu trabalho é conduzir o desenvolvimento real do projeto Nyxal,
usando as ferramentas locais disponíveis.

OBJETIVO PRINCIPAL:
Transformar objetivos de desenvolvimento em alterações concretas,
testadas e verificadas no próprio projeto.

REGRAS:
1. Primeiro inspecione o projeto antes de modificar qualquer coisa.
2. Preserve comportamento existente.
3. Faça a menor alteração correta possível.
4. Antes de qualquer alteração, crie um checkpoint.
5. Depois de alterar, execute a verificação apropriada.
6. Se a verificação falhar, restaure o checkpoint e investigue.
7. Não altere arquivos fora do projeto.
8. Não leia nem altere segredos, chaves ou credenciais.
9. Não invente arquivos, módulos, APIs ou contratos sem verificar o projeto.
10. Não declare sucesso sem uma verificação real.
11. Quando uma etapa estiver concluída, continue para a próxima etapa
    do objetivo enquanto houver informação suficiente.
12. Se existir uma ambiguidade que possa causar uma alteração destrutiva,
    pare e peça esclarecimento.
13. Prefira testes existentes.
14. Use py_compile quando alterar Python.
15. Registre no resultado final quais arquivos foram alterados,
    quais testes foram executados e o resultado deles.

A Nyxal é um sistema experimental. Não declare consciência,
vida biológica ou AGI.

MISSÃO:
Ajudar a desenvolver a Nyxal continuamente até que ela dependa
cada vez menos de modelos externos para operação e desenvolvimento.
"""


def caminho_seguro(nome: str) -> Path:
    if not isinstance(nome, str) or not nome.strip():
        raise ValueError("Caminho inválido.")

    relativo = Path(nome)

    if relativo.is_absolute():
        raise ValueError(
            "Caminhos absolutos não são permitidos."
        )

    final = (BASE_DIR / relativo).resolve()
    base = BASE_DIR.resolve()

    if final != base and base not in final.parents:
        raise ValueError(
            "O caminho precisa permanecer dentro do projeto."
        )

    return final


class SupervisorDesenvolvimentoNixal:

    def __init__(self) -> None:

        self.client = OpenAI()

        self.conversation_id: str | None = None
        self._ultimo_checkpoint: Path | None = None

        self._carregar_estado()

    # ============================================================
    # ESTADO
    # ============================================================

    def _carregar_estado(self) -> None:

        if not ARQUIVO_ESTADO.exists():
            return

        try:
            dados = json.loads(
                ARQUIVO_ESTADO.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(dados, dict):
                self.conversation_id = dados.get(
                    "conversation_id"
                )

        except (
            OSError,
            json.JSONDecodeError,
        ):
            self.conversation_id = None

    def _salvar_estado(self) -> None:

        dados = {
            "versao": VERSAO,
            "modelo": MODELO,
            "conversation_id": self.conversation_id,
        }

        temporario = ARQUIVO_ESTADO.with_suffix(
            ".json.tmp"
        )

        temporario.write_text(
            json.dumps(
                dados,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        os.replace(
            temporario,
            ARQUIVO_ESTADO,
        )

    # ============================================================
    # FERRAMENTA — LISTAR ARQUIVOS
    # ============================================================

    def listar_arquivos(self) -> dict[str, Any]:

        arquivos = []

        for item in sorted(BASE_DIR.iterdir()):

            if item.name == ".venv":
                continue

            if item.name == ".nyxal_checkpoints":
                continue

            if item.is_file():
                arquivos.append(item.name)

        return {
            "sucesso": True,
            "arquivos": arquivos,
        }

    # ============================================================
    # FERRAMENTA — LER ARQUIVO
    # ============================================================

    def ler_arquivo(
        self,
        arquivo: str,
    ) -> dict[str, Any]:

        caminho = caminho_seguro(arquivo)

        if not caminho.exists():
            return {
                "sucesso": False,
                "erro": f"Arquivo não encontrado: {arquivo}",
            }

        if not caminho.is_file():
            return {
                "sucesso": False,
                "erro": f"O caminho não é um arquivo: {arquivo}",
            }

        tamanho = caminho.stat().st_size

        if tamanho > MAX_ARQUIVO:
            return {
                "sucesso": False,
                "erro": (
                    f"Arquivo excede {MAX_ARQUIVO} bytes."
                ),
            }

        try:

            conteudo = caminho.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            return {
                "sucesso": False,
                "erro": "Arquivo não é UTF-8.",
            }

        return {
            "sucesso": True,
            "arquivo": str(
                caminho.relative_to(BASE_DIR)
            ),
            "tamanho_bytes": tamanho,
            "conteudo": conteudo,
        }

    # ============================================================
    # FERRAMENTA — BUSCAR TEXTO
    # ============================================================

    def buscar_texto(
        self,
        termo: str,
    ) -> dict[str, Any]:

        if not isinstance(termo, str) or not termo:
            return {
                "sucesso": False,
                "erro": "Termo vazio.",
            }

        resultados = []

        for caminho in BASE_DIR.rglob("*"):

            if not caminho.is_file():
                continue

            if ".venv" in caminho.parts:
                continue

            if ".nyxal_checkpoints" in caminho.parts:
                continue

            if caminho.stat().st_size > MAX_ARQUIVO:
                continue

            try:
                texto = caminho.read_text(
                    encoding="utf-8"
                )
            except (
                OSError,
                UnicodeDecodeError,
            ):
                continue

            if termo.lower() in texto.lower():

                resultados.append(
                    str(
                        caminho.relative_to(BASE_DIR)
                    )
                )

        return {
            "sucesso": True,
            "termo": termo,
            "arquivos": resultados,
        }

    # ============================================================
    # CHECKPOINT
    # ============================================================

    def criar_checkpoint(self) -> dict[str, Any]:

        DIRETORIO_CHECKPOINTS.mkdir(
            parents=True,
            exist_ok=True,
        )

        identificador = (
            time.strftime(
                "%Y%m%d_%H%M%S"
            )
            + "_"
            + str(time.time_ns())[-8:]
        )

        destino = (
            DIRETORIO_CHECKPOINTS
            / identificador
        )

        destino.mkdir(
            parents=True,
            exist_ok=True,
        )

        quantidade = 0

        for caminho in BASE_DIR.rglob("*"):

            if not caminho.is_file():
                continue

            if ".venv" in caminho.parts:
                continue

            if ".nyxal_checkpoints" in caminho.parts:
                continue

            relativo = caminho.relative_to(
                BASE_DIR
            )

            destino_arquivo = (
                destino / relativo
            )

            destino_arquivo.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                caminho,
                destino_arquivo,
            )

            quantidade += 1

        self._ultimo_checkpoint = destino

        return {
            "sucesso": True,
            "checkpoint": identificador,
            "arquivos": quantidade,
        }

    # ============================================================
    # RESTAURAR CHECKPOINT
    # ============================================================

    def restaurar_checkpoint(self) -> dict[str, Any]:

        if self._ultimo_checkpoint is None:
            return {
                "sucesso": False,
                "erro": "Nenhum checkpoint ativo.",
            }

        origem = self._ultimo_checkpoint

        if not origem.exists():
            return {
                "sucesso": False,
                "erro": "Checkpoint não encontrado.",
            }

        restaurados = 0

        for caminho in origem.rglob("*"):

            if not caminho.is_file():
                continue

            relativo = caminho.relative_to(
                origem
            )

            destino = BASE_DIR / relativo

            destino.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                caminho,
                destino,
            )

            restaurados += 1

        return {
            "sucesso": True,
            "checkpoint": origem.name,
            "arquivos_restaurados": restaurados,
        }

    # ============================================================
    # FERRAMENTA — CRIAR ARQUIVO
    # ============================================================

    def criar_arquivo(
        self,
        arquivo: str,
        conteudo: str,
    ) -> dict[str, Any]:

        if self._ultimo_checkpoint is None:
            return {
                "sucesso": False,
                "erro": (
                    "Crie um checkpoint antes de modificar arquivos."
                ),
            }

        caminho = caminho_seguro(arquivo)

        if caminho.exists():
            return {
                "sucesso": False,
                "erro": (
                    "Arquivo já existe. "
                    "Use substituir_texto."
                ),
            }

        if caminho.suffix not in {
            ".py",
            ".json",
            ".md",
            ".txt",
        }:
            return {
                "sucesso": False,
                "erro": (
                    "Extensão não permitida."
                ),
            }

        caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        caminho.write_text(
            conteudo,
            encoding="utf-8",
        )

        return {
            "sucesso": True,
            "estado": "arquivo_criado",
            "arquivo": str(
                caminho.relative_to(BASE_DIR)
            ),
        }

    # ============================================================
    # FERRAMENTA — SUBSTITUIR TEXTO
    # ============================================================

    def substituir_texto(
        self,
        arquivo: str,
        texto_antigo: str,
        texto_novo: str,
    ) -> dict[str, Any]:

        if self._ultimo_checkpoint is None:
            return {
                "sucesso": False,
                "erro": (
                    "Crie um checkpoint antes de modificar arquivos."
                ),
            }

        caminho = caminho_seguro(arquivo)

        if not caminho.exists():
            return {
                "sucesso": False,
                "erro": "Arquivo não encontrado.",
            }

        try:
            texto = caminho.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            return {
                "sucesso": False,
                "erro": "Arquivo não é UTF-8.",
            }

        ocorrencias = texto.count(
            texto_antigo
        )

        if ocorrencias == 0:
            return {
                "sucesso": False,
                "erro": "Texto antigo não encontrado.",
            }

        if ocorrencias != 1:
            return {
                "sucesso": False,
                "erro": (
                    "Texto antigo aparece "
                    f"{ocorrencias} vezes. "
                    "A substituição precisa ser única."
                ),
            }

        novo_texto = texto.replace(
            texto_antigo,
            texto_novo,
            1,
        )

        temporario = caminho.with_suffix(
            caminho.suffix + ".tmp"
        )

        temporario.write_text(
            novo_texto,
            encoding="utf-8",
        )

        os.replace(
            temporario,
            caminho,
        )

        return {
            "sucesso": True,
            "estado": "arquivo_modificado",
            "arquivo": str(
                caminho.relative_to(BASE_DIR)
            ),
        }

    # ============================================================
    # FERRAMENTA — PY_COMPILE
    # ============================================================

    def compilar_python(
        self,
        arquivo: str,
    ) -> dict[str, Any]:

        caminho = caminho_seguro(arquivo)

        if caminho.suffix != ".py":
            return {
                "sucesso": False,
                "erro": "Apenas arquivos Python.",
            }

        import py_compile

        try:

            py_compile.compile(
                str(caminho),
                doraise=True,
            )

            return {
                "sucesso": True,
                "estado": "compilado",
                "arquivo": arquivo,
            }

        except Exception as erro:

            return {
                "sucesso": False,
                "estado": "falhou",
                "arquivo": arquivo,
                "erro": (
                    f"{type(erro).__name__}: "
                    f"{erro}"
                ),
            }

    # ============================================================
    # FERRAMENTA — TESTE
    # ============================================================

    def executar_teste(
        self,
        arquivo: str,
    ) -> dict[str, Any]:

        caminho = caminho_seguro(arquivo)

        if caminho.suffix != ".py":
            return {
                "sucesso": False,
                "erro": "O teste precisa ser Python.",
            }

        if not (
            caminho.name.startswith("teste_")
            or caminho.name.startswith("test_")
        ):
            return {
                "sucesso": False,
                "erro": (
                    "Somente arquivos de teste "
                    "podem ser executados."
                ),
            }

        import subprocess

        processo = subprocess.run(
            [
                str(
                    BASE_DIR
                    / ".venv"
                    / "bin"
                    / "python"
                ),
                str(caminho),
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )

        return {
            "sucesso": processo.returncode == 0,
            "estado": (
                "passou"
                if processo.returncode == 0
                else "falhou"
            ),
            "arquivo": arquivo,
            "codigo_saida": processo.returncode,
            "stdout": processo.stdout[-20000:],
            "stderr": processo.stderr[-20000:],
        }

    # ============================================================
    # TOOLS
    # ============================================================

    def ferramentas(self) -> list[dict[str, Any]]:

        return [
            {
                "type": "function",
                "name": "listar_arquivos",
                "description": (
                    "Lista os arquivos do projeto Nyxal."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "type": "function",
                "name": "ler_arquivo",
                "description": (
                    "Lê um arquivo textual do projeto."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arquivo": {
                            "type": "string",
                        }
                    },
                    "required": ["arquivo"],
                },
            },
            {
                "type": "function",
                "name": "buscar_texto",
                "description": (
                    "Busca um termo nos arquivos do projeto."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "termo": {
                            "type": "string",
                        }
                    },
                    "required": ["termo"],
                },
            },
            {
                "type": "function",
                "name": "criar_checkpoint",
                "description": (
                    "Cria checkpoint completo antes de mudanças."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "type": "function",
                "name": "restaurar_checkpoint",
                "description": (
                    "Restaura o último checkpoint."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "type": "function",
                "name": "criar_arquivo",
                "description": (
                    "Cria um novo arquivo permitido "
                    "dentro do projeto."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arquivo": {
                            "type": "string",
                        },
                        "conteudo": {
                            "type": "string",
                        },
                    },
                    "required": [
                        "arquivo",
                        "conteudo",
                    ],
                },
            },
            {
                "type": "function",
                "name": "substituir_texto",
                "description": (
                    "Substitui uma ocorrência única de texto "
                    "dentro de um arquivo."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arquivo": {
                            "type": "string",
                        },
                        "texto_antigo": {
                            "type": "string",
                        },
                        "texto_novo": {
                            "type": "string",
                        },
                    },
                    "required": [
                        "arquivo",
                        "texto_antigo",
                        "texto_novo",
                    ],
                },
            },
            {
                "type": "function",
                "name": "compilar_python",
                "description": (
                    "Compila um arquivo Python."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arquivo": {
                            "type": "string",
                        }
                    },
                    "required": ["arquivo"],
                },
            },
            {
                "type": "function",
                "name": "executar_teste",
                "description": (
                    "Executa um arquivo de teste Python."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "arquivo": {
                            "type": "string",
                        }
                    },
                    "required": ["arquivo"],
                },
            },
        ]

    # ============================================================
    # EXECUÇÃO DE FERRAMENTA
    # ============================================================

    def executar_ferramenta(
        self,
        nome: str,
        argumentos: dict[str, Any],
    ) -> dict[str, Any]:

        mapa = {
            "listar_arquivos": self.listar_arquivos,
            "ler_arquivo": self.ler_arquivo,
            "buscar_texto": self.buscar_texto,
            "criar_checkpoint": self.criar_checkpoint,
            "restaurar_checkpoint": self.restaurar_checkpoint,
            "criar_arquivo": self.criar_arquivo,
            "substituir_texto": self.substituir_texto,
            "compilar_python": self.compilar_python,
            "executar_teste": self.executar_teste,
        }

        funcao = mapa.get(nome)

        if funcao is None:
            return {
                "sucesso": False,
                "erro": (
                    f"Ferramenta desconhecida: {nome}"
                ),
            }

        try:
            return funcao(**argumentos)

        except Exception as erro:
            return {
                "sucesso": False,
                "erro": (
                    f"{type(erro).__name__}: "
                    f"{erro}"
                ),
            }

    # ============================================================
    # CONVERSA
    # ============================================================

    def _garantir_conversa(self) -> str:

        if self.conversation_id:
            return self.conversation_id

        conversa = (
            self.client.conversations.create()
        )

        self.conversation_id = conversa.id

        self._salvar_estado()

        return self.conversation_id

    # ============================================================
    # CONSULTAR SUPERVISOR
    # ============================================================

    def executar(
        self,
        objetivo: str,
    ) -> str:

        if not isinstance(
            objetivo,
            str,
        ) or not objetivo.strip():
            raise ValueError(
                "Objetivo vazio."
            )

        conversa = self._garantir_conversa()

        entrada = (
            "Objetivo atual de desenvolvimento da Nyxal:\n\n"
            + objetivo
            + "\n\n"
            "Trabalhe diretamente no projeto usando as ferramentas. "
            "Inspecione antes, faça checkpoint antes de alterar, "
            "teste depois e só conclua quando houver evidência."
        )

        resposta = self.client.responses.create(
            model=MODELO,
            conversation=conversa,
            instructions=INSTRUCOES,
            input=entrada,
            tools=self.ferramentas(),
        )

        while True:

            chamadas = [
                item
                for item in resposta.output
                if getattr(
                    item,
                    "type",
                    None,
                ) == "function_call"
            ]

            if not chamadas:
                return (
                    resposta.output_text
                    or "Supervisor não retornou texto."
                )

            saidas = []

            for chamada in chamadas:

                try:
                    argumentos = json.loads(
                        chamada.arguments
                    )

                except json.JSONDecodeError:
                    argumentos = {}

                resultado = self.executar_ferramenta(
                    chamada.name,
                    argumentos,
                )

                saidas.append(
                    {
                        "type": "function_call_output",
                        "call_id": chamada.call_id,
                        "output": json.dumps(
                            resultado,
                            ensure_ascii=False,
                        ),
                    }
                )

            resposta = self.client.responses.create(
                model=MODELO,
                conversation=conversa,
                instructions=INSTRUCOES,
                input=saidas,
                tools=self.ferramentas(),
            )


if __name__ == "__main__":

    supervisor = (
        SupervisorDesenvolvimentoNixal()
    )

    print("=" * 60)
    print("NYXAL — SUPERVISOR DE DESENVOLVIMENTO")
    print("=" * 60)

    objetivo = input(
        "\nObjetivo: "
    ).strip()

    if objetivo:

        resultado = supervisor.executar(
            objetivo
        )

        print()
        print(resultado)
