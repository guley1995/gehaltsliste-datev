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
    # LA 1000 (Grundlohn / Stundenlohn) wird NICHT per CSV importiert —
    # bleibt manuell in DATEV: Schnellerfassung → Entlohnung →
    # Stunden-/Tageslöhne mit Historie (alte Einträge nicht überschreiben).

    # Zuschlags-Lohnarten: EUR aus Excel → Stunden = EUR / (Stundensatz × Prozent)
    # Beispiel 25% ZS: 16,52 € / (21,53 × 0,25) = 3,07 h
    # DATEV bekommt die Stunden in Spalte 5 (Wert) + Stundensatz in Spalte 6 (Abw. Faktor)
    {"excel_col": "F", "excel_header": "25% ZS",            "lohnart": "1500", "feld": "stunden", "label": "Nachtzuschlag 25% frei",      "umrechnen": "eur_zu_std", "prozent": 0.25},
    {"excel_col": "G", "excel_header": "40% ZS",            "lohnart": "1501", "feld": "stunden", "label": "Nachtzuschlag 40% frei",      "umrechnen": "eur_zu_std", "prozent": 0.40},
    {"excel_col": "H", "excel_header": "50% ZS",            "lohnart": "1510", "feld": "stunden", "label": "Sonntagszuschlag 50% frei",   "umrechnen": "eur_zu_std", "prozent": 0.50},
    {"excel_col": "I", "excel_header": "125% ZS",           "lohnart": "1520", "feld": "stunden", "label": "Feiertagszuschlag 125% frei", "umrechnen": "eur_zu_std", "prozent": 1.25},
    {"excel_col": "J", "excel_header": "150% ZS",           "lohnart": "1521", "feld": "stunden", "label": "Zuschlag 150% frei",          "umrechnen": "eur_zu_std", "prozent": 1.50},

    # Urlaub (Spalte Q "Urlaubsentgeld" in EUR) → Stunden = EUR / Stundensatz
    {"excel_col": "Q", "excel_header": "Urlaubsentgeld",    "lohnart": "1600", "feld": "stunden", "label": "Urlaub (EUR/Stundensatz → Std)", "umrechnen": "eur_zu_std", "prozent": 1.00},

    # EUR-Lohnarten direkt (keine Umrechnung)
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
