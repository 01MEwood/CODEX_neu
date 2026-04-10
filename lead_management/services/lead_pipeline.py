"""Lead Pipeline — der zentrale Orchestrator.

Was passiert wenn ein Lead reinkommt:

  1. Lead-Objekt anlegen
  2. Kunde matchen (lokal → Freund CRM → Prospect)
  3. Kundenmappe-Eintrag schreiben
  4. Kontaktdaten ergänzen (neue Nummer/Email)
  5. Telegram-Alert (mit Match-Info!)
  6. Auto-Reply ODER Buchungsseite (bei Neukunden)
  7. Optional: In Freund CRM zurückschreiben
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from lead_management.models.kunde import (
    KundenmappeEintrag,
    MatchKonfidenz,
    MatchResult,
)
from lead_management.models.lead import Lead, LeadCreate
from lead_management.services.auto_reply import send_auto_reply, send_booking_link
from lead_management.services.freund_crm import freund_crm
from lead_management.services.kunde_store import KundeStore
from lead_management.services.lead_store import LeadStore
from lead_management.services.matching import lead_zu_kunde
from lead_management.services.telegram_notify import (
    send_lead_notification_with_match,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Ergebnis der gesamten Pipeline."""

    lead: Lead
    match: MatchResult
    telegram_sent: bool = False
    auto_reply_sent: bool = False
    buchung_angeboten: bool = False
    crm_notiz_geschrieben: bool = False


# Stores werden beim Import initialisiert
lead_store = LeadStore()
kunde_store = KundeStore()


async def process_lead(data: LeadCreate) -> PipelineResult:
    """Hauptfunktion: Komplette Lead-Pipeline durchlaufen.

    Das ist der EINE Eingang für alle Kanäle.
    """

    # ── 1. Lead anlegen ──
    lead = lead_store.create(data)
    logger.info("Pipeline: Lead %s via %s", lead.id, lead.kanal.value)

    # ── 2. Kunde matchen ──
    match = await lead_zu_kunde(lead, kunde_store)

    # Lead mit Kunde verknüpfen
    if match.kunde:
        kunde_store.lead_verknuepfen(match.kunde.id, lead.id)

        # Lead-Objekt aktualisieren mit Kunden-Referenz
        from lead_management.models.lead import LeadUpdate

        lead_store.update(
            lead.id,
            LeadUpdate(
                kunde_id=match.kunde.id,
                match_konfidenz=match.konfidenz.value,
            ),
        )

    # ── 3. Kundenmappe-Eintrag ──
    if match.kunde:
        eintrag = KundenmappeEintrag(
            kanal=lead.kanal.value,
            richtung="eingehend",
            inhalt=lead.nachricht or "(kein Text)",
            lead_id=lead.id,
        )
        kunde_store.eintrag_hinzufuegen(match.kunde.id, eintrag)

    # ── 4. Telegram-Alert mit Match-Info ──
    telegram_sent = await send_lead_notification_with_match(lead, match)
    if telegram_sent:
        lead_store.mark_telegram_notified(lead.id)

    # ── 5. Auto-Reply oder Buchungsseite ──
    auto_reply_sent = False
    buchung_angeboten = False

    if match.ist_neukunde and match.konfidenz == MatchKonfidenz.KEIN:
        # Komplett neuer Kontakt → Buchungsseite anbieten
        buchung_angeboten = await send_booking_link(lead)
        if buchung_angeboten and match.kunde:
            kunde_store.buchung_markieren(match.kunde.id)
        # Auch normale Erstantwort senden
        auto_reply_sent = await send_auto_reply(lead)
    else:
        # Bestandskunde oder CRM-Match → nur Erstantwort
        auto_reply_sent = await send_auto_reply(lead)

    if auto_reply_sent:
        lead_store.mark_erstantwort(lead.id)

    # ── 6. Freund CRM Notiz ──
    crm_notiz = False
    if (
        freund_crm.enabled
        and match.kunde
        and match.kunde.freund_crm_id
        and match.konfidenz in (MatchKonfidenz.EXAKT, MatchKonfidenz.HOCH)
    ):
        notiz_text = (
            f"Neue Anfrage via {lead.kanal.value.title()}\n"
            f"Nachricht: {lead.nachricht or '(kein Text)'}\n"
            f"Lead-ID: {lead.id}"
        )
        crm_notiz = await freund_crm.notiz_hinzufuegen(
            match.kunde.freund_crm_id, notiz_text, lead.kanal.value
        )

    # ── Ergebnis ──
    return PipelineResult(
        lead=lead_store.get(lead.id),
        match=match,
        telegram_sent=telegram_sent,
        auto_reply_sent=auto_reply_sent,
        buchung_angeboten=buchung_angeboten,
        crm_notiz_geschrieben=crm_notiz,
    )
