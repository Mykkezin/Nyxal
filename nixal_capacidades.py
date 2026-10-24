#!/usr/bin/env python3

"""
NIXAL — SISTEMA DE CAPACIDADES

Microetapa 56.3.8

Agora cada capacidade possui um contrato semântico expandido:

- nome
- descrição
- objetivo
- exemplos de necessidades
- argumentos
- domínios
- evidências de domínio

Os domínios fazem parte do contrato nativo da capacidade.

Isso permite que outros módulos, como o compositor e o Qwen,
descubram não apenas COMO chamar uma capacidade e PARA QUE
ela serve, mas também EM QUAL DOMÍNIO ela opera.
"""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CAPACIDADES = (
    BASE_DIR / "capacidades_nixal.json"
)

ARQUIVO_LOG = (
    BASE_DIR / "log_capacidades_nixal.json"
)

MAX_TAMANHO_ARQUIVO = (
    1 * 1024 * 1024
)


# ================================================================
# ESTRUTURAS
# ================================================================

@dataclass
class ResultadoCapacidade:
    sucesso: bool
    capacidade: str
    resultado: Any = None
    erro: str | None = None
    timestamp: float = 0.0
    duracao_ms: float = 0.0


@dataclass
class Capacidade:
    nome: str
    descricao: str
    objetivo: str
    exemplos: list[str]
    funcao: Callable[..., Any]
    argumentos: dict[str, dict[str, Any]]
    dominios: list[str]
    evidencias_dominio: list[str]


# ================================================================
# GERENCIADOR
# ================================================================

class GerenciadorCapacidades:

    def __init__(self) -> None:

        self.capacidades: dict[
            str,
            Capacidade,
        ] = {}

        self.registro_anterior = (
            self._carregar_registro()
        )

        # --------------------------------------------------------
        # HORA
        # --------------------------------------------------------

        self.registrar(
            nome="obter_hora",
            descricao=(
                "Obtém o horário atual da máquina."
            ),
            objetivo=(
                "Descobrir o horário atual do sistema."
            ),
            dominios=[
                "sistema_computacional",
            ],
            evidencias_dominio=[
                "hora",
                "horario",
                "sistema",
                "maquina",
            ],
            exemplos=[
                "Que horas são?",
                "Preciso saber a hora.",
                "Qual é o horário agora?",
                "Me diga o horário atual.",
            ],
            funcao=self._obter_hora,
        )

        # --------------------------------------------------------
        # ARQUIVOS
        # --------------------------------------------------------

        self.registrar(
            nome="listar_arquivos",
            descricao=(
                "Lista os arquivos do diretório "
                "do projeto Nixal."
            ),
            objetivo=(
                "Descobrir quais arquivos existem "
                "no projeto Nixal."
            ),
            dominios=[
                "projeto_arquivo",
            ],
            evidencias_dominio=[
                "arquivo",
                "arquivos",
                "projeto",
                "diretorio",
                "pasta",
            ],
            exemplos=[
                "Quais arquivos existem?",
                "Quero conhecer os arquivos do projeto.",
                "Liste os arquivos da Nixal.",
                "Quais arquivos estão disponíveis?",
            ],
            funcao=self._listar_arquivos,
        )

        # --------------------------------------------------------
        # ESTADO CORPORAL
        # --------------------------------------------------------

        self.registrar(
            nome="ler_estado_corpo",
            descricao=(
                "Lê o estado atual do corpo da Nixal."
            ),
            objetivo=(
                "Consultar o estado atual do corpo "
                "computacional da Nixal, incluindo CPU, "
                "memória, GPU, temperaturas, armazenamento "
                "e processos."
            ),
            dominios=[
                "corpo_computacional",
            ],
            evidencias_dominio=[
                "corpo",
                "corporal",
                "cpu",
                "gpu",
                "memoria",
                "armazenamento",
                "processos",
                "computador",
                "computacional",
            ],
            exemplos=[
                "Como está meu corpo?",
                "Como está minha CPU?",
                "Qual é o uso da minha GPU?",
                "Como está minha memória?",
                "Quais são minhas temperaturas?",
                "Qual é o estado atual do meu computador?",
            ],
            funcao=self._ler_estado_corpo,
        )

        # --------------------------------------------------------
        # MEMÓRIA CORPORAL
        # --------------------------------------------------------

        self.registrar(
            nome="ler_memoria_corporal",
            descricao=(
                "Lê os eventos registrados "
                "na memória corporal."
            ),
            objetivo=(
                "Consultar eventos e acontecimentos "
                "registrados anteriormente pelo corpo "
                "da Nixal."
            ),
            dominios=[
                "corpo_computacional",
            ],
            evidencias_dominio=[
                "corpo",
                "corporal",
                "evento",
                "eventos",
                "historico",
                "acontecimentos",
            ],
            exemplos=[
                "Quais eventos meu corpo registrou?",
                "O que meu corpo registrou?",
                "Quais eventos corporais aconteceram?",
                "Mostre meu histórico corporal.",
                "O que aconteceu com meu corpo?",
                "Quais eventos estão na minha memória corporal?",
            ],
            funcao=self._ler_memoria_corporal,
        )

        # --------------------------------------------------------
        # LEITURA DE ARQUIVO
        # --------------------------------------------------------

        self.registrar(
            nome="ler_arquivo",
            descricao=(
                "Lê um arquivo de texto dentro "
                "do projeto Nixal."
            ),
            objetivo=(
                "Ler o conteúdo textual de um arquivo "
                "específico cujo nome ou caminho relativo "
                "foi fornecido."
            ),
            dominios=[
                "projeto_arquivo",
            ],
            evidencias_dominio=[
                "arquivo",
                "arquivos",
                "projeto",
                "texto",
                "conteudo",
                "caminho",
                "diretorio",
            ],
            exemplos=[
                "Leia o arquivo estado_corpo_nixal.json.",
                "Mostre o conteúdo de capacidades_nixal.json.",
                "Abra o arquivo teste.py.",
                "Leia o conteúdo de um arquivo específico.",
            ],
            funcao=self._ler_arquivo,
            argumentos={
                "arquivo": {
                    "tipo": "string",
                    "obrigatorio": True,
                    "descricao": (
                        "Nome ou caminho relativo "
                        "do arquivo dentro do projeto Nixal."
                    ),
                }
            },
        )

    # ============================================================
    # REGISTRO PERSISTENTE
    # ============================================================

    def _carregar_registro(
        self,
    ) -> list[dict[str, Any]]:

        if not ARQUIVO_CAPACIDADES.exists():
            return []

        try:

            with ARQUIVO_CAPACIDADES.open(
                "r",
                encoding="utf-8",
            ) as f:

                dados = json.load(f)

            if isinstance(dados, list):
                return dados

            return []

        except Exception as erro:

            print(
                "[Nixal] Não foi possível carregar "
                f"o registro de capacidades: {erro}"
            )

            return []

    def _salvar_registro(
        self,
    ) -> None:

        dados = (
            self.listar_capacidades()
        )

        try:

            with ARQUIVO_CAPACIDADES.open(
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    dados,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        except Exception as erro:

            print(
                "[Nixal] Não foi possível salvar "
                f"o registro de capacidades: {erro}"
            )

    # ============================================================
    # REGISTRAR
    # ============================================================

    def registrar(
        self,
        nome: str,
        descricao: str,
        objetivo: str,
        exemplos: list[str],
        funcao: Callable[..., Any],
        argumentos: dict[
            str,
            dict[str, Any],
        ] | None = None,
        dominios: list[str] | None = None,
        evidencias_dominio: list[str] | None = None,
    ) -> None:

        if not nome:
            raise ValueError(
                "Nome da capacidade não pode ser vazio."
            )

        if not callable(funcao):
            raise TypeError(
                f"A capacidade '{nome}' precisa possuir "
                "uma função válida."
            )

        if not isinstance(
            exemplos,
            list,
        ):
            raise TypeError(
                "Exemplos precisam ser uma lista."
            )

        dominios = (
            dominios
            if dominios is not None
            else []
        )

        evidencias_dominio = (
            evidencias_dominio
            if evidencias_dominio is not None
            else []
        )

        if not isinstance(
            dominios,
            list,
        ):
            raise TypeError(
                "Domínios precisam ser uma lista."
            )

        if not isinstance(
            evidencias_dominio,
            list,
        ):
            raise TypeError(
                "Evidências de domínio precisam "
                "ser uma lista."
            )

        dominios_normalizados = []

        for dominio in dominios:

            if not isinstance(
                dominio,
                str,
            ):
                raise TypeError(
                    "Cada domínio precisa ser string."
                )

            dominio = dominio.strip()

            if not dominio:
                continue

            if dominio not in (
                dominios_normalizados
            ):

                dominios_normalizados.append(
                    dominio
                )

        evidencias_normalizadas = []

        for evidencia in (
            evidencias_dominio
        ):

            if not isinstance(
                evidencia,
                str,
            ):
                raise TypeError(
                    "Cada evidência de domínio "
                    "precisa ser string."
                )

            evidencia = evidencia.strip()

            if not evidencia:
                continue

            if evidencia not in (
                evidencias_normalizadas
            ):

                evidencias_normalizadas.append(
                    evidencia
                )

        if not dominios_normalizados:
            raise ValueError(
                f"A capacidade '{nome}' "
                "precisa possuir pelo menos "
                "um domínio."
            )

        if not evidencias_normalizadas:
            raise ValueError(
                f"A capacidade '{nome}' "
                "precisa possuir pelo menos "
                "uma evidência de domínio."
            )

        if nome in self.capacidades:
            raise ValueError(
                f"A capacidade '{nome}' "
                "já está registrada."
            )

        self.capacidades[nome] = (
            Capacidade(
                nome=nome,
                descricao=descricao,
                objetivo=objetivo,
                exemplos=exemplos,
                funcao=funcao,
                argumentos=(
                    argumentos
                    or {}
                ),
                dominios=(
                    dominios_normalizados
                ),
                evidencias_dominio=(
                    evidencias_normalizadas
                ),
            )
        )

        self._salvar_registro()

    # ============================================================
    # ESPECIFICAÇÃO
    # ============================================================

    def obter_especificacao(
        self,
        nome: str,
    ) -> dict[str, Any] | None:

        capacidade = (
            self.capacidades.get(nome)
        )

        if capacidade is None:
            return None

        return {
            "nome": capacidade.nome,
            "descricao": capacidade.descricao,
            "objetivo": capacidade.objetivo,
            "exemplos": capacidade.exemplos,
            "argumentos": capacidade.argumentos,
            "dominios": capacidade.dominios,
            "evidencias_dominio": (
                capacidade.evidencias_dominio
            ),
        }

    # ============================================================
    # VALIDAÇÃO DE ARGUMENTOS
    # ============================================================

    def validar_argumentos(
        self,
        nome: str,
        argumentos: dict[str, Any],
    ) -> tuple[bool, str | None]:

        capacidade = (
            self.capacidades.get(nome)
        )

        if capacidade is None:

            return (
                False,
                f"Capacidade inexistente: {nome}",
            )

        if not isinstance(
            argumentos,
            dict,
        ):

            return (
                False,
                "Os argumentos precisam ser "
                "um objeto JSON.",
            )

        especificacao = (
            capacidade.argumentos
        )

        # --------------------------------------------------------
        # Argumentos desconhecidos
        # --------------------------------------------------------

        for nome_argumento in argumentos:

            if (
                nome_argumento
                not in especificacao
            ):

                return (
                    False,
                    (
                        f"Argumento não permitido para "
                        f"'{nome}': {nome_argumento}"
                    ),
                )

        # --------------------------------------------------------
        # Argumentos obrigatórios
        # --------------------------------------------------------

        for (
            nome_argumento,
            dados,
        ) in especificacao.items():

            obrigatorio = dados.get(
                "obrigatorio",
                False,
            )

            if (
                obrigatorio
                and nome_argumento
                not in argumentos
            ):

                return (
                    False,
                    (
                        "Argumento obrigatório ausente: "
                        f"{nome_argumento}"
                    ),
                )

        # --------------------------------------------------------
        # Tipos
        # --------------------------------------------------------

        for (
            nome_argumento,
            valor,
        ) in argumentos.items():

            esperado = (
                especificacao[
                    nome_argumento
                ].get("tipo")
            )

            if esperado == "string":

                if not isinstance(
                    valor,
                    str,
                ):

                    return (
                        False,
                        (
                            f"O argumento "
                            f"'{nome_argumento}' "
                            "precisa ser string."
                        ),
                    )

        return True, None

    # ============================================================
    # EXECUÇÃO
    # ============================================================

    def executar(
        self,
        nome: str,
        **argumentos: Any,
    ) -> ResultadoCapacidade:

        inicio = time.perf_counter()
        timestamp = time.time()

        valido, erro_validacao = (
            self.validar_argumentos(
                nome,
                argumentos,
            )
        )

        if not valido:

            resultado = (
                ResultadoCapacidade(
                    sucesso=False,
                    capacidade=nome,
                    erro=erro_validacao,
                    timestamp=timestamp,
                    duracao_ms=(
                        time.perf_counter()
                        - inicio
                    ) * 1000,
                )
            )

            self._registrar_execucao(
                resultado
            )

            return resultado

        capacidade = (
            self.capacidades[nome]
        )

        try:

            valor = capacidade.funcao(
                **argumentos
            )

            fim = time.perf_counter()

            resultado = (
                ResultadoCapacidade(
                    sucesso=True,
                    capacidade=nome,
                    resultado=valor,
                    timestamp=timestamp,
                    duracao_ms=(
                        fim - inicio
                    ) * 1000,
                )
            )

        except Exception as erro:

            fim = time.perf_counter()

            resultado = (
                ResultadoCapacidade(
                    sucesso=False,
                    capacidade=nome,
                    erro=(
                        f"{type(erro).__name__}: "
                        f"{erro}"
                    ),
                    timestamp=timestamp,
                    duracao_ms=(
                        fim - inicio
                    ) * 1000,
                )
            )

            print(
                "\n[Nixal] Erro durante execução:"
            )

            traceback.print_exc()

        self._registrar_execucao(
            resultado
        )

        return resultado

    # ============================================================
    # DESCOBERTA
    # ============================================================

    def listar_capacidades(
        self,
    ) -> list[dict[str, Any]]:

        capacidades = []

        for capacidade in (
            self.capacidades.values()
        ):

            capacidades.append(
                {
                    "nome": capacidade.nome,
                    "descricao": (
                        capacidade.descricao
                    ),
                    "objetivo": (
                        capacidade.objetivo
                    ),
                    "exemplos": (
                        capacidade.exemplos
                    ),
                    "argumentos": (
                        capacidade.argumentos
                    ),
                    "dominios": (
                        capacidade.dominios
                    ),
                    "evidencias_dominio": (
                        capacidade.evidencias_dominio
                    ),
                }
            )

        return capacidades

    # ============================================================
    # CAPACIDADE — HORA
    # ============================================================

    def _obter_hora(
        self,
    ) -> dict[str, Any]:

        agora = time.localtime()

        return {
            "hora": agora.tm_hour,
            "minuto": agora.tm_min,
            "segundo": agora.tm_sec,
            "timestamp": time.time(),
        }

    # ============================================================
    # CAPACIDADE — LISTAR ARQUIVOS
    # ============================================================

    def _listar_arquivos(
        self,
    ) -> list[str]:

        arquivos = []

        try:

            for item in sorted(
                BASE_DIR.iterdir()
            ):

                if item.is_file():

                    arquivos.append(
                        item.name
                    )

        except Exception as erro:

            return [
                (
                    f"erro: "
                    f"{type(erro).__name__}: "
                    f"{erro}"
                )
            ]

        return arquivos

    # ============================================================
    # CAPACIDADE — ESTADO DO CORPO
    # ============================================================

    def _ler_estado_corpo(
        self,
    ) -> dict[str, Any]:

        arquivo = (
            BASE_DIR
            / "estado_corpo_nixal.json"
        )

        if not arquivo.exists():

            return {
                "disponivel": False,
                "motivo": (
                    "estado_corpo_nixal.json "
                    "ainda não existe."
                ),
            }

        try:

            with arquivo.open(
                "r",
                encoding="utf-8",
            ) as f:

                dados = json.load(f)

            return {
                "disponivel": True,
                "estado": dados,
            }

        except Exception as erro:

            return {
                "disponivel": False,
                "erro": str(erro),
            }

    # ============================================================
    # CAPACIDADE — MEMÓRIA CORPORAL
    # ============================================================

    def _ler_memoria_corporal(
        self,
    ) -> dict[str, Any]:

        arquivo = (
            BASE_DIR
            / "memoria_corporal_nixal.json"
        )

        if not arquivo.exists():

            return {
                "disponivel": False,
                "motivo": (
                    "memoria_corporal_nixal.json "
                    "ainda não existe."
                ),
            }

        try:

            with arquivo.open(
                "r",
                encoding="utf-8",
            ) as f:

                dados = json.load(f)

            return {
                "disponivel": True,
                "memoria": dados,
            }

        except Exception as erro:

            return {
                "disponivel": False,
                "erro": str(erro),
            }

    # ============================================================
    # CAPACIDADE — LER ARQUIVO
    # ============================================================

    def _ler_arquivo(
        self,
        arquivo: str,
    ) -> dict[str, Any]:

        if not isinstance(
            arquivo,
            str,
        ):

            return {
                "sucesso": False,
                "erro": (
                    "O nome do arquivo precisa "
                    "ser uma string."
                ),
            }

        arquivo = arquivo.strip()

        if not arquivo:

            return {
                "sucesso": False,
                "erro": (
                    "O nome do arquivo está vazio."
                ),
            }

        caminho = Path(arquivo)

        if caminho.is_absolute():

            return {
                "sucesso": False,
                "erro": (
                    "Caminhos absolutos não são "
                    "permitidos por esta capacidade."
                ),
            }

        try:

            caminho_final = (
                BASE_DIR / caminho
            ).resolve()

            base_final = (
                BASE_DIR.resolve()
            )

            if (
                caminho_final != base_final
                and base_final
                not in caminho_final.parents
            ):

                return {
                    "sucesso": False,
                    "erro": (
                        "O arquivo precisa estar "
                        "dentro do projeto Nixal."
                    ),
                }

            if not caminho_final.exists():

                return {
                    "sucesso": False,
                    "erro": (
                        f"Arquivo não encontrado: "
                        f"{arquivo}"
                    ),
                }

            if not caminho_final.is_file():

                return {
                    "sucesso": False,
                    "erro": (
                        f"O caminho não é um arquivo: "
                        f"{arquivo}"
                    ),
                }

            tamanho = (
                caminho_final.stat().st_size
            )

            if (
                tamanho
                > MAX_TAMANHO_ARQUIVO
            ):

                return {
                    "sucesso": False,
                    "erro": (
                        "Arquivo excede o limite de "
                        f"{MAX_TAMANHO_ARQUIVO} bytes."
                    ),
                }

            conteudo = (
                caminho_final.read_text(
                    encoding="utf-8"
                )
            )

            return {
                "sucesso": True,
                "arquivo": str(
                    caminho_final.relative_to(
                        base_final
                    )
                ),
                "tamanho_bytes": tamanho,
                "conteudo": conteudo,
            }

        except UnicodeDecodeError:

            return {
                "sucesso": False,
                "erro": (
                    "O arquivo não é um texto UTF-8 "
                    "compatível com esta capacidade."
                ),
            }

        except Exception as erro:

            return {
                "sucesso": False,
                "erro": (
                    f"{type(erro).__name__}: "
                    f"{erro}"
                ),
            }

    # ============================================================
    # LOG
    # ============================================================

    def _registrar_execucao(
        self,
        resultado: ResultadoCapacidade,
    ) -> None:

        historico: list[
            dict[str, Any]
        ] = []

        if ARQUIVO_LOG.exists():

            try:

                with ARQUIVO_LOG.open(
                    "r",
                    encoding="utf-8",
                ) as f:

                    dados = json.load(f)

                if isinstance(
                    dados,
                    list,
                ):

                    historico = dados

            except Exception:

                historico = []

        try:

            registro = asdict(resultado)
            tamanho_registro = len(
                json.dumps(
                    registro,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
            )

            # Um único resultado não pode consumir todo o orçamento
            # do log. Preserve metadados e marque o conteúdo omitido.
            if tamanho_registro > MAX_TAMANHO_ARQUIVO // 2:

                registro["resultado"] = {
                    "truncado": True,
                    "motivo": (
                        "Resultado omitido para respeitar "
                        "o limite de armazenamento do log."
                    ),
                    "tamanho_original_bytes": tamanho_registro,
                }

                registro["capacidade"] = str(
                    registro.get("capacidade", "")
                )[:256]

                if registro.get("erro") is not None:
                    registro["erro"] = str(
                        registro["erro"]
                    )[:2048]

            historico.append(registro)
            historico = historico[-200:]

            payload = json.dumps(
                historico,
                ensure_ascii=False,
                indent=2,
            )

            # Limite rígido em bytes UTF-8, e não só em quantidade
            # de execuções. Remove primeiro os registros mais antigos.
            while (
                len(payload.encode("utf-8")) > MAX_TAMANHO_ARQUIVO
                and len(historico) > 1
            ):

                historico.pop(0)

                payload = json.dumps(
                    historico,
                    ensure_ascii=False,
                    indent=2,
                )

            if len(payload.encode("utf-8")) > MAX_TAMANHO_ARQUIVO:

                historico = [
                    {
                        "sucesso": bool(registro.get("sucesso")),
                        "capacidade": str(
                            registro.get("capacidade", "")
                        )[:256],
                        "erro": (
                            str(registro.get("erro"))[:1024]
                            if registro.get("erro") is not None
                            else None
                        ),
                        "timestamp": registro.get("timestamp", 0.0),
                        "duracao_ms": registro.get("duracao_ms", 0.0),
                        "resultado": {
                            "truncado": True,
                            "motivo": "Limite rígido de armazenamento",
                            "tamanho_original_bytes": tamanho_registro,
                        },
                    }
                ]

                payload = json.dumps(
                    historico,
                    ensure_ascii=False,
                    indent=2,
                )

            if len(payload.encode("utf-8")) > MAX_TAMANHO_ARQUIVO:
                payload = "[]"

            ARQUIVO_LOG.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            ARQUIVO_LOG.write_text(
                payload,
                encoding="utf-8",
            )

        except Exception as erro:

            print(
                "[Nixal] Não foi possível salvar "
                f"log de capacidade: {erro}"
            )


# ================================================================
# TESTE
# ================================================================

def main() -> None:

    gerenciador = (
        GerenciadorCapacidades()
    )

    print()
    print("=" * 60)
    print("NIXAL — SISTEMA DE CAPACIDADES")
    print("=" * 60)

    print()
    print("Capacidades disponíveis:")
    print()

    for capacidade in (
        gerenciador.listar_capacidades()
    ):

        print(
            f"- {capacidade['nome']}"
        )

        print(
            f"    descrição: "
            f"{capacidade['descricao']}"
        )

        print(
            f"    objetivo: "
            f"{capacidade['objetivo']}"
        )

        print(
            f"    domínios: "
            f"{capacidade['dominios']}"
        )

        print(
            f"    evidências: "
            f"{capacidade['evidencias_dominio']}"
        )

    print()
    print("=" * 60)
    print("MICROETAPA 56.3.8")
    print("=" * 60)


if __name__ == "__main__":
    main()
