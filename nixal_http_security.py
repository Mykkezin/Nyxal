"""Safe defaults for browser origins accepted by the local Nyxal API."""
from __future__ import annotations

from urllib.parse import urlsplit


DEFAULT_BROWSER_ORIGINS = frozenset(
    {
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://[::1]:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://[::1]:5173",
        "http://127.0.0.1:8010",
        "http://localhost:8010",
        "http://[::1]:8010",
    }
)


def normalize_origin(value: str | None) -> str | None:
    """Return a normalized HTTP(S) origin; reject wildcards and opaque origins."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or value in {"*", "null"}:
        return None

    try:
        parsed = urlsplit(value)
        # Accessing .port validates malformed/out-of-range ports.
        _ = parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None

    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def parse_allowed_origins(configured: str | None = None) -> frozenset[str]:
    """Combine safe loopback defaults with exact comma-separated configured origins.

    '*' is deliberately ignored: it must never make browser requests unrestricted.
    """
    allowed = set(DEFAULT_BROWSER_ORIGINS)
    if not configured:
        return frozenset(allowed)

    for raw_origin in configured.split(","):
        origin = normalize_origin(raw_origin)
        if origin is not None:
            allowed.add(origin)
    return frozenset(allowed)


def origin_is_allowed(
    origin: str | None,
    allowed_origins: frozenset[str] | set[str],
) -> bool:
    """Allow non-browser clients without Origin; validate every supplied Origin."""
    if origin is None or not origin.strip():
        return True
    normalized = normalize_origin(origin)
    return normalized is not None and normalized in allowed_origins


def cors_response_origin(
    origin: str | None,
    allowed_origins: frozenset[str] | set[str],
) -> str | None:
    """Echo only an explicitly allowed normalized origin, never a wildcard."""
    if origin is None or not origin.strip() or not origin_is_allowed(origin, allowed_origins):
        return None
    return normalize_origin(origin)
