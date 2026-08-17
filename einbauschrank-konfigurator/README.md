# Einbauschrank-Konfigurator

Sprachgesteuerter Konfigurator für Einbauschränke: Aufmaß bis Maschine aus einem JSON. FreeCAD ist nur der Geometrie-Renderer, die KI nur der Übersetzer — gerechnet wird deterministisch.

**Start hier:** [`WORKFLOW.md`](WORKFLOW.md) — der Master-Workflow (Nordstern, Datenmodell, Architektur, Etappenplan).

## Dateien

| Datei | Inhalt |
|---|---|
| [`WORKFLOW.md`](WORKFLOW.md) | Das Konzept: die vier Gesetze, Kern-Loop, Musk/Bezos/UX-Prinzipien, SWOOD/IMOS-Extrakt, Datenmodell, Architektur, Etappenplan, Disruptionsradar |
| [`beispiele/aufmass.beispiel.json`](beispiele/aufmass.beispiel.json) | IST: die Beispiel-Nische (Mehrpunktmaß, Steckdose, Sockelleiste, offene Punkte) |
| [`beispiele/konfiguration.beispiel.json`](beispiele/konfiguration.beispiel.json) | WUNSCH: drei Elemente, Presets, grifflos — semantisch, ohne Koordinaten |
| [`beispiele/werkregeln.beispiel.json`](beispiele/werkregeln.beispiel.json) | WISSEN: Skizze der Werk-DNA (Raster, Fachbreiten, Verbindungen, Kanten) |

`bauplan.json` (ABLEITUNG) entsteht ab Stufe 1 durch den Generator und wird nie von Hand angelegt.

## Nächster Schritt

Stufe 1 aus dem Etappenplan: Schema v0.1 festziehen und den Korpus-Generator (ohne Bohrungen) bauen — Definition of Done steht in `WORKFLOW.md`, Abschnitt 9.
