import secrets

from organization.models import Company
from organization.repository import CompanyRepository
from services.pdv_credentials import generate_pdv_id, is_weak_pdv_id
from shared.identity.security import hash_password, hash_pdv_pin, verify_pdv_pin


def test_weak_pdv_ids_are_rejected():
    assert is_weak_pdv_id("000000")
    assert is_weak_pdv_id("123456")
    assert is_weak_pdv_id("111111")
    assert not is_weak_pdv_id("482917")


def test_generate_pdv_id_is_six_digits_and_not_sequential(db_session):
    company = CompanyRepository.create(
        db_session,
        Company(
            legal_name="PDV Random Co",
            document="11222333000181",
            is_active=True,
        ),
    )
    db_session.commit()

    codes = [generate_pdv_id(db_session, company.id) for _ in range(8)]

    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert all(not is_weak_pdv_id(code) for code in codes)
    # Sequential allocator would yield 000001..000008 for an empty company.
    assert codes != [f"{i:06d}" for i in range(1, 9)]


def test_generate_pdv_id_skips_weak_codes(monkeypatch, db_session):
    company = CompanyRepository.create(
        db_session,
        Company(
            legal_name="PDV Weak Skip Co",
            document="11222333000182",
            is_active=True,
        ),
    )
    db_session.commit()

    # 0 -> 000000 (weak), 123456 (weak), 482917 (ok)
    values = iter([0, 123456, 482917])
    monkeypatch.setattr(secrets, "randbelow", lambda _n: next(values))

    assert generate_pdv_id(db_session, company.id) == "482917"


def test_pdv_pin_hash_is_argon2id():
    pin = "482917365018"
    hashed = hash_pdv_pin(pin)

    assert hashed.startswith("$argon2id$")
    assert not hashed.startswith("$2b$")
    assert verify_pdv_pin(pin, hashed) is True
    assert verify_pdv_pin("000000000000", hashed) is False
    assert verify_pdv_pin(pin, hash_password(pin)) is False
    assert verify_pdv_pin(pin, "not-a-valid-hash") is False
