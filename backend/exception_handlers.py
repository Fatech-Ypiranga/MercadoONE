from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from shared.exceptions import (
    BusinessRuleException,
    ConflictException,
    ExternalServiceException,
    ForbiddenException,
    InsufficientStockException,
    ResourceNotFoundException,
    UnauthorizedException,
    ValidationError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ResourceNotFoundException)
    async def resource_not_found_handler(_request: Request, exc: ResourceNotFoundException):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_error_handler(_request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(InsufficientStockException)
    async def insufficient_stock_handler(_request: Request, exc: InsufficientStockException):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ConflictException)
    async def conflict_handler(_request: Request, exc: ConflictException):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(BusinessRuleException)
    async def business_rule_handler(_request: Request, exc: BusinessRuleException):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_handler(_request: Request, exc: UnauthorizedException):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(_request: Request, exc: ForbiddenException):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ExternalServiceException)
    async def external_service_handler(_request: Request, exc: ExternalServiceException):
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_request: Request, _exc: IntegrityError):
        # Last-resort backstop: every known delete/write path already checks
        # dependencies before mutating (see docs/ROADMAP.md DB-02). This only
        # fires if a future code path forgets that check — without it, the
        # raw FK-violation SQL/params would otherwise leak into the response
        # (SQLAlchemy's exception message embeds the failed statement).
        return JSONResponse(
            status_code=409,
            content={"detail": "This operation conflicts with existing related data."},
        )
