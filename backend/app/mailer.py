import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger("finanzas.mail")


def _deliver(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def send_email(to: str, subject: str, body: str) -> None:
    """Envía un correo. Nunca lanza: se usa en segundo plano y un fallo no debe romper la petición."""
    if not settings.email_enabled:
        # En desarrollo el enlace se muestra en la consola. En producción NO: el log no debe guardar tokens.
        if not settings.cookie_secure:
            log.warning("[correo no configurado] Para %s: %s\n%s", to, subject, body)
        return
    try:
        _deliver(to, subject, body)
    except Exception:
        log.exception("No se pudo enviar el correo '%s'", subject)
