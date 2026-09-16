import os
import secrets
from typing import Annotated

from fastapi import Header

from shared.exceptions import UnauthorizedException


def get_platform_api_key() -> str | None:
    value = os.getenv("PLATFORM_API_KEY", "").strip()
    return value or None


def require_platform_api_key(
    x_platform_key: Annotated[str | None, Header(alias="X-Platform-Key")] = None,
) -> str:
    expected = get_platform_api_key()
    if not expected:
        raise UnauthorizedException("Platform API key is not configured.")
    if not x_platform_key or not secrets.compare_digest(x_platform_key, expected):
        raise UnauthorizedException("Invalid platform API key.")
    return "platform"
