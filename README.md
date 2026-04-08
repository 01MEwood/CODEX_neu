# Plusso MVP

Kleiner MVP für die Stundenverrechnungssatz-App (SVS) mit Tier-Logik, Whitelabel-Optionen und API-Berechnung.

## Status zu AGENTS.md, TASK.md, ARCHITECTURE.md

Im aktuellen Stand dieses Repositories sind diese drei Dateien nicht vorhanden. Der MVP wurde daher iterativ aus den vorhandenen Anforderungen im Projektkontext umgesetzt.

## Start (ohne externe Abhängigkeiten)

```bash
python3 plusso_app/app.py
```

Dann öffnen: `http://localhost:5050`

## API-Endpunkte

- `GET /api/health` – Healthcheck
- `POST /api/calculate` – SVS-Berechnung

### Beispiel: SVS berechnen

```bash
curl -s -X POST http://localhost:5050/api/calculate \
  -H 'Content-Type: application/json' \
  -d '{"total_costs":120000,"employee_count":4,"productive_hours":1600,"risk_buffer_pct":5,"regional_avg":70}'
```

## Enthalten (MVP)

- One-Click Eingabemaske (mobil + desktop)
- Tier 1/2/3 Verhalten inkl. Whitelabel-Regeln
- SVS API (`/api/calculate`) mit Ergebnisaufschlüsselung
  - Basis-SVS
  - finaler SVS mit Risikopuffer
  - Benchmark-Differenz + Trend
- Upload-Vorstufe für Tier 2/3
- Sub-Agenten-Plan mit 12 Agenten

## Tests

```bash
python3 -m unittest -v tests/test_svs.py
```
