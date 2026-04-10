"""Automatische Erstantwort + Buchungsseite.

Zwei Flows:
1. Bestandskunde → "Danke, wir melden uns innerhalb von 24h"
2. Neukunde → "Danke + hier können Sie direkt einen Termin buchen"
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

BUCHUNG_TEXT = (
    "Vielen Dank für Ihre Anfrage! 🙏\n\n"
    "Wir haben Ihre Nachricht erhalten und melden uns "
    "innerhalb von 24 Stunden bei Ihnen.\n\n"
    "Wenn Sie möchten, können Sie auch direkt einen "
    "Beratungstermin buchen:\n"
    "{booking_url}\n\n"
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

BUCHUNG_EMAIL_HTML = """\
<p>Guten Tag{name_greeting},</p>

<p>vielen Dank für Ihre Anfrage!</p>

<p>Wir haben Ihre Nachricht erhalten und melden uns
<strong>innerhalb von 24 Stunden</strong> bei Ihnen.</p>

<p>Wenn Sie möchten, können Sie auch direkt einen
<strong>kostenlosen Beratungstermin</strong> buchen:</p>

<p><a href="{booking_url}"
   style="display:inline-block;padding:12px 24px;background:#2563eb;color:#fff;
          text-decoration:none;border-radius:6px;font-weight:bold;">
   Termin buchen
</a></p>

<p>Mit freundlichen Grüßen<br>
Ihr Team von <strong>Schreinerhelden</strong></p>
"""


async def send_auto_reply(lead: Lead) -> bool:
    """Versucht eine Erstantwort über den passenden Kanal zu senden."""

    if lead.erstantwort_gesendet:
        return False

    if lead.kanal == Kanal.WHATSAPP and lead.telefon:
        return await _reply_whatsapp(lead, ERSTANTWORT_TEXT)
    elif lead.kanal == Kanal.EMAIL and lead.email:
        return await _reply_email(lead, ERSTANTWORT_EMAIL_HTML)
    return False


async def send_booking_link(lead: Lead) -> bool:
    """Buchungsseite an Neukunden senden.

    Wird nur bei Prospects aufgerufen die kein Match in Freund CRM haben.
    """
    if not settings.booking_url:
        logger.warning("Buchungs-URL nicht konfiguriert — übersprungen")
        return False

    if lead.kanal == Kanal.WHATSAPP and lead.telefon:
        text = BUCHUNG_TEXT.format(booking_url=settings.booking_url)
        return await _reply_whatsapp(lead, text)
    elif lead.kanal in (Kanal.EMAIL, Kanal.KONTAKTFORMULAR) and lead.email:
        html = BUCHUNG_EMAIL_HTML.format(
            name_greeting=f" {lead.name}" if lead.name else "",
            booking_url=settings.booking_url,
        )
        return await _reply_email(lead, html)
    return False


async def _reply_whatsapp(lead: Lead, text: str) -> bool:
    """WhatsApp-Nachricht über die Business API senden."""

    if not settings.whatsapp_token or not settings.whatsapp_phone_id:
        logger.warning("WhatsApp API nicht konfiguriert")
        return False

    url = f"https://graph.facebook.com/v19.0/{settings.whatsapp_phone_id}/messages"

    phone = lead.telefon.replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0"):
        phone = "49" + phone[1:]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": text},
                },
            )
            resp.raise_for_status()
            logger.info("WhatsApp-Nachricht gesendet an %s", lead.telefon)
            return True
    except httpx.HTTPError as e:
        logger.error("WhatsApp-Nachricht fehlgeschlagen: %s", e)
        return False


async def _reply_email(lead: Lead, html: str) -> bool:
    """Email über SMTP senden."""

    if not settings.smtp_host or not settings.smtp_user:
        logger.warning("SMTP nicht konfiguriert")
        return False

    name_greeting = f" {lead.name}" if lead.name else ""
    html = html.format(name_greeting=name_greeting, booking_url=settings.booking_url)

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = ERSTANTWORT_EMAIL_SUBJECT
    msg["From"] = settings.smtp_from
    msg["To"] = lead.email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("Email gesendet an %s", lead.email)
        return True
    except Exception as e:
        logger.error("Email fehlgeschlagen: %s", e)
        return False
