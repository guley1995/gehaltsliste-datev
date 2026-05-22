"""
Mapping Excel-Spalte (Gehalt-Sheet) -> DATEV-Lohnart.
Anpassbar pro Mandant falls Lohnarten abweichen.
"""

LOHNART_MAPPING = [
    {"excel_col": "C", "excel_header": "Arbeitsstunden",                "lohnart": "1000", "feld": "stunden", "label": "Stundenlohn"},
    {"excel_col": "F", "excel_header": "Stunden. Zuschlag 25% gesamt",  "lohnart": "1500", "feld": "stunden", "label": "Nachtzuschlag 25% frei"},
    {"excel_col": "G", "excel_header": "Stunden. Zuschlag 40% (00:00-04:00)", "lohnart": "1501", "feld": "stunden", "label": "Nachtzuschlag 40% frei"},
    {"excel_col": "H", "excel_header": "Stunden. Sonntagszuschlag  50%","lohnart": "1510", "feld": "stunden", "label": "Sonntagszuschlag 50% frei"},
    {"excel_col": "I", "excel_header": "Stunden. Feiertagszuschlag 125%","lohnart": "1520", "feld": "stunden", "label": "Feiertagszuschlag 125% frei"},
    {"excel_col": "M", "excel_header": "Einbehaltenes Bargeld",         "lohnart": "9001", "feld": "wert",    "label": "Einbehaltenes Bargeld"},
    {"excel_col": "N", "excel_header": "Verpflegungspauschale",         "lohnart": "9650", "feld": "wert",    "label": "Verpflegungszuschuss"},
    {"excel_col": "P", "excel_header": "Trinkgeld von Fahrgästen",      "lohnart": "9652", "feld": "wert",    "label": "Trinkgeld von Fahrgästen"},
]

UNGEKLAERTE_SPALTEN = [
    {"excel_col": "K", "excel_header": "€. Grundgehalt",          "hinweis": "Festbezug? LA-Nummer noch klären."},
    {"excel_col": "L", "excel_header": "Vorschuss",               "hinweis": "LA-Nummer für Vorschuss noch klären."},
    {"excel_col": "O", "excel_header": "Fughafengebühr",          "hinweis": "LA-Nummer für Flughafengebühr noch klären."},
    {"excel_col": "Q", "excel_header": "Urlaub",                  "hinweis": "Als Lohnart oder Abwesenheitstage? Klären."},
    {"excel_col": "R", "excel_header": "Krank",                   "hinweis": "Als Lohnart oder AU-Tage? Klären."},
]
