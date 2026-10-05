#!/usr/bin/env python3
"""NYXAL — coletor dual governado de datasets AE5.

Mantém dois destinos de treinamento futuros, sem executar treinamento:
- linguagem operacional / Qwen-Nyxal;
- transições de sistema / futuro modelo do Nyx Kernel.

O módulo coleta apenas observações já produzidas pelo Runtime/AE4 e pela
camada de habitat. Os datasets ficam fora da árvore Git do Nyxal.

Governança:
- uma transição por tipo de dataset por ciclo;
- deduplicação exata por fingerprint dentro de 24h;
- persistência do cursor de emparelhamento em JSON atômico;
- escrita de cada registro JSONL em uma única operação O_APPEND;
- nenhum shell, subprocesso, treino, merge, autorização ou implantação;
- nenhum valor econômico é inventado;
- causalidade nunca é promovida de forma automática.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


class ColetorDatasetDualAE5:
    """Coleta transições observadas para os dois futuros sem ampliar autoridade."""

    FONTE = "coletor_dataset_dual_ae5"
    VERSAO = "AE5-DUAL.1.0"
    JANELA_DUPLICATA = timedelta(hours=24)
    MAX_REGISTROS_DATASET = 50_000
    MAX_INDICE_RECENTE = 5_000

    DATASETS = {
        "qwen": "qwen-dataset.jsonl",
        "kernel": "kernel-dataset.jsonl",
    }

    def __init__(
        self,
        *,
        repositorio: str | Path,
        habilitada: bool = True,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self.repositorio = Path(repositorio).resolve()
        self.diretorio = (self.repositorio.parent / "Nyxal-datasets").resolve()
        self.diretorio_auditoria = (self.diretorio / "auditoria").resolve()
        self.diretorio.mkdir(parents=True, exist_ok=True)
        self.diretorio_auditoria.mkdir(parents=True, exist_ok=True)

        self.arquivo_estado = self.diretorio / "dual-cursor.json"
        self.arquivo_indice = self.diretorio / "dual-index.json"
        self.habilitada = bool(habilitada)
        self._agora_fn = agora or (lambda: datetime.now(timezone.utc))
        self._ultimo_resultado: dict[str, Any] | None = None

    @classmethod
    def _agora(cls, fn: Callable[[], datetime]) -> datetime:
        valor = fn()
        if not isinstance(valor, datetime):
            raise TypeError("agora_precisa_retornar_datetime")
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(timezone.utc)

    @classmethod
    def _timestamp(cls, fn: Callable[[], datetime]) -> str:
        return cls._agora(fn).isoformat()

    @staticmethod
    def _texto(valor: Any) -> str | None:
        if not isinstance(valor, str):
            return None
        valor = re.sub(r"\s+", " ", valor.strip())
        return valor or None

    @classmethod
    def _sem_volatilidade(cls, valor: Any) -> Any:
        if isinstance(valor, dict):
            return {
                chave: cls._sem_volatilidade(item)
                for chave, item in valor.items()
                if chave not in {"ciclo_id", "delta_id", "timestamp", "observado_em", "coletado_em"}
            }
        if isinstance(valor, list):
            return [cls._sem_volatilidade(item) for item in valor]
        return copy.deepcopy(valor)

    @staticmethod
    def _json(valor: Any) -> str:
        return json.dumps(
            valor,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _sha(cls, valor: Any) -> str:
        return hashlib.sha256(
            cls._json(valor).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _carregar(caminho: Path, padrao: Any) -> Any:
        try:
            valor = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return copy.deepcopy(padrao)
        return valor

    @staticmethod
    def _atomic_write(caminho: Path, dados: Any) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_name(
            f"{caminho.name}.{os.getpid()}.tmp"
        )
        temporario.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporario, caminho)

    @staticmethod
    def _append_jsonl(caminho: Path, registro: dict[str, Any]) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            json.dumps(
                registro,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        descritor = os.open(
            str(caminho),
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            total = 0
            while total < len(payload):
                total += os.write(descritor, payload[total:])
            os.fsync(descritor)
        finally:
            os.close(descritor)

    @classmethod
    def _invariantes(cls) -> dict[str, bool]:
        return {
            "autorizacao_explicita": False,
            "integracao_executada": False,
            "stable_modificada": False,
            "arquitetura_modificada": False,
            "conhecimento_permanente": False,
        }

    def _estado(self) -> dict[str, Any]:
        estado = self._carregar(
            self.arquivo_estado,
            {
                "versao": self.VERSAO,
                "qwen_anterior": None,
                "kernel_anterior": None,
            },
        )
        if not isinstance(estado, dict):
            estado = {}
        estado.setdefault("versao", self.VERSAO)
        estado.setdefault("qwen_anterior", None)
        estado.setdefault("kernel_anterior", None)
        return estado

    def _indice(self) -> dict[str, Any]:
        indice = self._carregar(
            self.arquivo_indice,
            {"versao": self.VERSAO, "entradas": [], "contagens": {}},
        )
        if not isinstance(indice, dict):
            indice = {"versao": self.VERSAO, "entradas": []}
        if not isinstance(indice.get("entradas"), list):
            indice["entradas"] = []
        if not isinstance(indice.get("contagens"), dict):
            indice["contagens"] = {}
        return indice

    def _limpar_indice(self, indice: dict[str, Any], agora: datetime) -> None:
        limite = agora - self.JANELA_DUPLICATA
        mantidas = []
        for item in indice.get("entradas", []):
            if not isinstance(item, dict):
                continue
            try:
                instante = datetime.fromisoformat(str(item.get("observado_em")))
            except ValueError:
                continue
            if instante.tzinfo is None:
                instante = instante.replace(tzinfo=timezone.utc)
            if instante.astimezone(timezone.utc) >= limite:
                mantidas.append(item)
        mantidas.sort(key=lambda item: str(item.get("observado_em")), reverse=True)
        indice["entradas"] = mantidas[: self.MAX_INDICE_RECENTE]

    def _duplicata_recente(
        self,
        indice: dict[str, Any],
        *,
        dataset: str,
        fingerprint: str,
        agora: datetime,
    ) -> bool:
        limite = agora - self.JANELA_DUPLICATA
        for item in indice.get("entradas", []):
            if not isinstance(item, dict):
                continue
            if item.get("dataset") != dataset:
                continue
            if item.get("fingerprint") != fingerprint:
                continue
            try:
                instante = datetime.fromisoformat(str(item.get("observado_em")))
            except ValueError:
                continue
            if instante.tzinfo is None:
                instante = instante.replace(tzinfo=timezone.utc)
            if instante.astimezone(timezone.utc) >= limite:
                return True
        return False

    def _auditar(
        self,
        *,
        dataset: str,
        ciclo_id: str,
        fingerprint: str | None,
        estado: str,
        motivo: str,
        gravado: bool,
    ) -> None:
        agora = self._timestamp(self._agora_fn)
        auditoria = {
            "auditoria_id": "dual-"
            + self._sha({
                "dataset": dataset,
                "ciclo_id": ciclo_id,
                "fingerprint": fingerprint,
                "observado_em": agora,
            })[:24],
            "versao": self.VERSAO,
            "origem": self.FONTE,
            "dataset": dataset,
            "ciclo_id": ciclo_id,
            "fingerprint": fingerprint,
            "estado": estado,
            "motivo": motivo,
            "gravado": gravado,
            "observado_em": agora,
            **self._invariantes(),
        }
        self._atomic_write(
            self.diretorio_auditoria / f"{auditoria['auditoria_id']}.json",
            auditoria,
        )

    @staticmethod
    def _valor_etapa(ciclo: dict[str, Any], nome: str) -> dict[str, Any] | None:
        valor = ciclo.get("valor")
        if not isinstance(valor, dict):
            return None
        etapas = valor.get("etapas")
        if not isinstance(etapas, list):
            return None
        for etapa in etapas:
            if not isinstance(etapa, dict):
                continue
            if etapa.get("etapa") != nome:
                continue
            return etapa
        return None

    @classmethod
    def _corpo_observado(cls, ciclo: dict[str, Any]) -> dict[str, Any]:
        etapa = cls._valor_etapa(ciclo, "percepcao") or {}
        estado = etapa.get("estado")
        return copy.deepcopy(estado) if isinstance(estado, dict) else {}

    @classmethod
    def _necessidade(cls, ciclo: dict[str, Any]) -> dict[str, Any]:
        valor = ciclo.get("valor")
        prioridade = valor.get("necessidade_prioritaria") if isinstance(valor, dict) else None
        if isinstance(prioridade, dict):
            selecionada = prioridade.get("selecionada")
            if isinstance(selecionada, dict):
                return copy.deepcopy(selecionada)
        return {}

    @classmethod
    def _aprendizado(cls, ciclo: dict[str, Any]) -> dict[str, Any]:
        valor = ciclo.get("valor")
        aprendizado = valor.get("aprendizado") if isinstance(valor, dict) else None
        return copy.deepcopy(aprendizado) if isinstance(aprendizado, dict) else {}

    @classmethod
    def _decisao(cls, ciclo: dict[str, Any]) -> dict[str, Any]:
        valor = ciclo.get("valor")
        decisao = valor.get("decisao") if isinstance(valor, dict) else None
        return copy.deepcopy(decisao) if isinstance(decisao, dict) else {}

    @classmethod
    def _resultado(cls, ciclo: dict[str, Any]) -> dict[str, Any]:
        valor = ciclo.get("valor")
        resultado = valor.get("resultado") if isinstance(valor, dict) else None
        return copy.deepcopy(resultado) if isinstance(resultado, dict) else {}

    @classmethod
    def _delta(cls, ciclo: dict[str, Any]) -> dict[str, Any]:
        valor = ciclo.get("valor")
        delta = valor.get("delta") if isinstance(valor, dict) else None
        return copy.deepcopy(delta) if isinstance(delta, dict) else {}

    @classmethod
    def _descricao_qwen(cls, ciclo: dict[str, Any]) -> dict[str, Any]:
        return {
            "necessidade": cls._necessidade(ciclo),
            "decisao": cls._decisao(ciclo),
            "resultado": cls._resultado(ciclo),
            "aprendizado_anterior": copy.deepcopy(
                (ciclo.get("valor") or {}).get("aprendizado_anterior")
            )
            if isinstance(ciclo.get("valor"), dict)
            else None,
        }

    @classmethod
    def _qwen_transicao(
        cls,
        anterior: dict[str, Any],
        atual: dict[str, Any],
    ) -> dict[str, Any]:
        anterior_corpo = cls._corpo_observado(anterior["ciclo"]) if isinstance(anterior.get("ciclo"), dict) else {}
        atual_corpo = cls._corpo_observado(atual)
        anterior_delta = anterior.get("delta", {})
        aprendizado = cls._aprendizado(atual)
        prompt = {
            "estado_anterior": anterior_corpo,
            "causa": {
                "delta_anterior": anterior_delta,
                "decisao_anterior": anterior.get("decisao", {}),
                "resultado_anterior": anterior.get("resultado", {}),
            },
        }
        completion = {
            "estado_novo": atual_corpo,
            "aprendizado": aprendizado,
        }
        return {
            "prompt": cls._json(prompt),
            "completion": cls._json(completion),
            "causalidade_comprovada": False,
        }

    @classmethod
    def _top5_processos(cls, habitat: dict[str, Any]) -> list[dict[str, Any]]:
        recursos = habitat.get("recursos")
        if not isinstance(recursos, dict):
            return []
        processos = recursos.get("processos_habitat")
        if not isinstance(processos, dict):
            return []
        entidades = processos.get("entidades")
        if not isinstance(entidades, list):
            return []
        resultado = []
        for item in entidades[:5]:
            if not isinstance(item, dict):
                continue
            resultado.append({
                "pid": item.get("pid"),
                "nome": cls._texto(item.get("nome")),
                "estado": item.get("estado"),
                "uso_cpu_percentual": item.get("uso_cpu_percentual"),
                "memoria_rss_mb": item.get("memoria_rss_mb"),
            })
        return resultado

    @classmethod
    def _kernel_features(
        cls,
        *,
        ciclo: dict[str, Any],
        habitat: dict[str, Any],
    ) -> dict[str, Any]:
        corpo = cls._corpo_observado(ciclo).get("corpo", {})
        corpo = corpo if isinstance(corpo, dict) else {}
        cpu = corpo.get("cpu", {})
        memoria = corpo.get("memoria", {})
        return {
            "cpu": {
                "uso_percentual": cpu.get("uso_percentual"),
                "estado": cpu.get("estado"),
            },
            "ram": {
                "uso_percentual": memoria.get("uso_percentual"),
                "estado": memoria.get("estado"),
                "usado_gb": memoria.get("usado_gb"),
                "total_gb": memoria.get("total_gb"),
            },
            "top5_processos": cls._top5_processos(habitat),
            "ultimo_delta": cls._delta(ciclo),
        }

    @classmethod
    def _kernel_transicao(
        cls,
        *,
        anterior: dict[str, Any],
        atual: dict[str, Any],
        habitat_atual: dict[str, Any],
    ) -> dict[str, Any]:
        entrada = cls._kernel_features(
            ciclo=anterior["ciclo"],
            habitat=anterior.get("habitat", {}),
        )
        delta_atual = cls._delta(atual)
        decisao_atual = cls._decisao(atual)
        acao = cls._texto(decisao_atual.get("acao"))
        return {
            "input": {
                "cpu": entrada["cpu"],
                "ram": entrada["ram"],
                "top5_processos": entrada["top5_processos"],
                "ultimo_delta": entrada["ultimo_delta"],
            },
            "output_observado": {
                "delta_id": cls._texto(delta_atual.get("delta_id")),
                "acao_ciclo": acao,
            },
            "acao_executada_observada": bool(
                ((atual.get("valor") or {}).get("acao") or {}).get("sucesso")
            )
            if isinstance(atual.get("valor"), dict)
            else False,
            "acao_autorizada": acao == "registrar_estado_corpo",
            "treinamento_autorizado": False,
        }

    def _registrar_dataset(
        self,
        *,
        dataset: str,
        ciclo_id: str,
        registro: dict[str, Any],
        fingerprint_payload: Any,
        agora: datetime,
        indice: dict[str, Any],
    ) -> dict[str, Any]:
        fingerprint = self._sha(fingerprint_payload)
        contagens = indice.setdefault("contagens", {})
        atual = contagens.get(dataset)
        if not isinstance(atual, int) or atual < 0:
            atual = 0
        if atual >= self.MAX_REGISTROS_DATASET:
            self._auditar(
                dataset=dataset,
                ciclo_id=ciclo_id,
                fingerprint=fingerprint,
                estado="limite_dataset",
                motivo="max_registros_dataset",
                gravado=False,
            )
            return {
                "gravado": False,
                "deduplicado": False,
                "fingerprint": fingerprint,
                "estado": "limite_dataset",
            }
        if self._duplicata_recente(
            indice,
            dataset=dataset,
            fingerprint=fingerprint,
            agora=agora,
        ):
            self._auditar(
                dataset=dataset,
                ciclo_id=ciclo_id,
                fingerprint=fingerprint,
                estado="duplicata_24h",
                motivo="registro_identico_janela_24h",
                gravado=False,
            )
            return {
                "gravado": False,
                "deduplicado": True,
                "fingerprint": fingerprint,
                "estado": "duplicata_24h",
            }

        registro = copy.deepcopy(registro)
        registro["dataset"] = dataset
        registro["versao_coleta"] = self.VERSAO
        registro["fingerprint"] = fingerprint
        registro["coletado_em"] = self._timestamp(self._agora_fn)
        self._append_jsonl(self.diretorio / self.DATASETS[dataset], registro)

        indice.setdefault("entradas", []).append({
            "dataset": dataset,
            "fingerprint": fingerprint,
            "observado_em": registro["coletado_em"],
        })
        contagens[dataset] = atual + 1
        self._limpar_indice(indice, agora)
        self._atomic_write(self.arquivo_indice, indice)

        self._auditar(
            dataset=dataset,
            ciclo_id=ciclo_id,
            fingerprint=fingerprint,
            estado="gravado",
            motivo="transicao_observada_registrada",
            gravado=True,
        )
        return {
            "gravado": True,
            "deduplicado": False,
            "fingerprint": fingerprint,
            "estado": "gravado",
        }

    def _contagem_dataset(self, dataset: str) -> int:
        indice = self._indice()
        contagem = indice.get("contagens", {}).get(dataset)
        if isinstance(contagem, int) and contagem >= 0:
            return contagem
        caminho = self.diretorio / self.DATASETS[dataset]
        if not caminho.is_file():
            return 0
        try:
            with caminho.open("rb") as arquivo:
                return sum(1 for _ in arquivo)
        except OSError:
            return 0

    def processar_ciclo(
        self,
        *,
        ciclo: dict[str, Any],
        habitat: dict[str, Any] | None = None,
        ae4_resultado: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ciclo_id = self._texto(ciclo.get("ciclo_id")) if isinstance(ciclo, dict) else None
        ciclo_id = ciclo_id or "sem-ciclo"

        if not self.habilitada:
            resultado = {
                "sucesso": True,
                "estado": "coletor_dual_ae5_desabilitado",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "coletado": False,
                **self._invariantes(),
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        if not isinstance(ciclo, dict):
            resultado = {
                "sucesso": False,
                "estado": "ciclo_invalido",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "coletado": False,
                **self._invariantes(),
            }
            self._ultimo_resultado = copy.deepcopy(resultado)
            return resultado

        habitat = habitat if isinstance(habitat, dict) else {}
        ae4_resultado = ae4_resultado if isinstance(ae4_resultado, dict) else {}

        agora = self._agora(self._agora_fn)
        indice = self._indice()
        self._limpar_indice(indice, agora)

        estado = self._estado()
        qwen_anterior = estado.get("qwen_anterior")
        kernel_anterior = estado.get("kernel_anterior")

        qwen_resultado: dict[str, Any]
        kernel_resultado: dict[str, Any]

        if not isinstance(qwen_anterior, dict):
            qwen_resultado = {
                "gravado": False,
                "estado": "aguardando_primeira_transicao",
                "deduplicado": False,
            }
        else:
            transicao_qwen = self._qwen_transicao(
                qwen_anterior["ciclo"],
                ciclo,
            )
            qwen_resultado = self._registrar_dataset(
                dataset="qwen",
                ciclo_id=ciclo_id,
                registro={
                    "schema": "nyxal-qwen-transition-1",
                    "fonte": self.FONTE,
                    "source_cycle": ciclo_id,
                    "prompt": transicao_qwen["prompt"],
                    "completion": transicao_qwen["completion"],
                    "causalidade_comprovada": False,
                    "evidence": {
                        "ae4": copy.deepcopy(ae4_resultado),
                        "runtime_ciclo_anterior": qwen_anterior["ciclo_id"],
                    },
                    **self._invariantes(),
                },
                fingerprint_payload=cls._sem_volatilidade({
                    "schema": "nyxal-qwen-transition-1",
                    "prompt": transicao_qwen["prompt"],
                    "completion": transicao_qwen["completion"],
                    "causalidade_comprovada": False,
                }),
                agora=agora,
                indice=indice,
            )

        if not isinstance(kernel_anterior, dict):
            kernel_resultado = {
                "gravado": False,
                "estado": "aguardando_primeira_transicao",
                "deduplicado": False,
            }
        else:
            transicao_kernel = self._kernel_transicao(
                anterior=kernel_anterior,
                atual=ciclo,
                habitat_atual=habitat,
            )
            kernel_resultado = self._registrar_dataset(
                dataset="kernel",
                ciclo_id=ciclo_id,
                registro={
                    "schema": "nyxal-kernel-transition-1",
                    "fonte": self.FONTE,
                    "source_cycle": ciclo_id,
                    **transicao_kernel,
                    "evidence": {
                        "ae4": copy.deepcopy(ae4_resultado),
                        "runtime_ciclo_anterior": kernel_anterior["ciclo_id"],
                        "treinamento_autorizado": False,
                    },
                    **self._invariantes(),
                },
                fingerprint_payload=cls._sem_volatilidade({
                    "schema": "nyxal-kernel-transition-1",
                    "input": transicao_kernel["input"],
                    "output_observado": transicao_kernel["output_observado"],
                    "acao_executada_observada": transicao_kernel[
                        "acao_executada_observada"
                    ],
                }),
                agora=agora,
                indice=indice,
            )

        estado["versao"] = self.VERSAO
        estado["qwen_anterior"] = {
            "ciclo_id": ciclo_id,
            "ciclo": copy.deepcopy(ciclo),
            "delta": self._delta(ciclo),
            "decisao": self._decisao(ciclo),
            "resultado": self._resultado(ciclo),
            "habitat": {},
        }
        estado["kernel_anterior"] = {
            "ciclo_id": ciclo_id,
            "ciclo": copy.deepcopy(ciclo),
            "habitat": copy.deepcopy(habitat),
        }
        self._atomic_write(self.arquivo_estado, estado)

        resultado = {
            "sucesso": True,
            "estado": "coleta_dual_processada",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "coletado": bool(
                qwen_resultado.get("gravado")
                or kernel_resultado.get("gravado")
            ),
            "qwen": copy.deepcopy(qwen_resultado),
            "kernel": copy.deepcopy(kernel_resultado),
            "quantidade_qwen": self._contagem_dataset("qwen"),
            "quantidade_kernel": self._contagem_dataset("kernel"),
            "limites": {
                "janela_duplicata_horas": 24,
                "max_registros_dataset": self.MAX_REGISTROS_DATASET,
            },
            **self._invariantes(),
        }
        self._ultimo_resultado = copy.deepcopy(resultado)
        return resultado

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "estado": "coletor_dual_ae5_disponivel",
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "habilitada": self.habilitada,
            "datasets": {
                "qwen": {
                    "arquivo": str(self.diretorio / self.DATASETS["qwen"]),
                    "registros": self._contagem_dataset("qwen"),
                },
                "kernel": {
                    "arquivo": str(self.diretorio / self.DATASETS["kernel"]),
                    "registros": self._contagem_dataset("kernel"),
                },
            },
            "treinamento_automatico": False,
            "implantacao_automatica": False,
            "invariantes": self._invariantes(),
            "ultimo_resultado": copy.deepcopy(self._ultimo_resultado),
        }


__all__ = ["ColetorDatasetDualAE5"]
