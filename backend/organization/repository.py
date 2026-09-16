from sqlalchemy import func
from sqlmodel import Session, select

from organization.models import Branch, Company, Store
from purchases.models import PurchaseOrder
from sales.models import Sale
from stock.models import StockMovement
from users.models import User


class CompanyRepository:
    @staticmethod
    def find_by_id(db: Session, company_id: int) -> Company | None:
        return db.get(Company, company_id)

    @staticmethod
    def find_by_document(db: Session, document: str) -> Company | None:
        stmt = select(Company).where(Company.document == document)
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, company: Company) -> Company:
        db.add(company)
        db.flush()
        return company


class BranchRepository:
    @staticmethod
    def find_all_for_company(db: Session, company_id: int) -> list[Branch]:
        stmt = select(Branch).where(Branch.company_id == company_id).order_by(Branch.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id_for_company(db: Session, branch_id: int, company_id: int) -> Branch | None:
        stmt = select(Branch).where(Branch.id == branch_id, Branch.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_code(db: Session, company_id: int, code: str) -> Branch | None:
        stmt = select(Branch).where(Branch.company_id == company_id, Branch.code == code)
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, branch: Branch) -> Branch:
        db.add(branch)
        db.flush()
        return branch

    @staticmethod
    def update(db: Session, branch: Branch) -> Branch:
        db.add(branch)
        db.flush()
        return branch

    @staticmethod
    def count_dependencies(db: Session, branch_id: int) -> int:
        stores = db.exec(
            select(func.count()).select_from(Store).where(Store.branch_id == branch_id)
        ).one()
        users = db.exec(
            select(func.count()).select_from(User).where(User.default_branch_id == branch_id)
        ).one()
        return int(stores) + int(users)

    @staticmethod
    def delete(db: Session, branch: Branch) -> None:
        db.delete(branch)
        db.flush()


class StoreRepository:
    @staticmethod
    def find_all_for_company(db: Session, company_id: int) -> list[Store]:
        stmt = select(Store).where(Store.company_id == company_id).order_by(Store.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id_for_company(db: Session, store_id: int, company_id: int) -> Store | None:
        stmt = select(Store).where(Store.id == store_id, Store.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_code(db: Session, company_id: int, code: str) -> Store | None:
        stmt = select(Store).where(Store.company_id == company_id, Store.code == code)
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, store: Store) -> Store:
        db.add(store)
        db.flush()
        return store

    @staticmethod
    def update(db: Session, store: Store) -> Store:
        db.add(store)
        db.flush()
        return store

    @staticmethod
    def count_dependencies(db: Session, store_id: int) -> int:
        sales = db.exec(
            select(func.count()).select_from(Sale).where(Sale.store_id == store_id)
        ).one()
        purchases = db.exec(
            select(func.count())
            .select_from(PurchaseOrder)
            .where(PurchaseOrder.store_id == store_id)
        ).one()
        movements = db.exec(
            select(func.count())
            .select_from(StockMovement)
            .where(StockMovement.store_id == store_id)
        ).one()
        users = db.exec(
            select(func.count()).select_from(User).where(User.default_store_id == store_id)
        ).one()
        return int(sales) + int(purchases) + int(movements) + int(users)

    @staticmethod
    def delete(db: Session, store: Store) -> None:
        db.delete(store)
        db.flush()
