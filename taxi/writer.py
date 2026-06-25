"""
DATEV-Writer für Taxi-Lohnlisten:

1. baue_csv()           — Bewegungsdaten-CSV (9-Spalten Monatserfassung).
                          Stunden + EUR-Lohnarten. KEIN Stundensatz mehr in Spalte 6.

2. baue_stammdaten_csv() — Stammdaten-CSV für Stundenlohn-Update.
                          Format: PersNr;MM/JJJJ;1;Stundenlohn
                          DATEV legt automatisch neue Historien-Zeile an.
                          Import in DATEV: ASCII-Import-Assistent → Stammdaten.

ARCHITEKTUR (DATEV-Regel):
 - Stammdaten = Stundenlohn EUR (historisiert, ST01)
 - Bewegungsdaten = geleistete Stunden / EUR-Buchungen
 Diese MÜSSEN getrennt importiert werden — Reihenfolge:
   1. Stammdaten-CSV einspielen (neuer Stundenlohn ab MM/JJJJ aktiv)
   2. Bewegungsdaten-CSV einspielen (DATEV rechnet Stunden × Stamm-Stundensatz)
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
            # KEIN Stundensatz mehr in Spalte 6 — Stundenlohn ist Stammdaten,
            # nicht Bewegungsdaten. Wird über separate Stammdaten-CSV gepflegt.
            zeile = ";".join([
                ma.pers_nr,   # 1 PersNr
                lohnart,      # 2 Lohnart
                "",           # 3 Stundenanzahl (LEER)
                "",           # 4 Tage
                der_wert,     # 5 Wert (Stunden bei Stunden-LA, EUR bei EUR-LA)
                "",           # 6 Abweichender Faktor (LEER — Stammdaten regeln Stundenlohn)
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


def _punkt(value: float) -> str:
    """Stammdaten-CSV nutzt Punkt als Dezimaltrennzeichen.
    Mindestens 2, höchstens 4 Nachkommastellen — damit DATEV-übliche
    3-Stellen-Stundenlöhne (z.B. 15,025) NICHT auf 15,03 gerundet
    werden und runde Werte trotzdem als 14.00 erscheinen."""
    s = f"{value:.4f}"  # z.B. "15.0250" oder "14.0000"
    # Trailing-Nullen entfernen, aber mindestens 2 Nachkommastellen behalten
    while s.endswith("0") and len(s.split(".")[1]) > 2:
        s = s[:-1]
    return s


def baue_stammdaten_csv(
    mitarbeiter: List[MitarbeiterZeile],
    jahr: int,
    monat: int,
    stundenlohn_nr: int = 1,
) -> Tuple[str, dict]:
    """Stammdaten-CSV für Stundenlohn-Update pro Mitarbeiter.

    Format:
      MitarbeiterNr;GueltigAb;StundenlohnNr;Betrag
      10001;06/2026;1;15.50

    DATEV legt durch das Datum automatisch eine neue Historien-Zeile an
    (alte Einträge bleiben erhalten).
    Import: ASCII-Import-Assistent → Stammdaten → Stunden-/Tagelöhne.
    """
    abr_monat = f"{monat:02d}/{jahr:04d}"
    buf = StringIO()
    buf.write("MitarbeiterNr;GueltigAb;StundenlohnNr;Betrag\r\n")

    geschrieben = 0
    uebersprungen: List[str] = []
    for ma in mitarbeiter:
        if not ma.pers_nr:
            uebersprungen.append(f"{ma.name} (keine PersNr)")
            continue
        if ma.stundensatz <= 0:
            uebersprungen.append(f"{ma.name} PersNr {ma.pers_nr} (kein Stundensatz)")
            continue
        zeile = ";".join([
            ma.pers_nr,
            abr_monat,
            str(stundenlohn_nr),
            _punkt(ma.stundensatz),
        ])
        buf.write(zeile + "\r\n")
        geschrieben += 1

    return buf.getvalue(), {
        "zeilen_geschrieben": geschrieben,
        "uebersprungen": uebersprungen,
        "abrechnungsmonat": abr_monat,
        "stundenlohn_nr": stundenlohn_nr,
    }
