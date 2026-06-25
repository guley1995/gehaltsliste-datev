"""
Lohnart-Mapping für TAXI-Lohnlisten (Sheet1, Header in Zeile 4).

Unterschiede zu Mietwagen:
- Alle Werte sind bereits in EUR (nicht Stunden × Satz)
- Andere Zuschlagsstruktur: 25% / 40% / 50% / 125% / 150%
- Stundensatz steht in eigener Spalte (S) — wird in CSV-Spalte 6 (Faktor) mitgegeben
- Vorschuss + Abschlag werden negativ gebucht (App invertiert Vorzeichen)
"""

# Stundensatz pro Mitarbeiter steht in Excel-Spalte S
STUNDENSATZ_COL = "S"

# Brutto-Spalte (K) ist nur Kontroll-Summe, NICHT importieren
KONTROLL_BRUTTO_COL = "K"

# Header-Zeile in der Excel (Mietwagen war Zeile 1, Taxi ist Zeile 4)
HEADER_ROW = 4
DATEN_START_ROW = 6  # Zeile 5 ist meist leer

# Info-Spalte (Freitext-Notizen) — wie Mietwagen-Spalte W
INFO_COL = "T"

LOHNART_MAPPING = [
    # Nur EUR-Lohnarten werden in die CSV exportiert.
    # Stunden-Lohnarten (Grundlohn / 25% / 40% / 50% / 125% / 150% / Urlaub)
    # werden NICHT per CSV importiert — sie werden in DATEV manuell gepflegt
    # (Schnellerfassung → Entlohnung → Stunden-/Tageslöhne mit Historie).
    {"excel_col": "E", "excel_header": "Verpfl. ZS",        "lohnart": "9650", "feld": "wert", "label": "Verpflegungszuschuss"},
    {"excel_col": "L", "excel_header": "Abschlag",          "lohnart": "9001", "feld": "wert", "label": "Einbehaltenes Bargeld", "vorzeichen_umkehren": True},
    {"excel_col": "M", "excel_header": "Vorschuss",         "lohnart": "9000", "feld": "wert", "label": "Vorschuss",             "vorzeichen_umkehren": True},
]

# Werte aus diesen Spalten werden in der App nur als Hinweis angezeigt, nicht importiert.
MANUELL_IN_DATEV = [
    {"excel_col": "R", "excel_header": "Soz.A", "lohnart": "?",
     "hinweis": "Soz.A (Sozialabgaben-Pauschale?) — Lohnart noch klären. Aktuell NICHT in CSV. "
                "Bei Bedarf manuell in DATEV nachtragen."},
]
