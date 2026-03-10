import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
import asyncio
import logging
from config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Assumes templates are in backend/agent/notifications/templates
        self.jinja_env = Environment(
            loader=FileSystemLoader("agent/notifications/templates")
        )

    async def send_application_success(
        self,
        user_email: str,
        user_full_name: str,
        user_salutation: str,
        job_title: str,
        company_name: str,
        job_url: str,
        match_score: float,
        applied_at: str,
        cover_note: str,
    ):
        """
        Sends an HTML email to the user confirming their application
        was submitted by the DevApply AI Agent.
        """
        try:
            template = self.jinja_env.get_template("application_success.html")
            html_body = template.render(
                salutation=user_salutation,
                full_name=user_full_name,
                job_title=job_title,
                company_name=company_name,
                job_url=job_url,
                match_score=int(match_score * 100),
                applied_at=applied_at,
                cover_note=cover_note,
                support_email=settings.FROM_EMAIL,
            )

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Your application to {company_name} has been submitted — DevApply"
            msg["From"]    = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            msg["To"]      = user_email

            msg.attach(MIMEText(html_body, "html"))

            # Send in a separate thread to avoid blocking the event loop
            await asyncio.to_thread(self._send_smtp, msg, user_email)
            logger.info(f"Success email sent to {user_email} for {company_name}")

        except Exception as e:
            logger.error(f"Failed to send success email to {user_email}: {str(e)}")
            # Do not re-raise; email failure shouldn't stop the agent

    def _send_smtp(self, msg: MIMEMultipart, to_email: str):
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            logger.warning("SMTP configuration missing; skipping email send")
            return

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
