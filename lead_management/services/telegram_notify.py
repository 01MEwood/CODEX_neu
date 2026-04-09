"""Telegram-Benachrichtigung bei neuem Lead.

Schickt eine formatierte Nachricht in den Schreinerhelden-Chat
sobald ein neuer Lead reinkommt — egal über welchen Kanal.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from lead_management.config.settings import settings
from lead_management.models.lead import Lead

logger = logging.getLogger(__name__)

KANAL_EMOJI = {
    "whatsapp": "📱",
    "messenger": "💬",
    "email": "📧",
    "anruf": "📞",
    "kontaktformular": "📋",
    "voice_memo": "🎙️",
    "sonstige": "📌",
}


def _format_message(lead: Lead) -> str:
    emoji = KANAL_EMOJI.get(lead.kanal.value, "📌")
    lines = [
        f"{emoji} *Neuer Lead!*",
        f"",
        f"*Kanal:* {lead.kanal.value.replace('_', ' ').title()}",
    ]

    if lead.name:
        lines.append(f"*Name:* {lead.name}")
    if lead.telefon:
        lines.append(f"*Telefon:* {lead.telefon}")
    if lead.email:
        lines.append(f"*Email:* {lead.email}")
    if lead.nachricht:
        # Nachricht kürzen auf 200 Zeichen für Telegram
        msg = lead.nachricht[:200]
        if len(lead.nachricht) > 200:
            msg += "…"
        lines.append(f"*Nachricht:* {msg}")
    if lead.quelle:
        lines.append(f"*Quelle:* {lead.quelle}")
    if lead.zustaendig:
        lines.append(f"*Zuständig:* {lead.zustaendig}")

    lines.append(f"")
    lines.append(f"🆔 `{lead.id}`")
    lines.append(f"⏰ {lead.eingang.strftime('%d.%m.%Y %H:%M')}")

    return "\n".join(lines)


async def send_lead_notification(lead: Lead) -> bool:
    """Sendet Telegram-Nachricht für neuen Lead. Gibt True bei Erfolg zurück."""

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram nicht konfiguriert — Notification übersprungen")
        return False

    message = _format_message(lead)
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                },
            )
            resp.raise_for_status()
            logger.info("Telegram-Notification gesendet für %s", lead.id)
            return True
    except httpx.HTTPError as e:
        logger.error("Telegram-Notification fehlgeschlagen: %s", e)
        return False
