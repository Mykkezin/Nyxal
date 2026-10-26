#!/usr/bin/env python3
"""Geração e edição visual com Gemini Image API, sem salvar uploads no servidor."""
from __future__ import annotations

import base64
import binascii
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 12 * 1024 * 1024
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}


def _assinatura_compativel(binary: bytes, mime_type: str) -> bool:
    """Verifica a assinatura do conteúdo para impedir MIME/Base64 incoerentes."""
    if mime_type == "image/png":
        return binary.startswith(b"\\x89PNG\\r\\n\\x1a\\n")
    if mime_type == "image/jpeg":
        return binary.startswith(b"\\xff\\xd8\\xff")
    if mime_type == "image/webp":
        return len(binary) >= 12 and binary[:4] == b"RIFF" and binary[8:12] == b"WEBP"
    return False


def _decodificar_imagem_validada(
    data: str,
    mime_type: str,
    *,
    limite_bytes: int,
    descricao: str,
) -> bytes:
    """Decodifica Base64 estritamente, aplica limite e confere assinatura/MIME."""
    try:
        binary = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"Base64 inválido para {descricao}.") from exc
    if not binary:
        raise ValueError(f"{descricao.capitalize()} vazia.")
    if len(binary) > limite_bytes:
        raise ValueError(f"{descricao.capitalize()} excede o limite de {limite_bytes} bytes.")
    if not _assinatura_compativel(binary, mime_type):
        raise ValueError(f"Os bytes de {descricao} não correspondem ao MIME {mime_type}.")
    return binary


def _imagem_saida_validada(data: Any, mime_type: Any) -> dict[str, str] | None:
    """Retorna uma imagem saída somente se MIME, Base64, assinatura e tamanho forem válidos."""
    if not isinstance(data, str) or not isinstance(mime_type, str):
        return None
    normalized_mime = mime_type.strip().lower()
    if normalized_mime not in ALLOWED_MIME:
        return None
    try:
        binary = _decodificar_imagem_validada(
            data,
            normalized_mime,
            limite_bytes=MAX_OUTPUT_BYTES,
            descricao="imagem gerada",
        )
    except ValueError:
        return None
    return {
        "mime_type": normalized_mime,
        "base64": base64.b64encode(binary).decode("ascii"),
    }


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
            "modelo": os.environ.get("NYXAL_GEMINI_IMAGE_MODEL", "gemini-nano-banana-2.1"),
            "entrada_max_bytes": MAX_INPUT_BYTES,
            "saida_max_bytes": MAX_OUTPUT_BYTES,
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
        if imagem_base64 is not None and not isinstance(imagem_base64, str):
            raise ValueError("A imagem precisa ser enviada como Base64.")
        if mime_type is not None and not isinstance(mime_type, str):
            raise ValueError("O tipo MIME da imagem é inválido.")

        inputs: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        if imagem_base64 is not None:
            if not isinstance(mime_type, str) or mime_type.strip().lower() not in ALLOWED_MIME:
                raise ValueError("Formato de imagem não permitido. Use PNG, JPEG ou WebP.")
            normalized_mime = mime_type.strip().lower()
            binary = _decodificar_imagem_validada(
                imagem_base64,
                normalized_mime,
                limite_bytes=MAX_INPUT_BYTES,
                descricao="imagem enviada",
            )
            inputs.append({
                "type": "image",
                "mime_type": normalized_mime,
                "data": base64.b64encode(binary).decode("ascii"),
            })

        model = os.environ.get("NYXAL_GEMINI_IMAGE_MODEL", "gemini-nano-banana-2.1").strip()
        url = "https://generativelanguage.googleapis.com/v1beta/interactions"
        payload = {
            "model": model,
            "input": inputs,
            "response_format": [{"type": "text"}, {"type": "image"}],
            "store": False,
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

        image = None
        text_parts: list[str] = []
        if isinstance(result, dict):
            output_text = result.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                text_parts.append(output_text.strip())
            output_image = result.get("output_image")
            if isinstance(output_image, dict):
                image = _imagem_saida_validada(
                    output_image.get("data"),
                    output_image.get("mime_type") or "image/png",
                )
        steps = result.get("steps", []) if isinstance(result, dict) else []
        for step in steps if isinstance(steps, list) else []:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            blocks = step.get("content", [])
            for item in blocks if isinstance(blocks, list) else []:
                if not isinstance(item, dict):
                    continue
                block_type = item.get("type")
                if block_type == "text":
                    text_value = item.get("text")
                    if isinstance(text_value, str) and text_value.strip():
                        text_parts.append(text_value.strip())
                elif block_type == "image":
                    candidate_image = _imagem_saida_validada(
                        item.get("data"),
                        item.get("mime_type") or "image/png",
                    )
                    if candidate_image is not None:
                        image = candidate_image
                        break
            if image:
                break

        # Compatibilidade defensiva com respostas antigas do endpoint Gemini.
        if image is None:
            candidates = result.get("candidates", []) if isinstance(result, dict) else []
            if candidates and isinstance(candidates[0], dict):
                content = candidates[0].get("content", {})
                blocks = content.get("parts", []) if isinstance(content, dict) else []
                for item in blocks if isinstance(blocks, list) else []:
                    if not isinstance(item, dict):
                        continue
                    if isinstance(item.get("text"), str) and item["text"].strip():
                        text_parts.append(item["text"].strip())
                    data = item.get("inlineData") or item.get("inline_data")
                    if isinstance(data, dict):
                        candidate_image = _imagem_saida_validada(
                            data.get("data"),
                            data.get("mimeType") or data.get("mime_type") or "image/png",
                        )
                        if candidate_image is not None:
                            image = candidate_image
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


__all__ = ["CapacidadeVisualGeminiNixOS", "MAX_INPUT_BYTES", "MAX_OUTPUT_BYTES", "ALLOWED_MIME"]
