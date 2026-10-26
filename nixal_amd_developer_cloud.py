#!/usr/bin/env python3
"""Conector governado para AMD Developer Cloud via endpoint OpenAI-compatible.

A AMD Developer Cloud fornece a VM/GPU; este adaptador conecta a Nyxal a um
servidor de inferência (por exemplo, vLLM com ROCm) iniciado nessa VM.
Não cria recursos na nuvem nem faz provisionamento/cobrança.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class AmdDeveloperCloud:
    FONTE = "amd_developer_cloud_nyxal"
    VERSAO = "1.0.0"
    ENV_BASE_URL = "NYXAL_AMD_CLOUD_BASE_URL"
    ENV_API_KEY = "NYXAL_AMD_CLOUD_API_KEY"
    ENV_MODEL = "NYXAL_AMD_CLOUD_MODEL"
    ENV_PROVIDER = "NYXAL_LLM_PROVIDER"
    MODELO_PADRAO = "Qwen/Qwen3.5-35B-A3B"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        raw_url = os.environ.get(self.ENV_BASE_URL, "") if base_url is None else base_url
        self.config_error: str | None = None
        try:
            self.base_url = self._normalizar_base_url(raw_url)
        except ValueError as erro:
            # A configuração inválida não deve impedir a API local de iniciar.
            self.base_url = ""
            self.config_error = str(erro)

        self.api_key = os.environ.get(self.ENV_API_KEY, "") if api_key is None else api_key
        self.model = (
            model
            if model is not None
            else os.environ.get(self.ENV_MODEL, self.MODELO_PADRAO)
        )

    @staticmethod
    def _normalizar_base_url(valor: str) -> str:
        if not isinstance(valor, str) or not valor.strip():
            return ""

        valor = valor.strip().rstrip("/")
        parsed = urlparse(valor)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("amd_cloud_url_deve_usar_http_ou_https")
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError(
                "amd_cloud_http_remoto_inseguro_use_https_ou_tunel_ssh"
            )
        if parsed.username or parsed.password:
            raise ValueError("amd_cloud_url_nao_pode_conter_credenciais")
        if parsed.query or parsed.fragment:
            raise ValueError("amd_cloud_url_nao_pode_conter_query_ou_fragmento")

        path = parsed.path.rstrip("/")
        if not path.endswith("/v1"):
            path = f"{path}/v1" if path else "/v1"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def status(self) -> dict[str, Any]:
        selecionado = os.environ.get(self.ENV_PROVIDER, "ollama").strip().lower() in {
            "amd_cloud",
            "amd-developer-cloud",
            "amd",
        }
        if self.config_error:
            estado = "configuracao_invalida"
        elif not self.base_url:
            estado = "nao_configurado"
        else:
            estado = "configurado"

        return {
            "sucesso": not bool(self.config_error),
            "estado": estado,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "provedor": "amd_developer_cloud",
            "selecionado_para_conversa": selecionado,
            "endpoint_configurado": bool(self.base_url),
            "credencial_configurada": bool(self.api_key),
            "modelo": self.model or None,
            "configuracao_secreta_exposta": False,
            "conexao_verificada": False,
            "motivo": self.config_error,
            "modo": "somente_leitura",
        }

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def verificar_conexao(self, timeout: float = 5.0) -> dict[str, Any]:
        """Consulta GET /models sem revelar endpoint nem credencial."""
        if self.config_error:
            return {
                "sucesso": False,
                "estado": "configuracao_invalida",
                "origem": self.FONTE,
                "motivo": self.config_error,
                "conexao_verificada": True,
            }
        if not self.base_url:
            return {
                "sucesso": False,
                "estado": "nao_configurado",
                "origem": self.FONTE,
                "motivo": "NYXAL_AMD_CLOUD_BASE_URL_nao_configurada",
                "conexao_verificada": False,
            }

        request = Request(
            f"{self.base_url}/models",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout) as resposta:
                payload = json.loads(resposta.read(2 * 1024 * 1024).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("resposta_models_invalida")
            dados_modelos = payload.get("data", [])
            modelos = [
                item.get("id")
                for item in dados_modelos
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            ] if isinstance(dados_modelos, list) else []
            return {
                "sucesso": True,
                "estado": "conectado",
                "origem": self.FONTE,
                "conexao_verificada": True,
                "quantidade_modelos": len(modelos),
                "modelos": modelos[:20],
                "modelo_configurado": self.model or None,
                "segredo_exposto": False,
            }
        except HTTPError as erro:
            return {
                "sucesso": False,
                "estado": "erro_http",
                "origem": self.FONTE,
                "conexao_verificada": True,
                "http_status": erro.code,
                "motivo": "credencial_rejeitada" if erro.code in {401, 403} else "endpoint_rejeitou_requisicao",
                "segredo_exposto": False,
            }
        except (URLError, TimeoutError, OSError) as erro:
            motivo = "timeout" if isinstance(erro, TimeoutError) else type(erro).__name__
            if isinstance(erro, URLError):
                motivo = "timeout" if isinstance(erro.reason, TimeoutError) else type(erro.reason).__name__
            return {
                "sucesso": False,
                "estado": "endpoint_inacessivel",
                "origem": self.FONTE,
                "conexao_verificada": True,
                "motivo": motivo,
                "segredo_exposto": False,
            }
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return {
                "sucesso": False,
                "estado": "resposta_invalida",
                "origem": self.FONTE,
                "conexao_verificada": True,
                "motivo": "resposta_models_nao_compativel",
                "segredo_exposto": False,
            }

    def chat(
        self,
        *,
        model: str | None,
        messages: list[dict[str, str]],
        options: dict[str, Any] | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Emula o contrato mínimo do cliente Ollama para não alterar o núcleo."""
        if self.config_error:
            raise RuntimeError(self.config_error)
        if not self.base_url:
            raise RuntimeError("NYXAL_AMD_CLOUD_BASE_URL_nao_configurada")

        nome_modelo = model or self.model
        if not nome_modelo:
            raise RuntimeError("NYXAL_AMD_CLOUD_MODEL_nao_configurado")

        opcoes = options or {}
        body: dict[str, Any] = {
            "model": nome_modelo,
            "messages": messages,
            "stream": False,
        }
        if isinstance(opcoes.get("temperature"), (float, int)):
            body["temperature"] = float(opcoes["temperature"])

        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as resposta:
                payload = json.loads(resposta.read(8 * 1024 * 1024).decode("utf-8"))
        except HTTPError as erro:
            raise RuntimeError(f"amd_cloud_http_{erro.code}") from None
        except URLError as erro:
            detalhe = "timeout" if isinstance(erro.reason, TimeoutError) else type(erro.reason).__name__
            raise RuntimeError(f"amd_cloud_network_{detalhe}") from None
        except (TimeoutError, OSError) as erro:
            raise RuntimeError(f"amd_cloud_network_{type(erro).__name__}") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError("amd_cloud_resposta_json_invalida") from None

        try:
            conteudo = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("amd_cloud_resposta_sem_conteudo") from None

        if isinstance(conteudo, list):
            conteudo = "".join(
                parte.get("text", "")
                for parte in conteudo
                if isinstance(parte, dict) and isinstance(parte.get("text"), str)
            )
        if not isinstance(conteudo, str) or not conteudo.strip():
            raise RuntimeError("amd_cloud_resposta_vazia")

        return {"message": {"content": conteudo.strip()}}


class AmdCloudChatClient:
    """Cliente compatível com a chamada chat() usada por DialogoQwenNixal."""

    def __init__(self, cloud: AmdDeveloperCloud | None = None) -> None:
        self.cloud = cloud if cloud is not None else AmdDeveloperCloud()

    def chat(self, **kwargs: Any) -> dict[str, Any]:
        return self.cloud.chat(
            model=kwargs.get("model"),
            messages=kwargs.get("messages", []),
            options=kwargs.get("options"),
        )


__all__ = ["AmdDeveloperCloud", "AmdCloudChatClient"]
