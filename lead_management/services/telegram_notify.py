"""Telegram-Benachrichtigung bei neuem Lead.

Schickt eine formatierte Nachricht in den Schreinerhelden-Chat
sobald ein neuer Lead reinkommt — egal über welchen Kanal.

Zeigt zusätzlich an ob der Lead einem Bestandskunden zugeordnet wurde,
ein Neukunde ist, oder ob ein möglicher Match existiert.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from lead_management.config.settings import settings
from lead_management.models.kunde import MatchKonfidenz, MatchResult
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

KONFIDENZ_EMOJI = {
    MatchKonfidenz.EXAKT: "✅",
    MatchKonfidenz.HOCH: "✅",
    MatchKonfidenz.MITTEL: "🟡",
    MatchKonfidenz.KEIN: "🆕",
}


def _format_message(lead: Lead, match: Optional[MatchResult] = None) -> str:
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
        msg = lead.nachricht[:200]
        if len(lead.nachricht) > 200:
            msg += "…"
        lines.append(f"*Nachricht:* {msg}")
    if lead.quelle:
        lines.append(f"*Quelle:* {lead.quelle}")

    # ── Kunden-Zuordnung ──
    if match and match.kunde:
        k_emoji = KONFIDENZ_EMOJI.get(match.konfidenz, "❓")
        lines.append(f"")

        if match.konfidenz in (MatchKonfidenz.EXAKT, MatchKonfidenz.HOCH):
            lines.append(f"{k_emoji} *BESTANDSKUNDE erkannt*")
            lines.append(f"*Kunde:* {match.kunde.name or 'Unbekannt'}")
            if match.kunde.freund_crm_id:
                lines.append(f"*Freund CRM:* #{match.kunde.freund_crm_id}")
            lines.append(f"*Match:* {match.match_grund}")
            # Bisherige Interaktionen zählen
            n = len(match.kunde.kundenmappe)
            if n > 0:
                lines.append(f"*Historie:* {n} Einträge in Kundenmappe")
        elif match.konfidenz == MatchKonfidenz.MITTEL:
            lines.append(f"{k_emoji} *Möglicher Match — bitte prüfen!*")
            lines.append(f"*Vorschlag:* {match.match_grund}")
        else:
            lines.append(f"{k_emoji} *NEUKUNDE — kein Match gefunden*")
            if match.kunde.buchung_angeboten:
                lines.append("📅 Buchungsseite wurde gesendet")

    if lead.zustaendig:
        lines.append(f"*Zuständig:* {lead.zustaendig}")

    lines.append(f"")
    lines.append(f"🆔 `{lead.id}`")
    if match and match.kunde:
        lines.append(f"👤 `{match.kunde.id}`")
    lines.append(f"⏰ {lead.eingang.strftime('%d.%m.%Y %H:%M')}")

    return "\n".join(lines)


async def _send_telegram(message: str) -> bool:
    """Nachricht an Telegram senden."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram nicht konfiguriert — Notification übersprungen")
        return False

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
            logger.info("Telegram-Notification gesendet")
            return True
    except httpx.HTTPError as e:
        logger.error("Telegram-Notification fehlgeschlagen: %s", e)
        return False


async def send_lead_notification(lead: Lead) -> bool:
    """Sendet Telegram-Nachricht für neuen Lead (ohne Match-Info)."""
    message = _format_message(lead)
    return await _send_telegram(message)


async def send_lead_notification_with_match(
    lead: Lead, match: MatchResult
) -> bool:
    """Sendet Telegram-Nachricht mit Kunden-Zuordnungs-Info."""
    message = _format_message(lead, match)
    return await _send_telegram(message)
