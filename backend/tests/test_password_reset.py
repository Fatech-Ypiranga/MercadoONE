from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from auth.models import PasswordResetToken
from database.seed import SEED_COMPANY_DOCUMENT
from shared import mailer


def _capture_emails(monkeypatch) -> list[dict]:
    sent: list[dict] = []

    def fake_send(to, subject, body):
        sent.append({"to": to, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(mailer, "send_email", fake_send)
    return sent


def _token_from(body: str) -> str:
    return body.split("token=")[1].split()[0]


def _request(client, email="admin@pyerp.local", document=SEED_COMPANY_DOCUMENT):
    return client.post(
        "/auth/password/request", json={"email": email, "company_document": document}
    )


def test_request_sends_email_and_confirm_changes_password(client, test_engine, monkeypatch):
    sent = _capture_emails(monkeypatch)
    response = _request(client)
    assert response.status_code == 202
    assert len(sent) == 1
    assert sent[0]["to"] == "admin@pyerp.local"
    token = _token_from(sent[0]["body"])

    assert client.post("/auth/password/check", json={"token": token}).json() == {"valid": True}
    confirm = client.post(
        "/auth/password/confirm", json={"token": token, "new_password": "NovaSenha123"}
    )
    assert confirm.status_code == 204

    login = client.post(
        "/auth/login",
        json={
            "login": "admin@pyerp.local",
            "password": "NovaSenha123",
            "company_document": SEED_COMPANY_DOCUMENT,
        },
    )
    assert login.status_code == 200

    # single use
    assert client.post("/auth/password/check", json={"token": token}).json() == {"valid": False}
    again = client.post(
        "/auth/password/confirm", json={"token": token, "new_password": "OutraSenha123"}
    )
    assert again.status_code == 422


def test_unknown_email_or_company_gets_same_answer_and_no_email(client, monkeypatch):
    sent = _capture_emails(monkeypatch)
    known = _request(client)
    unknown_email = _request(client, email="nobody@example.com")
    unknown_company = _request(client, document="11222333000181")
    assert known.status_code == unknown_email.status_code == unknown_company.status_code == 202
    assert known.json() == unknown_email.json() == unknown_company.json()
    assert len(sent) == 1  # only the real account


def test_resend_cooldown_and_new_link_invalidates_old(client, test_engine, monkeypatch):
    sent = _capture_emails(monkeypatch)
    _request(client)
    _request(client)  # within cooldown: no second email
    assert len(sent) == 1

    with Session(test_engine) as session:
        for record in session.exec(select(PasswordResetToken)).all():
            record.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            session.add(record)
        session.commit()

    _request(client)
    assert len(sent) == 2
    old, new = _token_from(sent[0]["body"]), _token_from(sent[1]["body"])
    assert client.post("/auth/password/check", json={"token": old}).json() == {"valid": False}
    assert client.post("/auth/password/check", json={"token": new}).json() == {"valid": True}


def test_expired_token_is_rejected(client, test_engine, monkeypatch):
    sent = _capture_emails(monkeypatch)
    _request(client)
    token = _token_from(sent[0]["body"])
    with Session(test_engine) as session:
        record = session.exec(select(PasswordResetToken)).first()
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.add(record)
        session.commit()
    assert client.post("/auth/password/check", json={"token": token}).json() == {"valid": False}
    response = client.post(
        "/auth/password/confirm", json={"token": token, "new_password": "NovaSenha123"}
    )
    assert response.status_code == 422


def test_confirm_signs_out_existing_sessions(client, monkeypatch):
    sent = _capture_emails(monkeypatch)
    assert client.get("/auth/me").status_code == 200
    _request(client)
    client.post(
        "/auth/password/confirm",
        json={"token": _token_from(sent[0]["body"]), "new_password": "NovaSenha123"},
    )
    assert client.get("/auth/me").status_code == 401


def test_smtp_not_configured_does_not_send(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert mailer.send_email("a@b.com", "x", "y") is False


def test_smtp_send_uses_starttls_and_login(monkeypatch):
    calls: list[tuple] = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, context=None):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user, password))

        def send_message(self, message):
            calls.append(("send", message["To"], message["From"]))

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "mailer@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)

    assert mailer.send_email("user@example.com", "Assunto", "Corpo") is True
    assert calls == [
        ("connect", "smtp.example.com", 587),
        ("starttls",),
        ("login", "mailer@example.com", "secret"),
        ("send", "user@example.com", "mailer@example.com"),
    ]
