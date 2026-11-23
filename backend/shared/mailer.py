"""Minimal SMTP sender configured through environment variables.

SMTP_HOST (required to send), SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD,
SMTP_FROM (defaults to SMTP_USER), SMTP_STARTTLS (true), SMTP_SSL (false).
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST", "").strip())


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns False (without raising) when SMTP is not configured."""
    if not smtp_configured():
        logger.warning("SMTP_HOST is not set; email to the user was not sent.")
        return False

    host = os.environ["SMTP_HOST"].strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", "").strip() or user
    if not sender:
        logger.warning("SMTP_FROM/SMTP_USER is not set; email was not sent.")
        return False

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    if _flag("SMTP_SSL", False):
        client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
    else:
        client = smtplib.SMTP(host, port, timeout=15)
    with client as smtp:
        if not _flag("SMTP_SSL", False) and _flag("SMTP_STARTTLS", True):
            smtp.starttls(context=context)
        if user:
            smtp.login(user, password)
        smtp.send_message(message)
    return True
