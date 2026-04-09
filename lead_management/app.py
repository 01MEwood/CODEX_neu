"""MEOS:BASE Lead Management Server.

Startet die FastAPI-Anwendung mit allen Webhook- und CRUD-Endpoints.
Auf dem Hostinger VPS läuft das hinter einem Reverse-Proxy (Caddy/Nginx).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lead_management.api.routes import router
from lead_management.config.settings import settings

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Zentraler Lead-Eingang für Schreinerhelden. "
        "WhatsApp, Messenger, Email, Anruf, Kontaktformular → ein Trichter."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion einschränken!
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "lead_management.app:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
    )
