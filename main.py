import os
from contextlib import asynccontextmanager
from pathlib import Path


def _load_dotenv() -> None:
    """Load `.env` before modules that read JWT/ADMIN_* at import or seed time."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


_load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.security import validate_production_config
from database.connection import init_db
from exception_handlers import register_exception_handlers
from middleware import LoginRateLimitMiddleware, SecurityHeadersMiddleware
from routers import (
    audit_router,
    auth_router,
    branch_router,
    category_router,
    cep_router,
    company_registration_router,
    company_router,
    customer_router,
    product_router,
    purchase_router,
    report_router,
    sale_router,
    stock_movement_router,
    store_router,
    supplier_router,
    user_router,
)

DEFAULT_CORS_ORIGINS = "http://localhost:3000"


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(*, init_database: bool = True, validate_config: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if validate_config:
            validate_production_config()
        if init_database:
            init_db()
        yield

    application = FastAPI(title="ERP API", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(LoginRateLimitMiddleware)
    register_exception_handlers(application)

    application.include_router(auth_router.router)
    application.include_router(user_router.router)
    application.include_router(audit_router.router)
    application.include_router(company_router.router)
    application.include_router(company_registration_router.router)
    application.include_router(branch_router.router)
    application.include_router(store_router.router)
    application.include_router(product_router.router)
    application.include_router(customer_router.router)
    application.include_router(sale_router.router)
    application.include_router(category_router.router)
    application.include_router(stock_movement_router.router)
    application.include_router(report_router.router)
    application.include_router(supplier_router.router)
    application.include_router(purchase_router.router)
    application.include_router(cep_router.router)

    @application.get("/")
    def root():
        return {"status": "ERP online e pronto para receber requisições"}

    return application


app = create_app()
