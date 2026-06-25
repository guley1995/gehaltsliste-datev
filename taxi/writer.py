"""
DATEV-CSV-Writer für Taxi-Lohnlisten — identisch zum Mietwagen-Writer
in der 9-Spalten-Monatserfassungs-Struktur.

Unterschied zur Mietwagen-CSV: Bei Taxi sind die meisten Werte EUR.
Stundensatz wird nur bei LA 1000 (Grundlohn) als Abweichender Faktor mitgegeben.
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


class EncodingError(Exception):
    def __init__(self, encoding: str, problem_chars: List[str]):
        self.encoding = encoding
        self.problem_chars = problem_chars
        super().__init__(
            f"Encoding '{encoding}' kann diese Zeichen nicht darstellen: "
            f"{', '.join(repr(c) for c in problem_chars)}. "
            f"In der Sidebar Encoding auf 'utf-8' wechseln."
        )


def _kann_encoden(ch: str, encoding: str) -> bool:
    try:
        ch.encode(encoding, errors="strict")
        return True
    except UnicodeEncodeError:
        return False


def csv_bytes(text: str, encoding: str = "cp1252") -> bytes:
    try:
        return text.encode(encoding, errors="strict")
    except UnicodeEncodeError:
        problem = sorted({ch for ch in text if not _kann_encoden(ch, encoding)})
        raise EncodingError(encoding, problem[:10])


def baue_csv(
    mitarbeiter: List[MitarbeiterZeile],
    jahr: int,
    monat: int,
    beraternr: str = "",
    mandantennr: str = "",
) -> Tuple[str, dict]:
    """9-Spalten-Monatserfassungs-CSV (gleiches Format wie Mietwagen).
    Werte gehen direkt in Spalte 5 (Wert), Stundensatz in Spalte 6 nur bei LA 1000."""

    tag = _kalendertag(jahr, monat)
    abr_monat = f"{monat:02d}/{jahr:04d}"
    buf = StringIO()

    if beraternr or mandantennr:
        buf.write(f"{beraternr};{mandantennr};{abr_monat}\r\n")

    geschrieben = 0
    uebersprungen_keine_persnr: List[str] = []
    uebersprungen_keine_werte: List[str] = []

    for ma in mitarbeiter:
        if not ma.pers_nr:
            uebersprungen_keine_persnr.append(ma.name)
            continue
        if not ma.werte:
            uebersprungen_keine_werte.append(ma.name)
            continue
        for lohnart, betrag in ma.werte.items():
            der_wert = _komma(betrag)

            # Stundensatz-Override bei ALLEN Stunden-Lohnarten (Spalte 6 Abw. Faktor)
            faktor = ""
            feld = LOHNART_FELD.get(lohnart, "wert")
            if feld == "stunden" and ma.stundensatz > 0:
                faktor = _komma(ma.stundensatz)

            zeile = ";".join([
                ma.pers_nr,   # 1 PersNr
                lohnart,      # 2 Lohnart
                "",           # 3 Stundenanzahl (LEER)
                "",           # 4 Tage
                der_wert,     # 5 Wert (EUR)
                faktor,       # 6 Abweichender Faktor (Stundensatz bei LA 1000)
                "",           # 7 Abweichende Lohnveränderung
                "",           # 8 KostST
                "",           # 9 KostTr
            ])
            buf.write(zeile + "\r\n")
            geschrieben += 1

    statistik = {
        "zeilen_geschrieben": geschrieben,
        "uebersprungen_keine_persnr": uebersprungen_keine_persnr,
        "uebersprungen_keine_werte": uebersprungen_keine_werte,
        "kalendertag": tag,
        "abrechnungsmonat": abr_monat,
        "header_vorhanden": bool(beraternr or mandantennr),
    }
    return buf.getvalue(), statistik
