# MEOS:BASE Lead Management — System-Architektur

## Gesamtübersicht

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EINGEHENDE KANÄLE                                    │
│                                                                                │
│   📱 WhatsApp        💬 Messenger      📧 Email         📞 Anruf              │
│   Business API       Meta API          IMAP             Sipgate/Voice          │
│       │                  │                │                  │                  │
│   📋 Kontaktformular                                                           │
│   WordPress CF7/WPForms                                                        │
│       │                                                                        │
└───────┼──────────────────┼────────────────┼──────────────────┼──────────────────┘
        │                  │                │                  │
        ▼                  ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│                        n8n  (Hostinger VPS)                                    │
│                        ════════════════════                                    │
│                                                                                │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│   │  Workflow 1   │ │  Workflow 2   │ │  Workflow 3   │ │  Workflow 4   │         │
│   │  WhatsApp     │ │  Messenger    │ │  Email IMAP   │ │  Anruf/Voice  │         │
│   │              │ │              │ │              │ │              │          │
│   │ Webhook ←────│ │ Webhook ←────│ │ IMAP Poll ───│ │ Webhook ←────│          │
│   │     │        │ │     │        │ │ (alle 2 Min) │ │     │        │          │
│   │     ▼        │ │     ▼        │ │     │        │ │     ▼        │          │
│   │ Normalize    │ │ Normalize    │ │     ▼        │ │ ┌──────────┐ │          │
│   │ (Code Node)  │ │ (Code Node)  │ │ Normalize    │ │ │ Whisper  │ │          │
│   │     │        │ │     │        │ │ (Code Node)  │ │ │ (OpenAI) │ │          │
│   │     ▼        │ │     ▼        │ │     │        │ │ └────┬─────┘ │          │
│   │ HTTP POST ───│ │ HTTP POST ───│ │     ▼        │ │      │       │          │
│   │ → MEOS API   │ │ → MEOS API   │ │ HTTP POST ───│ │      ▼       │          │
│   └──────────────┘ └──────────────┘ │ → MEOS API   │ │ HTTP POST ───│          │
│                                     └──────────────┘ │ → MEOS API   │          │
│   ┌──────────────┐                                   └──────────────┘          │
│   │  Workflow 5   │                                                             │
│   │  Kontaktform  │                                                             │
│   │              │                                                             │
│   │ Webhook ←────│  ← WordPress sendet POST                                   │
│   │     │        │                                                             │
│   │     ▼        │                                                             │
│   │ Normalize    │                                                             │
│   │ (Code Node)  │                                                             │
│   │     │        │                                                             │
│   │     ▼        │                                                             │
│   │ HTTP POST ───│                                                             │
│   │ → MEOS API   │                                                             │
│   └──────────────┘                                                             │
│                                                                                │
└────────────────────────────────────────┬───────────────────────────────────────┘
                                         │
                                         │  HTTP POST /api/v1/webhook/*
                                         │  (internes Docker-Netzwerk)
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                │
│                    MEOS:BASE Lead API  (Hostinger VPS)                         │
│                    ════════════════════════════════════                         │
│                    FastAPI · Port 8100 · Docker                                │
│                                                                                │
│   ┌─────────────────────────────────────────────────────────────────┐           │
│   │                    LEAD PIPELINE                                │           │
│   │                                                                 │           │
│   │  ① Lead anlegen                                                 │           │
│   │       │                                                         │           │
│   │       ▼                                                         │           │
│   │  ② Matching Engine ──────────────────────────────────┐          │           │
│   │       │                                              │          │           │
│   │       │  Telefon normalisiert? ──→ Lokaler Match ✅   │          │           │
│   │       │  Email bekannt? ─────────→ Lokaler Match ✅   │          │           │
│   │       │  Telefon in CRM? ────────→ Freund CRM ✅     │          │           │
│   │       │  Email in CRM? ──────────→ Freund CRM ✅     │          │           │
│   │       │  Name ähnlich? ──────────→ Fuzzy Match 🟡    │          │           │
│   │       │  Nichts? ────────────────→ Neuer Prospect 🆕 │          │           │
│   │       │                                              │          │           │
│   │       ▼                          ┌───────────────────┘          │           │
│   │  ③ Kundenmappe befüllen          │                              │           │
│   │       │                          ▼                              │           │
│   │       │              ┌──────────────────────┐                   │           │
│   │       │              │    Freund CRM API     │                   │           │
│   │       │              │  (freund-crm.de)      │                   │           │
│   │       │              │                      │                   │           │
│   │       │              │  GET /contacts?phone= │                   │           │
│   │       │              │  GET /contacts?email= │                   │           │
│   │       │              │  POST /contacts/notes │                   │           │
│   │       │              └──────────────────────┘                   │           │
│   │       ▼                                                         │           │
│   │  ④ Telegram Alert senden ───────────────────→ Telegram Bot API  │           │
│   │       │                                                         │           │
│   │       ▼                                                         │           │
│   │  ⑤ Auto-Reply / Buchungsseite                                   │           │
│   │       │                                                         │           │
│   │       ├── Bestandskunde? → "Danke, melden uns in 24h"          │           │
│   │       │                                                         │           │
│   │       └── Neukunde? → "Danke + hier Termin buchen: [URL]"      │           │
│   │                          │                                      │           │
│   │                          ├──→ WhatsApp Business API             │           │
│   │                          └──→ SMTP (Email)                      │           │
│   └─────────────────────────────────────────────────────────────────┘           │
│                                                                                │
│   ┌──────────────────────────────┐    ┌──────────────────────────────┐          │
│   │       LEAD STORE             │    │       KUNDEN STORE           │          │
│   │                              │    │                              │          │
│   │  GET  /api/v1/leads          │    │  GET  /api/v1/kunden         │          │
│   │  GET  /api/v1/leads/:id      │    │  GET  /api/v1/kunden/:id     │          │
│   │  PATCH /api/v1/leads/:id     │    │  GET  /api/v1/kunden/:id/    │          │
│   │  GET  /api/v1/stats          │    │       kundenmappe            │          │
│   │                              │    │  GET  /api/v1/kunden/:id/    │          │
│   │  leads.json                  │    │       leads                  │          │
│   └──────────────────────────────┘    │                              │          │
│                                       │  kunden.json                 │          │
│                                       └──────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## n8n Workflow-Detail: WhatsApp (Beispiel)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│             │     │              │     │             │     │              │     │             │
│  Webhook    │────→│  Code Node   │────→│  IF Node    │────→│  HTTP POST   │────→│  Respond    │
│  (POST)     │     │  Normalize   │     │  Echte Msg? │     │  → MEOS API  │     │  200 OK     │
│             │     │              │     │             │     │              │     │             │
│ /webhook/   │     │ Extrahiere:  │     │ skip=true?  │     │ POST /api/v1 │     │ {"status":  │
│ whatsapp-   │     │ · telefon    │     │ → ignoriere │     │ /webhook/    │     │  "received"}│
│ incoming    │     │ · name       │     │             │     │ whatsapp     │     │             │
│             │     │ · nachricht  │     │ Nein →      │     │              │     │             │
│ Meta ruft   │     │ · quelle     │     │ weiter      │     │ + Header:    │     │ ← An Meta   │
│ diese URL   │     │              │     │             │     │ X-Webhook-   │     │    zurück    │
│             │     │              │     │             │     │ Secret       │     │             │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
```

## n8n Workflow-Detail: Anruf + Voice-Memo

```
                                                    ┌──────────────┐     ┌──────────────┐
                                                    │              │     │              │
┌─────────────┐     ┌──────────────┐                │  HTTP POST   │────→│  Respond     │
│  Webhook    │────→│  Code Node   │───────────────→│  → MEOS API  │     │  200 OK      │
│  Sipgate    │     │  Normalize   │                │  /webhook/   │     │              │
│  (POST)     │     │  Anruf       │                │  anruf       │     │              │
└─────────────┘     └──────────────┘                └──────────────┘     └──────────────┘


┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Telegram   │────→│  IF Node     │────→│  Get File   │────→│  Whisper     │────→│  HTTP POST   │
│  Trigger    │     │  Hat Voice?  │     │  (Telegram   │     │  (OpenAI)    │     │  → MEOS API  │
│             │     │              │     │   Bot API)   │     │              │     │  /webhook/   │
│ Mario       │     │              │     │              │     │ Audio → Text │     │  anruf       │
│ schickt     │     │              │     │              │     │ (deutsch)    │     │              │
│ Voice-Memo  │     │              │     │              │     │              │     │ transkript:  │
│             │     │              │     │              │     │              │     │ "Herr Maier  │
│             │     │              │     │              │     │              │     │  will Küche" │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘     └──────────────┘
```

---

## Benötigte APIs & Zugangsdaten

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  DIENST                  WAS IHR BRAUCHT              STATUS             │
│  ══════                  ════════════════              ══════             │
│                                                                          │
│  ✅ n8n                   Läuft auf Hostinger VPS       HABT IHR         │
│                                                                          │
│  ⬜ Telegram Bot          Bot-Token + Chat-ID          5 MIN SETUP       │
│     @BotFather            (kostenlos)                                    │
│                                                                          │
│  ⬜ Email IMAP            Host, User, Passwort         HABT IHR          │
│     info@schreinerhelden  von eurem Hoster             (Zugangsdaten)    │
│                                                                          │
│  ⬜ SMTP                  Gleicher Hoster              HABT IHR          │
│     (für Auto-Reply)      smtp.strato.de o.ä.         (Zugangsdaten)    │
│                                                                          │
│  ⬜ Freund CRM            API-URL + API-Key            KLÄREN            │
│     (Kundenstamm)         Hat Freund eine REST API?    (siehe unten)     │
│                                                                          │
│  ⬜ Buchungsseite         URL zu Calendly/Cal.com      EINRICHTEN        │
│     (für Neukunden)       oder eigene Lösung           (10 Min)          │
│                                                                          │
│  ⬜ WhatsApp Business     Meta Business Verifizierung  PHASE 2           │
│     API                   Phone-ID + Token             (1-3 Tage)        │
│                                                                          │
│  ⬜ Messenger API         Facebook Developer App       PHASE 2           │
│     (Facebook)            Page-Token                   (1 Tag)           │
│                                                                          │
│  ⬜ Sipgate               Account + Webhook-Config     PHASE 2           │
│     (Anruf-Webhook)       (optional)                   (optional)        │
│                                                                          │
│  ⬜ OpenAI API            API-Key für Whisper           PHASE 2          │
│     (Voice-Transkription) (nur wenn Voice-Memos)       (optional)        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Docker-Architektur auf dem Hostinger VPS

```
┌─────────────────────────────────────────────────────────────┐
│                    Hostinger VPS                            │
│                                                             │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │                 │         │                 │           │
│  │     n8n         │────────→│   MEOS:BASE     │           │
│  │   (Container)   │  HTTP   │   Lead API      │           │
│  │                 │  POST   │   (Container)   │           │
│  │   Port 5678     │         │   Port 8100     │           │
│  │                 │         │                 │           │
│  └────────┬────────┘         └────────┬────────┘           │
│           │                           │                    │
│           │    Docker Netzwerk        │                    │
│           │    ═══════════════        │                    │
│           └───────────┬───────────────┘                    │
│                       │                                    │
│              ┌────────┴────────┐                           │
│              │     Caddy       │                           │
│              │  (Reverse Proxy)│                           │
│              │   Port 80/443   │                           │
│              └────────┬────────┘                           │
│                       │                                    │
└───────────────────────┼────────────────────────────────────┘
                        │
                   Internet
                        │
            ┌───────────┴───────────┐
            │                       │
    n8n.dein-vps.de     leads.dein-vps.de
```
