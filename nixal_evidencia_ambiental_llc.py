#!/usr/bin/env python3
"""NYXAL — LLC.4: evidencia ambiental real.

Responsabilidade:
    capturar observacoes somente-leitura do habitat NyxOS e transformar
    uma metrica declarada em evidencia ambiental observacional auditavel.

Esta camada aproxima o LLC do ambiente real, mas nao cria causalidade:
- usa o HabitatNixOS existente;
- nao executa comandos nem altera o host;
- nao escolhe metrica por conta propria;
- nao trata pre/post isolado como causa;
- nao marca causalidade_ambiental_comprovada.

A prova causal continua pertencendo ao protocolo controlado do LLC.3,
quando houver grupo de controle, contrafactual e repeticoes validas.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable

from nixal_habitat import HabitatNixOS


class EvidenciaAmbientalLLC:
    """Coletor e normalizador de evidencia ambiental observacional."""

    FONTE = "llc_evidencia_ambiental"
    VERSAO = "LLC.4.0.0"
    MODO = "somente_leitura"

    INVARIANTES = {
        "autorizacao_explicita": False,
        "integracao_executada": False,
        "stable_modificada": False,
        "arquitetura_modificada": False,
        "conhecimento_permanente": False,
        "execucao_local": False,
        "treinamento_automatico": False,
        "implantacao_automatica": False,
        "causalidade_ambiental_comprovada": False,
    }

    METRICAS_NUMERICAS = {
        "recursos.cpu.uso_percentual": ("%", "maior"),
        "recursos.memoria.uso_percentual": ("%", "menor"),
        "recursos.armazenamento.uso_percentual": ("%", "menor"),
        "recursos.processos": ("contagem", "menor"),
        "recursos.uptime_segundos": ("s", "maior"),
        "recursos.gpu.0.uso_percentual": ("%", "menor"),
        "recursos.gpu.0.temperaturas.0.temperatura_c": ("celsius", "menor"),
    }

    def __init__(
        self,
        habitat: HabitatNixOS | None = None,
        observador: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        if habitat is not None and not isinstance(habitat, HabitatNixOS):
            raise TypeError("habitat deve ser uma instancia de HabitatNixOS")
        if observador is not None and not callable(observador):
            raise TypeError("observador deve ser chamavel")
        if habitat is not None and observador is not None:
            raise ValueError("informe habitat ou observador, nao ambos")

        self._habitat = habitat or HabitatNixOS()
        self._observador = observador

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _numero(valor: Any) -> float | None:
        if isinstance(valor, bool):
            return None
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return None
        return (
            numero
            if numero == numero and abs(numero) != float("inf")
            else None
        )

    @staticmethod
    def _hash(dados: Any) -> str:
        canonico = json.dumps(
            dados,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            canonico.encode("utf-8")
        ).hexdigest()[:24]

    def capturar_snapshot(self) -> dict[str, Any]:
        try:
            if self._observador is not None:
                snapshot = self._observador()
            else:
                snapshot = self._habitat.snapshot()
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "snapshot_ambiental_falhou",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "motivo": f"{type(erro).__name__}: {erro}",
                **copy.deepcopy(self.INVARIANTES),
            }

        if not isinstance(snapshot, dict):
            return {
                "sucesso": False,
                "estado": "snapshot_ambiental_invalido",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "motivo": "O observador nao retornou um objeto.",
                **copy.deepcopy(self.INVARIANTES),
            }

        host = snapshot.get("host")
        recursos = snapshot.get("recursos")
        timestamp = snapshot.get("timestamp")

        if not isinstance(host, dict) or not isinstance(recursos, dict):
            return {
                "sucesso": False,
                "estado": "snapshot_ambiental_incompleto",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "motivo": "Snapshot sem host ou recursos estruturados.",
                **copy.deepcopy(self.INVARIANTES),
            }

        corpo_minimo = {
            "host": {
                "sistema": host.get("sistema"),
                "release": host.get("release"),
                "arquitetura": host.get("arquitetura"),
                "modo": self.MODO,
            },
            "recursos": copy.deepcopy(recursos),
            "timestamp": timestamp,
        }

        snapshot_id = self._hash(corpo_minimo)

        return {
            "sucesso": True,
            "estado": "snapshot_ambiental_observado",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "snapshot_id": snapshot_id,
            "modo": self.MODO,
            "host": copy.deepcopy(corpo_minimo["host"]),
            "recursos": copy.deepcopy(recursos),
            "timestamp": timestamp,
            "evidencia_ambiental_observacional": True,
            **copy.deepcopy(self.INVARIANTES),
        }

    @classmethod
    def _caminho_metric(cls, snapshot: dict[str, Any], caminho: str) -> Any:
        atual: Any = snapshot
        for parte in caminho.split("."):
            if isinstance(atual, dict):
                if parte not in atual:
                    return None
                atual = atual[parte]
            elif isinstance(atual, list) and parte.isdigit():
                indice = int(parte)
                if indice >= len(atual):
                    return None
                atual = atual[indice]
            else:
                return None
        return atual

    @classmethod
    def observar_metrica(
        cls,
        *,
        snapshot: dict[str, Any],
        caminho: str,
        nome: str,
        unidade: str,
        direcao_melhor: str,
        fonte: str = "habitat_nyxos",
    ) -> dict[str, Any]:
        if not isinstance(snapshot, dict):
            return {
                "sucesso": False,
                "estado": "metrica_snapshot_invalido",
                "motivo": "Snapshot precisa ser um objeto.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        if not isinstance(caminho, str) or not caminho.strip():
            return {
                "sucesso": False,
                "estado": "metrica_caminho_invalido",
                "motivo": "Caminho da metrica invalido.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        if caminho not in cls.METRICAS_NUMERICAS:
            return {
                "sucesso": False,
                "estado": "metrica_nao_declarada",
                "motivo": "A metrica precisa estar na lista declarada do LLC.4.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        if not isinstance(nome, str) or not nome.strip():
            return {
                "sucesso": False,
                "estado": "metrica_nome_invalido",
                "motivo": "Nome da metrica invalido.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        if not isinstance(unidade, str) or not unidade.strip():
            return {
                "sucesso": False,
                "estado": "metrica_unidade_invalida",
                "motivo": "Unidade da metrica invalida.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        if direcao_melhor not in {"maior", "menor"}:
            return {
                "sucesso": False,
                "estado": "metrica_direcao_invalida",
                "motivo": "Direcao de melhoria invalida.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        valor = cls._numero(cls._caminho_metric(snapshot, caminho))
        if valor is None:
            return {
                "sucesso": False,
                "estado": "metrica_valor_indisponivel",
                "motivo": "O valor numerico da metrica nao esta disponivel.",
                "caminho": caminho,
                **copy.deepcopy(cls.INVARIANTES),
            }

        observacao = {
            "id": cls._hash({
                "snapshot_id": snapshot.get("snapshot_id"),
                "caminho": caminho,
                "valor": valor,
                "timestamp": snapshot.get("timestamp"),
            }),
            "snapshot_id": snapshot.get("snapshot_id"),
            "timestamp": snapshot.get("timestamp"),
            "nome": nome.strip(),
            "caminho": caminho,
            "unidade": unidade.strip(),
            "valor": valor,
            "direcao_melhor": direcao_melhor,
            "fonte": fonte.strip() if isinstance(fonte, str) else "habitat_nyxos",
            "modo": cls.MODO,
            "evidencia_ambiental_observacional": True,
            "causalidade_ambiental_comprovada": False,
        }
        return {
            "sucesso": True,
            "estado": "metrica_ambiental_observada",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "observacao": observacao,
            **copy.deepcopy(cls.INVARIANTES),
        }

    @classmethod
    def comparar_observacoes(
        cls,
        *,
        antes: dict[str, Any],
        depois: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(antes, dict) or not isinstance(depois, dict):
            return {
                "sucesso": False,
                "estado": "comparacao_ambiental_invalida",
                "motivo": "As duas observacoes precisam ser objetos.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        obrigatorios = (
            "nome",
            "unidade",
            "caminho",
            "valor",
            "direcao_melhor",
        )
        for item in obrigatorios:
            if item not in antes or item not in depois:
                return {
                    "sucesso": False,
                    "estado": "comparacao_ambiental_incompleta",
                    "motivo": f"Observacoes sem campo obrigatorio: {item}.",
                    **copy.deepcopy(cls.INVARIANTES),
                }

        if antes.get("nome") != depois.get("nome"):
            return {
                "sucesso": False,
                "estado": "comparacao_metrica_diferente",
                "motivo": "Nome da metrica diverge.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        if antes.get("unidade") != depois.get("unidade"):
            return {
                "sucesso": False,
                "estado": "comparacao_unidade_diferente",
                "motivo": "Unidade diverge.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        if antes.get("caminho") != depois.get("caminho"):
            return {
                "sucesso": False,
                "estado": "comparacao_caminho_diferente",
                "motivo": "Caminho da metrica diverge.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        valor_antes = cls._numero(antes.get("valor"))
        valor_depois = cls._numero(depois.get("valor"))
        if valor_antes is None or valor_depois is None:
            return {
                "sucesso": False,
                "estado": "comparacao_valor_invalido",
                "motivo": "Valores da metrica precisam ser numericos.",
                **copy.deepcopy(cls.INVARIANTES),
            }

        delta = valor_depois - valor_antes
        return {
            "sucesso": True,
            "estado": "mudanca_ambiental_observada",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "metrica": {
                "nome": depois.get("nome"),
                "caminho": depois.get("caminho"),
                "unidade": depois.get("unidade"),
                "direcao_melhor": depois.get("direcao_melhor"),
            },
            "antes": valor_antes,
            "depois": valor_depois,
            "delta_observado": delta,
            "snapshot_antes_id": antes.get("snapshot_id"),
            "snapshot_depois_id": depois.get("snapshot_id"),
            "evidencia_ambiental_observacional": True,
            "causalidade_ambiental_comprovada": False,
            **copy.deepcopy(cls.INVARIANTES),
        }

    @classmethod
    def contexto(cls) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "llc4_disponivel",
            "origem": cls.FONTE,
            "versao": cls.VERSAO,
            "modo": cls.MODO,
            "metricas_declaradas": copy.deepcopy(cls.METRICAS_NUMERICAS),
            "evidencia_ambiental_observacional": True,
            "causalidade_ambiental": False,
            "coleta_automatica": False,
            "execucao_de_acao": False,
            "invariantes": copy.deepcopy(cls.INVARIANTES),
        }


__all__ = ["EvidenciaAmbientalLLC"]
