# Re-export for convenience; StoreRepository lives alongside CompanyRepository.
from repositories.company_repository import StoreRepository

__all__ = ["StoreRepository"]
