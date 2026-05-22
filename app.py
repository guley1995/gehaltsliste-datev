"""
Streamlit-App: Mietwagen-Gehaltsliste (Excel) -> DATEV LuG ASCII-Import-CSV.

Lokaler Start:  streamlit run app.py
Browser-Build:  identische Logik in index.html (stlite).
"""

import io
import zipfile

import streamlit as st

from mapping import LOHNART_MAPPING, UNGEKLAERTE_SPALTEN
from parser import monat_jahr_aus_dateiname, parse_excel
from writer import baue_csv, csv_bytes


st.set_page_config(page_title="Gehaltsliste → DATEV", layout="wide")
st.title("Gehaltsliste → DATEV Lohn und Gehalt")
st.caption(
    "Excel hochladen → CSV für ASCII-Import erzeugen. "
    "Daten bleiben im Browser (stlite) bzw. auf deinem Rechner (lokal). "
    "Importpfad in DATEV: Erfassen → Bewegungsdaten → Importieren."
)

with st.sidebar:
    st.header("Einstellungen")
    encoding = st.selectbox(
        "Encoding",
        ["cp1252", "utf-8"],
        index=0,
        help="DATEV erwartet meist ANSI/CP1252. Bei Umlautproblemen UTF-8 testen.",
    )
    st.divider()
    st.subheader("Lohnart-Mapping")
    st.dataframe(
        [
            {"Excel-Spalte": m["excel_col"], "Header": m["excel_header"], "Lohnart": m["lohnart"], "Feld": m["feld"]}
            for m in LOHNART_MAPPING
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Ungeklärte Spalten")
    st.caption("Werden NICHT in die CSV geschrieben — bitte LA-Nummern klären.")
    st.dataframe(
        [
            {"Excel-Spalte": u["excel_col"], "Header": u["excel_header"], "Hinweis": u["hinweis"]}
            for u in UNGEKLAERTE_SPALTEN
        ],
        hide_index=True,
        use_container_width=True,
    )

uploads = st.file_uploader(
    "Excel-Dateien (eine pro Mandant/Monat)",
    type=["xlsx"],
    accept_multiple_files=True,
)

if not uploads:
    st.info("Lade eine oder mehrere .xlsx hoch, um zu starten.")
    st.stop()


def _verarbeite(file) -> dict:
    raw = file.read()
    result = parse_excel(raw)
    jm = monat_jahr_aus_dateiname(file.name)
    return {"file": file, "raw": raw, "parse": result, "jm_default": jm}


verarbeitet = [_verarbeite(f) for f in uploads]

generierte_csvs: list[tuple[str, bytes]] = []

for v in verarbeitet:
    fname = v["file"].name
    parse = v["parse"]

    with st.expander(f"📄 {fname}", expanded=len(verarbeitet) == 1):
        if parse.globale_warnungen:
            for w in parse.globale_warnungen:
                st.error(w)
            continue

        col_j, col_m, col_dl = st.columns([1, 1, 2])
        jm = v["jm_default"]
        with col_j:
            jahr = st.number_input(
                "Jahr",
                value=jm[0] if jm else 2026,
                min_value=2000,
                max_value=2100,
                step=1,
                key=f"y_{fname}",
            )
        with col_m:
            monat = st.number_input(
                "Monat",
                value=jm[1] if jm else 3,
                min_value=1,
                max_value=12,
                step=1,
                key=f"m_{fname}",
            )

        csv_text, stat = baue_csv(parse.mitarbeiter, int(jahr), int(monat))
        data = csv_bytes(csv_text, encoding=encoding)

        out_name = fname.rsplit(".", 1)[0] + f"_DATEV_{int(jahr):04d}-{int(monat):02d}.csv"
        generierte_csvs.append((out_name, data))

        with col_dl:
            st.download_button(
                "⬇️ CSV herunterladen",
                data=data,
                file_name=out_name,
                mime="text/csv",
                key=f"dl_{fname}",
                use_container_width=True,
            )

        m1, m2, m3 = st.columns(3)
        m1.metric("Mitarbeiter erkannt", len(parse.mitarbeiter))
        m2.metric("Zeilen in CSV", stat["zeilen_geschrieben"])
        m3.metric("Kalendertag", stat["kalendertag"])

        tab_data, tab_warn, tab_csv = st.tabs(["Vorschau Daten", "Warnungen", "CSV-Inhalt"])

        with tab_data:
            st.caption(
                "Letzte Spalte „Soll-Grundgehalt €" ist nur Kontrolle (Excel-Spalte K = "
                "Stundensatz × Arbeitsstunden) — nicht im DATEV-Import enthalten, "
                "aber nach Import in DATEV zum Abgleich nutzbar."
            )
            zeilen = []
            for ma in parse.mitarbeiter:
                row = {"PersNr": ma.pers_nr or "—", "Name": ma.name}
                for m in LOHNART_MAPPING:
                    row[f'{m["lohnart"]} {m["label"]}'] = ma.werte.get(m["lohnart"], "")
                row["Soll-Grundgehalt €"] = round(ma.soll_grundgehalt, 2) if ma.soll_grundgehalt else ""
                zeilen.append(row)
            st.dataframe(zeilen, hide_index=True, use_container_width=True)

        with tab_warn:
            mit_unklar = [ma for ma in parse.mitarbeiter if ma.ungeklaerte_werte or ma.warnungen or ma.info]
            if not mit_unklar and not stat["uebersprungen_keine_persnr"] and not stat["uebersprungen_keine_werte"]:
                st.success("Keine Warnungen.")
            if stat["uebersprungen_keine_persnr"]:
                st.warning(
                    "Übersprungen — kein Mitarbeiter-Tab gefunden, daher keine Personalnummer: "
                    + ", ".join(stat["uebersprungen_keine_persnr"])
                )
            if stat["uebersprungen_keine_werte"]:
                st.info(
                    "Übersprungen — keine Werte in den gemappten Spalten: "
                    + ", ".join(stat["uebersprungen_keine_werte"])
                )
            for ma in mit_unklar:
                zeilen = []
                if ma.ungeklaerte_werte:
                    for header, val in ma.ungeklaerte_werte.items():
                        zeilen.append(f"  • {header}: {val}")
                if ma.warnungen:
                    for w in ma.warnungen:
                        zeilen.append(f"  ⚠ {w}")
                if ma.info:
                    zeilen.append(f"  ℹ Info-Spalte: {ma.info}")
                if zeilen:
                    st.markdown(f"**{ma.name}** (PersNr {ma.pers_nr or '—'})\n\n" + "\n".join(zeilen))

        with tab_csv:
            st.code(csv_text or "(leer)", language="csv")

if len(generierte_csvs) > 1:
    st.divider()
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in generierte_csvs:
            zf.writestr(name, data)
    st.download_button(
        "⬇️ Alle CSVs als ZIP herunterladen",
        data=zbuf.getvalue(),
        file_name="DATEV_CSVs.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )
