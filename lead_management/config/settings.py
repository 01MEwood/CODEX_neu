"""Zentrale Konfiguration — Umgebungsvariablen für alle Integrationen.

Auf dem Hostinger VPS werden diese als Environment-Variablen gesetzt,
oder in einer .env-Datei neben der docker-compose.yml.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "MEOS:BASE Lead Management"
    app_port: int = 8100
    debug: bool = False

    # --- Sicherheit ---
    webhook_secret: str = "CHANGE-ME-auf-dem-VPS"

    # --- Telegram ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # Gruppen-Chat oder persönlicher Chat

    # --- WhatsApp Business API (Meta) ---
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = ""

    # --- Meta Messenger ---
    messenger_page_token: str = ""
    messenger_verify_token: str = ""

    # --- Email (IMAP für n8n, SMTP für Antworten) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "info@schreinerhelden.de"

    # --- Freund CRM ---
    freund_crm_url: str = ""  # z.B. https://api.freund-crm.de
    freund_crm_api_key: str = ""

    # --- Buchungsseite ---
    booking_url: str = ""  # z.B. https://calendly.com/schreinerhelden/beratung

    # --- n8n ---
    n8n_base_url: str = "https://n8n.dein-vps.de"

    # --- Datenbank ---
    database_url: str = "sqlite:///./leads.db"

    model_config = {"env_prefix": "MEOS_", "env_file": ".env"}


settings = Settings()
