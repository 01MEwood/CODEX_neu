"""FastAPI Routes für Lead Management.

Zwei Hauptbereiche:
1. Webhook-Endpoints — empfangen Daten von n8n (ein universeller + kanalspezifische)
2. CRUD-Endpoints — für das Frontend / Dashboard
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query

from lead_management.config.settings import settings
from lead_management.models.lead import (
    Kanal,
    Lead,
    LeadCreate,
    LeadStatus,
    LeadUpdate,
)
from lead_management.services.auto_reply import send_auto_reply
from lead_management.services.lead_store import LeadStore
from lead_management.services.telegram_notify import send_lead_notification

logger = logging.getLogger(__name__)

router = APIRouter()
store = LeadStore()


# ──────────────────────────────────────────────
# Webhook Endpoints (n8n → MEOS:BASE)
# ──────────────────────────────────────────────


def _verify_webhook_secret(secret: Optional[str]) -> None:
    """Einfache Secret-Prüfung für Webhook-Aufrufe."""
    if settings.webhook_secret and settings.webhook_secret != "CHANGE-ME-auf-dem-VPS":
        if not secret or not hmac.compare_digest(secret, settings.webhook_secret):
            raise HTTPException(status_code=401, detail="Ungültiges Webhook-Secret")


@router.post("/webhook/lead", response_model=Lead, tags=["Webhooks"])
async def webhook_universal(
    data: LeadCreate,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Universeller Webhook — n8n schickt normalisierte Lead-Daten hierher.

    Egal welcher Kanal — n8n normalisiert die Daten und POSTet sie
    in diesem einheitlichen Format.
    """
    _verify_webhook_secret(x_webhook_secret)

    lead = store.create(data)
    logger.info("Neuer Lead: %s via %s", lead.id, lead.kanal.value)

    # Parallel: Telegram-Alert + Auto-Reply
    notified = await send_lead_notification(lead)
    if notified:
        store.mark_telegram_notified(lead.id)

    replied = await send_auto_reply(lead)
    if replied:
        store.mark_erstantwort(lead.id)

    return store.get(lead.id)


@router.post("/webhook/whatsapp", response_model=Lead, tags=["Webhooks"])
async def webhook_whatsapp(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """WhatsApp-spezifischer Webhook.

    n8n empfängt die WhatsApp Business API Notification,
    extrahiert die relevanten Felder und leitet sie hierher weiter.
    """
    _verify_webhook_secret(x_webhook_secret)

    # n8n normalisiert das WhatsApp-Payload in dieses Format
    data = LeadCreate(
        kanal=Kanal.WHATSAPP,
        name=payload.get("name"),
        telefon=payload.get("telefon") or payload.get("from"),
        nachricht=payload.get("nachricht") or payload.get("text"),
        quelle=payload.get("quelle", "WhatsApp"),
        raw_payload=payload,
    )
    lead = store.create(data)

    await send_lead_notification(lead)
    store.mark_telegram_notified(lead.id)

    await send_auto_reply(lead)
    store.mark_erstantwort(lead.id)

    return store.get(lead.id)


@router.post("/webhook/messenger", response_model=Lead, tags=["Webhooks"])
async def webhook_messenger(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Facebook Messenger Webhook — von n8n weitergeleitet."""
    _verify_webhook_secret(x_webhook_secret)

    data = LeadCreate(
        kanal=Kanal.MESSENGER,
        name=payload.get("name") or payload.get("sender_name"),
        nachricht=payload.get("nachricht") or payload.get("message"),
        quelle=payload.get("quelle", "Facebook Messenger"),
        raw_payload=payload,
    )
    lead = store.create(data)

    await send_lead_notification(lead)
    store.mark_telegram_notified(lead.id)

    return store.get(lead.id)


@router.post("/webhook/email", response_model=Lead, tags=["Webhooks"])
async def webhook_email(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Email-Webhook — n8n holt IMAP-Mails und schickt sie hierher."""
    _verify_webhook_secret(x_webhook_secret)

    data = LeadCreate(
        kanal=Kanal.EMAIL,
        name=payload.get("name") or payload.get("from_name"),
        email=payload.get("email") or payload.get("from"),
        nachricht=payload.get("nachricht") or payload.get("subject", "")
        + "\n\n"
        + payload.get("body", ""),
        quelle=payload.get("quelle", "Email"),
        raw_payload=payload,
    )
    lead = store.create(data)

    await send_lead_notification(lead)
    store.mark_telegram_notified(lead.id)

    await send_auto_reply(lead)
    store.mark_erstantwort(lead.id)

    return store.get(lead.id)


@router.post("/webhook/anruf", response_model=Lead, tags=["Webhooks"])
async def webhook_anruf(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Anruf/Voice-Memo Webhook.

    Flow: Anruf → Voice-Memo → Telegram → n8n transkribiert mit Whisper → hierher.
    Oder: Sipgate Webhook → n8n → hierher.
    """
    _verify_webhook_secret(x_webhook_secret)

    data = LeadCreate(
        kanal=Kanal.ANRUF if payload.get("type") != "voice_memo" else Kanal.VOICE_MEMO,
        name=payload.get("name"),
        telefon=payload.get("telefon") or payload.get("caller"),
        nachricht=payload.get("nachricht") or payload.get("transkript"),
        quelle=payload.get("quelle", "Anruf"),
        raw_payload=payload,
    )
    lead = store.create(data)

    await send_lead_notification(lead)
    store.mark_telegram_notified(lead.id)

    return store.get(lead.id)


@router.post("/webhook/kontaktformular", response_model=Lead, tags=["Webhooks"])
async def webhook_kontaktformular(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """WordPress Kontaktformular Webhook (CF7, WPForms, etc.)."""
    _verify_webhook_secret(x_webhook_secret)

    data = LeadCreate(
        kanal=Kanal.KONTAKTFORMULAR,
        name=payload.get("name") or payload.get("your-name"),
        email=payload.get("email") or payload.get("your-email"),
        telefon=payload.get("telefon") or payload.get("your-phone"),
        nachricht=payload.get("nachricht") or payload.get("your-message"),
        quelle=payload.get("quelle", "Website Kontaktformular"),
        raw_payload=payload,
    )
    lead = store.create(data)

    await send_lead_notification(lead)
    store.mark_telegram_notified(lead.id)

    await send_auto_reply(lead)
    store.mark_erstantwort(lead.id)

    return store.get(lead.id)


# ──────────────────────────────────────────────
# CRUD Endpoints (Dashboard / Frontend)
# ──────────────────────────────────────────────


@router.get("/leads", response_model=list[Lead], tags=["Leads"])
async def list_leads(
    status: Optional[LeadStatus] = Query(default=None),
    kanal: Optional[str] = Query(default=None),
    zustaendig: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Alle Leads auflisten — filterbar nach Status, Kanal, Zuständigem."""
    return store.list_all(
        status=status,
        kanal=kanal,
        zustaendig=zustaendig,
        limit=limit,
        offset=offset,
    )


@router.get("/leads/{lead_id}", response_model=Lead, tags=["Leads"])
async def get_lead(lead_id: str):
    """Einzelnen Lead abrufen."""
    lead = store.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    return lead


@router.patch("/leads/{lead_id}", response_model=Lead, tags=["Leads"])
async def update_lead(lead_id: str, data: LeadUpdate):
    """Lead-Status, Zuständigen oder Notizen aktualisieren."""
    lead = store.update(lead_id, data)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    return lead


@router.get("/stats", tags=["Dashboard"])
async def lead_stats():
    """Schnelle Übersicht für das Dashboard."""
    return {
        "gesamt": store.count(),
        "neu": store.count(LeadStatus.NEU),
        "kontaktiert": store.count(LeadStatus.KONTAKTIERT),
        "qualifiziert": store.count(LeadStatus.QUALIFIZIERT),
        "aufmass_termin": store.count(LeadStatus.AUFMASS_TERMIN),
        "angebot_erstellt": store.count(LeadStatus.ANGEBOT_ERSTELLT),
        "gewonnen": store.count(LeadStatus.GEWONNEN),
        "verloren": store.count(LeadStatus.VERLOREN),
    }
