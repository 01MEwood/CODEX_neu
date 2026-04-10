"""Smart Contact Matching — Lead → Kunde zuordnen.

Das Matching-Problem:
  Petra Müller schreibt per WhatsApp mit +49 171 1234567
  Petra.Mueller@web.de schickt eine Email
  "Frau Müller" ruft an von 0171-1234567
  → Alles EINE Person. Alles in EINE Kundenmappe.

Strategie (Wasserfall, höchste Konfidenz zuerst):

  1. Telefon (normalisiert) → EXAKT
  2. Email (case-insensitive) → EXAKT
  3. Telefon in Freund CRM    → EXAKT
  4. Email in Freund CRM      → EXAKT
  5. Name (fuzzy)             → MITTEL (nur als Vorschlag, kein Auto-Merge)

Wenn kein Match → neuer Prospect anlegen.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from lead_management.models.kunde import (
    Kunde,
    KundenmappeEintrag,
    KundenTyp,
    MatchKonfidenz,
    MatchResult,
)
from lead_management.models.lead import Lead
from lead_management.services.freund_crm import freund_crm
from lead_management.services.kunde_store import KundeStore

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """Telefonnummer auf reines Ziffernformat mit Ländervorwahl bringen.

    +49 171 123 4567  →  491711234567
    0171-123-4567     →  491711234567
    0049171/1234567   →  491711234567
    171 1234567       →  491711234567
    """
    digits = "".join(c for c in phone if c.isdigit())

    # Deutsche Sonderformate
    if digits.startswith("0049"):
        digits = "49" + digits[4:]
    elif digits.startswith("0"):
        digits = "49" + digits[1:]
    elif not digits.startswith("49") and len(digits) <= 11:
        # Kurze Nummer ohne Vorwahl → wahrscheinlich deutsch
        digits = "49" + digits

    return digits


def normalize_email(email: str) -> str:
    """Email normalisieren für Vergleich."""
    return email.lower().strip()


def _name_similarity(name1: str, name2: str) -> float:
    """Einfacher Namensvergleich — 0.0 bis 1.0.

    Kein externes Dependency (kein fuzzywuzzy nötig).
    Splittet in Wörter und vergleicht Überlappung.
    """
    if not name1 or not name2:
        return 0.0

    def _clean(n: str) -> set[str]:
        # Titel, Anrede, Sonderzeichen entfernen
        n = re.sub(r"\b(herr|frau|dr|prof|ing)\b", "", n, flags=re.IGNORECASE)
        n = re.sub(r"[^a-zäöüß\s]", "", n.lower())
        return {w for w in n.split() if len(w) > 1}

    words1 = _clean(name1)
    words2 = _clean(name2)

    if not words1 or not words2:
        return 0.0

    gemeinsam = words1 & words2
    gesamt = words1 | words2

    return len(gemeinsam) / len(gesamt) if gesamt else 0.0


async def lead_zu_kunde(lead: Lead, kunde_store: KundeStore) -> MatchResult:
    """Hauptfunktion: Ordne einen Lead einem Kunden zu.

    Returns:
        MatchResult mit dem zugeordneten/neu angelegten Kunden,
        der Konfidenz und ob es ein Neukunde ist.
    """

    # ──────────────────────────────────────────
    # Schritt 1: Lokaler Match (schnell, kein API-Call)
    # ──────────────────────────────────────────

    # 1a: Telefon-Match (beste Konfidenz)
    if lead.telefon:
        phone_norm = normalize_phone(lead.telefon)
        kunde = kunde_store.suche_nach_telefon(phone_norm)
        if kunde:
            logger.info(
                "MATCH (Telefon, lokal): Lead %s → Kunde %s (%s)",
                lead.id, kunde.id, kunde.name,
            )
            return MatchResult(
                kunde=kunde,
                konfidenz=MatchKonfidenz.EXAKT,
                match_grund=f"Telefon {lead.telefon}",
                ist_neukunde=False,
            )

    # 1b: Email-Match
    if lead.email:
        email_norm = normalize_email(lead.email)
        kunde = kunde_store.suche_nach_email(email_norm)
        if kunde:
            logger.info(
                "MATCH (Email, lokal): Lead %s → Kunde %s (%s)",
                lead.id, kunde.id, kunde.name,
            )
            return MatchResult(
                kunde=kunde,
                konfidenz=MatchKonfidenz.EXAKT,
                match_grund=f"Email {lead.email}",
                ist_neukunde=False,
            )

    # ──────────────────────────────────────────
    # Schritt 2: Freund CRM Match (API-Call)
    # ──────────────────────────────────────────

    if freund_crm.enabled:
        crm_kunde = None

        # 2a: Telefon in Freund CRM
        if lead.telefon:
            crm_kunde = await freund_crm.suche_nach_telefon(lead.telefon)

        # 2b: Email in Freund CRM
        if not crm_kunde and lead.email:
            crm_kunde = await freund_crm.suche_nach_email(lead.email)

        if crm_kunde:
            # CRM-Treffer → in lokalen Store übernehmen oder aktualisieren
            crm_id = str(
                crm_kunde.get("id")
                or crm_kunde.get("contact_id")
                or crm_kunde.get("nummer")
            )

            # Schon lokal vorhanden?
            lokaler_kunde = kunde_store.get_by_freund_id(crm_id)
            if lokaler_kunde:
                # Kontaktdaten ergänzen
                _kontaktdaten_ergaenzen(lokaler_kunde, lead, kunde_store)
                logger.info(
                    "MATCH (Freund CRM, bekannt): Lead %s → Kunde %s",
                    lead.id, lokaler_kunde.id,
                )
                return MatchResult(
                    kunde=lokaler_kunde,
                    konfidenz=MatchKonfidenz.EXAKT,
                    match_grund=f"Freund CRM #{crm_id}",
                    ist_neukunde=False,
                )
            else:
                # Neuen lokalen Kunden aus CRM-Daten anlegen
                neuer_kunde = _kunde_aus_crm(crm_kunde, crm_id, lead)
                kunde_store.create(neuer_kunde)
                logger.info(
                    "MATCH (Freund CRM, neu importiert): Lead %s → Kunde %s",
                    lead.id, neuer_kunde.id,
                )
                return MatchResult(
                    kunde=neuer_kunde,
                    konfidenz=MatchKonfidenz.EXAKT,
                    match_grund=f"Freund CRM #{crm_id} (importiert)",
                    ist_neukunde=False,
                )

        # 2c: Name-Suche in Freund CRM (fuzzy, nur als Vorschlag)
        if lead.name:
            crm_treffer = await freund_crm.suche_nach_name(lead.name)
            if crm_treffer:
                for t in crm_treffer:
                    crm_name = (
                        t.get("name")
                        or f"{t.get('first_name', '')} {t.get('last_name', '')}".strip()
                    )
                    sim = _name_similarity(lead.name, crm_name)
                    if sim >= 0.6:
                        crm_id = str(t.get("id") or t.get("contact_id"))
                        logger.info(
                            "MATCH (Name fuzzy, CRM): Lead %s → '%s' ≈ '%s' (%.0f%%)",
                            lead.id, lead.name, crm_name, sim * 100,
                        )
                        # Name-Match ist nur MITTEL — kein Auto-Merge,
                        # wird im Telegram-Alert als Vorschlag angezeigt
                        lokaler_kunde = kunde_store.get_by_freund_id(crm_id)
                        if not lokaler_kunde:
                            lokaler_kunde = _kunde_aus_crm(t, crm_id, lead)
                            kunde_store.create(lokaler_kunde)

                        return MatchResult(
                            kunde=lokaler_kunde,
                            konfidenz=MatchKonfidenz.MITTEL,
                            match_grund=f"Name ähnlich: '{crm_name}' (CRM #{crm_id})",
                            ist_neukunde=False,
                        )

    # ──────────────────────────────────────────
    # Schritt 3: Kein Match → Neuen Prospect anlegen
    # ──────────────────────────────────────────

    logger.info("KEIN MATCH: Lead %s → neuer Prospect wird angelegt", lead.id)

    telefonnummern = []
    if lead.telefon:
        telefonnummern = [lead.telefon]

    email_adressen = []
    if lead.email:
        email_adressen = [lead.email]

    neuer_kunde = Kunde(
        typ=KundenTyp.PROSPECT,
        name=lead.name,
        telefonnummern=telefonnummern,
        email_adressen=email_adressen,
    )
    kunde_store.create(neuer_kunde)

    return MatchResult(
        kunde=neuer_kunde,
        konfidenz=MatchKonfidenz.KEIN,
        match_grund=None,
        ist_neukunde=True,
    )


def _kontaktdaten_ergaenzen(
    kunde: Kunde, lead: Lead, store: KundeStore
) -> None:
    """Neue Kontaktdaten vom Lead zum bestehenden Kunden hinzufügen.

    Wenn Petra sich per WhatsApp mit +49 171... meldet,
    aber wir kennen nur ihre Email → Nummer wird ergänzt.
    """
    if lead.telefon:
        store.telefon_hinzufuegen(kunde.id, lead.telefon)
    if lead.email:
        store.email_hinzufuegen(kunde.id, lead.email)


def _kunde_aus_crm(crm_data: dict, crm_id: str, lead: Lead) -> Kunde:
    """Lokalen Kunden aus Freund CRM Daten erstellen."""

    # Telefonnummern sammeln (CRM + Lead)
    telefonnummern = []
    for key in ("phone", "mobile", "telefon", "handy", "tel"):
        if crm_data.get(key):
            telefonnummern.append(crm_data[key])
    if lead.telefon and lead.telefon not in telefonnummern:
        telefonnummern.append(lead.telefon)

    # Emails sammeln
    email_adressen = []
    for key in ("email", "mail", "e_mail"):
        if crm_data.get(key):
            email_adressen.append(crm_data[key])
    if lead.email and lead.email not in email_adressen:
        email_adressen.append(lead.email)

    name = (
        crm_data.get("name")
        or f"{crm_data.get('first_name', '')} {crm_data.get('last_name', '')}".strip()
        or lead.name
    )

    return Kunde(
        typ=KundenTyp.BESTANDSKUNDE,
        freund_crm_id=crm_id,
        name=name,
        firma=crm_data.get("company") or crm_data.get("firma"),
        strasse=crm_data.get("street") or crm_data.get("strasse"),
        plz=crm_data.get("zip") or crm_data.get("plz"),
        ort=crm_data.get("city") or crm_data.get("ort"),
        telefonnummern=telefonnummern,
        email_adressen=email_adressen,
    )
