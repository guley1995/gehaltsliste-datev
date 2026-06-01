"""
Mapping Excel-Spalte (Gehalt-Sheet) -> DATEV-Lohnart.
Anpassbar pro Mandant falls Lohnarten abweichen.
"""

# Stundensatz pro Mitarbeiter steht in Excel-Spalte B. Wird für die
# Umrechnung Urlaub (€) -> Urlaubsstunden gebraucht.
STUNDENSATZ_COL = "B"

LOHNART_MAPPING = [
    # Arbeitsstunden & Zuschläge (Stunden)
    {"excel_col": "C", "excel_header": "Arbeitsstunden",                       "lohnart": "1000", "feld": "stunden", "label": "Stundenlohn"},
    {"excel_col": "F", "excel_header": "Stunden. Zuschlag 25% gesamt",         "lohnart": "1500", "feld": "stunden", "label": "Nachtzuschlag 25% frei"},
    {"excel_col": "G", "excel_header": "Stunden. Zuschlag 40% (00:00-04:00)",  "lohnart": "1501", "feld": "stunden", "label": "Nachtzuschlag 40% frei"},
    {"excel_col": "H", "excel_header": "Stunden. Sonntagszuschlag  50%",       "lohnart": "1510", "feld": "stunden", "label": "Sonntagszuschlag 50% frei"},
    {"excel_col": "I", "excel_header": "Stunden. Feiertagszuschlag 125%",      "lohnart": "1520", "feld": "stunden", "label": "Feiertagszuschlag 125% frei"},
    # Urlaub: Excel hat €, DATEV will Stunden -> teilen durch Stundensatz
    {"excel_col": "Q", "excel_header": "Urlaub",                               "lohnart": "1600", "feld": "stunden", "label": "Urlaub", "umrechnen": "eur_durch_stundensatz"},
    # EUR-Beträge
    {"excel_col": "L", "excel_header": "Vorschuss",                            "lohnart": "9000", "feld": "wert",    "label": "Vorschuss"},
    {"excel_col": "M", "excel_header": "Einbehaltenes Bargeld",                "lohnart": "9001", "feld": "wert",    "label": "Einbehaltenes Bargeld"},
    {"excel_col": "N", "excel_header": "Verpflegungspauschale",                "lohnart": "9650", "feld": "wert",    "label": "Verpflegungszuschuss"},
    {"excel_col": "O", "excel_header": "Fughafengebühr",                       "lohnart": "9651", "feld": "wert",    "label": "Flughafengebühr"},
    {"excel_col": "P", "excel_header": "Trinkgeld von Fahrgästen",             "lohnart": "9652", "feld": "wert",    "label": "Trinkgeld von Fahrgästen"},
]

# Nicht in den DATEV-Import übernehmen — wird in DATEV anderswo gepflegt.
# Werte aus diesen Spalten werden in der App nur als Hinweis angezeigt.
MANUELL_IN_DATEV = [
    {"excel_col": "R", "excel_header": "Krank", "lohnart": "1650",
     "hinweis": "LA 1650 Krank wird über den DATEV-Kalender gepflegt (AU-Tage). "
                "Nicht via CSV-Import — bitte sicherstellen, dass die AU-Tage im "
                "DATEV-Kalender erfasst sind."},
]

# Spalte K (€. Grundgehalt) wird in der Excel als B*C berechnet und dient
# nur als Soll-Wert zur Kontrolle nach dem DATEV-Import. NICHT importieren.
KONTROLL_GRUNDGEHALT_COL = "K"
