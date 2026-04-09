"""Automatische Erstantwort — WhatsApp + Email.

"Danke, wir melden uns innerhalb von 24h" — sofort, automatisch.
Der Kunde weiß: seine Anfrage ist angekommen.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

import httpx

from lead_management.config.settings import settings
from lead_management.models.lead import Kanal, Lead

logger = logging.getLogger(__name__)


# --- Templates ---

ERSTANTWORT_TEXT = (
    "Vielen Dank für Ihre Anfrage! 🙏\n\n"
    "Wir haben Ihre Nachricht erhalten und melden uns "
    "innerhalb von 24 Stunden bei Ihnen.\n\n"
    "Ihr Team von Schreinerhelden"
)

ERSTANTWORT_EMAIL_SUBJECT = "Ihre Anfrage bei Schreinerhelden — wir melden uns!"

ERSTANTWORT_EMAIL_HTML = """\
<p>Guten Tag{name_greeting},</p>

<p>vielen Dank für Ihre Anfrage!</p>

<p>Wir haben Ihre Nachricht erhalten und melden uns
<strong>innerhalb von 24 Stunden</strong> bei Ihnen.</p>

<p>Mit freundlichen Grüßen<br>
Ihr Team von <strong>Schreinerhelden</strong></p>
"""


async def send_auto_reply(lead: Lead) -> bool:
    """Versucht eine Erstantwort über den passenden Kanal zu senden."""

    if lead.erstantwort_gesendet:
        return False

    if lead.kanal == Kanal.WHATSAPP and lead.telefon:
        return await _reply_whatsapp(lead)
    elif lead.kanal == Kanal.EMAIL and lead.email:
        return await _reply_email(lead)
    # Messenger-Antwort läuft über n8n direkt (Meta API erfordert Page-Token)
    return False


async def _reply_whatsapp(lead: Lead) -> bool:
    """WhatsApp-Erstantwort über die Business API."""

    if not settings.whatsapp_token or not settings.whatsapp_phone_id:
        logger.warning("WhatsApp API nicht konfiguriert")
        return False

    url = f"https://graph.facebook.com/v19.0/{settings.whatsapp_phone_id}/messages"

    # Telefonnummer bereinigen (nur Ziffern + Ländervorwahl)
    phone = lead.telefon.replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0"):
        phone = "49" + phone[1:]  # Deutsche Nummer → internationales Format

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": ERSTANTWORT_TEXT},
                },
            )
            resp.raise_for_status()
            logger.info("WhatsApp-Erstantwort gesendet an %s", lead.telefon)
            return True
    except httpx.HTTPError as e:
        logger.error("WhatsApp-Erstantwort fehlgeschlagen: %s", e)
        return False


async def _reply_email(lead: Lead) -> bool:
    """Email-Erstantwort über SMTP."""

    if not settings.smtp_host or not settings.smtp_user:
        logger.warning("SMTP nicht konfiguriert")
        return False

    name_greeting = f" {lead.name}" if lead.name else ""
    html = ERSTANTWORT_EMAIL_HTML.format(name_greeting=name_greeting)

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = ERSTANTWORT_EMAIL_SUBJECT
    msg["From"] = settings.smtp_from
    msg["To"] = lead.email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("Email-Erstantwort gesendet an %s", lead.email)
        return True
    except Exception as e:
        logger.error("Email-Erstantwort fehlgeschlagen: %s", e)
        return False
