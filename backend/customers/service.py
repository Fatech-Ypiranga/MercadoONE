from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from customers.address_repository import CustomerAddressRepository
from customers.models import (
    Customer,
    CustomerAddress,
    CustomerAddressCreate,
    CustomerAddressUpdate,
    CustomerCreate,
    CustomerUpdate,
)
from customers.repository import CustomerRepository
from shared.audit import AuditService
from shared.exceptions import BusinessRuleException, ResourceNotFoundException, ValidationError
from utils.cnpj import require_valid_cnpj
from utils.cpf import require_valid_cpf
from utils.enums import AuditAction, CustomerType


class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_document(*, document: str, customer_type: CustomerType) -> str:
        if customer_type == CustomerType.FISICA:
            return require_valid_cpf(document, entity="Customer document")
        return require_valid_cnpj(document, entity="Customer document")

    def list_customers(self, company_id: int) -> list[Customer]:
        return CustomerRepository.find_all(self.db, company_id)

    def get_by_id(self, customer_id: int, company_id: int) -> Customer:
        stmt = (
            select(Customer)
            .where(Customer.id == customer_id, Customer.company_id == company_id)
            .options(selectinload(Customer.addresses))
        )
        customer = self.db.exec(stmt).first()
        if not customer:
            raise ResourceNotFoundException(f"Customer {customer_id} was not found.")
        return customer

    def create(self, customer_in: CustomerCreate, *, company_id: int, actor_id: int) -> Customer:
        try:
            customer_data = customer_in.model_dump(exclude={"addresses"})
            customer_data["document"] = self._normalize_document(
                document=customer_data["document"],
                customer_type=customer_data["customer_type"],
            )
            customer_data["company_id"] = company_id
            customer = Customer.model_validate(customer_data)
            customer.created_by = actor_id
            customer.updated_by = actor_id
            CustomerRepository.create(self.db, customer)
            self.db.flush()

            for address_in in customer_in.addresses:
                address = CustomerAddress(customer_id=customer.id, **address_in.model_dump())
                address.created_by = actor_id
                address.updated_by = actor_id
                CustomerAddressRepository.create(self.db, address)

            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.CREATE,
                entity_type="customer",
                entity_id=customer.id,
            )
            self.db.commit()
            return self.get_by_id(customer.id, company_id)
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error creating customer: {exc}") from exc

    def update(
        self,
        customer_id: int,
        customer_in: CustomerUpdate,
        *,
        company_id: int,
        actor_id: int,
    ) -> Customer:
        update_data = customer_in.model_dump(exclude_unset=True)
        try:
            if "document" in update_data or "customer_type" in update_data:
                current = CustomerRepository.find_by_id(self.db, customer_id, company_id)
                if not current:
                    raise ResourceNotFoundException(f"Customer {customer_id} was not found.")
                customer_type = update_data.get("customer_type", current.customer_type)
                document = update_data.get("document", current.document)
                update_data["document"] = self._normalize_document(
                    document=document,
                    customer_type=customer_type,
                )

            customer = CustomerRepository.update(
                self.db,
                customer_id,
                company_id,
                **update_data,
            )
            if not customer:
                raise ResourceNotFoundException(f"Customer {customer_id} was not found.")

            customer.updated_by = actor_id
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.UPDATE,
                entity_type="customer",
                entity_id=customer_id,
            )
            self.db.commit()
            self.db.refresh(customer)
            return customer
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error updating customer: {exc}") from exc

    def delete(self, customer_id: int, *, company_id: int, actor_id: int) -> None:
        try:
            deleted = CustomerRepository.delete(self.db, customer_id, company_id)
            if not deleted:
                raise ResourceNotFoundException(f"Customer {customer_id} was not found.")

            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.DELETE,
                entity_type="customer",
                entity_id=customer_id,
            )
            self.db.commit()
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error deleting customer: {exc}") from exc

    def create_address(
        self,
        customer_id: int,
        address_in: CustomerAddressCreate,
        *,
        company_id: int,
        actor_id: int,
    ) -> CustomerAddress:
        if not CustomerRepository.find_by_id(self.db, customer_id, company_id):
            raise ResourceNotFoundException(f"Customer {customer_id} was not found.")

        try:
            address = CustomerAddress(customer_id=customer_id, **address_in.model_dump())
            address.created_by = actor_id
            address.updated_by = actor_id
            CustomerAddressRepository.create(self.db, address)
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.CREATE,
                entity_type="customer_address",
                entity_id=address.id,
            )
            self.db.commit()
            self.db.refresh(address)
            return address
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error creating customer address: {exc}") from exc

    def update_address(
        self,
        customer_id: int,
        address_id: int,
        address_in: CustomerAddressUpdate,
        *,
        company_id: int,
        actor_id: int,
    ) -> CustomerAddress:
        address = CustomerAddressRepository.find_by_id(self.db, address_id, company_id)
        if not address or address.customer_id != customer_id:
            raise ResourceNotFoundException(
                f"Address {address_id} was not found for customer {customer_id}."
            )

        try:
            address = CustomerAddressRepository.update(
                self.db, address_id, company_id, **address_in.model_dump(exclude_unset=True)
            )
            address.updated_by = actor_id
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.UPDATE,
                entity_type="customer_address",
                entity_id=address_id,
            )
            self.db.commit()
            self.db.refresh(address)
            return address
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error updating customer address: {exc}") from exc

    def delete_address(
        self, customer_id: int, address_id: int, *, company_id: int, actor_id: int
    ) -> None:
        address = CustomerAddressRepository.find_by_id(self.db, address_id, company_id)
        if not address or address.customer_id != customer_id:
            raise ResourceNotFoundException(
                f"Address {address_id} was not found for customer {customer_id}."
            )

        try:
            CustomerAddressRepository.delete(self.db, address_id, company_id)
            AuditService(self.db).log(
                user_id=actor_id,
                company_id=company_id,
                action=AuditAction.DELETE,
                entity_type="customer_address",
                entity_id=address_id,
            )
            self.db.commit()
        except (ResourceNotFoundException, ValidationError):
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise BusinessRuleException(f"Error deleting customer address: {exc}") from exc
