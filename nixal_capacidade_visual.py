#!/usr/bin/env python3
"""Geração e edição visual da Nyxal com Gemini Image, sem persistir uploads."""
from __future__ import annotations

import base64
import json
import math
import os
import re
import unicodedata
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_IMAGE_BYTES = 28 * 1024 * 1024
MAX_RESPONSE_BYTES = 40 * 1024 * 1024
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
DEFAULT_IMAGE_MODEL = "gemini-nano-banana-2.1"
SUPPORTED_ASPECT_RATIOS = {
    "1:1", "1:4", "1:8", "2:3", "3:2", "3:4", "4:1",
    "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9",
}
STANDARD_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5",
    "5:4", "9:16", "16:9", "21:9",
}
MODEL_ASPECT_RATIOS = {
    "gemini-nano-banana-2.1": SUPPORTED_ASPECT_RATIOS,
    "gemini-3.1-flash-image": SUPPORTED_ASPECT_RATIOS,
    "gemini-3.1-flash-lite-image": STANDARD_ASPECT_RATIOS,
    "gemini-3-pro-image": STANDARD_ASPECT_RATIOS,
    "gemini-2.5-flash-image": STANDARD_ASPECT_RATIOS,
}
MODELS_WITH_IMAGE_SIZE = {
    "gemini-nano-banana-2.1",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image",
}
MODELS_1K_ONLY = {"gemini-3.1-flash-lite-image", "gemini-2.5-flash-image"}
MODELS_WITH_512PX = {"gemini-3.1-flash-image"}
# These explicit levels are limited to models whose official model pages publish them.
# Thinking levels verified against Google's official image-generation model table.
MODEL_THINKING_LEVELS = {
    DEFAULT_IMAGE_MODEL: frozenset({"minimal", "medium", "high"}),
    "gemini-3.1-flash-image": frozenset({"minimal", "high"}),
    "gemini-3.1-flash-lite-image": frozenset({"minimal", "high"}),
}
MODEL_DEFAULT_THINKING_LEVEL = {
    DEFAULT_IMAGE_MODEL: "medium",
    "gemini-3.1-flash-image": "minimal",
    "gemini-3.1-flash-lite-image": "minimal",
}
class _RejectRedirects(HTTPRedirectHandler):
    """Never forward API-key-bearing requests to a redirected destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _urlopen_no_redirect(request: Request, *, timeout: int):
    """Open a Gemini request while preserving proxy support but refusing redirects."""
    return build_opener(_RejectRedirects()).open(request, timeout=timeout)


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


def _direcao_visual_especifica(prompt: str) -> str:
    """Adiciona instruções focadas no tipo de imagem sem trocar o briefing original."""
    texto = _normalizar_texto(prompt)
    regras: list[str] = []

    if re.search(r"\b(?:infograf(?:ico|ica)?|diagrama|fluxograma|tabela|chart|diagram|infographic)\b", texto):
        regras.append(
            "Para informação visual: organize os elementos em uma grade clara, com hierarquia, "
            "espaçamento e contraste legíveis. Reproduza textos e dados fornecidos exatamente; "
            "não invente métricas, rótulos ou legendas e evite sobreposição."
        )

    if re.search(r"\b(?:logo|logotipo|logomarca)\b|identidade visual", texto):
        regras.append(
            "Para a marca: priorize uma silhueta distintiva, formas simples, espaço negativo "
            "intencional e legibilidade em tamanho pequeno. Não acrescente slogans, palavras, "
            "apresentações 3D ou mockups de marca sem solicitação."
        )

    if re.search(r"\b(?:interface|dashboard|painel|ux|ui)\b|tela de login|mockup de aplicativo", texto):
        regras.append(
            "Para a interface: mantenha grade, alinhamento, espaçamento, tipografia e estados "
            "visuais consistentes. Garanta contraste e legibilidade; não sobreponha controles "
            "nem invente métricas ou textos pequenos que não foram fornecidos."
        )

    if re.search(r"\b(?:produto|packshot|e-commerce|comercial)\b|fotografia de produto|foto de produto", texto):
        regras.append(
            "Para o produto: trate o objeto principal como protagonista, mantendo forma, cor, "
            "material e marcações coerentes. Use iluminação e sombras de contato plausíveis; "
            "não acrescente acessórios, rótulos ou marcas não solicitados."
        )

    if re.search(r"wallpaper|papel de parede|fundo de tela", texto):
        regras.append(
            "Para o papel de parede: preencha o formato pedido de ponta a ponta, mantenha um "
            "ponto focal claro e preserve espaço de respiro quando a composição pedir. Não adicione "
            "molduras ou margens."
        )

    if re.search(r"\b(?:retrato|portrait|headshot)\b|foto de rosto|close[- ]up de rosto", texto):
        regras.append(
            "Para o retrato: priorize estrutura facial coerente, textura natural da pele, luz "
            "consistente e anatomia plausível. Se houver imagem de referência, preserve a identidade "
            "e não altere traços pessoais sem pedido."
        )

    if re.search(r"\b(?:fotorealista|fotorrealista|fotorealismo|fotorrealismo|photorealistic|realismo fotografico)\b", texto):
        regras.append(
            "Para o realismo fotográfico: use perspectiva, escala, direção da luz, sombras e "
            "materiais fisicamente plausíveis; evite aparência de pintura ou render artificial "
            "a menos que seja solicitada."
        )

    return " ".join(regras[:3])


def _selecionar_nivel_raciocinio(prompt: str, *, modelo: str) -> str | None:
    """Valida o nível de raciocínio e permite selecionar automaticamente para prompts complexos."""
    solicitado = os.environ.get("NYXAL_GEMINI_IMAGE_THINKING_LEVEL", "").strip().lower()
    if not solicitado:
        return None  # Mantém o padrão e o custo definidos pelo provedor.

    permitidos = MODEL_THINKING_LEVELS.get(modelo)
    if not permitidos:
        raise ValueError(
            f"O modelo {modelo} não possui níveis de raciocínio configuráveis validados. "
            "Remova NYXAL_GEMINI_IMAGE_THINKING_LEVEL para usar o padrão do provedor."
        )

    if solicitado != "auto":
        if solicitado not in permitidos:
            opcoes = ", ".join(sorted(permitidos))
            raise ValueError(
                f"O modelo {modelo} não suporta o nível de raciocínio {solicitado!r}. "
                f"Opções válidas: {opcoes} ou auto."
            )
        return solicitado

    texto = _normalizar_texto(prompt)
    sinais_de_complexidade = (
        "tipografia", "infograf", "diagrama", "mapa", "rotulo", "layout",
        "composicao", "arquitetura", "anatomia", "perspectiva", "fotoreal",
        "fotorreal", "consistencia", "multiplos", "varios sujeitos", "muitas camadas",
        "detalhado", "detalhada", "precisao", "cartaz", "poster", "legivel",
    )
    termos_exatos_de_complexidade = re.search(
        r"\b(?:texto|textos|logo|logotipo|logomarca|capa|marca|exatamente)\b",
        texto,
    )
    complexo = (
        len(prompt) >= 700
        or bool(termos_exatos_de_complexidade)
        or any(sinal in texto for sinal in sinais_de_complexidade)
    )
    return "high" if complexo else MODEL_DEFAULT_THINKING_LEVEL[modelo]


def _normalizar_proporcao(largura: int, altura: int) -> str | None:
    if largura <= 0 or altura <= 0:
        return None
    divisor = math.gcd(largura, altura)
    proporcao = f"{largura // divisor}:{altura // divisor}"
    return proporcao if proporcao in SUPPORTED_ASPECT_RATIOS else None


def _inferir_proporcao(prompt: str, *, modelo: str = DEFAULT_IMAGE_MODEL) -> str | None:
    """Infere uma proporção e respeita as proporções documentadas para o modelo."""
    texto = _normalizar_texto(prompt)
    permitidas = MODEL_ASPECT_RATIOS.get(modelo, STANDARD_ASPECT_RATIOS)

    for match in re.finditer(r"(?<!\d)(\d{1,4})\s*:\s*(\d{1,4})(?!\d)", texto):
        proporcao = _normalizar_proporcao(int(match.group(1)), int(match.group(2)))
        if proporcao:
            if proporcao not in permitidas:
                raise ValueError(
                    f"O modelo {modelo} não suporta a proporção {proporcao}. "
                    "Use uma proporção suportada pelo modelo."
                )
            return proporcao

    # A orientação explícita sempre tem precedência sobre palavras genéricas como wallpaper.
    vertical_phrases = (
        "vertical", "9:16", "tela de bloqueio", "wallpaper para telefone",
        "wallpaper para celular", "fundo de tela do celular", "para celular",
        "para smartphone", "phone wallpaper", "mobile wallpaper", "smartphone wallpaper",
        "portrait orientation", "portrait format", "vertical format", "imagem vertical",
        "foto vertical", "lock screen",
    )
    vertical_social = re.search(r"\b(?:story|stories|reel|reels|tiktok)\b", texto)
    if any(pista in texto for pista in vertical_phrases) or vertical_social:
        return "9:16" if "9:16" in permitidas else None

    quadrado = ("quadrado", "foto de perfil", "profile picture", "profile photo")
    quadrado_token = re.search(r"\b(?:square|avatar|icon|icone|sticker)\b", texto)
    if any(pista in texto for pista in quadrado) or quadrado_token:
        return "1:1" if "1:1" in permitidas else None

    horizontal = (
        "horizontal", "landscape orientation", "landscape format", "panoram",
        "widescreen", "paisagem ampla", "wallpaper", "papel de parede",
        "desktop wallpaper", "desktop background", "monitor wallpaper", "wallpaper para pc",
        "papel de parede para computador", "wallpaper para monitor", "fundo de tela do pc",
        "tela de pc", "capa do youtube", "thumbnail do youtube", "youtube thumbnail",
        "banner", "wide wallpaper",
    )
    if any(pista in texto for pista in horizontal):
        return "16:9" if "16:9" in permitidas else None

    impresso_vertical = (
        "poster", "cartaz", "capa de livro", "book cover", "capa de revista",
        "magazine cover", "folha a4 vertical", "vertical a4",
    )
    if any(pista in texto for pista in impresso_vertical):
        return "2:3" if "2:3" in permitidas else None
    return None


def _inferir_tamanho_imagem(prompt: str, *, padrao: str | None) -> str | None:
    """Escolhe apenas tamanhos nativos conhecidos do modelo; nunca promete 8K."""
    texto = _normalizar_texto(prompt)
    if re.search(r"(?<![a-z0-9])(?:512\s*(?:px|pixels?)|0\.5\s*k)(?![a-z0-9])", texto):
        return "512px"
    if re.search(r"(?:(?<![a-z0-9])(?:4k|uhd|ultra[\s-]*hd)(?![a-z0-9])|(?<!\d)4096\s*(?:px|pixels?)?(?!\d))", texto):
        return "4K"
    if re.search(r"(?<![a-z0-9])(?:2k|1440p)(?![a-z0-9])", texto):
        return "2K"
    if re.search(r"(?<![a-z0-9])(?:1k|1024p)(?![a-z0-9])", texto):
        return "1K"
    # A solicitação é mantida explícita para que o chamador rejeite 8K
    # com uma mensagem compatível com as capacidades do modelo selecionado.
    if re.search(r"(?<![a-z0-9])8k(?![a-z0-9])", texto):
        return "8K"
    return padrao


def _preparar_prompt(
    prompt: str, *, edicao: bool, nivel_estilizado: int | None = None,
    elementos_excluir: str | None = None,
) -> str:
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

    direcao_especifica = _direcao_visual_especifica(prompt)
    if direcao_especifica:
        direcao += " " + direcao_especifica

    if nivel_estilizado is not None:
        if nivel_estilizado <= 100:
            direcao += " Prefira interpretação literal e mínima invenção artística."
        elif nivel_estilizado < 500:
            direcao += (
                " Equilibre fidelidade ao briefing e interpretação artística, sem inventar "
                "detalhes que contradigam os requisitos explícitos."
            )
        else:
            direcao += (
                " Permita uma interpretação artística mais ousada, sem contradizer o briefing "
                "nem alterar os requisitos explícitos."
            )
    if elementos_excluir:
        direcao += (
            " Exclusões explícitas do usuário: não inclua "
            f"{elementos_excluir}. Trate essas exclusões como restrições prioritárias."
        )

    return (
        f"{direcao}\n\n"
        "Briefing original do usuário — prioridade máxima; preserve o significado e as restrições:\n"
        f"{prompt}"
    )


def _assinatura_compativel(dados: bytes, mime_type: str) -> bool:
    assinatura = MIME_SIGNATURES.get(mime_type.lower())
    return bool(assinatura and assinatura(dados))


def _extrair_parametros_midjourney(
    prompt: str, *, modelo: str = DEFAULT_IMAGE_MODEL
) -> tuple[str, int | None, str | None, str | None]:
    """Traduz --ar/--aspect, --s/--stylize e --no para instruções compatíveis."""
    limpo = prompt
    stylize = None
    proporcao_solicitada = None
    elementos_excluir = None
    permitidas = MODEL_ASPECT_RATIOS.get(modelo, STANDARD_ASPECT_RATIOS)

    # --no é uma exclusão textual em Midjourney; converte-a em linguagem natural.
    negative_match = re.search(
        r"(?is)(?:^|\s)--no\s+(.+?)(?=\s+--(?:ar|aspect|s|stylize)\b|$)",
        limpo,
    )
    if negative_match:
        elementos_excluir = negative_match.group(1).strip(" ,;")
        limpo = limpo[:negative_match.start()] + " " + limpo[negative_match.end():]

    stylize_match = re.search(r"(?i)(?:--stylize|--s)\s*(\d{1,4})(?!\d)", limpo)
    if stylize_match:
        stylize = min(1000, int(stylize_match.group(1)))
        limpo = limpo[:stylize_match.start()] + limpo[stylize_match.end():]

    ratio_match = re.search(
        r"(?i)--(?:ar|aspect)\s*(\d{1,4})\s*:\s*(\d{1,4})(?!\d)",
        limpo,
    )
    if ratio_match:
        proporcao_solicitada = _normalizar_proporcao(
            int(ratio_match.group(1)), int(ratio_match.group(2))
        )
        if proporcao_solicitada is None:
            raise ValueError(
                "A proporção --ar solicitada não é suportada. "
                f"Opções válidas: {', '.join(sorted(permitidas))}."
            )
        if proporcao_solicitada not in permitidas:
            raise ValueError(
                f"O modelo {modelo} não suporta a proporção {proporcao_solicitada}. "
                f"Opções válidas para esse modelo: {', '.join(sorted(permitidas))}."
            )
        limpo = limpo[:ratio_match.start()] + limpo[ratio_match.end():]

    return re.sub(r"\s{2,}", " ", limpo).strip(), stylize, proporcao_solicitada, elementos_excluir


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
            "nivel_raciocinio_configurado": (
                os.environ.get("NYXAL_GEMINI_IMAGE_THINKING_LEVEL", "").strip().lower()
                or "padrao_do_provedor"
            ),
            "niveis_raciocinio_suportados": sorted(MODEL_THINKING_LEVELS.get(model, ())),
            "entrada_max_bytes": MAX_INPUT_BYTES,
            "mime_permitidos": sorted(ALLOWED_MIME),
            "salva_upload_no_servidor": False,
            "controles": {
                "proporcao_automatica": True,
                "tamanho_nativo": (
                    ["1K"] if model in MODELS_1K_ONLY
                    else ["512px", "1K", "2K", "4K"] if model in MODELS_WITH_512PX
                    else ["1K", "2K", "4K"] if model in MODELS_WITH_IMAGE_SIZE
                    else ["definido_pelo_provedor"]
                ),
                "edicao_preserva_areas_nao_solicitadas": True,
                "parametros_midjourney": ["--ar", "--aspect", "--s", "--stylize", "--no"],
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
        model = os.environ.get("NYXAL_GEMINI_IMAGE_MODEL", "").strip() or DEFAULT_IMAGE_MODEL
        prompt_limpo, nivel_estilizado, proporcao_solicitada, elementos_excluir = _extrair_parametros_midjourney(
            prompt, modelo=model
        )
        nivel_raciocinio = _selecionar_nivel_raciocinio(prompt_limpo, modelo=model)
        inputs: list[dict[str, Any]] = [{
            "type": "text",
            "text": _preparar_prompt(
                prompt_limpo,
                edicao=imagem_presente,
                nivel_estilizado=nivel_estilizado,
                elementos_excluir=elementos_excluir,
            ),
        }]

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

        image_format: dict[str, Any] = {"type": "image", "mime_type": "image/png"}
        aspect_ratio = proporcao_solicitada or _inferir_proporcao(prompt_limpo, modelo=model)
        if aspect_ratio:
            image_format["aspect_ratio"] = aspect_ratio

        if model in MODELS_1K_ONLY:
            requested_size = _inferir_tamanho_imagem(prompt, padrao=None)
            if requested_size in {"512px", "2K", "4K", "8K"}:
                raise ValueError(
                    f"O modelo {model} só gera imagens em 1K. "
                    "Use gemini-nano-banana-2.1 para solicitar 2K ou 4K."
                )
            if requested_size == "1K":
                image_format["image_size"] = "1K"
        elif model in MODELS_WITH_512PX:
            default_size = None if imagem_presente else "2K"
            image_size = _inferir_tamanho_imagem(prompt, padrao=default_size)
            if image_size == "8K":
                raise ValueError(
                    f"O modelo {model} não oferece saída nativa em 8K; a resolução máxima é 4K."
                )
            if image_size:
                image_format["image_size"] = image_size
        elif model in MODELS_WITH_IMAGE_SIZE:
            # Evita forçar resolução nas edições; o provedor decide a saída a partir da entrada.
            default_size = None if imagem_presente else "2K"
            image_size = _inferir_tamanho_imagem(prompt, padrao=default_size)
            if image_size == "8K":
                raise ValueError(
                    f"O modelo {model} não oferece saída nativa em 8K; a resolução máxima é 4K."
                )
            if image_size:
                image_format["image_size"] = image_size
        elif _inferir_tamanho_imagem(prompt, padrao=None) == "8K":
            raise ValueError(
                f"Não foi possível confirmar saída nativa em 8K para o modelo {model}. "
                "Selecione um modelo compatível com a resolução desejada."
            )

        url = "https://generativelanguage.googleapis.com/v1beta/interactions"
        payload = {
            "model": model,
            "input": inputs,
            "response_format": [{"type": "text"}, image_format],
            "store": False,
        }
        if nivel_raciocinio is not None:
            payload["generation_config"] = {"thinking_level": nivel_raciocinio}
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
            with _urlopen_no_redirect(request, timeout=120) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise RuntimeError("A resposta visual excedeu 40 MiB.")
            result = json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Gemini Image retornou HTTP {exc.code}. Confira modelo, chave e cota.") from exc
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Falha ao comunicar com Gemini Image ({type(exc).__name__}).") from exc

        image = None
        output_image_found = False
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
                    output_image_found = True
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
                elif (
                    block_type == "image"
                    and isinstance(item.get("data"), str)
                    and not output_image_found
                ):
                    mime = item.get("mime_type") or "image/png"
                    if isinstance(mime, str) and mime.lower() in ALLOWED_MIME:
                        # Quando a resposta contém múltiplas imagens, a última é a saída final.
                        image = {"mime_type": mime.lower(), "base64": item["data"]}

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
