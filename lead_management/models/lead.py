"""Lead-Datenmodell für MEOS:BASE.

Jeder Lead — egal ob WhatsApp, Messenger, Email, Anruf oder Kontaktformular —
wird in dasselbe Schema normalisiert.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Kanal(str, enum.Enum):
    WHATSAPP = "whatsapp"
    MESSENGER = "messenger"
    EMAIL = "email"
    ANRUF = "anruf"
    KONTAKTFORMULAR = "kontaktformular"
    VOICE_MEMO = "voice_memo"
    SONSTIGE = "sonstige"


class LeadStatus(str, enum.Enum):
    NEU = "neu"
    KONTAKTIERT = "kontaktiert"
    QUALIFIZIERT = "qualifiziert"
    AUFMASS_TERMIN = "aufmass_termin"
    ANGEBOT_ERSTELLT = "angebot_erstellt"
    ANGEBOT_VERSENDET = "angebot_versendet"
    GEWONNEN = "gewonnen"
    VERLOREN = "verloren"
    PAUSIERT = "pausiert"


class LeadCreate(BaseModel):
    """Payload den n8n per Webhook an die API schickt."""

    kanal: Kanal
    name: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    nachricht: Optional[str] = None
    quelle: Optional[str] = None
    zustaendig: Optional[str] = None
    raw_payload: Optional[dict] = Field(
        default=None,
        description="Original-Payload vom Kanal (WhatsApp-JSON, Email-Header etc.)",
    )


class LeadUpdate(BaseModel):
    """Felder die beim Status-Update geändert werden können."""

    status: Optional[LeadStatus] = None
    zustaendig: Optional[str] = None
    naechste_aktion: Optional[str] = None
    notizen: Optional[str] = None


class Lead(BaseModel):
    """Vollständiges Lead-Objekt wie es in der DB gespeichert wird."""

    id: str = Field(default_factory=lambda: f"LEAD-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}")
    kanal: Kanal
    eingang: datetime = Field(default_factory=datetime.now)
    name: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    nachricht: Optional[str] = None
    status: LeadStatus = LeadStatus.NEU
    zustaendig: Optional[str] = None
    naechste_aktion: Optional[str] = None
    notizen: Optional[str] = None
    quelle: Optional[str] = None
    raw_payload: Optional[dict] = None
    erstantwort_gesendet: bool = False
    telegram_notified: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
