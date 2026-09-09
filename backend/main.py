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


def _init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ENV", "development"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        send_default_pii=False,
    )


_init_sentry()

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlmodel import Session

from audit_log import router as audit_router
from auth import router as auth_router
from categories import router as category_router
from cep import router as cep_router
from company_registration import router as company_registration_router
from customers import router as customer_router
from database.connection import engine, init_db
from exception_handlers import register_exception_handlers
from middleware import LoginRateLimitMiddleware, SecurityHeadersMiddleware
from organization import branch_router, company_router, store_router
from reports import router as report_router
from routers import (
    product_router,
    purchase_router,
    sale_router,
    stock_movement_router,
    user_router,
)
from shared.identity.security import validate_production_config
from suppliers import router as supplier_router

DEFAULT_CORS_ORIGINS = "http://localhost:3000"


def get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _is_production() -> bool:
    return os.getenv("ENV", "development").lower() == "production"


def create_app(*, init_database: bool = True, validate_config: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if validate_config:
            validate_production_config()
        if init_database:
            init_db()
        yield

    docs_enabled = not _is_production()
    application = FastAPI(
        title="ERP API",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
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

    @application.get("/livez")
    def livez():
        """Liveness: process is up (no dependency checks)."""
        return {"status": "ok"}

    @application.get("/readyz")
    def readyz(response: Response):
        """Readiness: database reachable."""
        try:
            with Session(engine) as session:
                session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "ok"}
        except Exception:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "degraded", "database": "unreachable"}

    @application.get("/healthz")
    def healthz(response: Response):
        """Compatibility alias for readiness (prefer /livez and /readyz)."""
        return readyz(response)

    return application


app = create_app()
