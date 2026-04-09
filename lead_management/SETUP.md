# MEOS:BASE Lead Management — Setup auf Hostinger VPS

## Übersicht

```
WhatsApp Business API ─┐
Facebook Messenger ────┤
Email (IMAP) ──────────┼→ n8n (Hostinger VPS) → MEOS:BASE API → Lead-Objekt
Sipgate / Anruf ───────┤                                         ↓
WordPress Formular ────┘                                    Telegram Alert
                                                            + Auto-Reply
```

---

## 1. Voraussetzungen

- [x] Hostinger VPS mit Docker + Docker Compose
- [x] n8n läuft bereits auf dem VPS
- [ ] Domain/Subdomain für die Lead-API (z.B. `leads.schreinerhelden.de`)
- [ ] Telegram Bot erstellt (@BotFather)
- [ ] WhatsApp Business API Zugang (optional, Phase 2)

---

## 2. Lead-API deployen

```bash
# Auf dem VPS:
cd /opt/meos
git clone <repo-url> lead-management
cd lead-management/lead_management

# .env erstellen
cp .env.example .env
nano .env  # Werte ausfüllen!

# Starten
docker compose up -d

# Testen
curl http://localhost:8100/health
# → {"status":"ok","service":"MEOS:BASE Lead Management"}
```

### Reverse Proxy (Caddy)

Falls du Caddy nutzt, füge in `/etc/caddy/Caddyfile` hinzu:

```
leads.schreinerhelden.de {
    reverse_proxy localhost:8100
}
```

```bash
sudo systemctl reload caddy
```

---

## 3. Telegram Bot einrichten

1. Öffne @BotFather in Telegram
2. `/newbot` → Name: `Schreinerhelden Leads`
3. Token kopieren → in `.env` als `MEOS_TELEGRAM_BOT_TOKEN`
4. Bot zur Team-Gruppe hinzufügen
5. Chat-ID herausfinden:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```
   Die `chat.id` kopieren → in `.env` als `MEOS_TELEGRAM_CHAT_ID`

---

## 4. n8n Workflows importieren

In deiner n8n-Instanz auf dem Hostinger VPS:

1. **Einstellungen → Environment Variables** setzen:
   ```
   MEOS_API_URL=https://leads.schreinerhelden.de  (oder http://meos-lead-api:8100 wenn im selben Docker-Netzwerk)
   MEOS_WEBHOOK_SECRET=dein-secret-aus-der-env
   TELEGRAM_BOT_TOKEN=dein-telegram-bot-token
   MESSENGER_PAGE_TOKEN=dein-facebook-page-token
   OPENAI_API_KEY=dein-openai-key  (nur für Voice-Memo Transkription)
   ```

2. **Workflows importieren** (Menü → Import from File):
   - `workflows/01_whatsapp_lead.json`
   - `workflows/02_messenger_lead.json`
   - `workflows/03_email_lead.json`
   - `workflows/04_anruf_voice_lead.json`
   - `workflows/05_kontaktformular_lead.json`

3. **Jeden Workflow aktivieren** (Toggle oben rechts)

---

## 5. Kanäle anbinden

### Email (sofort machbar!)

Der einfachste Kanal — brauchst nur die IMAP-Daten:

1. In n8n: Workflow `03_email_lead` öffnen
2. Email-Trigger Node → Credentials eintragen:
   - IMAP Host: `imap.strato.de` (oder euer Provider)
   - User: `info@schreinerhelden.de`
   - Passwort: euer Email-Passwort
   - Port: 993, SSL: true
3. Aktivieren → jede neue Email wird zum Lead

### WordPress Kontaktformular (sofort machbar!)

Option A — CF7 Plugin mit Webhook:
In `functions.php` deines WordPress-Themes:

```php
add_action('wpcf7_mail_sent', function($cf7) {
    $submission = WPCF7_Submission::get_instance();
    $data = $submission->get_posted_data();
    
    wp_remote_post('https://n8n.dein-vps.de/webhook/kontaktformular-incoming', [
        'body' => json_encode($data),
        'headers' => ['Content-Type' => 'application/json'],
    ]);
});
```

Option B — WPForms hat einen eingebauten Webhook-Addon.

### WhatsApp Business API (Phase 2)

1. Meta Business Suite → WhatsApp → API Setup
2. Webhook URL eintragen: `https://n8n.dein-vps.de/webhook/whatsapp-incoming`
3. Verify Token eintragen (gleicher wie in `.env`)
4. Events subscriben: `messages`

**Wichtig:** WhatsApp Business API braucht ein verifiziertes Business-Konto bei Meta. Das dauert 1-3 Tage.

### Facebook Messenger (Phase 2)

1. Facebook Developer Portal → App erstellen
2. Messenger Product hinzufügen
3. Webhook URL: `https://n8n.dein-vps.de/webhook/messenger-incoming`
4. Page subscriben

### Anruf / Voice-Memo (Phase 2)

**Option A — Sipgate:**
1. Sipgate Account → Einstellungen → Webhooks
2. URL: `https://n8n.dein-vps.de/webhook/anruf-incoming`

**Option B — Voice-Memo (sofort machbar!):**
1. Telegram Bot ist schon eingerichtet (Schritt 3)
2. Workflow `04_anruf_voice_lead` aktivieren
3. Mario schickt nach jedem Anruf ein Voice-Memo an den Bot
4. n8n transkribiert mit Whisper → Lead wird angelegt

---

## 6. Testen

```bash
# Lead manuell anlegen
curl -X POST https://leads.schreinerhelden.de/api/v1/webhook/lead \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: dein-secret" \
  -d '{
    "kanal": "whatsapp",
    "name": "Petra Müller",
    "telefon": "+49 171 1234567",
    "nachricht": "Schrank für Dachschräge, ca 4m breit",
    "quelle": "Instagram Story"
  }'

# Alle Leads anzeigen
curl https://leads.schreinerhelden.de/api/v1/leads

# Dashboard Stats
curl https://leads.schreinerhelden.de/api/v1/stats
```

---

## 7. Reihenfolge der Umsetzung

| Phase | Kanal | Aufwand | Was ihr braucht |
|-------|-------|---------|-----------------|
| **1** | Email | 30 Min | IMAP-Zugangsdaten |
| **1** | Kontaktformular | 30 Min | WordPress Admin-Zugang |
| **1** | Voice-Memo | 15 Min | Telegram Bot (schon da) |
| **2** | WhatsApp Business API | 2-3 Tage | Meta Business Verifizierung |
| **2** | Facebook Messenger | 1 Tag | Facebook Developer Account |
| **3** | Sipgate Anruf-Webhook | 1 Std | Sipgate Account |

**Phase 1 könnt ihr heute noch machen.**
