"""
Streamlit-App: Mietwagen-Gehaltsliste (Excel) -> DATEV LuG ASCII-Import-CSV.

Mappings (Mitarbeitername -> DATEV-Personalnummer) werden pro Firma im
Browser-LocalStorage gespeichert. Export/Import als JSON für Backup oder
Gerätewechsel.

Lokaler Start:  streamlit run app.py
Browser-Build:  identische Logik in index.html (stlite).
"""

import io
import json
import zipfile

import streamlit as st

from mapping import LOHNART_MAPPING, MANUELL_IN_DATEV
from parser import firma_aus_dateiname, monat_jahr_aus_dateiname, parse_excel
from writer import baue_csv, csv_bytes


LOCAL_STORAGE_KEY = "gehaltsliste_datev_mappings_v1"


def _localstorage():
    """Browser-LocalStorage über Pyodide (stlite). None wenn nicht verfügbar."""
    try:
        from js import localStorage  # type: ignore
        return localStorage
    except Exception:
        return None


def _ls_load() -> dict:
    ls = _localstorage()
    if not ls:
        return {}
    try:
        raw = ls.getItem(LOCAL_STORAGE_KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {}


def _ls_save(data: dict) -> None:
    ls = _localstorage()
    if not ls:
        return
    try:
        ls.setItem(LOCAL_STORAGE_KEY, json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


st.set_page_config(page_title="Gehaltsliste → DATEV", layout="wide")
st.title("Gehaltsliste → DATEV Lohn und Gehalt")
st.caption(
    "Excel hochladen → CSV für ASCII-Import erzeugen. "
    "Daten bleiben im Browser (stlite). "
    "Importpfad in DATEV: Erfassen → Bewegungsdaten → Importieren."
)

# Mappings (Firma -> {Name: PersNr}) aus LocalStorage laden
if "all_mappings" not in st.session_state:
    st.session_state["all_mappings"] = _ls_load()


with st.sidebar:
    st.header("Einstellungen")
    encoding = st.selectbox(
        "Encoding",
        ["cp1252", "utf-8"],
        index=0,
        help="DATEV erwartet meist ANSI/CP1252. Bei Umlautproblemen UTF-8 testen.",
    )

    st.divider()
    st.subheader("Personalnummer-Mappings")
    n_firmen = len(st.session_state["all_mappings"])
    n_pers = sum(len(v) for v in st.session_state["all_mappings"].values())
    st.caption(
        f"Aktuell gespeichert: **{n_firmen} Firma(en)**, {n_pers} Mitarbeiter-PersNr. "
        "Liegen im Browser-LocalStorage. Mit Export/Import sicherst du sie z.B. in iCloud/Drive."
    )

    if st.session_state["all_mappings"]:
        st.download_button(
            "⬇️ Mappings exportieren (JSON)",
            data=json.dumps(st.session_state["all_mappings"], indent=2, ensure_ascii=False),
            file_name="datev_persnr_mappings.json",
            mime="application/json",
            use_container_width=True,
        )

    imp = st.file_uploader("⬆️ Mappings importieren (JSON)", type=["json"], key="mapping_import")
    if imp is not None:
        try:
            data = json.loads(imp.read().decode("utf-8"))
            if isinstance(data, dict):
                st.session_state["all_mappings"].update(data)
                _ls_save(st.session_state["all_mappings"])
                st.success(f"{len(data)} Firma(en) importiert.")
            else:
                st.error("JSON-Format unerwartet (erwartet: {Firma: {Name: PersNr}}).")
        except Exception as e:
            st.error(f"Import fehlgeschlagen: {e}")

    if st.session_state["all_mappings"]:
        with st.expander("Mappings ansehen / löschen"):
            for firma in list(st.session_state["all_mappings"].keys()):
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**{firma}** — {len(st.session_state['all_mappings'][firma])} Einträge")
                if col_b.button("🗑", key=f"del_{firma}"):
                    del st.session_state["all_mappings"][firma]
                    _ls_save(st.session_state["all_mappings"])
                    st.rerun()

    st.divider()
    st.subheader("Lohnart-Mapping (fest)")
    st.dataframe(
        [
            {"Excel-Spalte": m["excel_col"], "Header": m["excel_header"],
             "Lohnart": m["lohnart"], "Feld": m["feld"]}
            for m in LOHNART_MAPPING
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Manuell in DATEV erfassen")
    st.caption("Werden NICHT in die CSV geschrieben — über DATEV-Maske/Kalender pflegen.")
    st.dataframe(
        [
            {"Excel-Spalte": u["excel_col"], "Header": u["excel_header"],
             "Lohnart": u["lohnart"], "Hinweis": u["hinweis"]}
            for u in MANUELL_IN_DATEV
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
    firma = firma_aus_dateiname(file.name)
    return {"file": file, "parse": result, "jm_default": jm, "firma_default": firma}


verarbeitet = [_verarbeite(f) for f in uploads]
generierte_csvs: list = []

for v in verarbeitet:
    fname = v["file"].name
    parse = v["parse"]

    with st.expander(f"📄 {fname}", expanded=len(verarbeitet) == 1):
        if parse.globale_warnungen:
            for w in parse.globale_warnungen:
                st.error(w)
            continue

        col_f, col_j, col_m = st.columns([2, 1, 1])
        with col_f:
            firma = st.text_input(
                "Firma / DATEV-Mandant",
                value=v["firma_default"],
                key=f"firma_{fname}",
                help="Aus dem Dateinamen erkannt. PersNr-Mappings werden pro Firma gespeichert.",
            )
        jm = v["jm_default"]
        with col_j:
            jahr = st.number_input("Jahr", value=jm[0] if jm else 2026,
                                   min_value=2000, max_value=2100, step=1, key=f"y_{fname}")
        with col_m:
            monat = st.number_input("Monat", value=jm[1] if jm else 3,
                                    min_value=1, max_value=12, step=1, key=f"m_{fname}")

        firma_map = st.session_state["all_mappings"].setdefault(firma, {})

        # PersNr für jede Zeile vorbelegen: erst Mapping, dann Tabname-Fallback
        for ma in parse.mitarbeiter:
            saved = firma_map.get(ma.name)
            if saved:
                ma.pers_nr = saved

        st.markdown("##### Personalnummer-Mapping")
        st.caption(
            "Tipp pro Mitarbeiter die DATEV-Personalnummer ein. "
            "Wird beim Verlassen des Feldes automatisch für die Firma gespeichert. "
            "Vorbelegung kommt aus dem Excel-Tab-Suffix — bitte gegen DATEV verifizieren."
        )

        editor_rows = []
        for ma in parse.mitarbeiter:
            editor_rows.append({
                "Name": ma.name,
                "Tab-Suffix": ma.pers_nr or "" if ma.name not in firma_map else "",
                "PersNr (DATEV)": firma_map.get(ma.name, ma.pers_nr or ""),
                "Info": ma.info or "",
            })

        edited = st.data_editor(
            editor_rows,
            hide_index=True,
            use_container_width=True,
            disabled=["Name", "Tab-Suffix", "Info"],
            column_config={
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Tab-Suffix": st.column_config.TextColumn("aus Excel-Tab", width="small",
                                                          help="Suffix aus dem Mitarbeiter-Tab-Namen, nur als Hinweis."),
                "PersNr (DATEV)": st.column_config.TextColumn("PersNr (DATEV)", width="small",
                                                              help="Editierbar. Wird gespeichert."),
                "Info": st.column_config.TextColumn("Info aus Excel", width="large"),
            },
            key=f"editor_{fname}",
        )

        # Editierte PersNr zurück in Mapping + LocalStorage
        changed = False
        for row in edited:
            name = row["Name"]
            persnr = (row["PersNr (DATEV)"] or "").strip()
            if persnr:
                if firma_map.get(name) != persnr:
                    firma_map[name] = persnr
                    changed = True
            else:
                if name in firma_map:
                    del firma_map[name]
                    changed = True
        if changed:
            _ls_save(st.session_state["all_mappings"])

        # PersNr aus Editor in Parser-Objekte übernehmen für CSV
        editor_map = {row["Name"]: (row["PersNr (DATEV)"] or "").strip() for row in edited}
        for ma in parse.mitarbeiter:
            ma.pers_nr = editor_map.get(ma.name) or None

        # CSV bauen
        csv_text, stat = baue_csv(parse.mitarbeiter, int(jahr), int(monat))
        data = csv_bytes(csv_text, encoding=encoding)
        out_name = f"{firma}_{int(jahr):04d}-{int(monat):02d}_DATEV.csv".replace(" ", "_")
        generierte_csvs.append((out_name, data))

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Mitarbeiter", len(parse.mitarbeiter))
        m2.metric("CSV-Zeilen", stat["zeilen_geschrieben"])
        m3.metric("Übersprungen", len(stat["uebersprungen_keine_persnr"]) +
                                    len(stat["uebersprungen_keine_werte"]))
        m4.metric("Kalendertag", stat["kalendertag"])

        st.download_button(
            "⬇️ CSV herunterladen",
            data=data,
            file_name=out_name,
            mime="text/csv",
            key=f"dl_{fname}",
            type="primary",
            use_container_width=True,
        )

        tab_data, tab_warn, tab_csv = st.tabs(["Werte-Vorschau", "Warnungen", "CSV-Inhalt"])

        with tab_data:
            st.caption(
                "Letzte Spalte „Soll-Grundgehalt €" = Excel-Spalte K (B × C), "
                "nicht im DATEV-Import — nur zum Abgleich nach Import."
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
            mit_hinweis = [ma for ma in parse.mitarbeiter if ma.manuell_werte or ma.warnungen or ma.info]
            if not mit_hinweis and not stat["uebersprungen_keine_persnr"] and not stat["uebersprungen_keine_werte"]:
                st.success("Keine Warnungen.")
            if stat["uebersprungen_keine_persnr"]:
                st.warning(
                    "Übersprungen — keine PersNr eingetragen: "
                    + ", ".join(stat["uebersprungen_keine_persnr"])
                )
            if stat["uebersprungen_keine_werte"]:
                st.info(
                    "Übersprungen — keine Werte in den gemappten Spalten: "
                    + ", ".join(stat["uebersprungen_keine_werte"])
                )
            if mit_hinweis:
                st.markdown("**Mitarbeiter mit manuellen Nachträgen oder Info-Notizen:**")
            for ma in mit_hinweis:
                zeilen = []
                if ma.manuell_werte:
                    for header, val in ma.manuell_werte.items():
                        zeilen.append(f"  • {header}: {val} → manuell in DATEV erfassen")
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
