# Gehaltsliste → DATEV Lohn und Gehalt

Streamlit-Tool, das eine Monats-Gehaltsliste (Excel) von Mietwagen-Mandanten in eine **ASCII-Importdatei für DATEV Lohn und Gehalt** umwandelt. Spart das händische Eintippen der Monatswerte pro Mitarbeiter in der DATEV-Monatserfassung.

**Datenschutz:** Läuft als [stlite](https://stlite.net/) komplett im Browser — Excel-Dateien werden **nie** auf einen Server hochgeladen. Lohndaten verlassen den Rechner des Nutzers nicht.

## Live-App

➡️ **https://USERNAME.github.io/REPO/** (wird nach Deploy gesetzt)

## Was die App macht

1. Excel mit `Gehalt`-Übersichts-Sheet hochladen.
2. App liest pro Mitarbeiter die Monatswerte und ermittelt die Personalnummer aus dem zugehörigen Mitarbeiter-Tab (Tabname `Alit Caka_1` → PersNr `1`).
3. Erzeugt eine 11-Spalten-CSV im DATEV-Format:
   `PersNr; Kalendertag; Ausfallschl; Lohnart; Std; Tage; Wert; Faktor; LohnVer; KostST; KostTr`
4. Du lädst die CSV in DATEV unter `Erfassen → Bewegungsdaten → Importieren`.

## Lohnart-Mapping

Konfiguriert in [`mapping.py`](mapping.py):

| Excel-Spalte | Inhalt | DATEV-Lohnart |
|---|---|---|
| C `Arbeitsstunden` | Std | 1000 Stundenlohn |
| F `Zuschlag 25% gesamt` | Std | 1500 Nachtzuschlag 25% frei |
| G `Zuschlag 40%` | Std | 1501 Nachtzuschlag 40% frei |
| H `Sonntagszuschlag 50%` | Std | 1510 Sonntagszuschlag 50% frei |
| I `Feiertagszuschlag 125%` | Std | 1520 Feiertagszuschlag 125% frei |
| M `Einbehaltenes Bargeld` | EUR | 9001 Einbehaltenes Bargeld |
| N `Verpflegungspauschale` | EUR | 9650 Verpflegungszuschuss |
| P `Trinkgeld von Fahrgästen` | EUR | 9652 Trinkgeld von Fahrgästen |

Ungeklärt (kommen als Warnung, nicht in die CSV): K Grundgehalt, L Vorschuss, O Flughafengebühr, Q Urlaub, R Krank.

## Einmalige DATEV-Einrichtung pro Mandant

In DATEV Lohn und Gehalt:

1. `Extras → ASCII-Import Assistent` → neues Format anlegen (z.B. „Mietwagen Monatswerte").
2. Feldtrennzeichen: Semikolon `;`. Encoding ANSI/CP1252.
3. Felder in dieser Reihenfolge zuordnen: Personalnummer, Kalendertag, Ausfallschlüssel, Lohnartennummer, Stundenanzahl, Tagesanzahl, Wert, Faktor, Lohnveränderung, Kostenstelle, Kostenträger.
4. Speichern.

Danach monatlich: `Erfassen → Bewegungsdaten → Importieren` → Profil wählen → CSV-Datei → Import.

## Lokal entwickeln / testen

```bash
pip3 install -r requirements.txt
streamlit run app.py
```

## Deploy

Automatisch via GitHub Pages: jeder Push auf `main` wird live unter `https://USERNAME.github.io/REPO/`.

## Files

- `app.py` — Streamlit-UI (Multi-Upload, Vorschau, Download)
- `parser.py` — Excel-Parser
- `writer.py` — DATEV-CSV-Generator
- `mapping.py` — Lohnart-Mapping (hier anpassen, falls Mandant andere Lohnarten nutzt)
- `index.html` — stlite-Loader für Browser-Betrieb
- `requirements.txt` — Python-Abhängigkeiten (für lokale Entwicklung)
