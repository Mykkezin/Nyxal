"""Políticas HTTP de segurança para a API local da Nyxal.

Normaliza origens, valida hosts loopback e mantém a política sem dependências
externas nem efeitos colaterais.
"""
from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit


def host_loopback(host: str) -> bool:
    """Retorna True apenas para localhost ou um endereço IP de loopback."""
    if not isinstance(host, str):
        return False
    valor = host.strip().lower()
    if not valor:
        return False
    if valor == "localhost":
        return True
    try:
        return ip_address(valor).is_loopback
    except ValueError:
        return False


def origin_host_loopback(origin: str | None) -> bool:
    """Identifica origens HTTP(S) explícitas hospedadas somente em loopback."""
    normalized = normalize_origin(origin)
    if normalized is None:
        return False
    try:
        hostname = urlsplit(normalized).hostname
    except ValueError:
        return False
    return host_loopback(hostname or "")


def normalize_origin(value: str | None) -> str | None:
    """Normaliza uma origem HTTP(S); rejeita wildcard, null e valores inválidos."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or value.lower() in {"*", "null"}:
        return None
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or "?" in value
        or "#" in value
        or any(char.isspace() for char in value)
    ):
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def parse_allowed_origins(
    raw_origins: str | None,
    *,
    default_origins: set[str] | frozenset[str],
) -> frozenset[str]:
    """Valida origens explícitas; curingas e listas inválidas são rejeitados."""
    if raw_origins is None or not raw_origins.strip():
        normalized_defaults = {
            normalized
            for item in default_origins
            if (normalized := normalize_origin(item)) is not None
        }
        return frozenset(normalized_defaults)
    items = [item.strip() for item in raw_origins.split(",")]
    if not items or any(not item for item in items):
        raise ValueError("Lista CORS contém uma origem vazia.")
    allowed: set[str] = set()
    for item in items:
        origin = normalize_origin(item)
        if origin is None:
            raise ValueError(
                f"Origem CORS inválida: {item!r}. Use apenas origens HTTP(S) exatas."
            )
        allowed.add(origin)
    return frozenset(allowed)


def origin_permitida(
    origin: str | None,
    allowed_origins: set[str] | frozenset[str],
) -> bool:
    """Origem ausente é válida para clientes não-browser; toda origem fornecida é validada."""
    if origin is None:
        return True
    normalized = normalize_origin(origin)
    return normalized is not None and normalized in allowed_origins
