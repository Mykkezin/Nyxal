#!/usr/bin/env python3
"""Geração e edição visual da Nyxal com Gemini Image, sem persistir uploads."""
from __future__ import annotations

import base64
import json
import os
import re
import unicodedata
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_IMAGE_BYTES = 28 * 1024 * 1024
MAX_RESPONSE_BYTES = 40 * 1024 * 1024
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
DEFAULT_IMAGE_MODEL = "gemini-nano-banana-2.1"
SUPPORTED_ASPECT_RATIOS = {
    "1:1", "1:4", "1:8", "2:3", "3:2", "3:4", "4:1",
    "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9",
}
MODELS_WITH_IMAGE_SIZE = {
    "gemini-nano-banana-2.1",
    "gemini-3.1-flash-lite-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
}
MIME_SIGNATURES = {
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda data: len(data) >= 3 and data.startswith(b"\xff\xd8\xff"),
    "image/webp": lambda data: (
        len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    ),
}


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(char for char in texto if not unicodedata.combining(char))


def _inferir_proporcao(prompt: str) -> str | None:
    """Converte proporções e pistas de enquadramento em opções reais da API."""
    texto = _normalizar_texto(prompt)
    for match in re.finditer(r"(?<!\d)(\d{1,2})\s*:\s*(\d{1,2})(?!\d)", texto):
        proporcao = f"{int(match.group(1))}:{int(match.group(2))}"
        if proporcao in SUPPORTED_ASPECT_RATIOS:
            return proporcao

    # A orientação explícita sempre tem precedência sobre palavras genéricas como wallpaper.
    vertical_phrases = (
        "vertical", "9:16", "celular", "smartphone", "tela de bloqueio",
        "wallpaper para telefone", "wallpaper para celular", "phone wallpaper",
        "mobile wallpaper", "portrait orientation", "vertical format", "lock screen",
    )
    vertical_social = re.search(r"\b(?:story|stories|reel|reels|tiktok)\b", texto)
    if any(pista in texto for pista in vertical_phrases) or vertical_social:
        return "9:16"

    quadrado = ("quadrado", "square", "foto de perfil", "profile picture", "profile photo", "icone", "sticker")
    quadrado_token = re.search(r"\b(?:avatar|icon|icone|sticker)\b", texto)
    if any(pista in texto for pista in quadrado) or quadrado_token:
        return "1:1"

    horizontal = (
        "horizontal", "landscape orientation", "landscape format", "panoram",
        "widescreen", "cinematic", "paisagem ampla", "wallpaper", "papel de parede",
        "desktop", "monitor", "tela de pc", "capa do youtube", "thumbnail do youtube",
        "youtube thumbnail", "banner", "wide wallpaper",
    )
    if any(pista in texto for pista in horizontal):
        return "16:9"

    impresso_vertical = (
        "poster", "cartaz", "capa de livro", "book cover", "capa de revista",
        "magazine cover", "folha a4 vertical", "vertical a4",
    )
    if any(pista in texto for pista in impresso_vertical):
        return "2:3"
    return None


def _inferir_tamanho_imagem(prompt: str, *, padrao: str | None) -> str | None:
    """Escolhe apenas tamanhos nativos conhecidos do modelo; nunca promete 8K."""
    texto = _normalizar_texto(prompt)
    if re.search(r"(?<![a-z0-9])(?:4k|uhd|ultra[\s-]*hd)(?![a-z0-9])|4096\s*(?:px|pixels?)?", texto):
        return "4K"
    if re.search(r"(?<![a-z0-9])(?:2k|1440p)(?![a-z0-9])", texto):
        return "2K"
    if re.search(r"(?<![a-z0-9])(?:1k|1024p)(?![a-z0-9])", texto):
        return "1K"
    # Uma solicitação de 8K não é um modo suportado: usa a maior saída disponível.
    if re.search(r"(?<![a-z0-9])8k(?![a-z0-9])", texto):
        return "4K"
    return padrao


def _preparar_prompt(prompt: str, *, edicao: bool, nivel_estilizado: int | None = None) -> str:
    """Acrescenta direção visual sem reescrever ou substituir a intenção do usuário."""
    if edicao:
        direcao = (
            "Direção para edição: use a imagem fornecida como referência principal e aplique "
            "somente as mudanças pedidas. Preserve identidade, anatomia, pose, enquadramento, "
            "perspectiva, cores, iluminação, textura, fundo e demais áreas não mencionadas. "
            "Não redesenhe a cena inteira nem remova ou acrescente elementos sem solicitação. "
            "Se o pedido exigir uma mudança global de estilo ou de formato, faça apenas essa "
            "mudança global e mantenha o restante fiel. Não acrescente texto, assinaturas, "
            "logotipos ou marcas-d'água não solicitados."
        )
    else:
        direcao = (
            "Direção visual: atue como diretor de arte experiente. Preserve a intenção e todos "
            "os requisitos explícitos do briefing; escolha uma hierarquia visual clara, composição "
            "intencional, perspectiva coerente, iluminação e paleta consistentes com o estilo pedido, "
            "e materiais/texturas convincentes no nível de detalhe apropriado. Evite enfeites, "
            "objetos, texto, assinaturas, logotipos ou marcas-d'água não solicitados. Se houver texto "
            "pedido, reproduza-o exatamente e não invente palavras adicionais."
        )

    if nivel_estilizado is not None:
        if nivel_estilizado <= 100:
            direcao += " Prefira interpretação literal e mínima invenção artística."
        elif nivel_estilizado >= 500:
            direcao += (
                " Permita uma interpretação artística mais ousada, sem contradizer o briefing "
                "nem alterar os requisitos explícitos."
            )

    return (
        f"{direcao}\n\n"
        "Briefing original do usuário — prioridade máxima; preserve o significado e as restrições:\n"
        f"{prompt}"
    )


def _assinatura_compativel(dados: bytes, mime_type: str) -> bool:
    assinatura = MIME_SIGNATURES.get(mime_type.lower())
    return bool(assinatura and assinatura(dados))


def _extrair_parametros_midjourney(prompt: str) -> tuple[str, int | None]:
    """Traduz os parâmetros comuns --ar e --stylize para controles que a API suporta."""
    limpo = prompt
    stylize = None

    stylize_match = re.search(r"(?i)(?:--stylize|--s)\s*(\d{1,4})(?!\d)", limpo)
    if stylize_match:
        stylize = min(1000, int(stylize_match.group(1)))
        limpo = limpo[:stylize_match.start()] + limpo[stylize_match.end():]

    # --ar/--aspect é aplicado em response_format; não deve ser apresentado ao modelo como texto.
    ratio_match = re.search(r"(?i)--(?:ar|aspect)\s*(\d{1,2})\s*:\s*(\d{1,2})", limpo)
    if ratio_match:
        ratio = f"{int(ratio_match.group(1))}:{int(ratio_match.group(2))}"
        if ratio in SUPPORTED_ASPECT_RATIOS:
            limpo = limpo[:ratio_match.start()] + limpo[ratio_match.end():]

    return re.sub(r"\s{2,}", " ", limpo).strip(), stylize


class CapacidadeVisualGeminiNixOS:
    FONTE = "gemini_image_api"
    VERSAO = "1.1.0"

    def status(self) -> dict[str, Any]:
        configured = bool(
            os.environ.get("NYXAL_GEMINI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        )
        model = os.environ.get("NYXAL_GEMINI_IMAGE_MODEL", "").strip() or DEFAULT_IMAGE_MODEL
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "estado": "configurado" if configured else "configuracao_pendente",
            "modelo": model,
            "entrada_max_bytes": MAX_INPUT_BYTES,
            "mime_permitidos": sorted(ALLOWED_MIME),
            "salva_upload_no_servidor": False,
            "controles": {
                "proporcao_automatica": True,
                "tamanho_nativo": ["1K", "2K", "4K"],
                "edicao_preserva_areas_nao_solicitadas": True,
                "parametros_midjourney": ["--ar", "--aspect", "--s", "--stylize"],
            },
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
        if imagem_base64 is not None and not isinstance(imagem_base64, str):
            raise ValueError("A imagem precisa ser enviada como Base64.")
        if mime_type is not None and not isinstance(mime_type, str):
            raise ValueError("O tipo MIME da imagem é inválido.")

        api_key = (
            os.environ.get("NYXAL_GEMINI_API_KEY", "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        )
        if not api_key:
            raise RuntimeError("Gemini não configurado. Adicione NYXAL_GEMINI_API_KEY à configuração local.")

        imagem_presente = bool(imagem_base64)
        inputs: list[dict[str, Any]] = []
        prompt_limpo, nivel_estilizado = _extrair_parametros_midjourney(prompt)
        inputs.append({
            "type": "text",
            "text": _preparar_prompt(prompt_limpo, edicao=imagem_presente, nivel_estilizado=nivel_estilizado),
        })

        if imagem_presente:
            mime = mime_type.lower().strip() if isinstance(mime_type, str) else ""
            if mime not in ALLOWED_MIME:
                raise ValueError("Formato de imagem não permitido. Use PNG, JPEG ou WebP.")
            # Rejeita strings enormes antes da alocação causada pela decodificação Base64.
            max_encoded_bytes = 4 * ((MAX_INPUT_BYTES + 2) // 3)
            if len(imagem_base64) > max_encoded_bytes:
                raise ValueError("A imagem excede o limite de 8 MiB.")
            try:
                binary = base64.b64decode(imagem_base64, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                raise ValueError("A imagem enviada não contém Base64 válido.") from exc
            if not binary:
                raise ValueError("O arquivo de imagem está vazio.")
            if len(binary) > MAX_INPUT_BYTES:
                raise ValueError("A imagem excede o limite de 8 MiB.")
            if not _assinatura_compativel(binary, mime):
                raise ValueError("O conteúdo da imagem não corresponde ao tipo MIME informado.")
            inputs.append({
                "type": "image",
                "mime_type": mime,
                "data": base64.b64encode(binary).decode("ascii"),
            })

        model = os.environ.get("NYXAL_GEMINI_IMAGE_MODEL", "").strip() or DEFAULT_IMAGE_MODEL
        image_format: dict[str, Any] = {"type": "image", "mime_type": "image/png"}
        aspect_ratio = _inferir_proporcao(prompt)
        if aspect_ratio:
            image_format["aspect_ratio"] = aspect_ratio

        if model in MODELS_WITH_IMAGE_SIZE:
            # 2K é o padrão para novas imagens; edições mantêm o tamanho de origem,
            # salvo quando a pessoa pede explicitamente uma resolução.
            default_size = None if imagem_presente else "2K"
            image_size = _inferir_tamanho_imagem(prompt, padrao=default_size)
            if image_size:
                image_format["image_size"] = image_size

        url = "https://generativelanguage.googleapis.com/v1beta/interactions"
        payload = {
            "model": model,
            "input": inputs,
            "response_format": [{"type": "text"}, image_format],
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
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise RuntimeError("A resposta visual excedeu 40 MiB.")
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
            if isinstance(output_image, dict) and isinstance(output_image.get("data"), str):
                mime = output_image.get("mime_type") or "image/png"
                if isinstance(mime, str) and mime.lower() in ALLOWED_MIME:
                    image = {"mime_type": mime.lower(), "base64": output_image["data"]}
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
                elif block_type == "image" and isinstance(item.get("data"), str):
                    mime = item.get("mime_type") or "image/png"
                    if isinstance(mime, str) and mime.lower() in ALLOWED_MIME:
                        image = {"mime_type": mime.lower(), "base64": item["data"]}
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
                    if isinstance(data, dict) and isinstance(data.get("data"), str):
                        mime = data.get("mimeType") or data.get("mime_type") or "image/png"
                        if isinstance(mime, str) and mime.lower() in ALLOWED_MIME:
                            image = {"mime_type": mime.lower(), "base64": data["data"]}
                            break

        if image is None:
            status = result.get("status") if isinstance(result, dict) else None
            if status in {"failed", "cancelled", "incomplete"}:
                raise RuntimeError(f"Gemini Image não concluiu a geração (status: {status}).")
            raise RuntimeError("Gemini respondeu sem imagem. Tente descrever melhor a edição ou consulte a cota do modelo.")

        try:
            image_bytes = base64.b64decode(image["base64"], validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise RuntimeError("Gemini retornou dados de imagem inválidos.") from exc
        if not image_bytes:
            raise RuntimeError("Gemini retornou uma imagem vazia.")
        if len(image_bytes) > MAX_OUTPUT_IMAGE_BYTES:
            raise RuntimeError("A imagem gerada excedeu o limite de 28 MiB.")
        if not _assinatura_compativel(image_bytes, image["mime_type"]):
            raise RuntimeError("Gemini retornou bytes incompatíveis com o formato de imagem declarado.")

        return {
            "sucesso": True,
            "estado": "imagem_editada" if imagem_presente else "imagem_gerada",
            "origem": self.FONTE,
            "modelo": model,
            "mime_type": image["mime_type"],
            "imagem_base64": base64.b64encode(image_bytes).decode("ascii"),
            "mensagem": "\n".join(text_parts)[:2000],
            "upload_salvo_no_servidor": False,
        }


__all__ = [
    "CapacidadeVisualGeminiNixOS",
    "MAX_INPUT_BYTES",
    "MAX_OUTPUT_IMAGE_BYTES",
    "ALLOWED_MIME",
]
