# Gehaltsliste → DATEV Lohn und Gehalt

Streamlit-Tool, das eine Monats-Gehaltsliste (Excel) von Mietwagen-Mandanten in eine **ASCII-Importdatei für DATEV Lohn und Gehalt (Monatserfassung)** umwandelt. Spart das händische Eintippen der Monatswerte pro Mitarbeiter in der DATEV-Monatserfassungsmaske.

**Datenschutz:** Läuft als [stlite](https://stlite.net/) komplett im Browser — Excel-Dateien werden **nie** auf einen Server hochgeladen. Lohndaten verlassen den Rechner des Nutzers nicht.

## Live-App

➡️ **https://guley1995.github.io/gehaltsliste-datev/**

Zugangspasswort konfigurierbar in [`config.py`](config.py).

## Was die App macht

1. Excel mit `Gehalt`-Übersichts-Sheet hochladen.
2. App liest pro Mitarbeiter die Monatswerte, validiert die Header und erzeugt eine 9-Spalten-CSV mit Header-Zeile im DATEV-Format:
   ```
   Beraternr;Mandantennr;MM/JJJJ
   PersNr;Lohnart;;;Wert;;;;
   …
   ```
3. Du lädst die CSV in DATEV unter `Erfassen → Bewegungsdaten → Importieren` → Tab `Monatserfassung`.

## Lohnart-Mapping

Konfiguriert in [`mapping.py`](mapping.py):

| Excel-Spalte | Inhalt | DATEV-Lohnart |
|---|---|---|
| C `Arbeitsstunden` | Std | 1000 Stundenlohn |
| F `Zuschlag 25% gesamt` | Std | 1500 Nachtzuschlag 25% frei |
| G `Zuschlag 40%` | Std | 1501 Nachtzuschlag 40% frei |
| H `Sonntagszuschlag 50%` | Std | 1510 Sonntagszuschlag 50% frei |
| I `Feiertagszuschlag 125%` | Std | 1520 Feiertagszuschlag 125% frei |
| Q `Urlaub` | EUR | 1600 Urlaub (EUR/Stundensatz → Std) |
| L `Vorschuss` | EUR | 9000 Vorschuss |
| M `Einbehaltenes Bargeld` | EUR | 9001 Einbehaltenes Bargeld |
| N `Verpflegungspauschale` | EUR | 9650 Verpflegungszuschuss |
| O `Flughafengebühr` | EUR | 9651 Flughafengebühr |
| P `Trinkgeld von Fahrgästen` | EUR | 9652 Trinkgeld von Fahrgästen |

Spalte **R `Krank`** (LA 1650) wird **nicht** in die CSV geschrieben — die Krank-Tage werden direkt im DATEV-Kalender gepflegt.  
Spalte **K `Grundgehalt`** ist eine Excel-interne Prüfsumme (B × C) und dient nur dem Soll-Abgleich nach Import.

## CSV-Format (DATEV Lohn und Gehalt — Monatserfassung)

**Zeile 1 (Pflicht-Header):**
```
Beraternr;Mandantennr;MM/JJJJ
```
z.B. `1479590;10010;05/2026`.

**Ab Zeile 2 — 9 Spalten:**

| # | Feld | Inhalt |
|---|---|---|
| 1 | Personalnummer | aus dem PersNr-Mapping pro Firma |
| 2 | Lohnartennummer | siehe Mapping oben |
| 3 | Stundenanzahl | **immer leer** (DATEV-Feld hat hartes 24h-Limit) |
| 4 | Tagesanzahl | leer |
| 5 | **Wert** | **hier kommen alle Werte rein — Std UND EUR.** DATEV erkennt anhand der Lohnart. |
| 6 | Abweichender Faktor | leer |
| 7 | Abweichende Lohnveränderung | leer |
| 8 | Kostenstellennummer | leer |
| 9 | Kostenträger | leer |

Trennzeichen Semikolon, Dezimaltrenner Komma, Encoding ANSI/CP1252, Zeilenende CRLF.

## Einmalige DATEV-Einrichtung pro Mandant

In DATEV Lohn und Gehalt:

1. Mandant öffnen → `Extras → ASCII-Import Assistent` → **Neu**
2. Profilname (z.B. `Huen Monat`)
3. Datei-Format: Strichpunkt-Trennzeichen, Enter als Datensatztrennzeichen, Komma als Dezimaltrennzeichen
4. **Aufbau des Datensatzes** — genau die 9 Spalten oben mappen, **OHNE** Kalendertag und **OHNE** Ausfallschlüssel
5. Speichern

Danach monatlich pro Mandant: `Erfassen → Bewegungsdaten → Importieren` → Hersteller (z.B. `Huen Monat`) → Tab `Monatserfassung` → CSV-Datei → **Übernehmen**.

## Multi-Mandanten-Workflow

Die App unterstützt beliebig viele Mandanten parallel:

- **Mandanten-Stammdaten** (Berater-Nr + Mandanten-Nr pro Firma) werden im Browser-LocalStorage gespeichert.
- **PersNr-Mapping** (Name → DATEV-Personalnummer) pro Firma im Browser.
- **Backup/Restore:** Sidebar-Buttons „Mappings exportieren" / „importieren" als JSON.
- Bei Excel-Upload erkennt die App den Firmennamen aus dem Dateinamen und **mappt fuzzy** auf den vollen DATEV-Mandantennamen (z.B. „Wittys" → „Wittys Shuttleservice GmbH").

## Lokal entwickeln / testen

```bash
pip3 install -r requirements.txt
streamlit run app.py
```

## Deploy

Automatisch via GitHub Pages: jeder Push auf `main` wird live unter https://guley1995.github.io/gehaltsliste-datev/.

In `index.html` wird der Cache-Buster `?v=<timestamp>` bei jedem Reload neu gesetzt, damit Browser-Cache nicht hängenbleibt.

## Files

- [`app.py`](app.py) — Streamlit-UI (Multi-Upload, PersNr-Editor, Vorschau, Download)
- [`parser.py`](parser.py) — Excel-Parser inkl. Header-Schema-Validierung
- [`writer.py`](writer.py) — DATEV-CSV-Generator mit Modus `MODUS_MONAT` / `MODUS_KALENDER`
- [`mapping.py`](mapping.py) — Lohnart-Mapping
- [`config.py`](config.py) — Passwort + Logo
- [`index.html`](index.html) — stlite-Loader
- [`requirements.txt`](requirements.txt) — Python-Abhängigkeiten (für lokale Entwicklung)
