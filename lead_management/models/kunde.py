"""Kunde + Kundenmappe — das Herzstück der Kundenzuordnung.

Jeder Kontakt der reinkommt wird einer Person zugeordnet:
- Bestandskunde aus Freund CRM → direkt in die Kundenmappe
- Neuer Interessent → Prospect anlegen, Buchungsseite anbieten

Die Kundenmappe ist eine chronologische Timeline ALLER Interaktionen
über ALLE Kanäle hinweg — egal ob WhatsApp, Email oder Anruf.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KundenTyp(str, enum.Enum):
    BESTANDSKUNDE = "bestandskunde"  # Aus Freund CRM bekannt
    INTERESSENT = "interessent"  # Noch kein Kunde, aber Lead
    PROSPECT = "prospect"  # Komplett neu, kein Match


class MatchKonfidenz(str, enum.Enum):
    EXAKT = "exakt"  # Telefon oder Email stimmt 1:1
    HOCH = "hoch"  # Mehrere Felder passen (Name + Stadt, etc.)
    MITTEL = "mittel"  # Nur Name matched (fuzzy)
    KEIN = "kein"  # Kein Match gefunden


class KundenmappeEintrag(BaseModel):
    """Ein einzelner Eintrag in der Kundenmappe — eine Interaktion."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: datetime = Field(default_factory=datetime.now)
    kanal: str  # whatsapp, email, anruf, etc.
    richtung: str = "eingehend"  # eingehend | ausgehend
    inhalt: str  # Nachricht, Transkript, Betreff
    lead_id: Optional[str] = None  # Verknüpfung zum Lead
    bearbeiter: Optional[str] = None  # Wer hat bearbeitet
    notiz: Optional[str] = None  # Interne Notiz


class Kunde(BaseModel):
    """Kundendatensatz — zusammengeführt aus Freund CRM + Leads."""

    id: str = Field(default_factory=lambda: f"KD-{uuid.uuid4().hex[:8].upper()}")
    typ: KundenTyp = KundenTyp.PROSPECT
    freund_crm_id: Optional[str] = None  # ID in Freund CRM (wenn vorhanden)

    # Stammdaten
    name: Optional[str] = None
    firma: Optional[str] = None
    strasse: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None

    # Kontaktdaten — ALLE bekannten (ein Kunde hat oft mehrere!)
    telefonnummern: list[str] = Field(default_factory=list)
    email_adressen: list[str] = Field(default_factory=list)

    # Kundenmappe — chronologische Timeline
    kundenmappe: list[KundenmappeEintrag] = Field(default_factory=list)

    # Verknüpfte Leads
    lead_ids: list[str] = Field(default_factory=list)

    # Metadaten
    erstellt: datetime = Field(default_factory=datetime.now)
    letzte_interaktion: Optional[datetime] = None
    buchung_angeboten: bool = False  # Wurde Buchungsseite schon geschickt?

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MatchResult(BaseModel):
    """Ergebnis der Kundenzuordnung."""

    kunde: Optional[Kunde] = None
    konfidenz: MatchKonfidenz = MatchKonfidenz.KEIN
    match_grund: Optional[str] = None  # "Telefon +49171...", "Email max@...", etc.
    ist_neukunde: bool = True
