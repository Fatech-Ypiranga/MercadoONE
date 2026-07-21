import secrets
from typing import Annotated

from fastapi import Header

from services.company_registration_service import get_platform_api_key
from services.exceptions import UnauthorizedException


def require_platform_api_key(
    x_platform_key: Annotated[str | None, Header(alias="X-Platform-Key")] = None,
) -> str:
    expected = get_platform_api_key()
    if not expected:
        raise UnauthorizedException("Platform API key is not configured.")
    if not x_platform_key or not secrets.compare_digest(x_platform_key, expected):
        raise UnauthorizedException("Invalid platform API key.")
    return "platform"
