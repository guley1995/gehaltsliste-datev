"""
Schreibt die 11-Spalten-DATEV-CSV für den ASCII-Import in
'Lohn und Gehalt' (Erfassen -> Bewegungsdaten -> Importieren).

Spaltenreihenfolge fest:
1 PersNr | 2 Kalendertag | 3 Ausfallschl | 4 Lohnart | 5 Stunden |
6 Tage  | 7 Wert (EUR)  | 8 Faktor       | 9 LohnVer | 10 KostST | 11 KostTr
"""

import calendar
from io import StringIO
from typing import List, Tuple

from mapping import LOHNART_MAPPING
from parser import MitarbeiterZeile


LOHNART_FELD = {m["lohnart"]: m["feld"] for m in LOHNART_MAPPING}


def _komma(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _kalendertag(jahr: int, monat: int) -> str:
    letzter = calendar.monthrange(jahr, monat)[1]
    return f"{letzter:02d}.{monat:02d}.{jahr:04d}"


def baue_csv(
    mitarbeiter: List[MitarbeiterZeile],
    jahr: int,
    monat: int,
) -> Tuple[str, dict]:
    """Liefert (csv_text, statistik). Mitarbeiter ohne PersNr oder ohne
    Werte werden übersprungen und in der Statistik gemeldet."""

    tag = _kalendertag(jahr, monat)
    buf = StringIO()

    geschrieben = 0
    uebersprungen_keine_persnr = []
    uebersprungen_keine_werte = []

    for ma in mitarbeiter:
        if not ma.pers_nr:
            uebersprungen_keine_persnr.append(ma.name)
            continue
        if not ma.werte:
            uebersprungen_keine_werte.append(ma.name)
            continue
        for lohnart, betrag in ma.werte.items():
            feld = LOHNART_FELD.get(lohnart, "wert")
            stunden = _komma(betrag) if feld == "stunden" else ""
            wert = _komma(betrag) if feld == "wert" else ""
            zeile = ";".join([
                ma.pers_nr,
                tag,
                "",
                lohnart,
                stunden,
                "",
                wert,
                "",
                "",
                "",
                "",
            ])
            buf.write(zeile + "\r\n")
            geschrieben += 1

    statistik = {
        "zeilen_geschrieben": geschrieben,
        "uebersprungen_keine_persnr": uebersprungen_keine_persnr,
        "uebersprungen_keine_werte": uebersprungen_keine_werte,
        "kalendertag": tag,
    }
    return buf.getvalue(), statistik


def csv_bytes(text: str, encoding: str = "cp1252") -> bytes:
    return text.encode(encoding, errors="replace")
