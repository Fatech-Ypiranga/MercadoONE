from sqlalchemy import func, update
from sqlmodel import Session, select

from models.audit_log import AuditLog
from models.category import Category
from models.company import Company
from models.customer import Customer, CustomerAddress
from models.product import Product
from models.purchase import PurchaseOrder
from models.sale import Sale
from models.stock_movement import StockMovement
from models.supplier import Supplier
from models.user import User
from utils.enums import UserProfile


class UserRepository:
    @staticmethod
    def find_all(
        db: Session,
        *,
        company_id: int,
        include_inactive: bool = False,
        q: str | None = None,
        profile: UserProfile | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        stmt = select(User).where(User.company_id == company_id).order_by(User.full_name)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        elif not include_inactive:
            stmt = stmt.where(User.is_active == True)  # noqa: E712
        if profile is not None:
            stmt = stmt.where(User.profile == profile)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                (User.full_name.ilike(pattern))
                | (User.email.ilike(pattern))
                | (User.username.ilike(pattern))
                | (User.cpf.ilike(pattern))
                | (User.pdv_id.ilike(pattern))
            )
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, user_id: int, *, company_id: int | None = None) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if company_id is not None:
            stmt = stmt.where(User.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_email(db: Session, email: str, *, company_id: int | None = None) -> User | None:
        stmt = select(User).where(User.email == email)
        if company_id is not None:
            stmt = stmt.where(User.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_username(
        db: Session, username: str, *, company_id: int | None = None
    ) -> User | None:
        stmt = select(User).where(User.username == username)
        if company_id is not None:
            stmt = stmt.where(User.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_cpf(db: Session, cpf: str, *, company_id: int | None = None) -> User | None:
        stmt = select(User).where(User.cpf == cpf)
        if company_id is not None:
            stmt = stmt.where(User.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_pdv_id(db: Session, pdv_id: str, *, company_id: int) -> User | None:
        stmt = select(User).where(User.company_id == company_id, User.pdv_id == pdv_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_login(db: Session, login: str, *, company_id: int | None = None) -> User | None:
        user = UserRepository.find_by_email(db, login, company_id=company_id)
        if user:
            return user
        return UserRepository.find_by_username(db, login, company_id=company_id)

    @staticmethod
    def create(db: Session, user: User) -> User:
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def count_required_refs(db: Session, user_id: int) -> int:
        purchases = db.exec(
            select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.user_id == user_id)
        ).one()
        return int(purchases)

    @staticmethod
    def detach_optional_refs(db: Session, user_id: int) -> None:
        """Nullify nullable FKs so the user row can be hard-deleted."""
        nullable_refs: list[tuple] = [
            (AuditLog, "user_id"),
            (Sale, "user_id"),
            (Sale, "created_by"),
            (Sale, "updated_by"),
            (PurchaseOrder, "created_by"),
            (PurchaseOrder, "updated_by"),
            (StockMovement, "created_by"),
            (StockMovement, "updated_by"),
            (Product, "created_by"),
            (Product, "updated_by"),
            (Category, "created_by"),
            (Category, "updated_by"),
            (Customer, "created_by"),
            (Customer, "updated_by"),
            (CustomerAddress, "created_by"),
            (CustomerAddress, "updated_by"),
            (Supplier, "created_by"),
            (Supplier, "updated_by"),
            (Company, "created_by"),
            (Company, "updated_by"),
            (User, "created_by"),
            (User, "updated_by"),
        ]
        for model, column_name in nullable_refs:
            if not hasattr(model, column_name):
                continue
            column = getattr(model, column_name)
            db.execute(update(model).where(column == user_id).values(**{column_name: None}))
        db.flush()

    @staticmethod
    def delete(db: Session, user_id: int, *, company_id: int) -> bool:
        user = UserRepository.find_by_id(db, user_id, company_id=company_id)
        if not user:
            return False
        db.delete(user)
        db.flush()
        return True
