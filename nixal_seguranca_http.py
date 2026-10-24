"""Políticas HTTP de segurança para a API local da Nyxal.

Este módulo mantém validações simples e determinísticas, sem dependências
externas nem efeitos colaterais.
"""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit


def host_loopback(host: str) -> bool:
    """Retorna True apenas para localhost ou um endereço IP de loopback."""
    valor = host.strip().lower()
    if valor == "localhost":
        return True
    try:
        return ip_address(valor).is_loopback
    except ValueError:
        return False


def origin_host_loopback(origin: str | None) -> bool:
    """Reconhece somente origens HTTP(S) com hostname loopback."""
    if not origin:
        return False
    try:
        parsed = urlsplit(origin)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() in {"http", "https"}
        and parsed.netloc != ""
        and hostname is not None
        and parsed.username is None
        and parsed.password is None
        and parsed.path == ""
        and parsed.query == ""
        and parsed.fragment == ""
        and host_loopback(hostname)
    )


def parse_allowed_origins(
    raw_origins: str | None,
    *,
    default_origins: set[str] | frozenset[str],
) -> frozenset[str]:
    """Valida uma lista de origens HTTP(S) explícitas; curingas são proibidos."""
    if raw_origins is None or not raw_origins.strip():
        return frozenset(default_origins)

    items = [item.strip() for item in raw_origins.split(",") if item.strip()]
    if not items:
        return frozenset(default_origins)

    if any(item == "*" or item.lower() == "null" for item in items):
        raise ValueError(
            "CORS não aceita '*' nem a origem 'null'; configure origens HTTP(S) exatas."
        )

    allowed: set[str] = set()
    for item in items:
        if any(char.isspace() for char in item):
            raise ValueError(f"Origem CORS inválida: {item!r}")

        try:
            parsed = urlsplit(item)
            hostname = parsed.hostname
            _ = parsed.port  # Valida porta malformada.
        except ValueError as erro:
            raise ValueError(f"Origem CORS inválida: {item!r}") from erro

        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.netloc
            or hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                f"Origem CORS inválida: {item!r}. Use apenas scheme://host[:port], sem caminho."
            )

        allowed.add(f"{parsed.scheme.lower()}://{parsed.netloc.lower()}")

    return frozenset(allowed)


def origin_permitida(
    origin: str | None,
    allowed_origins: set[str] | frozenset[str],
) -> bool:
    """Origem ausente é comum em clientes não-browser; presente precisa casar exatamente."""
    return origin is None or origin in allowed_origins
