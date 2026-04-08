# Plusso – Phase 1: Forschung, Agentenstruktur und Geschäftsmodell

## 1) Zielbild (MVP bis Tier-3-Roadmap)

**Produktname:** Plusso  
**Kernnutzen:** Handwerksbetriebe erhalten in wenigen Schritten einen belastbaren Stundenverrechnungssatz (SVS) aus betriebswirtschaftlichen Daten (BWA + Team-/Stundenparameter), inkl. verständlicher Einordnung.

### One-Click-Prinzip (UX-Leitidee)
1. **Datenquelle wählen:** Manuell / Foto / PDF / Screenshot
2. **BWA-Felder prüfen:** Erkannte Felder bestätigen oder korrigieren
3. **Personalparameter:** Anzahl Mitarbeiter, produktive Stunden, ggf. Zuschläge
4. **Berechnung:** SVS + Ampel (unter/über Benchmark)
5. **Ergebnis sichern:** PDF-Bericht, Export, optional Beratungstermin

---

## 2) Tier-Modell (Produktstrategie)

## Tier 1 – Lead Magnet (kostenlos)
- Manuelle Dateneingabe
- Basis-SVS-Rechner
- Einfaches PDF-Ergebnis mit Plusso-Branding (kein Whitelabel)
- Ziel: Lead-Generierung für Upsell in Tier 2/3

## Tier 2 – Smart Input (Web-App)
- Upload: Foto, PDF, Screenshot
- OCR + semantische Feldzuordnung (BWA-zu-SVS)
- Mobile-first Web-App
- Whitelabel Light: eigenes Logo + Kontaktdaten
- FAQ/Knowledge-Base integriert

## Tier 3 – Pro Intelligence
- Umkalkulationen und Szenario-Rechner
- Regionalvergleich mit anonymisierten Peer-Werten
- Erweiterte KPI-Insights + Alerts
- Whitelabel Pro (Mandanten-/Partnerfähigkeit)

---

## 3) Acht Sub-Agenten (Arbeitsauftrag & Deliverables)

## Agent 1 – **Product Scope & Requirements**
**Mission:** Anforderungen je Tier schärfen.  
**Ergebnis:** PRD mit Must/Should/Could, User Journeys, Abnahmekriterien.

## Agent 2 – **Data Model & SVS-Engine**
**Mission:** Formelwerk, Datenfelder, Validierungslogik definieren.  
**Ergebnis:** Rechenmodell, Eingabe-/Ausgabe-Schema, Fehlergrenzen, Plausibilitätsregeln.

## Agent 3 – **OCR/Document Ingestion**
**Mission:** Pipeline für Foto/PDF/Screenshot entwerfen (Tier 2/3).  
**Ergebnis:** Architektur für Upload, OCR, Feldmapping, Confidence-Scoring, Review-UI.

## Agent 4 – **UX/UI & One-Click Flow**
**Mission:** Idiotensicheren Schritt-für-Schritt-Flow entwickeln.  
**Ergebnis:** Wireframes, Komponentenleitfaden, mobile/tablet/desktop Breakpoints, Accessibility-Regeln.

## Agent 5 – **Benchmark & Regional Intelligence**
**Mission:** Öffentliche Vergleichsdatenquellen identifizieren und nutzen.  
**Ergebnis:** Datenquellenkatalog, Aktualisierungslogik, Anonymisierungskonzept, Vergleichsmetriken.

## Agent 6 – **Knowledge-Base & FAQ Agent**
**Mission:** Wissenssystem für SVS-Fragen in Tier 2/3 aufbauen.  
**Ergebnis:** FAQ-Taxonomie, Redaktionsprozess, Quellen-Policy (nur öffentliche Daten), In-App-Pattern.

## Agent 7 – **Monetization & Pricing Agent**
**Mission:** Zahlungsmodell + Verpackung + Conversion-Trichter.  
**Ergebnis:** Preismodell, Zahlungsarten, Upgrade-Logik, Unit Economics, Angebotsseitenstruktur.

## Agent 8 – **Whitelabel & Partner System**
**Mission:** Rollen-/Branding-System für Betriebe, Berater, Innungen.  
**Ergebnis:** Rechtekonzept, Branding-Matrix (Tier 1/2/3), Onboarding-Flow, Partnerpakete.

---

## 4) Monetarisierungsmodell (Startvorschlag)

## Preisarchitektur
- **Tier 1 (Free):** 0 €, 1 Nutzer, manuell, Plusso-Brand fix
- **Tier 2 (Pro):** monatlich (z. B. 29–79 €), OCR-Kontingent, Export, Whitelabel Light
- **Tier 3 (Business):** monatlich (z. B. 99–299 €), Regional-Benchmark, Szenarien, Multi-User, Whitelabel Pro

## Add-ons
- OCR-Zusatzkontingente
- Beratungsreport als Premium-PDF
- API/CSV-Export
- Partnerzugänge (Steuerberater/Verbände)

## Zahlungsmodell
- Stripe/SEPA/Kreditkarte
- Monats- und Jahresplan (Jahresplan mit Rabatt)
- In-App-Upgrades bei Nutzungslimits
- Kündigung self-service, DSGVO-konforme Datenlöschung

## Funnel
1. Kostenloser Rechner (Tier 1)
2. Ergebnis mit klaren „Nächster Schritt“-Hinweisen
3. Testphase Tier 2 (7–14 Tage)
4. Aktivierung über OCR-Mehrwert + FAQ + Export
5. Upsell Tier 3 über Regionalvergleich und Szenario-Simulation

---

## 5) White-Label-System (Regelwerk)

## Branding-Matrix
- **Tier 1:** Plusso-Logo fix, keine Markenanpassung
- **Tier 2:** eigenes Logo, Kontaktdaten, Farb-Akzent
- **Tier 3:** volles Whitelabel inkl. Subdomain/Partner-Dashboard

## Technische Leitplanken
- Branding je Mandant als Theme-Konfiguration
- Vorlagenbasierte PDF-Ausgabe je Tier
- Rechtebasiertes Freischalten von White-Label-Features

---

## 6) Frei verfügbare Daten – Startstrategie

Für den Produktstart werden **nur öffentlich verfügbare, zitierbare Daten** verwendet.

## Quellenkategorien
1. **Verbands-/Innungsveröffentlichungen** (Betriebsvergleich, Branchenkennzahlen)
2. **Offizielle Statistikquellen** (z. B. Destatis, Länder-/Kammerberichte)
3. **Offene Fachpublikationen** mit klarer Veröffentlichungsgrundlage

## Daten-Governance
- Jede Kennzahl erhält Metadaten: Quelle, Stichtag, Region, Branche, Erhebungsmethodik
- Keine Nutzung proprietärer oder geschützter Vergleichsdaten ohne Lizenz
- Sichtbarer Quellenhinweis im Ergebnisbericht

---

## 7) Technische Grundarchitektur (VPS-freundlich)

- **Frontend:** React/Next.js (responsive, PWA-fähig)
- **Backend:** Node.js/NestJS oder Python/FastAPI
- **DB:** PostgreSQL
- **Dateispeicher:** S3-kompatibel (optional)
- **OCR-Layer:** austauschbar (Cloud-OCR oder self-hosted Pipeline)
- **Deployment:** Docker + Reverse Proxy (Nginx/Caddy) auf Hostinger VPS
- **Observability:** Logging, Error-Tracking, Audit-Events

---

## 8) Phase-1-Ergebnis (was als Nächstes entschieden werden soll)

1. Zielbranche(n) zum Start (z. B. SHK, Elektro, Dachdecker, **Schreiner/Tischler, Parkettleger, Zimmerer**)
2. Primäre Datenquellen für Start-Benchmarks (konkret benennen)
3. Exaktes Preisschema pro Tier (inkl. OCR-Limits)
4. Welche Whitelabel-Optionen in Tier 2 „Pflicht“ sind
5. Ob Tier-2-Testphase zeit- oder nutzungsbasiert startet

---

## Branchen-Fokus (ergänzt)
- Plusso wird von Beginn an **gewerkeübergreifend** konzipiert, inkl. **Schreiner/Tischler, Parkettleger und Zimmerer**.
- Benchmark- und FAQ-Inhalte werden je Gewerk separat pflegbar aufgebaut, damit Kennzahlen und Begriffe branchenspezifisch passen.
- In der SVS-Engine werden gewerkspezifische Kosten-/Stundenprofile als konfigurierbare Parameter vorgesehen.

---

## 9) Konkreter 14-Tage-Startplan

- **Tag 1–2:** PRD + Datenfeldliste + rechtliche Leitplanken
- **Tag 3–5:** UX-Flow + Klickdummy + Ergebnisreport-Layout
- **Tag 6–8:** SVS-Engine MVP (manuelle Eingabe, Tier 1)
- **Tag 9–10:** OCR-Prototyp für 2–3 BWA-Layouts
- **Tag 11–12:** Pricing/Paywall + Whitelabel-Konfiguration (Basis)
- **Tag 13:** QA mit 5 Beispielbetrieben (anonymisierte Testdaten)
- **Tag 14:** Launch Tier 1 + Warteliste Tier 2
