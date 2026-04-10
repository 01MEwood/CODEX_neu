"""FastAPI Routes für Lead Management + Kundenverwaltung.

Drei Bereiche:
1. Webhook-Endpoints — empfangen Daten von n8n → Pipeline
2. Lead CRUD — für Dashboard
3. Kunden + Kundenmappe — für Kundenverwaltung
"""

from __future__ import annotations

import hmac
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query

from lead_management.config.settings import settings
from lead_management.models.kunde import Kunde, KundenTyp, KundenmappeEintrag
from lead_management.models.lead import (
    Kanal,
    Lead,
    LeadCreate,
    LeadStatus,
    LeadUpdate,
)
from lead_management.services.lead_pipeline import (
    PipelineResult,
    kunde_store,
    lead_store,
    process_lead,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────


def _verify_webhook_secret(secret: Optional[str]) -> None:
    if settings.webhook_secret and settings.webhook_secret != "CHANGE-ME-auf-dem-VPS":
        if not secret or not hmac.compare_digest(secret, settings.webhook_secret):
            raise HTTPException(status_code=401, detail="Ungültiges Webhook-Secret")


# ──────────────────────────────────────────────
# Webhook Endpoints (n8n → Pipeline)
# ──────────────────────────────────────────────


@router.post("/webhook/lead", tags=["Webhooks"])
async def webhook_universal(
    data: LeadCreate,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Universeller Webhook — alle Kanäle in einem Endpoint."""
    _verify_webhook_secret(x_webhook_secret)
    result = await process_lead(data)
    return _pipeline_response(result)


@router.post("/webhook/whatsapp", tags=["Webhooks"])
async def webhook_whatsapp(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """WhatsApp Business API Webhook."""
    _verify_webhook_secret(x_webhook_secret)
    data = LeadCreate(
        kanal=Kanal.WHATSAPP,
        name=payload.get("name"),
        telefon=payload.get("telefon") or payload.get("from"),
        nachricht=payload.get("nachricht") or payload.get("text"),
        quelle=payload.get("quelle", "WhatsApp"),
        raw_payload=payload,
    )
    result = await process_lead(data)
    return _pipeline_response(result)


@router.post("/webhook/messenger", tags=["Webhooks"])
async def webhook_messenger(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Facebook Messenger Webhook."""
    _verify_webhook_secret(x_webhook_secret)
    data = LeadCreate(
        kanal=Kanal.MESSENGER,
        name=payload.get("name") or payload.get("sender_name"),
        nachricht=payload.get("nachricht") or payload.get("message"),
        quelle=payload.get("quelle", "Facebook Messenger"),
        raw_payload=payload,
    )
    result = await process_lead(data)
    return _pipeline_response(result)


@router.post("/webhook/email", tags=["Webhooks"])
async def webhook_email(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Email-Webhook (n8n IMAP-Trigger)."""
    _verify_webhook_secret(x_webhook_secret)

    nachricht = payload.get("nachricht")
    if not nachricht:
        subject = payload.get("subject", "")
        body = payload.get("body", "")
        nachricht = f"{subject}\n\n{body}".strip()

    data = LeadCreate(
        kanal=Kanal.EMAIL,
        name=payload.get("name") or payload.get("from_name"),
        email=payload.get("email") or payload.get("from"),
        nachricht=nachricht,
        quelle=payload.get("quelle", "Email"),
        raw_payload=payload,
    )
    result = await process_lead(data)
    return _pipeline_response(result)


@router.post("/webhook/anruf", tags=["Webhooks"])
async def webhook_anruf(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """Anruf/Voice-Memo Webhook."""
    _verify_webhook_secret(x_webhook_secret)
    data = LeadCreate(
        kanal=Kanal.ANRUF if payload.get("type") != "voice_memo" else Kanal.VOICE_MEMO,
        name=payload.get("name"),
        telefon=payload.get("telefon") or payload.get("caller"),
        nachricht=payload.get("nachricht") or payload.get("transkript"),
        quelle=payload.get("quelle", "Anruf"),
        raw_payload=payload,
    )
    result = await process_lead(data)
    return _pipeline_response(result)


@router.post("/webhook/kontaktformular", tags=["Webhooks"])
async def webhook_kontaktformular(
    payload: dict,
    x_webhook_secret: Optional[str] = Header(default=None),
):
    """WordPress Kontaktformular Webhook."""
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
    result = await process_lead(data)
    return _pipeline_response(result)


def _pipeline_response(result: PipelineResult) -> dict:
    """Pipeline-Ergebnis als API-Response formatieren."""
    return {
        "lead": result.lead.model_dump(mode="json") if result.lead else None,
        "kunde": {
            "id": result.match.kunde.id,
            "name": result.match.kunde.name,
            "typ": result.match.kunde.typ.value,
            "freund_crm_id": result.match.kunde.freund_crm_id,
            "ist_neukunde": result.match.ist_neukunde,
        }
        if result.match.kunde
        else None,
        "matching": {
            "konfidenz": result.match.konfidenz.value,
            "grund": result.match.match_grund,
        },
        "aktionen": {
            "telegram_gesendet": result.telegram_sent,
            "erstantwort_gesendet": result.auto_reply_sent,
            "buchung_angeboten": result.buchung_angeboten,
            "crm_notiz_geschrieben": result.crm_notiz_geschrieben,
        },
    }


# ──────────────────────────────────────────────
# Lead CRUD
# ──────────────────────────────────────────────


@router.get("/leads", response_model=list[Lead], tags=["Leads"])
async def list_leads(
    status: Optional[LeadStatus] = Query(default=None),
    kanal: Optional[str] = Query(default=None),
    zustaendig: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Alle Leads auflisten."""
    return lead_store.list_all(
        status=status, kanal=kanal, zustaendig=zustaendig,
        limit=limit, offset=offset,
    )


@router.get("/leads/{lead_id}", response_model=Lead, tags=["Leads"])
async def get_lead(lead_id: str):
    lead = lead_store.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    return lead


@router.patch("/leads/{lead_id}", response_model=Lead, tags=["Leads"])
async def update_lead(lead_id: str, data: LeadUpdate):
    lead = lead_store.update(lead_id, data)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead nicht gefunden")
    return lead


# ──────────────────────────────────────────────
# Kunden + Kundenmappe
# ──────────────────────────────────────────────


@router.get("/kunden", tags=["Kunden"])
async def list_kunden(
    typ: Optional[KundenTyp] = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Alle Kunden auflisten — filterbar nach Typ (bestandskunde/interessent/prospect)."""
    kunden = kunde_store.list_all(typ=typ, limit=limit, offset=offset)
    return [_kunde_summary(k) for k in kunden]


@router.get("/kunden/{kunde_id}", tags=["Kunden"])
async def get_kunde(kunde_id: str):
    """Kunden-Details mit vollständiger Kundenmappe."""
    kunde = kunde_store.get(kunde_id)
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    return kunde.model_dump(mode="json")


@router.get("/kunden/{kunde_id}/kundenmappe", tags=["Kundenmappe"])
async def get_kundenmappe(
    kunde_id: str,
    limit: int = Query(default=50, le=200),
):
    """Kundenmappe-Einträge für einen Kunden (neueste zuerst)."""
    kunde = kunde_store.get(kunde_id)
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    eintraege = kunde_store.kundenmappe_abrufen(kunde_id, limit=limit)
    return {
        "kunde_id": kunde_id,
        "kunde_name": kunde.name,
        "typ": kunde.typ.value,
        "freund_crm_id": kunde.freund_crm_id,
        "anzahl_eintraege": len(kunde.kundenmappe),
        "eintraege": [e.model_dump(mode="json") for e in eintraege],
    }


@router.get("/kunden/{kunde_id}/leads", response_model=list[Lead], tags=["Kundenmappe"])
async def get_kunde_leads(kunde_id: str):
    """Alle Leads die diesem Kunden zugeordnet sind."""
    kunde = kunde_store.get(kunde_id)
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")

    leads = []
    for lead_id in kunde.lead_ids:
        lead = lead_store.get(lead_id)
        if lead:
            leads.append(lead)
    return leads


# ──────────────────────────────────────────────
# Dashboard Stats
# ──────────────────────────────────────────────


@router.get("/stats", tags=["Dashboard"])
async def stats():
    """Gesamtübersicht für das Dashboard."""
    return {
        "leads": {
            "gesamt": lead_store.count(),
            "neu": lead_store.count(LeadStatus.NEU),
            "kontaktiert": lead_store.count(LeadStatus.KONTAKTIERT),
            "qualifiziert": lead_store.count(LeadStatus.QUALIFIZIERT),
            "aufmass_termin": lead_store.count(LeadStatus.AUFMASS_TERMIN),
            "angebot_erstellt": lead_store.count(LeadStatus.ANGEBOT_ERSTELLT),
            "gewonnen": lead_store.count(LeadStatus.GEWONNEN),
            "verloren": lead_store.count(LeadStatus.VERLOREN),
        },
        "kunden": {
            "gesamt": kunde_store.count(),
            "bestandskunden": kunde_store.count(KundenTyp.BESTANDSKUNDE),
            "interessenten": kunde_store.count(KundenTyp.INTERESSENT),
            "prospects": kunde_store.count(KundenTyp.PROSPECT),
        },
    }


def _kunde_summary(kunde: Kunde) -> dict:
    """Kunden-Kurzinfo für Listen."""
    return {
        "id": kunde.id,
        "name": kunde.name,
        "typ": kunde.typ.value,
        "freund_crm_id": kunde.freund_crm_id,
        "telefonnummern": kunde.telefonnummern,
        "email_adressen": kunde.email_adressen,
        "anzahl_leads": len(kunde.lead_ids),
        "anzahl_interaktionen": len(kunde.kundenmappe),
        "letzte_interaktion": kunde.letzte_interaktion.isoformat()
        if kunde.letzte_interaktion
        else None,
    }
