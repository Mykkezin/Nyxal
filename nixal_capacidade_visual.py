#!/usr/bin/env python3
"""Geração e edição visual com Gemini Image API, sem salvar uploads no servidor."""
from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


MAX_INPUT_BYTES = 8 * 1024 * 1024
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}


class CapacidadeVisualGeminiNixOS:
    FONTE = "gemini_image_api"
    VERSAO = "1.0.0"

    def status(self) -> dict[str, Any]:
        configured = bool(
            os.environ.get("NYXAL_GEMINI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        )
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "configurado" if configured else "configuracao_pendente",
            "modelo": os.environ.get("NYXAL_GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
            "entrada_max_bytes": MAX_INPUT_BYTES,
            "mime_permitidos": sorted(ALLOWED_MIME),
            "salva_upload_no_servidor": False,
        }

    def gerar_ou_editar(
        self,
        prompt: str,
        *,
        imagem_base64: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        prompt = prompt.strip() if isinstance(prompt, str) else ""
        if not prompt:
            raise ValueError("Descreva a imagem que deseja criar ou a edição solicitada.")
        if len(prompt) > 4000:
            raise ValueError("A descrição visual excede 4.000 caracteres.")

        api_key = (
            os.environ.get("NYXAL_GEMINI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        )
        if not api_key:
            raise RuntimeError("Gemini não configurado. Adicione NYXAL_GEMINI_API_KEY à configuração local.")

        parts: list[dict[str, Any]] = [{"text": prompt}]
        if imagem_base64:
            if not isinstance(mime_type, str) or mime_type.lower() not in ALLOWED_MIME:
                raise ValueError("Formato de imagem não permitido. Use PNG, JPEG ou WebP.")
            try:
                binary = base64.b64decode(imagem_base64, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                raise ValueError("A imagem enviada não contém Base64 válido.") from exc
            if not binary:
                raise ValueError("O arquivo de imagem está vazio.")
            if len(binary) > MAX_INPUT_BYTES:
                raise ValueError("A imagem excede o limite de 8 MiB.")
            parts.append({
                "inlineData": {
                    "mimeType": mime_type.lower(),
                    "data": base64.b64encode(binary).decode("ascii"),
                }
            })

        model = os.environ.get("NYXAL_GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image").strip()
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + quote(model, safe="")
            + ":generateContent"
        )
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                raw = response.read(20 * 1024 * 1024 + 1)
            if len(raw) > 20 * 1024 * 1024:
                raise RuntimeError("A resposta visual excedeu 20 MiB.")
            result = json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Gemini Image retornou HTTP {exc.code}. Confira modelo, chave e cota.") from exc
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Falha ao comunicar com Gemini Image ({type(exc).__name__}).") from exc

        candidates = result.get("candidates", []) if isinstance(result, dict) else []
        if not candidates or not isinstance(candidates[0], dict):
            raise RuntimeError("Gemini Image não retornou candidatos. Verifique cota, região e modelo.")
        response_content = candidates[0].get("content", {})
        response_parts = response_content.get("parts", []) if isinstance(response_content, dict) else []
        image = None
        text_parts: list[str] = []
        for item in response_parts if isinstance(response_parts, list) else []:
            if not isinstance(item, dict):
                continue
            text_value = item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                text_parts.append(text_value.strip())
            for key in ("inlineData", "inline_data"):
                image_data = item.get(key)
                if isinstance(image_data, dict) and isinstance(image_data.get("data"), str):
                    mime = image_data.get("mimeType") or image_data.get("mime_type") or "image/png"
                    if mime not in ALLOWED_MIME:
                        continue
                    image = {"mime_type": mime, "base64": image_data["data"]}
                    break
            if image:
                break

        if image is None:
            raise RuntimeError("Gemini respondeu sem imagem. Tente descrever melhor a edição ou consulte a cota do modelo.")
        return {
            "sucesso": True,
            "estado": "imagem_gerada" if not imagem_base64 else "imagem_editada",
            "origem": self.FONTE,
            "modelo": model,
            "mime_type": image["mime_type"],
            "imagem_base64": image["base64"],
            "mensagem": "\n".join(text_parts)[:2000],
            "upload_salvo_no_servidor": False,
        }


__all__ = ["CapacidadeVisualGeminiNixOS", "MAX_INPUT_BYTES", "ALLOWED_MIME"]
