import os

os.environ.setdefault("ENV", "development")
# Testes locais: senha só no ambiente de teste (seed exige ADMIN_PASSWORD sem default).
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
# Evita 429 nos muitos logins da suíte (P2-06 rate limit).
os.environ.setdefault("LOGIN_RATE_LIMIT", "10000")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, create_engine

from auth.security import hash_password
from database.connection import get_db
from database.migrate import upgrade_head
from database.seed import ensure_demo_organization, seed_admin_user
from main import create_app
from models.user import User
from repositories.user_repository import UserRepository
from tests.catalog_seed import seed_purchase_test_catalog
from utils.enums import UserProfile

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://erp_user:erp_password@localhost:5432/erp_vendas_test",
)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@pyerp.local")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

TABLES = (
    "audit_log",
    "purchase_items",
    "purchase_orders",
    "supplier_product_mappings",
    "suppliers",
    "stock_movements",
    "sale_items",
    "sales",
    "product_fiscals",
    "products",
    "customer_addresses",
    "customers",
    "brands",
    "categories",
    "users",
    "stores",
    "branches",
    "companies",
)


def truncate_tables(engine) -> None:
    table_list = ", ".join(TABLES)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))


def reset_database_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def create_test_user(
    session: Session,
    *,
    full_name: str,
    cpf: str,
    email: str | None = None,
    username: str | None = None,
    password: str = "test1234",
    profile: UserProfile = UserProfile.OPERADOR,
    company_id: int | None = None,
    default_branch_id: int | None = None,
    default_store_id: int | None = None,
) -> User:
    if company_id is None:
        company, branch, store = ensure_demo_organization(session)
        company_id = company.id
        default_branch_id = default_branch_id or branch.id
        default_store_id = default_store_id or store.id

    user = User(
        full_name=full_name,
        cpf=cpf,
        email=email,
        username=username,
        password_hash=hash_password(password),
        profile=profile,
        is_active=True,
        company_id=company_id,
        default_branch_id=default_branch_id,
        default_store_id=default_store_id,
    )
    UserRepository.create(session, user)
    session.commit()
    session.refresh(user)
    return user


def page_items(response) -> list:
    """Unwrap list endpoints that return a Page envelope `{items, total, offset, limit}`."""
    body = response.json()
    if isinstance(body, dict) and "items" in body:
        return body["items"]
    return body


def login(client: TestClient, login_value: str, password: str) -> str:
    response = client.post("/auth/login", json={"login": login_value, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def make_client(test_engine, *, username: str, password: str) -> TestClient:
    def override_get_db():
        with Session(test_engine) as session:
            yield session

    app = create_app(init_database=False)
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    token = login(test_client, username, password)
    test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL de teste indisponível: {exc}")

    reset_database_schema(TEST_DATABASE_URL)
    upgrade_head(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def client(test_engine):
    truncate_tables(test_engine)

    with Session(test_engine) as session:
        ensure_demo_organization(session)
        session.commit()
        seed_admin_user(session)

    test_client = make_client(test_engine, username=ADMIN_USERNAME, password=ADMIN_PASSWORD)
    yield test_client
    test_client.app.dependency_overrides.clear()


@pytest.fixture
def admin_token(client: TestClient) -> str:
    return client.headers["Authorization"].split(" ", 1)[1]


@pytest.fixture
def db_session(test_engine, client):
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def seeded_catalog(db_session):
    seed_purchase_test_catalog(db_session)
    return db_session


@pytest.fixture
def operador_client(test_engine, client):
    with Session(test_engine) as session:
        create_test_user(
            session,
            full_name="Operador Teste",
            cpf="11111111111",
            email="operador@test.local",
            username="operador",
            password="oper1234",
            profile=UserProfile.OPERADOR,
        )

    test_client = make_client(test_engine, username="operador", password="oper1234")
    yield test_client
    test_client.app.dependency_overrides.clear()


@pytest.fixture
def conferente_client(test_engine, client):
    with Session(test_engine) as session:
        create_test_user(
            session,
            full_name="Conferente Teste",
            cpf="22222222222",
            email="conferente@test.local",
            username="conferente",
            password="conf1234",
            profile=UserProfile.CONFERENTE,
        )

    test_client = make_client(test_engine, username="conferente", password="conf1234")
    yield test_client
    test_client.app.dependency_overrides.clear()


@pytest.fixture
def colaborador_client(test_engine, client):
    with Session(test_engine) as session:
        create_test_user(
            session,
            full_name="Colaborador Teste",
            cpf="33333333333",
            email="colaborador@test.local",
            username="colaborador",
            password="colab1234",
            profile=UserProfile.COLABORADOR,
        )

    test_client = make_client(test_engine, username="colaborador", password="colab1234")
    yield test_client
    test_client.app.dependency_overrides.clear()


@pytest.fixture
def gerente_client(test_engine, client):
    with Session(test_engine) as session:
        create_test_user(
            session,
            full_name="Gerente Teste",
            cpf="44444444444",
            email="gerente@test.local",
            username="gerente",
            password="ger1234",
            profile=UserProfile.GERENTE,
        )

    test_client = make_client(test_engine, username="gerente", password="ger1234")
    yield test_client
    test_client.app.dependency_overrides.clear()


@pytest.fixture
def supervisor_client(test_engine, client):
    with Session(test_engine) as session:
        create_test_user(
            session,
            full_name="Supervisor Teste",
            cpf="55555555555",
            email="supervisor@test.local",
            username="supervisor",
            password="sup1234",
            profile=UserProfile.SUPERVISOR,
        )

    test_client = make_client(test_engine, username="supervisor", password="sup1234")
    yield test_client
    test_client.app.dependency_overrides.clear()


@pytest.fixture
def category(client: TestClient) -> dict:
    response = client.post(
        "/categories/",
        json={"name": "Eletrônicos", "slug": "eletronicos", "is_active": True},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def product(client: TestClient, category: dict) -> dict:
    response = client.post(
        "/products/",
        json={
            "name": "Mouse Gamer",
            "sku": "MOU-001",
            "sale_price": "50.00",
            "cost_price": "30.00",
            "category_id": category["id"],
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def stocked_product(client: TestClient, product: dict) -> dict:
    response = client.post(
        "/stock/move",
        json={
            "product_id": product["id"],
            "quantity": "20",
            "type": "E",
            "reason": "compra",
        },
    )
    assert response.status_code == 201
    return product
