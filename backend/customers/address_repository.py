from sqlmodel import Session, select

from customers.models import Customer, CustomerAddress


class CustomerAddressRepository:
    # Optional business fields that a client may explicitly clear via update().
    _NULLABLE_FIELDS = {"complement", "ibge_code"}

    @staticmethod
    def find_by_customer(db: Session, customer_id: int, company_id: int) -> list[CustomerAddress]:
        stmt = (
            select(CustomerAddress)
            .join(Customer, CustomerAddress.customer_id == Customer.id)
            .where(
                CustomerAddress.customer_id == customer_id,
                Customer.company_id == company_id,
            )
        )
        return list(db.exec(stmt).all())

    @staticmethod
    def find_by_id(db: Session, address_id: int, company_id: int) -> CustomerAddress | None:
        stmt = (
            select(CustomerAddress)
            .join(Customer, CustomerAddress.customer_id == Customer.id)
            .where(CustomerAddress.id == address_id, Customer.company_id == company_id)
        )
        return db.exec(stmt).first()

    @staticmethod
    def create(db: Session, address: CustomerAddress) -> CustomerAddress:
        db.add(address)
        db.flush()
        return address

    @staticmethod
    def update(db: Session, address_id: int, company_id: int, **fields) -> CustomerAddress | None:
        address = CustomerAddressRepository.find_by_id(db, address_id, company_id)
        if not address:
            return None

        for field_name, field_value in fields.items():
            if field_value is not None or field_name in CustomerAddressRepository._NULLABLE_FIELDS:
                setattr(address, field_name, field_value)

        db.add(address)
        db.flush()
        return address

    @staticmethod
    def delete(db: Session, address_id: int, company_id: int) -> bool:
        address = CustomerAddressRepository.find_by_id(db, address_id, company_id)
        if not address:
            return False

        db.delete(address)
        db.flush()
        return True
