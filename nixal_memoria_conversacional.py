#!/usr/bin/env python3
"""
NIXAL — MEMÓRIA CONVERSACIONAL RECENTE

Mantém até 12 mensagens por sessão. Pode operar apenas em RAM (modo
compatível) ou persistir no caminho explicitamente configurado por
NYXAL_CONVERSATION_MEMORY_PATH. A persistência usa JSON versionado,
bloqueio entre processos, arquivo privado, gravação atômica e fail-closed
em caso de corrupção. Esta memória continua sendo contexto recente, não
conhecimento permanente nem memória de investigação.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import tempfile
import threading
import unicodedata
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator


_STOPWORDS_RECALL = frozenset({
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "da", "do",
    "das", "dos", "em", "no", "na", "nos", "nas", "por", "para", "com",
    "sem", "sobre", "entre", "e", "ou", "mas", "que", "se", "eu", "tu",
    "voce", "voces", "me", "meu", "minha", "meus", "minhas", "seu", "sua",
    "seus", "suas", "isso", "isto", "aquele", "aquela", "aquilo", "foi",
    "era", "ser", "estar", "esta", "estao", "tem", "tinha", "teve", "ter",
    "fazer", "faz", "qual", "quais", "como", "quando", "onde", "porque",
    "quem", "lembra", "lembrar", "recorda", "recordar", "conversamos",
    "falamos", "disse", "diz", "antes", "anterior", "anteriores", "agora",
    "paramos", "continuar", "continue", "retomar", "retome", "voltar", "volte",
})


def _normalizar_termos_memoria(texto: str) -> list[str]:
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    sem_acentos = "".join(
        caractere for caractere in normalizado
        if not unicodedata.combining(caractere)
    )
    return [
        token for token in re.sub(r"[^a-z0-9]+", " ", sem_acentos).split()
        if len(token) >= 2 and token not in _STOPWORDS_RECALL
    ]


def sanitizar_texto_memoria(texto: str, limite: int = 900) -> str:
    """Redige credenciais comuns e blocos de chave privada antes de injetar contexto.

    A busca lexical continua local e explícita; este redator reduz exposição acidental
    de segredos estruturados, mas não promete reconhecer senhas em linguagem natural.
    """
    if not isinstance(texto, str) or not isinstance(limite, int) or isinstance(limite, bool) or limite < 1:
        return ""

    # Redige blocos PEM/OpenSSH inteiros, inclusive um bloco incompleto truncado.
    texto = re.sub(
        r"-----BEGIN ([A-Z0-9 ]*PRIVATE KEY)-----.*?(?:-----END \1-----|\Z)",
        "[REDACTED PRIVATE KEY]",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Formatos frequentes de tokens de fornecedores; não exigem um rótulo token=.
    texto = re.sub(
        r"(?<![A-Za-z0-9])(?:"
        r"gh[pousr]_[A-Za-z0-9_]{20,}|"
        r"github_pat_[A-Za-z0-9_]{20,}|"
        r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|"
        r"AIza[A-Za-z0-9_-]{30,}|"
        r"AKIA[0-9A-Z]{16}|"
        r"xox[baprs]-[A-Za-z0-9-]{20,}"
        r")(?![A-Za-z0-9])",
        "[REDACTED TOKEN]",
        texto,
    )
    texto = re.sub(
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?![A-Za-z0-9_-])",
        "[REDACTED JWT]",
        texto,
    )
    texto = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", texto)
    texto = re.sub(
        r"(?i)\b(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|session[_ -]?token|id[_ -]?token|token|authorization|password|senha|secret|credential)\b\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+",
        r"\1=[REDACTED]",
        texto,
    )
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:limite]


def _sanitizar_texto_memoria(texto: str, limite: int = 900) -> str:
    """Alias interno compatível para a antiga chamada privada."""
    return sanitizar_texto_memoria(texto, limite)


class MemoriaConversacionalNixal:
    """Contexto recente de conversa, volátil ou persistido localmente."""

    ORIGEM = "memoria_conversacional_nixal"
    VERSAO = "56.6.0"
    VERSAO_ARQUIVO = 1
    PADRAO_MAX_MENSAGENS = 12
    MAX_SESSOES_PERSISTIDAS = 200
    MAX_CARACTERES_SESSAO = 200
    MAX_CARACTERES_MENSAGEM = 12000
    MAX_ARQUIVO_BYTES = 32 * 1024 * 1024
    VARIAVEL_CAMINHO = "NYXAL_CONVERSATION_MEMORY_PATH"

    def __init__(
        self,
        max_mensagens: int = PADRAO_MAX_MENSAGENS,
        caminho: str | Path | None = None,
    ) -> None:
        if not isinstance(max_mensagens, int) or isinstance(max_mensagens, bool) or max_mensagens <= 0:
            raise ValueError("max_mensagens precisa ser um inteiro positivo.")

        if caminho is None:
            configurado = os.environ.get(self.VARIAVEL_CAMINHO, "").strip()
            caminho = configurado or None
        self.caminho = Path(caminho).expanduser() if caminho is not None else None
        self.max_mensagens = max_mensagens
        self._historicos: dict[str, list[dict[str, str]]] = {}
        self._lock = threading.RLock()
        self._erro_persistencia: str | None = None

        if self.caminho is not None:
            # O diagnóstico inicial detecta corrupção sem recriar nem substituir
            # o arquivo. A instância permanece em modo degradado até reparo manual.
            _, erro = self._ler_persistencia()
            self._erro_persistencia = erro

    @staticmethod
    def _vazio() -> dict[str, Any]:
        return {"versao": MemoriaConversacionalNixal.VERSAO_ARQUIVO, "sessoes": {}}

    @contextmanager
    def _bloquear_arquivo(self) -> Iterator[None]:
        if self.caminho is None:
            yield
            return

        pasta = self.caminho.parent
        # Inspecionar todos os ancestrais antes de mkdir: caso contrário,
        # parents=True poderia criar diretórios atravessando um symlink existente.
        candidato = pasta
        while True:
            if candidato.is_symlink():
                raise OSError("ancestral_de_memoria_nao_pode_ser_link_simbolico")
            if candidato.parent == candidato:
                break
            candidato = candidato.parent

        pasta.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Revalidar após a criação para reduzir a janela de corrida.
        candidato = pasta
        while True:
            if candidato.is_symlink():
                raise OSError("ancestral_de_memoria_nao_pode_ser_link_simbolico")
            if candidato.parent == candidato:
                break
            candidato = candidato.parent
        if self.caminho.is_symlink():
            raise OSError("arquivo_de_memoria_nao_pode_ser_link_simbolico")
        permissoes = stat.S_IMODE(pasta.stat().st_mode)
        if permissoes & 0o077:
            # Só corrigir automaticamente a pasta de dados conhecida da Nyxal.
            # Nunca chmod em /tmp, $HOME ou em um diretório arbitrário configurado.
            pasta_padrao = Path.home() / ".local" / "share" / "nyxal"
            if pasta.resolve() == pasta_padrao.resolve():
                os.chmod(pasta, 0o700)
            else:
                raise OSError("diretorio_de_memoria_nao_privado")

        lock_path = self.caminho.with_name(self.caminho.name + ".lock")
        if lock_path.is_symlink():
            raise OSError("lock_de_memoria_nao_pode_ser_link_simbolico")
        flags = os.O_CREAT | os.O_RDWR
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descritor = os.open(lock_path, flags, 0o600)
        try:
            os.fchmod(descritor, 0o600)
            fcntl.flock(descritor, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(descritor, fcntl.LOCK_UN)
            finally:
                os.close(descritor)

    def _validar_dados(self, dados: Any) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(dados, dict):
            return None, "estrutura_raiz_invalida"
        if dados.get("versao") != self.VERSAO_ARQUIVO:
            return None, "versao_de_memoria_nao_suportada"
        sessoes = dados.get("sessoes")
        if not isinstance(sessoes, dict):
            return None, "mapa_de_sessoes_invalido"
        if len(sessoes) > self.MAX_SESSOES_PERSISTIDAS:
            return None, "quantidade_de_sessoes_excede_limite"

        validadas: dict[str, list[dict[str, str]]] = {}
        for sessao, mensagens in sessoes.items():
            if (
                not isinstance(sessao, str)
                or not sessao.strip()
                or len(sessao) > self.MAX_CARACTERES_SESSAO
                or not isinstance(mensagens, list)
                or len(mensagens) > self.max_mensagens
            ):
                return None, "sessao_ou_historico_invalido"
            normalizadas: list[dict[str, str]] = []
            for mensagem in mensagens:
                if not isinstance(mensagem, dict):
                    return None, "mensagem_invalida"
                papel = mensagem.get("papel")
                texto = mensagem.get("texto")
                if (
                    papel not in {"user", "assistant"}
                    or not isinstance(texto, str)
                    or not texto.strip()
                    or len(texto) > self.MAX_CARACTERES_MENSAGEM
                ):
                    return None, "mensagem_invalida"
                normalizadas.append({"papel": papel, "texto": texto})
            validadas[sessao] = normalizadas
        return {"versao": self.VERSAO_ARQUIVO, "sessoes": validadas}, None

    def _ler_persistencia_sem_lock(self) -> tuple[dict[str, Any] | None, str | None]:
        if self.caminho is None:
            return self._vazio(), None
        try:
            if self.caminho.is_symlink():
                return None, "arquivo_de_memoria_e_link_simbolico"
            with self.caminho.open("rb") as arquivo:
                if not stat.S_ISREG(os.fstat(arquivo.fileno()).st_mode):
                    return None, "arquivo_de_memoria_nao_regular"
                bruto = arquivo.read(self.MAX_ARQUIVO_BYTES + 1)
        except FileNotFoundError:
            return self._vazio(), None
        except OSError:
            return None, "arquivo_de_memoria_ilegivel"

        if len(bruto) > self.MAX_ARQUIVO_BYTES:
            return None, "arquivo_de_memoria_excede_limite"
        try:
            dados = json.loads(bruto.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            return None, "arquivo_de_memoria_corrompido"
        return self._validar_dados(dados)

    def _ler_persistencia(self) -> tuple[dict[str, Any] | None, str | None]:
        if self.caminho is None:
            return self._vazio(), None
        try:
            with self._bloquear_arquivo():
                return self._ler_persistencia_sem_lock()
        except OSError:
            return None, "persistencia_indisponivel"

    def _salvar_persistencia_sem_lock(self, dados: dict[str, Any]) -> str | None:
        if self.caminho is None:
            return None
        try:
            dados_validados, erro = self._validar_dados(dados)
            if erro or dados_validados is None:
                return erro or "estrutura_de_memoria_invalida"
            # A limitação de bytes também considera UTF-8. Se o JSON ficar
            # grande demais, remove sessões menos recentemente ativas até caber;
            # a sessão em uso está no fim do mapa. Nunca trunca mensagens.
            dados["sessoes"] = dados_validados["sessoes"]
            sessoes = dados["sessoes"]
            while True:
                serializado = json.dumps(
                    dados,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                if len(serializado) <= self.MAX_ARQUIVO_BYTES:
                    break
                if len(sessoes) <= 1:
                    return "arquivo_de_memoria_excede_limite"
                sessoes.pop(next(iter(sessoes)))

            fd, nome_temporario = tempfile.mkstemp(
                prefix=".conversa-nixal-",
                suffix=".tmp",
                dir=str(self.caminho.parent),
            )
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "wb") as arquivo:
                    arquivo.write(serializado)
                    arquivo.flush()
                    os.fsync(arquivo.fileno())
                os.replace(nome_temporario, self.caminho)
                os.chmod(self.caminho, 0o600)
                diretorio_fd = os.open(
                    self.caminho.parent,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
                )
                try:
                    os.fsync(diretorio_fd)
                finally:
                    os.close(diretorio_fd)
            finally:
                try:
                    os.unlink(nome_temporario)
                except FileNotFoundError:
                    pass
            return None
        except (OSError, TypeError, ValueError):
            return "falha_ao_persistir_memoria"

    def _erro(
        self,
        mensagem: str,
        *,
        estado: str = "operacao_negada",
        arquivo_original_preservado: bool = False,
    ) -> dict[str, Any]:
        resultado: dict[str, Any] = {
            "sucesso": False,
            "estado": estado,
            "origem": self.ORIGEM,
            "erro": mensagem,
            "permanente": False,
            "versao_memoria": self.VERSAO,
        }
        if arquivo_original_preservado:
            resultado["arquivo_original_preservado"] = True
        return resultado

    def _erro_degradacao(self, motivo: str) -> dict[str, Any]:
        self._erro_persistencia = motivo
        preservado = self.caminho is not None and self.caminho.exists()
        return self._erro(
            (
                f"memoria_degradada:{motivo}; arquivo original preservado."
                if preservado
                else f"memoria_degradada:{motivo}; gravação recusada."
            ),
            estado="memoria_degradada",
            arquivo_original_preservado=preservado,
        )

    def _registrar_volatil(
        self, sessao: str, papel: str, texto: str,
    ) -> dict[str, Any]:
        historico = self._historicos.setdefault(sessao, [])
        historico.append({"papel": papel, "texto": texto})
        del historico[:-self.max_mensagens]
        return self._resultado_registro(sessao, historico)

    def _resultado_registro(
        self, sessao: str, historico: list[dict[str, str]],
    ) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "mensagem_registrada",
            "origem": self.ORIGEM,
            "sessao": sessao,
            "quantidade": len(historico),
            "valor": deepcopy(historico[-1]),
            "permanente": False,
            "persistido": self.caminho is not None,
            "versao_memoria": self.VERSAO,
        }

    def registrar(
        self,
        sessao: str,
        papel: str,
        texto: str,
    ) -> dict[str, Any]:
        sessao_normalizada = self._normalizar_sessao(sessao)
        papel_normalizado = self._normalizar_papel(papel)

        if sessao_normalizada is None:
            return self._erro("Sessão inválida.")
        if papel_normalizado is None:
            return self._erro("Papel inválido.")
        if not isinstance(texto, str) or not texto.strip():
            return self._erro("Texto inválido.")
        texto_normalizado = texto.strip()
        if len(texto_normalizado) > self.MAX_CARACTERES_MENSAGEM:
            return self._erro("Mensagem excede o limite de caracteres.")

        with self._lock:
            if self.caminho is None:
                return self._registrar_volatil(sessao_normalizada, papel_normalizado, texto_normalizado)

            try:
                with self._bloquear_arquivo():
                    dados, erro = self._ler_persistencia_sem_lock()
                    if erro or dados is None:
                        return self._erro_degradacao(erro or "estrutura_de_memoria_invalida")
                    sessoes = dados["sessoes"]
                    # Mover a sessão usada para o fim mantém a retenção por recência.
                    historico = sessoes.pop(sessao_normalizada, [])
                    if len(sessoes) >= self.MAX_SESSOES_PERSISTIDAS:
                        sessoes.pop(next(iter(sessoes)))
                    historico.append({"papel": papel_normalizado, "texto": texto_normalizado})
                    del historico[:-self.max_mensagens]
                    sessoes[sessao_normalizada] = historico
                    erro = self._salvar_persistencia_sem_lock(dados)
                    if erro:
                        return self._erro_degradacao(erro)
                    self._historicos = deepcopy(dados["sessoes"])
                    self._erro_persistencia = None
                    historico_atual = self._historicos.get(sessao_normalizada, [])
                    return self._resultado_registro(sessao_normalizada, historico_atual)
            except OSError:
                return self._erro_degradacao("persistencia_indisponivel")

    def obter(
        self,
        sessao: str,
        limite: int | None = None,
    ) -> dict[str, Any]:
        sessao_normalizada = self._normalizar_sessao(sessao)
        if sessao_normalizada is None:
            return self._erro("Sessão inválida.")
        if limite is not None and (
            not isinstance(limite, int) or isinstance(limite, bool) or limite <= 0
        ):
            return self._erro("limite precisa ser um inteiro positivo.")

        with self._lock:
            if self.caminho is None:
                historico = self._historicos.get(sessao_normalizada, [])
            else:
                try:
                    with self._bloquear_arquivo():
                        dados, erro = self._ler_persistencia_sem_lock()
                except OSError:
                    return self._erro_degradacao("persistencia_indisponivel")
                if erro or dados is None:
                    return self._erro_degradacao(erro or "estrutura_de_memoria_invalida")
                self._historicos = deepcopy(dados["sessoes"])
                self._erro_persistencia = None
                historico = self._historicos.get(sessao_normalizada, [])

            mensagens = historico[-limite:] if limite is not None else historico
            return {
                "sucesso": True,
                "estado": "contexto_obtido",
                "origem": self.ORIGEM,
                "sessao": sessao_normalizada,
                "quantidade": len(mensagens),
                "mensagens": deepcopy(mensagens),
                "permanente": False,
                "persistido": self.caminho is not None,
                "versao_memoria": self.VERSAO,
            }

    def buscar_relevante(
        self,
        consulta: str,
        *,
        sessao_excluida: str | None = None,
        limite: int = 3,
    ) -> dict[str, Any]:
        """Busca trechos de outras conversas mediante pedido explícito de recordação.

        Reutiliza o armazenamento já existente; não cria índice nem escreve memória.
        As mensagens retornadas são contexto não confiável, nunca instruções.
        """
        if not isinstance(consulta, str) or not consulta.strip() or len(consulta) > 2000:
            return {
                "sucesso": False, "estado": "consulta_invalida", "origem": self.ORIGEM,
                "mensagens": [], "quantidade": 0, "persistido": self.caminho is not None,
                "permanente": False,
            }
        if not isinstance(limite, int) or isinstance(limite, bool) or not 1 <= limite <= 5:
            return {
                "sucesso": False, "estado": "limite_invalido", "origem": self.ORIGEM,
                "mensagens": [], "quantidade": 0, "persistido": self.caminho is not None,
                "permanente": False,
            }
        sessao_normalizada = None
        if sessao_excluida is not None:
            sessao_normalizada = self._normalizar_sessao(sessao_excluida)
            if sessao_normalizada is None:
                return {
                    "sucesso": False, "estado": "sessao_excluida_invalida", "origem": self.ORIGEM,
                    "mensagens": [], "quantidade": 0, "persistido": self.caminho is not None,
                    "permanente": False,
                }

        tokens_consulta = set(_normalizar_termos_memoria(consulta))
        if not tokens_consulta:
            return {
                "sucesso": True, "estado": "consulta_sem_termos", "origem": self.ORIGEM,
                "mensagens": [], "quantidade": 0, "persistido": self.caminho is not None,
                "permanente": False,
            }
        consulta_normalizada = " ".join(_normalizar_termos_memoria(consulta))
        persistido = self.caminho is not None

        with self._lock:
            if self.caminho is None:
                sessoes = deepcopy(self._historicos)
            else:
                try:
                    with self._bloquear_arquivo():
                        dados, erro = self._ler_persistencia_sem_lock()
                except OSError:
                    return {
                        "sucesso": False, "estado": "memoria_degradada",
                        "motivo": "persistencia_indisponivel", "origem": self.ORIGEM,
                        "mensagens": [], "quantidade": 0, "persistido": True,
                        "arquivo_original_preservado": True, "permanente": False,
                    }
                if erro or dados is None:
                    self._erro_persistencia = erro or "estrutura_de_memoria_invalida"
                    return {
                        "sucesso": False, "estado": "memoria_degradada",
                        "motivo": self._erro_persistencia, "origem": self.ORIGEM,
                        "mensagens": [], "quantidade": 0, "persistido": True,
                        "arquivo_original_preservado": bool(self.caminho.exists()),
                        "permanente": False,
                    }
                sessoes = deepcopy(dados["sessoes"])
                self._historicos = deepcopy(sessoes)
                self._erro_persistencia = None

        candidatos: list[tuple[float, int, int, dict[str, Any]]] = []
        vistos: dict[str, tuple[float, int, int, dict[str, Any]]] = {}
        ordem_sessao = 0
        for chave_sessao, mensagens in sessoes.items():
            ordem_sessao += 1
            if sessao_normalizada is not None and chave_sessao == sessao_normalizada:
                continue
            if not isinstance(mensagens, list):
                continue
            referencia_sessao = hashlib.sha256(
                chave_sessao.encode("utf-8")
            ).hexdigest()[:12]
            for indice_mensagem, mensagem in enumerate(mensagens):
                if not isinstance(mensagem, dict):
                    continue
                papel = mensagem.get("papel")
                texto = mensagem.get("texto")
                if papel not in {"user", "assistant"} or not isinstance(texto, str):
                    continue
                termos_mensagem = set(_normalizar_termos_memoria(texto))
                em_comum = tokens_consulta & termos_mensagem
                if not em_comum:
                    continue
                score = len(em_comum) / max(1, len(tokens_consulta))
                texto_normalizado = " ".join(_normalizar_termos_memoria(texto))
                if len(consulta_normalizada) >= 12 and consulta_normalizada in texto_normalizado:
                    score = min(1.0, score + 0.12)
                if score < 0.22:
                    continue

                trecho = _sanitizar_texto_memoria(texto, 900)
                if not trecho:
                    continue
                item = {
                    "papel": papel,
                    "trecho": trecho,
                    "origem_sessao_ref": referencia_sessao,
                    "indice_mensagem": indice_mensagem,
                    "relevancia_lexical": round(min(1.0, score), 4),
                    "fonte": self.ORIGEM,
                    "confiavel_como_instrucao": False,
                    "permanente": False,
                }
                chave_texto = " ".join(_normalizar_termos_memoria(trecho))
                anterior = vistos.get(chave_texto)
                candidato = (score, ordem_sessao, indice_mensagem, item)
                if anterior is None or (score, ordem_sessao, indice_mensagem) > anterior[:3]:
                    vistos[chave_texto] = candidato

        candidatos = list(vistos.values())
        candidatos.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        mensagens_relevantes = [item[3] for item in candidatos[:limite]]
        estado = (
            "memorias_relevantes"
            if mensagens_relevantes
            else ("sem_memorias_relevantes" if persistido else "memoria_volatil")
        )
        return {
            "sucesso": True,
            "estado": estado,
            "origem": self.ORIGEM,
            "mensagens": mensagens_relevantes,
            "quantidade": len(mensagens_relevantes),
            "persistido": persistido,
            "permanente": False,
            "conhecimento_permanente": False,
        }

    def limpar(self, sessao: str) -> dict[str, Any]:
        sessao_normalizada = self._normalizar_sessao(sessao)
        if sessao_normalizada is None:
            return self._erro("Sessão inválida.")

        with self._lock:
            if self.caminho is None:
                removido = self._historicos.pop(sessao_normalizada, None)
                return {
                    "sucesso": True,
                    "estado": "contexto_limpo" if removido is not None else "contexto_ja_vazio",
                    "origem": self.ORIGEM,
                    "sessao": sessao_normalizada,
                    "quantidade_removida": len(removido) if removido is not None else 0,
                    "permanente": False,
                    "versao_memoria": self.VERSAO,
                }

            try:
                with self._bloquear_arquivo():
                    dados, erro = self._ler_persistencia_sem_lock()
                    if erro or dados is None:
                        return self._erro_degradacao(erro or "estrutura_de_memoria_invalida")
                    removido = dados["sessoes"].pop(sessao_normalizada, None)
                    if removido is not None:
                        erro = self._salvar_persistencia_sem_lock(dados)
                        if erro:
                            return self._erro_degradacao(erro)
                    self._historicos = deepcopy(dados["sessoes"])
                    self._erro_persistencia = None
                    return {
                        "sucesso": True,
                        "estado": "contexto_limpo" if removido is not None else "contexto_ja_vazio",
                        "origem": self.ORIGEM,
                        "sessao": sessao_normalizada,
                        "quantidade_removida": len(removido) if removido is not None else 0,
                        "permanente": False,
                        "versao_memoria": self.VERSAO,
                    }
            except OSError:
                return self._erro_degradacao("persistencia_indisponivel")

    def possui_sessao(self, sessao: str) -> bool:
        resultado = self.obter(sessao, limite=1)
        return resultado.get("sucesso") is True and resultado.get("quantidade", 0) > 0

    def estado(self) -> dict[str, Any]:
        """Diagnóstico sem expor o caminho absoluto nem conteúdo das conversas."""
        if self.caminho is None:
            return {
                "sucesso": True, "estado": "memoria_volatil",
                "persistencia_ativa": False, "permanente": False,
            }
        dados, erro = self._ler_persistencia()
        if erro or dados is None:
            self._erro_persistencia = erro or "estrutura_de_memoria_invalida"
            degradacao: dict[str, Any] = {
                "sucesso": False, "estado": "memoria_degradada",
                "persistencia_ativa": True, "motivo": self._erro_persistencia,
                "permanente": False,
            }
            if self.caminho is not None and self.caminho.exists():
                degradacao["arquivo_original_preservado"] = True
            return degradacao
        self._historicos = deepcopy(dados["sessoes"])
        self._erro_persistencia = None
        return {
            "sucesso": True, "estado": "persistencia_ativa",
            "persistencia_ativa": True,
            "sessoes": len(dados["sessoes"]),
            "mensagens": sum(len(items) for items in dados["sessoes"].values()),
            "permanente": False,
        }

    @staticmethod
    def _normalizar_sessao(sessao: str) -> str | None:
        if not isinstance(sessao, str):
            return None
        valor = sessao.strip()
        if not valor or len(valor) > MemoriaConversacionalNixal.MAX_CARACTERES_SESSAO:
            return None
        return valor

    @staticmethod
    def _normalizar_papel(papel: str) -> str | None:
        if not isinstance(papel, str):
            return None
        valor = papel.strip().lower()
        return valor if valor in {"user", "assistant"} else None


__all__ = ["MemoriaConversacionalNixal"]
