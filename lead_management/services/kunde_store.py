"""Kunden-Store — lokaler Kundenstamm mit Kundenmappe.

Synchronisiert sich mit Freund CRM, führt aber auch eigene
Prospects/Interessenten die noch nicht im CRM sind.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from lead_management.models.kunde import (
    Kunde,
    KundenmappeEintrag,
    KundenTyp,
)


class KundeStore:
    """Thread-safe Kunden-Storage mit JSON-Backup."""

    def __init__(self, db_path: str = "kunden.json") -> None:
        self._path = Path(db_path)
        self._lock = threading.Lock()
        self._kunden: dict[str, Kunde] = {}
        self._load()

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    def create(self, kunde: Kunde) -> Kunde:
        with self._lock:
            self._kunden[kunde.id] = kunde
            self._save()
        return kunde

    def get(self, kunde_id: str) -> Optional[Kunde]:
        return self._kunden.get(kunde_id)

    def get_by_freund_id(self, freund_crm_id: str) -> Optional[Kunde]:
        for k in self._kunden.values():
            if k.freund_crm_id == freund_crm_id:
                return k
        return None

    def list_all(
        self,
        typ: Optional[KundenTyp] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Kunde]:
        kunden = list(self._kunden.values())
        if typ:
            kunden = [k for k in kunden if k.typ == typ]
        kunden.sort(
            key=lambda k: k.letzte_interaktion or k.erstellt, reverse=True
        )
        return kunden[offset : offset + limit]

    # ──────────────────────────────────────────────
    # Kontaktdaten erweitern
    # ──────────────────────────────────────────────

    def telefon_hinzufuegen(self, kunde_id: str, telefon: str) -> None:
        """Neue Telefonnummer zum Kunden hinzufügen (wenn noch nicht bekannt)."""
        with self._lock:
            kunde = self._kunden.get(kunde_id)
            if kunde and telefon not in kunde.telefonnummern:
                neue_nummern = kunde.telefonnummern + [telefon]
                self._kunden[kunde_id] = kunde.model_copy(
                    update={"telefonnummern": neue_nummern}
                )
                self._save()

    def email_hinzufuegen(self, kunde_id: str, email: str) -> None:
        """Neue Email-Adresse zum Kunden hinzufügen (wenn noch nicht bekannt)."""
        with self._lock:
            kunde = self._kunden.get(kunde_id)
            if kunde and email.lower() not in [
                e.lower() for e in kunde.email_adressen
            ]:
                neue_emails = kunde.email_adressen + [email]
                self._kunden[kunde_id] = kunde.model_copy(
                    update={"email_adressen": neue_emails}
                )
                self._save()

    # ──────────────────────────────────────────────
    # Kundenmappe
    # ──────────────────────────────────────────────

    def eintrag_hinzufuegen(
        self, kunde_id: str, eintrag: KundenmappeEintrag
    ) -> Optional[Kunde]:
        """Neuen Eintrag in die Kundenmappe schreiben."""
        with self._lock:
            kunde = self._kunden.get(kunde_id)
            if not kunde:
                return None

            neue_mappe = kunde.kundenmappe + [eintrag]
            self._kunden[kunde_id] = kunde.model_copy(
                update={
                    "kundenmappe": neue_mappe,
                    "letzte_interaktion": eintrag.timestamp,
                }
            )
            self._save()
            return self._kunden[kunde_id]

    def lead_verknuepfen(self, kunde_id: str, lead_id: str) -> None:
        """Lead-ID mit Kunden verknüpfen."""
        with self._lock:
            kunde = self._kunden.get(kunde_id)
            if kunde and lead_id not in kunde.lead_ids:
                neue_ids = kunde.lead_ids + [lead_id]
                self._kunden[kunde_id] = kunde.model_copy(
                    update={"lead_ids": neue_ids}
                )
                self._save()

    def buchung_markieren(self, kunde_id: str) -> None:
        """Markieren dass Buchungsseite schon angeboten wurde."""
        with self._lock:
            kunde = self._kunden.get(kunde_id)
            if kunde:
                self._kunden[kunde_id] = kunde.model_copy(
                    update={"buchung_angeboten": True}
                )
                self._save()

    def kundenmappe_abrufen(
        self, kunde_id: str, limit: int = 50
    ) -> list[KundenmappeEintrag]:
        """Kundenmappe-Einträge holen (neueste zuerst)."""
        kunde = self._kunden.get(kunde_id)
        if not kunde:
            return []
        eintraege = sorted(
            kunde.kundenmappe, key=lambda e: e.timestamp, reverse=True
        )
        return eintraege[:limit]

    # ──────────────────────────────────────────────
    # Suche (für Matching)
    # ──────────────────────────────────────────────

    def suche_nach_telefon(self, telefon_normalisiert: str) -> Optional[Kunde]:
        """Kunden anhand normalisierter Telefonnummer finden."""
        for kunde in self._kunden.values():
            for nr in kunde.telefonnummern:
                if _normalize_phone(nr) == telefon_normalisiert:
                    return kunde
        return None

    def suche_nach_email(self, email: str) -> Optional[Kunde]:
        """Kunden anhand Email-Adresse finden."""
        email_lower = email.lower().strip()
        for kunde in self._kunden.values():
            for e in kunde.email_adressen:
                if e.lower().strip() == email_lower:
                    return kunde
        return None

    # ──────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for item in raw:
                kunde = Kunde(**item)
                self._kunden[kunde.id] = kunde

    def _save(self) -> None:
        data = [k.model_dump(mode="json") for k in self._kunden.values()]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def count(self, typ: Optional[KundenTyp] = None) -> int:
        if typ:
            return sum(1 for k in self._kunden.values() if k.typ == typ)
        return len(self._kunden)


def _normalize_phone(phone: str) -> str:
    """Telefonnummer normalisieren für Vergleich."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("0049"):
        digits = "49" + digits[4:]
    elif digits.startswith("0"):
        digits = "49" + digits[1:]
    return digits
