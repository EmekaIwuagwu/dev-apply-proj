import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config import settings

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))


async def send_success_email(
    user_email: str,
    user_full_name: str,
    user_salutation: str,
    job_title: str,
    company_name: str,
    job_url: str,
    match_score: float,
    applied_at: str,
    cover_note: str,
) -> None:
    try:
        html = _jinja.get_template("application_success.html").render(
            salutation=user_salutation,
            full_name=user_full_name,
            job_title=job_title,
            company_name=company_name,
            job_url=job_url,
            match_score=int(match_score * 100),
            applied_at=applied_at,
            cover_note=cover_note,
        )
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Application submitted to {company_name} — DevApply"
        msg["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        msg["To"] = user_email
        msg.attach(MIMEText(html, "html"))

        await asyncio.to_thread(_smtp_send, msg, user_email)
        logger.info(f"Email sent to {user_email} ({company_name})")
    except Exception as e:
        logger.error(f"Email failed for {user_email}: {e}")


def _smtp_send(msg: MIMEMultipart, to: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured — skipping email")
        return
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as s:
        s.ehlo()
        s.starttls()
        s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        s.sendmail(settings.FROM_EMAIL, to, msg.as_string())
