from sqlmodel import Session, select

from models.company_registration import CompanyRegistrationRequest


class CompanyRegistrationRepository:
    @staticmethod
    def create(db: Session, request: CompanyRegistrationRequest) -> CompanyRegistrationRequest:
        db.add(request)
        db.flush()
        return request

    @staticmethod
    def find_by_id(db: Session, request_id: int) -> CompanyRegistrationRequest | None:
        return db.get(CompanyRegistrationRequest, request_id)

    @staticmethod
    def find_pending_by_document(db: Session, document: str) -> CompanyRegistrationRequest | None:
        stmt = select(CompanyRegistrationRequest).where(
            CompanyRegistrationRequest.document == document,
            CompanyRegistrationRequest.status == "pending",
        )
        return db.exec(stmt).first()

    @staticmethod
    def list_all(
        db: Session,
        *,
        status: str | None = None,
    ) -> list[CompanyRegistrationRequest]:
        stmt = select(CompanyRegistrationRequest).order_by(
            CompanyRegistrationRequest.created_at.desc()
        )
        if status:
            stmt = stmt.where(CompanyRegistrationRequest.status == status)
        return list(db.exec(stmt).all())

    @staticmethod
    def update(db: Session, request: CompanyRegistrationRequest) -> CompanyRegistrationRequest:
        db.add(request)
        db.flush()
        return request
