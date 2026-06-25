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
    # Alle Lohnarten sind EUR-Beträge (im Gegensatz zu Mietwagen wo viele Stunden waren)
    {"excel_col": "D", "excel_header": "Grundlohn",         "lohnart": "1000", "feld": "wert", "label": "Stundenlohn / Grundlohn"},
    {"excel_col": "E", "excel_header": "Verpfl. ZS",        "lohnart": "9650", "feld": "wert", "label": "Verpflegungszuschuss"},
    {"excel_col": "F", "excel_header": "25% ZS",            "lohnart": "1500", "feld": "wert", "label": "Nachtzuschlag 25% frei"},
    {"excel_col": "G", "excel_header": "40% ZS",            "lohnart": "1501", "feld": "wert", "label": "Nachtzuschlag 40% frei"},
    {"excel_col": "H", "excel_header": "50% ZS",            "lohnart": "1510", "feld": "wert", "label": "Sonntagszuschlag 50% frei"},
    {"excel_col": "I", "excel_header": "125% ZS",           "lohnart": "1520", "feld": "wert", "label": "Feiertagszuschlag 125% frei"},
    {"excel_col": "J", "excel_header": "150% ZS",           "lohnart": "1521", "feld": "wert", "label": "Zuschlag 150% frei"},
    # Abschlag (Spalte L) = ausgezahltes Bargeld, in DATEV als negative Buchung (Einbehaltenes Bargeld)
    {"excel_col": "L", "excel_header": "Abschlag",          "lohnart": "9001", "feld": "wert", "label": "Einbehaltenes Bargeld", "vorzeichen_umkehren": True},
    # Vorschuss (Spalte M) als Abzug
    {"excel_col": "M", "excel_header": "Vorschuss",         "lohnart": "9000", "feld": "wert", "label": "Vorschuss", "vorzeichen_umkehren": True},
    # Urlaubsentgeld (Q) direkt als EUR — bei Taxi ist es bereits berechnet, nicht durch Stundensatz teilen
    {"excel_col": "Q", "excel_header": "Urlaubsentgeld",    "lohnart": "1600", "feld": "wert", "label": "Urlaub (EUR direkt)"},
]

# Werte aus diesen Spalten werden in der App nur als Hinweis angezeigt, nicht importiert.
MANUELL_IN_DATEV = [
    {"excel_col": "R", "excel_header": "Soz.A", "lohnart": "?",
     "hinweis": "Soz.A (Sozialabgaben-Pauschale?) — Lohnart noch klären. Aktuell NICHT in CSV. "
                "Bei Bedarf manuell in DATEV nachtragen."},
]
