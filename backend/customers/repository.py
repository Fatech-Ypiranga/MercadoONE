from sqlmodel import Session, select

from customers.models import Customer


class CustomerRepository:
    # Optional business fields that a client may explicitly clear via update().
    _NULLABLE_FIELDS = {"trade_name", "email", "phone", "state_registration"}

    @staticmethod
    def find_all(db: Session, company_id: int) -> list[Customer]:
        stmt = select(Customer).where(Customer.company_id == company_id).order_by(Customer.name)
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, customer_id: int, company_id: int) -> Customer | None:
        stmt = select(Customer).where(Customer.id == customer_id, Customer.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def find_by_email(db: Session, email: str, company_id: int) -> Customer | None:
        stmt = select(Customer).where(Customer.email == email, Customer.company_id == company_id)
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, customer: Customer) -> Customer:
        db.add(customer)
        db.flush()
        return customer

    @staticmethod
    def update(db: Session, customer_id: int, company_id: int, **fields) -> Customer | None:
        customer = CustomerRepository.find_by_id(db, customer_id, company_id)
        if not customer:
            return None

        for field_name, field_value in fields.items():
            if field_value is not None or field_name in CustomerRepository._NULLABLE_FIELDS:
                setattr(customer, field_name, field_value)

        db.add(customer)
        db.flush()
        return customer

    @staticmethod
    def delete(db: Session, customer_id: int, company_id: int) -> bool:
        customer = CustomerRepository.find_by_id(db, customer_id, company_id)
        if not customer:
            return False

        db.delete(customer)
        db.flush()
        return True
