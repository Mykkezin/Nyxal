#!/usr/bin/env python3
"""Contrato de capacidade operacional: validação, política e auditoria segura."""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CAPACIDADES = BASE_DIR / "capacidades_nixal.json"
ARQUIVO_LOG = BASE_DIR / "log_capacidades_nixal.json"
MAX_TAMANHO_ARQUIVO = 1 * 1024 * 1024
POLITICAS_CAPACIDADE = {"somente_leitura", "acao_com_pedido_explicito", "requer_confirmacao"}


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


class GerenciadorCapacidades:
    """Registro de capacidades existente, com validação e guarda de execução."""

    def __init__(self) -> None:
        self.capacidades: dict[str, Capacidade] = {}
        self.registro_anterior = self._carregar_registro()

        self.registrar(
            nome="obter_hora", descricao="Obtém o horário atual da máquina.",
            objetivo="Descobrir o horário atual do sistema.",
            dominios=["sistema_computacional"], evidencias_dominio=["hora", "horario", "sistema", "maquina"],
            exemplos=["Que horas são?", "Preciso saber a hora.", "Qual é o horário agora?", "Me diga o horário atual."],
            funcao=self._obter_hora,
        )
        self.registrar(
            nome="listar_arquivos", descricao="Lista arquivos não ocultos do diretório do projeto.",
            objetivo="Descobrir quais arquivos existem no projeto Nyxal.",
            dominios=["projeto_arquivo"], evidencias_dominio=["arquivo", "arquivos", "projeto", "diretorio", "pasta"],
            exemplos=["Quais arquivos existem?", "Quero conhecer os arquivos do projeto.", "Liste os arquivos da Nyxal."],
            funcao=self._listar_arquivos,
        )
        self.registrar(
            nome="ler_estado_corpo", descricao="Lê o estado operacional corporal da Nyxal.",
            objetivo="Consultar o estado corporal registrado.",
            dominios=["sistema_computacional"], evidencias_dominio=["estado", "corpo", "fisiologia"],
            exemplos=["Qual é o estado do corpo?", "Leia o estado operacional."], funcao=self._ler_estado_corpo,
        )
        self.registrar(
            nome="ler_memoria_corporal", descricao="Lê a memória corporal operacional.",
            objetivo="Consultar a memória corporal registrada.",
            dominios=["memoria_operacional"], evidencias_dominio=["memoria", "corpo", "estado"],
            exemplos=["Leia a memória corporal.", "Consulte a memória operacional."], funcao=self._ler_memoria_corporal,
        )
        self.registrar(
            nome="ler_arquivo", descricao="Lê arquivo textual relativo dentro do projeto.",
            objetivo="Ler o conteúdo textual de arquivo específico dentro do projeto.",
            dominios=["projeto_arquivo"], evidencias_dominio=["arquivo", "arquivos", "projeto", "texto", "conteudo", "caminho", "diretorio"],
            exemplos=["Leia o arquivo estado_corpo_nixal.json.", "Mostre o conteúdo de capacidades_nixal.json.", "Abra o arquivo teste.py."],
            funcao=self._ler_arquivo,
            argumentos={"arquivo": {"tipo": "string", "obrigatorio": True, "descricao": "Caminho relativo ao projeto"}},
        )

    def _carregar_registro(self) -> list[dict[str, Any]]:
        if not ARQUIVO_CAPACIDADES.exists():
            return []
        try:
            valor = json.loads(ARQUIVO_CAPACIDADES.read_text(encoding="utf-8"))
            return valor if isinstance(valor, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _salvar_registro(self) -> None:
        try:
            ARQUIVO_CAPACIDADES.parent.mkdir(parents=True, exist_ok=True)
            tmp = ARQUIVO_CAPACIDADES.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.listar_capacidades(), ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(ARQUIVO_CAPACIDADES)
        except OSError:
            # Falha de persistência do catálogo não deve impedir o uso em memória.
            pass

    def registrar(
        self, nome: str, descricao: str, objetivo: str, exemplos: list[str],
        funcao: Callable[..., Any], argumentos: dict[str, dict[str, Any]] | None = None,
        dominios: list[str] | None = None, evidencias_dominio: list[str] | None = None,
        politica: str = "somente_leitura",
    ) -> None:
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("Nome de capacidade vazio.")
        if not callable(funcao):
            raise TypeError(f"A capacidade '{nome}' precisa possuir função válida.")
        if not isinstance(exemplos, list) or not all(isinstance(x, str) for x in exemplos):
            raise TypeError("Exemplos precisam ser uma lista de strings.")
        if not isinstance(argumentos or {}, dict):
            raise TypeError("Argumentos precisam ser um objeto.")
        dominios = list(dict.fromkeys(x.strip() for x in (dominios or []) if isinstance(x, str) and x.strip()))
        evidencias = list(dict.fromkeys(x.strip() for x in (evidencias_dominio or []) if isinstance(x, str) and x.strip()))
        if not dominios or not evidencias:
            raise ValueError(f"A capacidade '{nome}' precisa de domínio e evidências.")
        if politica not in POLITICAS_CAPACIDADE:
            raise ValueError("Política de execução da capacidade inválida.")
        if nome in self.capacidades:
            raise ValueError(f"A capacidade '{nome}' já está registrada.")
        self.capacidades[nome] = Capacidade(
            nome=nome, descricao=descricao, objetivo=objetivo, exemplos=exemplos,
            funcao=funcao, argumentos=argumentos or {}, dominios=dominios,
            evidencias_dominio=evidencias, politica=politica,
        )
        self._salvar_registro()

    def obter_especificacao(self, nome: str) -> dict[str, Any] | None:
        capacidade = self.capacidades.get(nome)
        if capacidade is None:
            return None
        return {
            "nome": capacidade.nome, "descricao": capacidade.descricao,
            "objetivo": capacidade.objetivo, "exemplos": capacidade.exemplos,
            "argumentos": capacidade.argumentos, "dominios": capacidade.dominios,
            "evidencias_dominio": capacidade.evidencias_dominio, "politica": capacidade.politica,
        }

    def validar_argumentos(self, nome: str, argumentos: dict[str, Any]) -> tuple[bool, str | None]:
        capacidade = self.capacidades.get(nome)
        if capacidade is None:
            return False, f"Capacidade inexistente: {nome}"
        if not isinstance(argumentos, dict):
            return False, "Os argumentos precisam ser um objeto JSON."
        especificacao = capacidade.argumentos
        desconhecidos = set(argumentos) - set(especificacao)
        if desconhecidos:
            return False, f"Argumento não permitido para '{nome}': {sorted(desconhecidos)[0]}"
        for key, spec in especificacao.items():
            if not isinstance(spec, dict):
                return False, f"Especificação inválida para '{key}'."
            if spec.get("obrigatorio", False) and key not in argumentos:
                return False, f"Argumento obrigatório ausente: {key}"
        for key, value in argumentos.items():
            spec = especificacao[key]
            esperado = spec.get("tipo")
            tipo_ok = True
            if esperado in {"string", "str"}:
                tipo_ok = isinstance(value, str)
            elif esperado in {"integer", "int", "inteiro"}:
                tipo_ok = isinstance(value, int) and not isinstance(value, bool)
            elif esperado in {"number", "float", "numero"}:
                tipo_ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif esperado in {"boolean", "bool", "booleano"}:
                tipo_ok = isinstance(value, bool)
            elif esperado in {"object", "dict", "objeto"}:
                tipo_ok = isinstance(value, dict)
            elif esperado in {"array", "list", "lista"}:
                tipo_ok = isinstance(value, list)
            if not tipo_ok:
                return False, f"O argumento '{key}' precisa ser {esperado}."
            if isinstance(spec.get("enum"), list) and value not in spec["enum"]:
                return False, f"O argumento '{key}' não está entre os valores permitidos."
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if spec.get("minimo", spec.get("minimum")) is not None and value < spec.get("minimo", spec.get("minimum")):
                    return False, f"O argumento '{key}' está abaixo do mínimo permitido."
                if spec.get("maximo", spec.get("maximum")) is not None and value > spec.get("maximo", spec.get("maximum")):
                    return False, f"O argumento '{key}' excede o máximo permitido."
            if isinstance(value, str):
                if spec.get("min_length") is not None and len(value) < spec["min_length"]:
                    return False, f"O argumento '{key}' é curto demais."
                if spec.get("max_length") is not None and len(value) > spec["max_length"]:
                    return False, f"O argumento '{key}' é longo demais."
        return True, None

    def executar(self, nome: str, *, autorizacao_explicita: bool = False, confirmacao: bool = False, **argumentos: Any) -> ResultadoCapacidade:
        inicio, timestamp = time.perf_counter(), time.time()
        capacidade = self.capacidades.get(nome)
        if capacidade is not None:
            if capacidade.politica == "acao_com_pedido_explicito" and not autorizacao_explicita:
                resultado = ResultadoCapacidade(False, nome, erro="Ação bloqueada: falta pedido explícito do usuário.", timestamp=timestamp, duracao_ms=(time.perf_counter()-inicio)*1000)
                self._registrar_execucao(resultado)
                return resultado
            if capacidade.politica == "requer_confirmacao" and not (autorizacao_explicita and confirmacao):
                resultado = ResultadoCapacidade(False, nome, erro="Ação bloqueada: requer autorização explícita e confirmação.", timestamp=timestamp, duracao_ms=(time.perf_counter()-inicio)*1000)
                self._registrar_execucao(resultado)
                return resultado
        valido, erro = self.validar_argumentos(nome, argumentos)
        if not valido:
            resultado = ResultadoCapacidade(False, nome, erro=erro, timestamp=timestamp, duracao_ms=(time.perf_counter()-inicio)*1000)
            self._registrar_execucao(resultado)
            return resultado
        try:
            valor = capacidade.funcao(**argumentos)
            resultado = ResultadoCapacidade(True, nome, resultado=valor, timestamp=timestamp, duracao_ms=(time.perf_counter()-inicio)*1000)
        except Exception as exc:
            resultado = ResultadoCapacidade(False, nome, erro=f"{type(exc).__name__}: {exc}", timestamp=timestamp, duracao_ms=(time.perf_counter()-inicio)*1000)
            traceback.print_exc()
        self._registrar_execucao(resultado)
        return resultado

    def listar_capacidades(self) -> list[dict[str, Any]]:
        return [{
            "nome": c.nome, "descricao": c.descricao, "objetivo": c.objetivo,
            "exemplos": c.exemplos, "argumentos": c.argumentos,
            "dominios": c.dominios, "evidencias_dominio": c.evidencias_dominio,
            "politica": c.politica,
        } for c in self.capacidades.values()]

    def _obter_hora(self) -> dict[str, Any]:
        agora = time.localtime()
        return {"hora": agora.tm_hour, "minuto": agora.tm_min, "segundo": agora.tm_sec, "timestamp": time.time()}

    def _listar_arquivos(self) -> list[str]:
        try:
            return sorted(item.name for item in BASE_DIR.iterdir() if item.is_file() and not item.name.startswith("."))
        except OSError:
            return []

    def _ler_estado_corpo(self) -> dict[str, Any]:
        arquivo = BASE_DIR / "estado_corpo_nixal.json"
        if not arquivo.exists():
            return {"disponivel": False, "motivo": "estado_corpo_nixal.json ainda não existe."}
        try:
            return {"disponivel": True, "estado": json.loads(arquivo.read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError) as exc:
            return {"disponivel": False, "erro": type(exc).__name__}

    def _ler_memoria_corporal(self) -> dict[str, Any]:
        arquivo = BASE_DIR / "memoria_corporal_nixal.json"
        if not arquivo.exists():
            return {"disponivel": False, "motivo": "memoria_corporal_nixal.json ainda não existe."}
        try:
            return {"disponivel": True, "memoria": json.loads(arquivo.read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError) as exc:
            return {"disponivel": False, "erro": type(exc).__name__}

    def _ler_arquivo(self, arquivo: str) -> dict[str, Any]:
        import re
        if not isinstance(arquivo, str) or not arquivo.strip():
            return {"sucesso": False, "erro": "Informe um caminho relativo."}
        caminho = Path(arquivo)
        if caminho.is_absolute() or ".." in caminho.parts or any(part.startswith(".") for part in caminho.parts):
            return {"sucesso": False, "erro": "Caminho absoluto, traversal e caminhos ocultos são bloqueados."}
        try:
            destino = (BASE_DIR / caminho).resolve()
            destino.relative_to(BASE_DIR.resolve())
        except (OSError, ValueError):
            return {"sucesso": False, "erro": "O arquivo precisa estar dentro do projeto Nyxal."}
        sensivel = {".env", ".env.local", "credentials.json", "token.json", "id_rsa", "id_ed25519", ".bashrc", ".profile"}
        if destino.name.lower() in sensivel or destino.name.lower().startswith(".env") or destino.suffix.lower() in {".pem", ".key", ".p12", ".pfx"} or any(x in destino.name.lower() for x in ("secret", "credential", "access_token", "refresh_token", "private_key")):
            return {"sucesso": False, "erro": "Leitura bloqueada pela política de proteção de credenciais."}
        try:
            if not destino.is_file():
                return {"sucesso": False, "erro": f"Arquivo não encontrado: {arquivo}"}
            if destino.stat().st_size > 1_000_000:
                return {"sucesso": False, "erro": "Arquivo excede o limite de 1 MiB."}
            return {"sucesso": True, "conteudo": destino.read_text(encoding="utf-8")[:20000]}
        except (OSError, UnicodeDecodeError):
            return {"sucesso": False, "erro": "Arquivo indisponível ou não textual UTF-8."}

    def _registrar_execucao(self, resultado: ResultadoCapacidade) -> None:
        historico: list[dict[str, Any]] = []
        if ARQUIVO_LOG.exists():
            try:
                dados = json.loads(ARQUIVO_LOG.read_text(encoding="utf-8"))
                if isinstance(dados, list):
                    historico = dados
            except (OSError, json.JSONDecodeError):
                historico = []
        registro = asdict(resultado)
        if resultado.capacidade in {"ler_arquivo", "ler_arquivo_usuario", "consultar_emails_google", "ler_email_google", "consultar_agenda_google", "listar_notas_lembretes", "salvar_nota", "criar_lembrete", "consultar_home_assistant"}:
            registro["resultado"] = {"conteudo_omitido": True, "motivo": "Resultado privado não é gravado no log."}
            if registro.get("erro"):
                registro["erro"] = "Falha de ferramenta omitida do log por privacidade."
        tamanho = len(json.dumps(registro, ensure_ascii=False).encode("utf-8"))
        if tamanho > MAX_TAMANHO_ARQUIVO // 2:
            registro["resultado"] = {"truncado": True, "tamanho_original_bytes": tamanho}
        historico.append(registro)
        orcamento = MAX_TAMANHO_ARQUIVO // 2
        mantido = []
        tamanho_atual = 2
        for item in reversed(historico):
            item_size = len(json.dumps(item, ensure_ascii=False).encode("utf-8")) + 1
            if tamanho_atual + item_size > orcamento:
                break
            mantido.append(item)
            tamanho_atual += item_size
        seguro = list(reversed(mantido))
        try:
            temp = ARQUIVO_LOG.with_suffix(".json.tmp")
            temp.write_text(json.dumps(seguro, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(ARQUIVO_LOG)
        except OSError:
            pass


def ativar_ferramentas_operacionais(capacidades: GerenciadorCapacidades | None = None, *, incluir_acoes: bool = True) -> GerenciadorCapacidades:
    """Registra adaptadores no gerenciador existente; retorna a instância utilizada."""
    alvo = capacidades if capacidades is not None else GerenciadorCapacidades()
    from nixal_tool_use import registrar_capacidades_operacionais
    registrar_capacidades_operacionais(alvo, incluir_acoes=incluir_acoes)
    return alvo


def _obter_gerenciador_capacidades() -> GerenciadorCapacidades:
    """Usado pelo diálogo para compartilhar a mesma instância e os contratos."""
    return ativar_ferramentas_operacionais(GerenciadorCapacidades(), incluir_acoes=True)

__all__ = ["GerenciadorCapacidades", "ResultadoCapacidade", "Capacidade", "ativar_ferramentas_operacionais", "_obter_gerenciador_capacidades"]
