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
import math
import os
import tempfile
import threading
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
_AUDIT_LOCK = threading.Lock()


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
    politica: str = "somente_leitura"


# ================================================================
# GERENCIADOR
# ================================================================

class GerenciadorCapacidades:

    def __init__(self) -> None:

        self.capacidades: dict[
            str,
            Capacidade,
        ] = {}

        # A corrupção de um catálogo existente nunca autoriza substituí-lo por defaults.
        self._preservar_catalogo_corrompido = False
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
            with ARQUIVO_CAPACIDADES.open("rb") as arquivo:
                conteudo = arquivo.read(MAX_TAMANHO_ARQUIVO + 1)
            if len(conteudo) > MAX_TAMANHO_ARQUIVO:
                raise ValueError("O catálogo ultrapassa o limite de tamanho.")
            dados = json.loads(conteudo.decode("utf-8"))
            if not isinstance(dados, list) or not all(isinstance(item, dict) for item in dados):
                raise ValueError("Formato de catálogo inválido.")
            return dados
        except Exception as erro:
            self._preservar_catalogo_corrompido = True
            print(
                "[Nixal] Catálogo inválido; preservando o arquivo original "
                f"sem sobrescrever: {type(erro).__name__}"
            )
            return []

    def _salvar_registro(
        self,
    ) -> None:

        if self._preservar_catalogo_corrompido:
            return

        temporario: str | None = None
        try:
            ARQUIVO_CAPACIDADES.parent.mkdir(parents=True, exist_ok=True)
            dados = self.listar_capacidades()
            payload = json.dumps(
                dados, ensure_ascii=False, indent=2, allow_nan=False
            )
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=ARQUIVO_CAPACIDADES.parent,
                prefix=".capacidades-nixal-",
                suffix=".tmp",
                delete=False,
            ) as arquivo:
                temporario = arquivo.name
                try:
                    os.fchmod(arquivo.fileno(), 0o600)
                except OSError:
                    pass
                arquivo.write(payload)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, ARQUIVO_CAPACIDADES)
            temporario = None
            try:
                os.chmod(ARQUIVO_CAPACIDADES, 0o600)
            except OSError:
                pass
        except Exception as erro:
            print(
                "[Nixal] Não foi possível salvar o registro de capacidades: "
                f"{type(erro).__name__}"
            )
        finally:
            if temporario is not None:
                try:
                    os.unlink(temporario)
                except OSError:
                    pass

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
        *,
        politica: str = "somente_leitura",
    ) -> None:

        if politica not in {"somente_leitura", "acao_com_pedido_explicito", "requer_confirmacao"}:
            raise ValueError("Política de capacidade desconhecida.")

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
                politica=politica,
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
            "politica": capacidade.politica,
        }

    # ============================================================
    # VALIDAÇÃO DE ARGUMENTOS
    # ============================================================

    def validar_argumentos(
        self,
        nome: str,
        argumentos: dict[str, Any],
    ) -> tuple[bool, str | None]:
        capacidade = self.capacidades.get(nome)
        if capacidade is None:
            return False, f"Capacidade inexistente: {nome}"
        if not isinstance(argumentos, dict):
            return False, "Os argumentos precisam ser um objeto JSON."

        especificacao = capacidade.argumentos
        desconhecidos = set(argumentos) - set(especificacao)
        if desconhecidos:
            return False, f"Argumento não permitido para '{nome}': {sorted(desconhecidos)[0]}"

        def validar_valor(valor: Any, schema: dict[str, Any], caminho: str) -> str | None:
            esperado = schema.get("tipo", "string")
            mapa_tipos = {
                "string": str,
                "integer": int,
                "int": int,
                "number": (int, float),
                "float": (int, float),
                "boolean": bool,
                "bool": bool,
                "object": dict,
                "array": list,
            }
            tipo_python = mapa_tipos.get(esperado, str)
            if esperado in {"integer", "int"}:
                tipo_valido = isinstance(valor, int) and not isinstance(valor, bool)
            elif esperado in {"number", "float"}:
                tipo_valido = isinstance(valor, (int, float)) and not isinstance(valor, bool)
                if tipo_valido and isinstance(valor, float) and not math.isfinite(valor):
                    return f"O argumento '{caminho}' precisa ser um número finito."
            else:
                tipo_valido = isinstance(valor, tipo_python)
            if not tipo_valido:
                return f"O argumento '{caminho}' precisa ter tipo {esperado}."

            enum = schema.get("enum")
            if isinstance(enum, list) and valor not in enum:
                return f"O argumento '{caminho}' não pertence aos valores permitidos."
            if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                minimo = schema.get("minimo", schema.get("minimum"))
                maximo = schema.get("maximo", schema.get("maximum"))
                if isinstance(minimo, (int, float)) and valor < minimo:
                    return f"O argumento '{caminho}' está abaixo do mínimo permitido."
                if isinstance(maximo, (int, float)) and valor > maximo:
                    return f"O argumento '{caminho}' excede o máximo permitido."
            if isinstance(valor, str):
                minimo = schema.get("min_length", schema.get("minLength"))
                maximo = schema.get("max_length", schema.get("maxLength"))
                if isinstance(minimo, int) and len(valor) < minimo:
                    return f"O argumento '{caminho}' é curto demais."
                if isinstance(maximo, int) and len(valor) > maximo:
                    return f"O argumento '{caminho}' é longo demais."
            if isinstance(valor, dict):
                props = schema.get("properties")
                required = schema.get("required", [])
                if isinstance(props, dict):
                    extras = set(valor) - set(props)
                    if extras:
                        return f"O argumento '{caminho}' contém propriedade não permitida."
                    if isinstance(required, list) and any(k not in valor for k in required):
                        return f"O argumento '{caminho}' não contém todos os campos obrigatórios."
                    for subnome, subvalor in valor.items():
                        if isinstance(props.get(subnome), dict):
                            erro = validar_valor(subvalor, props[subnome], f"{caminho}.{subnome}")
                            if erro:
                                return erro
            if isinstance(valor, list):
                item_schema = schema.get("items")
                limite_minimo = schema.get("min_items", schema.get("minItems"))
                limite = schema.get("max_items", schema.get("maxItems"))
                if isinstance(limite_minimo, int) and len(valor) < limite_minimo:
                    return f"O argumento '{caminho}' contém poucos itens."
                if isinstance(limite, int) and len(valor) > limite:
                    return f"O argumento '{caminho}' contém itens demais."
                if isinstance(item_schema, dict):
                    for indice, item in enumerate(valor):
                        erro = validar_valor(item, item_schema, f"{caminho}[{indice}]")
                        if erro:
                            return erro
            return None

        for nome_argumento, schema in especificacao.items():
            if schema.get("obrigatorio", False) and nome_argumento not in argumentos:
                return False, f"Argumento obrigatório ausente: {nome_argumento}"
        for nome_argumento, valor in argumentos.items():
            erro = validar_valor(valor, especificacao[nome_argumento], nome_argumento)
            if erro:
                return False, erro
        return True, None

    # ============================================================
    # EXECUÇÃO
    # ============================================================

    def executar(
        self,
        nome: str,
        *,
        autorizacao_explicita: bool = False,
        confirmacao: bool = False,
        **argumentos: Any,
    ) -> ResultadoCapacidade:

        inicio = time.perf_counter()
        timestamp = time.time()
        capacidade_registrada = self.capacidades.get(nome)
        bloqueio = None
        if capacidade_registrada is not None:
            if capacidade_registrada.politica not in {
                "somente_leitura", "acao_com_pedido_explicito", "requer_confirmacao",
            }:
                bloqueio = "Política de capacidade inválida; execução bloqueada."
            elif capacidade_registrada.politica == "acao_com_pedido_explicito" and not autorizacao_explicita:
                bloqueio = "Ação exige pedido explícito do usuário; nada foi alterado."
            elif capacidade_registrada.politica == "requer_confirmacao" and not confirmacao:
                bloqueio = "Ação pendente de confirmação; nada foi alterado."
        if bloqueio:
            resultado = ResultadoCapacidade(
                sucesso=False, capacidade=nome, erro=bloqueio, timestamp=timestamp,
                duracao_ms=(time.perf_counter() - inicio) * 1000,
            )
            self._registrar_execucao(resultado)
            return resultado

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

            # Avoid logging exception text/tracebacks that can contain credentials or private data.
            print(f"[Nixal] Falha na capacidade '{nome}': {type(erro).__name__}")

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
                    "politica": capacidade.politica,
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

            segmentos = {
                parte.casefold()
                for parte in caminho_final.relative_to(base_final).parts
            }
            nome_arquivo = caminho_final.name.casefold()
            sufixo = caminho_final.suffix.casefold()
            diretorios_sensiveis = {
                ".ssh", ".gnupg", ".aws", ".config", ".pki", ".hermes",
                "keyrings", "secrets", "secret", "credentials", "credential",
                "tokens", "token",
            }
            nomes_sensiveis = {
                ".bashrc", ".profile", ".netrc", ".npmrc", ".pypirc",
                "authorized_keys", "known_hosts", "credentials.json",
                "token.json", "client_secret.json", "oauth.json",
            }
            palavras_sensiveis = (
                "secret", "credential", "token", "password", "passwd",
                "private_key", "id_rsa", "id_ed25519", "oauth", "cookie", "keystore",
            )
            extensoes_sensiveis = {".pem", ".key", ".p12", ".pfx", ".kdb", ".jks", ".kdbx"}
            if (
                any(parte.startswith(".env") for parte in segmentos)
                or any(parte in diretorios_sensiveis for parte in segmentos)
                or any(parte in nomes_sensiveis for parte in segmentos)
                or any(any(palavra in parte for palavra in palavras_sensiveis) for parte in segmentos)
                or nome_arquivo in nomes_sensiveis
                or sufixo in extensoes_sensiveis
            ):
                return {"sucesso": False, "erro": "A leitura de arquivos de credenciais ou chaves está bloqueada."}

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
        # Serialize read-modify-write within this process. Keep invalid or oversized
        # existing logs intact instead of treating them as empty and destroying evidence.
        with _AUDIT_LOCK:
            historico: list[dict[str, Any]] = []
            if ARQUIVO_LOG.exists():
                try:
                    with ARQUIVO_LOG.open("rb") as arquivo:
                        existente = arquivo.read(MAX_TAMANHO_ARQUIVO + 1)
                    if len(existente) > MAX_TAMANHO_ARQUIVO:
                        return
                    dados = json.loads(existente.decode("utf-8"))
                except Exception:
                    return
                if not isinstance(dados, list) or not all(isinstance(item, dict) for item in dados):
                    return
                historico = dados

            try:
                registro = asdict(resultado)
                capacidades_privadas = {
                    "listar_arquivos", "ler_estado_corpo", "ler_memoria_corporal",
                    "ler_arquivo", "buscar_arquivos", "ler_arquivo_usuario",
                    "consultar_emails_google", "ler_email_google",
                    "consultar_agenda_google", "consultar_home_assistant",
                    "listar_notas_lembretes", "salvar_nota", "criar_lembrete",
                }
                if resultado.capacidade in capacidades_privadas:
                    registro["resultado"] = {
                        "conteudo_omitido": True,
                        "motivo": "Resultado privado omitido do log de execução.",
                    }
                    if registro.get("erro") is not None:
                        registro["erro"] = "Falha de capacidade privada; detalhes omitidos."

                tamanho_registro = len(
                    json.dumps(registro, ensure_ascii=False, indent=2).encode("utf-8")
                )
                if tamanho_registro > MAX_TAMANHO_ARQUIVO // 2:
                    registro["resultado"] = {
                        "truncado": True,
                        "motivo": "Resultado omitido para respeitar o limite do log.",
                        "tamanho_original_bytes": tamanho_registro,
                    }
                    registro["capacidade"] = str(registro.get("capacidade", ""))[:256]
                    if registro.get("erro") is not None:
                        registro["erro"] = str(registro["erro"])[:1024]

                historico.append(registro)
                historico = historico[-200:]
                payload = json.dumps(historico, ensure_ascii=False, indent=2, allow_nan=False)
                while len(payload.encode("utf-8")) > MAX_TAMANHO_ARQUIVO and len(historico) > 1:
                    historico.pop(0)
                    payload = json.dumps(historico, ensure_ascii=False, indent=2, allow_nan=False)
                if len(payload.encode("utf-8")) > MAX_TAMANHO_ARQUIVO:
                    historico = [{
                        "sucesso": bool(registro.get("sucesso")),
                        "capacidade": str(registro.get("capacidade", ""))[:256],
                        "erro": str(registro.get("erro"))[:1024] if registro.get("erro") is not None else None,
                        "timestamp": registro.get("timestamp", 0.0),
                        "duracao_ms": registro.get("duracao_ms", 0.0),
                        "resultado": {
                            "truncado": True,
                            "motivo": "Limite rígido de armazenamento",
                            "tamanho_original_bytes": tamanho_registro,
                        },
                    }]
                    payload = json.dumps(historico, ensure_ascii=False, indent=2, allow_nan=False)
                if len(payload.encode("utf-8")) > MAX_TAMANHO_ARQUIVO:
                    return

                ARQUIVO_LOG.parent.mkdir(parents=True, exist_ok=True)
                temporario: str | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        dir=ARQUIVO_LOG.parent,
                        prefix=".log-capacidades-nixal-",
                        suffix=".tmp",
                        delete=False,
                    ) as arquivo:
                        temporario = arquivo.name
                        try:
                            os.fchmod(arquivo.fileno(), 0o600)
                        except OSError:
                            pass
                        arquivo.write(payload)
                        arquivo.flush()
                        os.fsync(arquivo.fileno())
                    os.replace(temporario, ARQUIVO_LOG)
                    temporario = None
                    try:
                        os.chmod(ARQUIVO_LOG, 0o600)
                    except OSError:
                        pass
                finally:
                    if temporario is not None:
                        try:
                            os.unlink(temporario)
                        except OSError:
                            pass
            except Exception as erro:
                print(
                    "[Nixal] Não foi possível salvar log de capacidade: "
                    f"{type(erro).__name__}"
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
