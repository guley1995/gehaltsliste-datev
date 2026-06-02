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


MODUS_MONAT = "monat"  # 9 Spalten, ohne Kalendertag/Ausfallschlüssel
MODUS_KALENDER = "kalender"  # 11 Spalten, mit Kalendertag/Ausfallschlüssel


def baue_csv(
    mitarbeiter: List[MitarbeiterZeile],
    jahr: int,
    monat: int,
    beraternr: str = "",
    mandantennr: str = "",
    modus: str = MODUS_MONAT,
) -> Tuple[str, dict]:
    """Liefert (csv_text, statistik).

    DATEV Lohn und Gehalt erwartet als ERSTE Zeile einen Header:
        Beraternummer;Mandantennummer;MM/JJJJ
        z.B. 1479590;10010;05/2026

    Danach folgen die Bewegungsdaten-Zeilen. Format hängt vom Modus ab:

    - MODUS_MONAT (9 Spalten, Standard für Monatserfassung):
        PersNr;Lohnart;Std;Tage;Wert;Faktor;LohnVer;KostST;KostTr

    - MODUS_KALENDER (11 Spalten, für Kalendererfassung):
        PersNr;Kalendertag;Ausfallschl;Lohnart;Std;Tage;Wert;Faktor;LohnVer;KostST;KostTr

    Mitarbeiter ohne PersNr oder ohne Werte werden übersprungen und in
    der Statistik gemeldet."""

    tag = _kalendertag(jahr, monat)
    abr_monat = f"{monat:02d}/{jahr:04d}"
    buf = StringIO()

    # Header-Zeile (Pflicht laut DATEV ASCII-Import Assistent)
    if beraternr or mandantennr:
        buf.write(f"{beraternr};{mandantennr};{abr_monat}\r\n")

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
            if modus == MODUS_MONAT:
                # 9 Spalten — ohne Kalendertag, ohne Ausfallschlüssel
                zeile = ";".join([
                    ma.pers_nr,   # 1 PersNr
                    lohnart,      # 2 Lohnart
                    stunden,      # 3 Stunden
                    "",           # 4 Tage
                    wert,         # 5 Wert
                    "",           # 6 Faktor
                    "",           # 7 LohnVer
                    "",           # 8 KostST
                    "",           # 9 KostTr
                ])
            else:
                # 11 Spalten — Kalendererfassung
                zeile = ";".join([
                    ma.pers_nr,   # 1
                    tag,          # 2 Kalendertag
                    "",           # 3 Ausfallschl
                    lohnart,      # 4
                    stunden,      # 5
                    "",           # 6 Tage
                    wert,         # 7
                    "",           # 8 Faktor
                    "",           # 9 LohnVer
                    "",           # 10 KostST
                    "",           # 11 KostTr
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
        "modus": modus,
    }
    return buf.getvalue(), statistik


class EncodingError(Exception):
    """Encoding kann ein Zeichen aus dem CSV-Text nicht darstellen."""

    def __init__(self, encoding: str, problem_chars: List[str]):
        self.encoding = encoding
        self.problem_chars = problem_chars
        super().__init__(
            f"Encoding '{encoding}' kann diese Zeichen nicht darstellen: "
            f"{', '.join(repr(c) for c in problem_chars)}. "
            f"In der Sidebar Encoding auf 'utf-8' wechseln."
        )


def csv_bytes(text: str, encoding: str = "cp1252") -> bytes:
    """Encodiert die CSV strict — wirft EncodingError wenn nicht möglich.
    Verhindert stille `?`-Ersetzungen (Datenverlust ohne Warnung)."""
    try:
        return text.encode(encoding, errors="strict")
    except UnicodeEncodeError:
        # Sammle alle Problem-Zeichen für eine klare Fehlermeldung
        problem = sorted({ch for ch in text if not _kann_encoden(ch, encoding)})
        raise EncodingError(encoding, problem[:10])


def _kann_encoden(ch: str, encoding: str) -> bool:
    try:
        ch.encode(encoding, errors="strict")
        return True
    except UnicodeEncodeError:
        return False
