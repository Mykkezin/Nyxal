#!/usr/bin/env python3
"""Recuperação contextual local sobre as memórias duráveis que a Nyxal já possui.

Este módulo é somente leitura: não cria índice persistente, não modifica as fontes,
não promove candidatos e não executa capacidades. Combina investigações históricas
com candidatos da memória de conhecimento existente, preservando proveniência e
estado epistemológico. A busca lexical é uma baseline deliberada antes de adotar
embeddings ou um banco vetorial adicional.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

from nixal_contexto_historico_relevante import ContextoHistoricoRelevanteNixal
from nixal_memoria_conhecimento import MemoriaConhecimentoNixal
from nixal_memoria_investigacao import MemoriaInvestigacaoNixal


_STOPWORDS = frozenset({
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "da", "do",
    "das", "dos", "em", "no", "na", "nos", "nas", "por", "para", "com",
    "sem", "sobre", "entre", "e", "ou", "mas", "que", "se", "eu", "tu",
    "voce", "voces", "me", "meu", "minha", "meus", "minhas", "seu", "sua",
    "seus", "suas", "ele", "ela", "eles", "elas", "isso", "isto", "aquele",
    "aquela", "aquilo", "foi", "era", "ser", "estar", "esta", "estao", "tem",
    "tinha", "teve", "ter", "fazer", "faz", "falei", "disse", "sobre", "qual",
    "quais", "como", "quando", "onde", "porque", "por que", "quem", "me",
    "lembre", "lembrar", "recordar", "anterior", "anteriores", "agora",
})

_MAX_CONSULTA = 2000
_MAX_TEXTO_CANDIDATO = 900
_MAX_RETORNO = 5
_SCORE_MINIMO = 0.16


def _normalizar(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    sem_acentos = "".join(
        caractere for caractere in normalizado
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-z0-9]+", " ", sem_acentos).strip()


def _tokens(texto: str) -> list[str]:
    return [
        token for token in _normalizar(texto).split()
        if len(token) >= 2 and token not in _STOPWORDS
    ]


def _texto_seguro(valor: Any, limite: int = _MAX_TEXTO_CANDIDATO) -> str:
    if not isinstance(valor, str):
        return ""
    texto = re.sub(r"\s+", " ", valor).strip()
    texto = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", texto)
    texto = re.sub(
        r"(?i)\b(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|session[_ -]?token|id[_ -]?token|token|authorization|password|senha|secret|credential)\b\s*[:=]\s*(?:Bearer\s+)?[^\s,;]+",
        r"\1=[REDACTED]",
        texto,
    )
    return texto[:limite]


def _origem_segura(valor: Any) -> dict[str, Any]:
    """Preserva somente campos de proveniência pequenos e conhecidos."""
    if not isinstance(valor, dict):
        return {}
    saida: dict[str, Any] = {}
    for chave in ("estado", "fonte", "registro_id", "indice_avaliacao", "data", "timestamp"):
        item = valor.get(chave)
        if isinstance(item, str):
            saida[chave] = _texto_seguro(item, 120)
        elif isinstance(item, bool) or isinstance(item, int):
            saida[chave] = item
        elif isinstance(item, float) and math.isfinite(item):
            saida[chave] = item
    return saida


class RecuperadorContextoNixal:
    """Consulta memória de investigação e candidatos sem duplicar armazenamento."""

    FONTE = "recuperador_contexto_nixal"

    def __init__(
        self,
        memoria_investigacao: MemoriaInvestigacaoNixal,
        contexto_historico: ContextoHistoricoRelevanteNixal,
        memoria_conhecimento: MemoriaConhecimentoNixal | None = None,
    ) -> None:
        if not isinstance(memoria_investigacao, MemoriaInvestigacaoNixal):
            raise TypeError("memoria_investigacao precisa ser MemoriaInvestigacaoNixal.")
        if not isinstance(contexto_historico, ContextoHistoricoRelevanteNixal):
            raise TypeError("contexto_historico precisa ser ContextoHistoricoRelevanteNixal.")
        if memoria_conhecimento is not None and not isinstance(memoria_conhecimento, MemoriaConhecimentoNixal):
            raise TypeError("memoria_conhecimento precisa ser MemoriaConhecimentoNixal.")
        self.memoria_investigacao = memoria_investigacao
        self.contexto_historico = contexto_historico
        self.memoria_conhecimento = memoria_conhecimento or MemoriaConhecimentoNixal()

    @staticmethod
    def _limite(valor: Any, padrao: int) -> int:
        if not isinstance(valor, int) or isinstance(valor, bool) or not 1 <= valor <= _MAX_RETORNO:
            return padrao
        return valor

    @staticmethod
    def _textos_historicos(contextos: list[dict[str, Any]]) -> list[str]:
        textos: list[str] = []
        for contexto in contextos:
            if not isinstance(contexto, dict):
                continue
            investigacao = contexto.get("investigacao", {})
            if not isinstance(investigacao, dict):
                continue
            for campo in ("necessidade", "pergunta", "hipotese", "estado_atual"):
                valor = investigacao.get(campo)
                if isinstance(valor, str) and valor.strip():
                    textos.append(valor)
        return textos

    def _buscar_candidatos(
        self,
        consulta: str,
        contextos_historicos: list[dict[str, Any]],
        limite: int,
    ) -> tuple[list[dict[str, Any]], str]:
        recarregamento = self.memoria_conhecimento.recarregar()
        if not isinstance(recarregamento, dict) or recarregamento.get("sucesso") is not True:
            return [], "memoria_degradada"

        tokens_consulta = set(_tokens(consulta))
        if not tokens_consulta:
            return [], "consulta_sem_termos"
        consulta_norm = _normalizar(consulta)
        registros = self.memoria_conhecimento.listar()
        documentos: list[dict[str, Any]] = []
        frequencia: Counter[str] = Counter()
        fingerprints_historicos = [
            _normalizar(texto) for texto in self._textos_historicos(contextos_historicos)
        ]
        tokens_historicos = [
            set(_tokens(texto)) for texto in self._textos_historicos(contextos_historicos)
        ]

        for ordem, registro in enumerate(registros):
            if not isinstance(registro, dict) or registro.get("gravado") is not True:
                continue
            if registro.get("conhecimento_permanente") is not False:
                continue
            candidato = registro.get("candidato")
            if not isinstance(candidato, dict):
                continue
            if candidato.get("gravado") is not False or candidato.get("conhecimento_permanente") is not False:
                continue
            origem = candidato.get("origem")
            if not isinstance(origem, dict) or origem.get("estado") != "suportada":
                continue
            texto = candidato.get("texto")
            tipo = candidato.get("tipo")
            if not isinstance(texto, str) or not texto.strip() or not isinstance(tipo, str):
                continue

            texto_norm = _normalizar(texto)
            tokens_doc = set(_tokens(texto + " " + tipo))
            if not tokens_doc:
                continue

            # Deduplica cópias exatas e quase idênticas já representadas por uma investigação.
            duplicado_historico = texto_norm in fingerprints_historicos and bool(texto_norm)
            if not duplicado_historico:
                for tokens_hist in tokens_historicos:
                    if len(tokens_doc & tokens_hist) >= 3:
                        uniao = len(tokens_doc | tokens_hist)
                        if uniao and len(tokens_doc & tokens_hist) / uniao >= 0.90:
                            duplicado_historico = True
                            break
            if duplicado_historico:
                continue

            for token in tokens_doc:
                frequencia[token] += 1
            documentos.append({
                "ordem": ordem,
                "registro": registro,
                "candidato": candidato,
                "texto_norm": texto_norm,
                "tokens": tokens_doc,
            })

        if not documentos:
            return [], "sem_candidatos_relevantes"

        pesos = {
            token: math.log(1.0 + (len(documentos) + 0.5) / (frequencia[token] + 0.5))
            for token in tokens_consulta
        }
        peso_total = sum(pesos.values()) or 1.0
        classificados: list[tuple[float, int, dict[str, Any]]] = []
        for documento in documentos:
            correspondentes = tokens_consulta & documento["tokens"]
            if not correspondentes:
                continue
            score = sum(pesos[token] for token in correspondentes) / peso_total
            texto_norm = documento["texto_norm"]
            if len(consulta_norm) >= 12 and consulta_norm in texto_norm:
                score = min(1.0, score + 0.08)
            if score < _SCORE_MINIMO:
                continue
            registro = documento["registro"]
            candidato = documento["candidato"]
            origem = _origem_segura(candidato.get("origem"))
            item = {
                "registro_id": _texto_seguro(registro.get("registro_id"), 80),
                "texto": _texto_seguro(candidato.get("texto")),
                "tipo": _texto_seguro(candidato.get("tipo"), 80),
                "origem": origem,
                "relevancia_lexical": round(score, 4),
                "estado_epistemico": {
                    "tipo": "candidato_conhecimento",
                    "origem_suportada": True,
                    "nao_equivale_a_verdade": True,
                    "conhecimento_permanente": False,
                },
                "conhecimento_permanente": False,
            }
            classificados.append((score, documento["ordem"], item))

        classificados.sort(key=lambda item: (-item[0], -item[1], item[2]["registro_id"]))
        selecionados: list[dict[str, Any]] = []
        vistos: set[str] = set()
        for _, _, item in classificados:
            fingerprint = _normalizar(item["texto"])
            if not fingerprint or fingerprint in vistos:
                continue
            vistos.add(fingerprint)
            selecionados.append(item)
            if len(selecionados) >= limite:
                break
        return selecionados, (
            "conhecimento_candidato_relevante" if selecionados else "sem_candidatos_relevantes"
        )

    def consultar(
        self,
        consulta: str,
        *,
        limite_investigacoes: int = 3,
        limite_conhecimento: int = 3,
    ) -> dict[str, Any]:
        if not isinstance(consulta, str) or not consulta.strip() or len(consulta) > _MAX_CONSULTA:
            return {
                "sucesso": False,
                "estado": "consulta_invalida",
                "origem": self.FONTE,
                "motivo": "Consulta vazia ou maior que 2.000 caracteres.",
                "contextos_historicos": [],
                "conhecimentos_candidatos": [],
            }
        limite_investigacoes = self._limite(limite_investigacoes, 3)
        limite_conhecimento = self._limite(limite_conhecimento, 3)

        estado_historico = "consulta_indisponivel"
        contextos: list[dict[str, Any]] = []
        try:
            recarregamento = self.memoria_investigacao.recarregar()
            if isinstance(recarregamento, dict) and recarregamento.get("sucesso") is True:
                resultado = self.contexto_historico.analisar_consulta(
                    consulta, limite=limite_investigacoes
                )
                if isinstance(resultado, dict) and resultado.get("sucesso") is True:
                    valor = resultado.get("valor")
                    contextos_raw = valor.get("contextos", []) if isinstance(valor, dict) else []
                    contextos = [item for item in contextos_raw if isinstance(item, dict)][:limite_investigacoes]
                    estado_historico = str(resultado.get("estado", "consulta_concluida"))[:80]
                else:
                    estado_historico = "consulta_indisponivel"
            else:
                estado_historico = "memoria_degradada"
        except Exception:
            estado_historico = "consulta_indisponivel"

        try:
            conhecimentos, estado_conhecimento = self._buscar_candidatos(
                consulta, contextos, limite_conhecimento
            )
        except Exception:
            conhecimentos, estado_conhecimento = [], "consulta_indisponivel"

        return {
            "sucesso": True,
            "estado": estado_historico,
            "origem": self.FONTE,
            "contextos_historicos": contextos,
            "conhecimentos_candidatos": conhecimentos,
            "fontes": {
                "investigacoes": {
                    "estado": estado_historico,
                    "quantidade": len(contextos),
                },
                "conhecimento_candidato": {
                    "estado": estado_conhecimento,
                    "quantidade": len(conhecimentos),
                },
            },
            "armazenamento_adicional": False,
            "conhecimento_permanente": False,
        }
