"""In-Memory Lead Store mit JSON-Persistenz.

Für den MVP reicht eine JSON-Datei. Später austauschbar gegen PostgreSQL
ohne die API zu ändern — das Interface bleibt gleich.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from lead_management.models.lead import Lead, LeadCreate, LeadStatus, LeadUpdate


class LeadStore:
    """Thread-safe Lead Storage mit JSON-Backup."""

    def __init__(self, db_path: str = "leads.json") -> None:
        self._path = Path(db_path)
        self._lock = threading.Lock()
        self._leads: dict[str, Lead] = {}
        self._load()

    # --- CRUD ---

    def create(self, data: LeadCreate) -> Lead:
        lead = Lead(
            kanal=data.kanal,
            name=data.name,
            telefon=data.telefon,
            email=data.email,
            nachricht=data.nachricht,
            quelle=data.quelle,
            zustaendig=data.zustaendig,
            raw_payload=data.raw_payload,
        )
        with self._lock:
            self._leads[lead.id] = lead
            self._save()
        return lead

    def get(self, lead_id: str) -> Optional[Lead]:
        return self._leads.get(lead_id)

    def list_all(
        self,
        status: Optional[LeadStatus] = None,
        kanal: Optional[str] = None,
        zustaendig: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Lead]:
        leads = list(self._leads.values())

        if status:
            leads = [l for l in leads if l.status == status]
        if kanal:
            leads = [l for l in leads if l.kanal.value == kanal]
        if zustaendig:
            leads = [l for l in leads if l.zustaendig == zustaendig]

        # Neueste zuerst
        leads.sort(key=lambda l: l.eingang, reverse=True)
        return leads[offset : offset + limit]

    def update(self, lead_id: str, data: LeadUpdate) -> Optional[Lead]:
        with self._lock:
            lead = self._leads.get(lead_id)
            if not lead:
                return None

            update_data = data.model_dump(exclude_unset=True)
            updated = lead.model_copy(update=update_data)
            self._leads[lead_id] = updated
            self._save()
            return updated

    def mark_erstantwort(self, lead_id: str) -> None:
        with self._lock:
            lead = self._leads.get(lead_id)
            if lead:
                self._leads[lead_id] = lead.model_copy(
                    update={"erstantwort_gesendet": True}
                )
                self._save()

    def mark_telegram_notified(self, lead_id: str) -> None:
        with self._lock:
            lead = self._leads.get(lead_id)
            if lead:
                self._leads[lead_id] = lead.model_copy(
                    update={"telegram_notified": True}
                )
                self._save()

    def count(self, status: Optional[LeadStatus] = None) -> int:
        if status:
            return sum(1 for l in self._leads.values() if l.status == status)
        return len(self._leads)

    # --- Persistence ---

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for item in raw:
                lead = Lead(**item)
                self._leads[lead.id] = lead

    def _save(self) -> None:
        data = [l.model_dump(mode="json") for l in self._leads.values()]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
