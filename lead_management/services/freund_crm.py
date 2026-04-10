"""Freund CRM Anbindung — Kunden aus eurem CRM holen.

Freund CRM (freund-crm.de) wird von vielen Schreinereien genutzt.
Die API-Anbindung holt Kundenstammdaten und erlaubt es,
neue Kontakte / Interaktionen zurückzuschreiben.

Falls die Freund API nicht erreichbar ist oder kein API-Key
konfiguriert wurde, läuft das System im "Standalone"-Modus
mit eigenem Kundenstamm.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from lead_management.config.settings import settings

logger = logging.getLogger(__name__)


class FreundCRMClient:
    """Client für die Freund CRM API."""

    def __init__(self) -> None:
        self.base_url = settings.freund_crm_url.rstrip("/")
        self.api_key = settings.freund_crm_api_key
        self._enabled = bool(self.base_url and self.api_key)

        if not self._enabled:
            logger.warning(
                "Freund CRM nicht konfiguriert — läuft im Standalone-Modus"
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> Optional[dict | list]:
        """HTTP-Request an Freund CRM mit Auth-Header."""
        if not self._enabled:
            return None

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.request(
                    method, url, headers=headers, **kwargs
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            logger.error("Freund CRM Anfrage fehlgeschlagen: %s %s → %s", method, path, e)
            return None

    # ──────────────────────────────────────────────
    # Kunden suchen
    # ──────────────────────────────────────────────

    async def suche_nach_telefon(self, telefon: str) -> Optional[dict]:
        """Kunden in Freund CRM anhand Telefonnummer suchen."""
        result = await self._request(
            "GET",
            "/api/v1/contacts",
            params={"phone": telefon, "limit": 5},
        )
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        if result and isinstance(result, dict) and result.get("data"):
            return result["data"][0]
        return None

    async def suche_nach_email(self, email: str) -> Optional[dict]:
        """Kunden in Freund CRM anhand Email-Adresse suchen."""
        result = await self._request(
            "GET",
            "/api/v1/contacts",
            params={"email": email, "limit": 5},
        )
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        if result and isinstance(result, dict) and result.get("data"):
            return result["data"][0]
        return None

    async def suche_nach_name(self, name: str) -> Optional[list[dict]]:
        """Kunden in Freund CRM anhand Name suchen (kann mehrere Treffer liefern)."""
        result = await self._request(
            "GET",
            "/api/v1/contacts",
            params={"search": name, "limit": 10},
        )
        if result and isinstance(result, list):
            return result
        if result and isinstance(result, dict) and result.get("data"):
            return result["data"]
        return None

    async def kunde_details(self, crm_id: str) -> Optional[dict]:
        """Vollständige Kundendaten aus Freund CRM laden."""
        return await self._request("GET", f"/api/v1/contacts/{crm_id}")

    # ──────────────────────────────────────────────
    # Daten zurückschreiben
    # ──────────────────────────────────────────────

    async def notiz_hinzufuegen(
        self, crm_id: str, text: str, kanal: str = "system"
    ) -> bool:
        """Notiz / Interaktion in Freund CRM beim Kunden hinterlegen."""
        result = await self._request(
            "POST",
            f"/api/v1/contacts/{crm_id}/notes",
            json={
                "content": text,
                "channel": kanal,
            },
        )
        return result is not None

    async def kontakt_anlegen(self, daten: dict) -> Optional[dict]:
        """Neuen Kontakt in Freund CRM anlegen.

        daten sollte enthalten: name, phone, email, etc.
        """
        return await self._request(
            "POST",
            "/api/v1/contacts",
            json=daten,
        )

    # ──────────────────────────────────────────────
    # Alle Kunden laden (für lokalen Cache / Matching)
    # ──────────────────────────────────────────────

    async def alle_kunden_laden(self, limit: int = 1000) -> list[dict]:
        """Alle Kunden aus Freund CRM laden (für lokalen Matching-Cache).

        Wird beim Start einmal aufgerufen und dann periodisch aktualisiert.
        """
        alle = []
        page = 1

        while len(alle) < limit:
            result = await self._request(
                "GET",
                "/api/v1/contacts",
                params={"page": page, "per_page": 100},
            )
            if not result:
                break

            items = result if isinstance(result, list) else result.get("data", [])
            if not items:
                break

            alle.extend(items)
            page += 1

            # Keine weitere Seite
            if len(items) < 100:
                break

        logger.info("Freund CRM: %d Kunden geladen", len(alle))
        return alle


# Singleton
freund_crm = FreundCRMClient()
