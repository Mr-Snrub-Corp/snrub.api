import os
from pathlib import Path
from uuid import UUID

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings

# Make sure the template directory exists
template_dir = Path(__file__).parent.parent / "templates" / "email"
os.makedirs(template_dir, exist_ok=True)

# Correct configuration for FastAPI-Mail 1.4.2
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=template_dir,
    SUPPRESS_SEND=settings.MAIL_SUPPRESS_SEND,
)

# Module-level FastMail instance for testability
fm = FastMail(conf)


async def send_password_reset_email(email: str, token: UUID):
    """Send password reset email with token using Jinja2 template"""
    reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"

    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        template_body={"reset_link": reset_link},
        subtype=MessageType.html,
    )

    await fm.send_message(message, template_name="password_reset.html")
