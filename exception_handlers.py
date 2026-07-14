from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.exceptions import (
    BusinessRuleException,
    ConflictException,
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
