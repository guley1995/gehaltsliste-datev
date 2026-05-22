"""
Liest die Mietwagen-Gehaltsliste-Excel und extrahiert pro Mitarbeiter
die Monatswerte aus dem 'Gehalt'-Sheet sowie die Personalnummer aus
dem zugehörigen Mitarbeiter-Tabnamen.
"""

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import openpyxl

from mapping import KONTROLL_GRUNDGEHALT_COL, LOHNART_MAPPING, UNGEKLAERTE_SPALTEN

UEBERSICHT_SHEET = "Gehalt"
NAME_COL = "A"


@dataclass
class MitarbeiterZeile:
    name: str
    pers_nr: Optional[str]
    werte: Dict[str, float] = field(default_factory=dict)
    ungeklaerte_werte: Dict[str, float] = field(default_factory=dict)
    soll_grundgehalt: float = 0.0
    info: Optional[str] = None
    warnungen: List[str] = field(default_factory=list)


@dataclass
class ParseResult:
    mitarbeiter: List[MitarbeiterZeile]
    globale_warnungen: List[str] = field(default_factory=list)


def _col_letter_to_index(letter: str) -> int:
    return openpyxl.utils.column_index_from_string(letter)


def _persnr_aus_tabname(tab: str) -> Optional[str]:
    m = re.search(r"_([\d.]+)\s*$", tab)
    return m.group(1) if m else None


def _baue_namen_index(sheet_names: List[str]) -> Dict[str, str]:
    """Map exakter Mitarbeitername -> Tabname. Übersichts-Sheet ausgenommen."""
    out: Dict[str, str] = {}
    for tab in sheet_names:
        if tab == UEBERSICHT_SHEET:
            continue
        prefix = re.sub(r"_[\d.]+\s*$", "", tab).strip()
        out[prefix] = tab
    return out


def _zahl(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def parse_excel(file_bytes: bytes) -> ParseResult:
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)

    if UEBERSICHT_SHEET not in wb.sheetnames:
        return ParseResult(
            mitarbeiter=[],
            globale_warnungen=[f"Sheet '{UEBERSICHT_SHEET}' nicht gefunden. Vorhandene Sheets: {wb.sheetnames}"],
        )

    ws = wb[UEBERSICHT_SHEET]
    name_to_tab = _baue_namen_index(wb.sheetnames)

    name_col_idx = _col_letter_to_index(NAME_COL)
    info_col_idx = _col_letter_to_index("W")

    mapped_cols = [(m, _col_letter_to_index(m["excel_col"])) for m in LOHNART_MAPPING]
    unklare_cols = [(u, _col_letter_to_index(u["excel_col"])) for u in UNGEKLAERTE_SPALTEN]
    kontroll_col_idx = _col_letter_to_index(KONTROLL_GRUNDGEHALT_COL)

    mitarbeiter: List[MitarbeiterZeile] = []

    for r in range(2, ws.max_row + 1):
        name = ws.cell(r, name_col_idx).value
        if not name or not str(name).strip():
            continue
        name = str(name).strip()

        info_val = ws.cell(r, info_col_idx).value
        info = str(info_val).strip() if info_val else None

        zeile = MitarbeiterZeile(name=name, pers_nr=None, info=info)

        tab = name_to_tab.get(name)
        if tab:
            zeile.pers_nr = _persnr_aus_tabname(tab)
            if not zeile.pers_nr:
                zeile.warnungen.append(f"Kein PersNr-Suffix im Tabname '{tab}' gefunden.")
        else:
            zeile.warnungen.append("Kein eigenes Mitarbeiter-Sheet gefunden (Tabname fehlt).")

        for m, col_idx in mapped_cols:
            val = _zahl(ws.cell(r, col_idx).value)
            if val != 0:
                zeile.werte[m["lohnart"]] = val

        for u, col_idx in unklare_cols:
            val = _zahl(ws.cell(r, col_idx).value)
            if val != 0:
                zeile.ungeklaerte_werte[u["excel_header"]] = val

        zeile.soll_grundgehalt = _zahl(ws.cell(r, kontroll_col_idx).value)

        mitarbeiter.append(zeile)

    return ParseResult(mitarbeiter=mitarbeiter)


def monat_jahr_aus_dateiname(filename: str) -> Optional[Tuple[int, int]]:
    """'Gehaltsliste_2026_3 Wittys.xlsx' -> (2026, 3). None wenn nicht erkannt."""
    m = re.search(r"(\d{4})[_\-\s](\d{1,2})", filename)
    if not m:
        return None
    jahr, monat = int(m.group(1)), int(m.group(2))
    if 1 <= monat <= 12 and 2000 <= jahr <= 2100:
        return (jahr, monat)
    return None
