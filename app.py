"""Stage 2 minus data_editor — PersNr-Editor via Textarea statt data_editor."""
import io
import json
import zipfile

import streamlit as st

from mapping import LOHNART_MAPPING, MANUELL_IN_DATEV
from parser import firma_aus_dateiname, monat_jahr_aus_dateiname, parse_excel
from writer import baue_csv, csv_bytes

st.set_page_config(page_title="Gehaltsliste → DATEV", layout="wide")

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:4px;">
      <div style="background:#0f62fe;color:white;padding:6px 14px;border-radius:8px;
                  font-weight:700;font-size:18px;letter-spacing:0.5px;">Hue.IT</div>
      <div style="color:#888;font-size:13px;">DATEV-Tools für Lohnbüros</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("Gehaltsliste → DATEV Lohn und Gehalt")
st.caption("Excel hochladen → CSV erzeugen. Daten bleiben im Browser.")

if "all_mappings" not in st.session_state:
    st.session_state["all_mappings"] = {}

with st.sidebar:
    st.header("Einstellungen")
    encoding = st.selectbox("Encoding", ["cp1252", "utf-8"], index=0)

    st.divider()
    st.subheader("PersNr-Mappings")
    n_firmen = len(st.session_state["all_mappings"])
    n_pers = sum(len(v) for v in st.session_state["all_mappings"].values())
    st.caption(f"Session: {n_firmen} Firma(en), {n_pers} Einträge.")

    if st.session_state["all_mappings"]:
        st.download_button(
            "⬇️ Mappings exportieren",
            data=json.dumps(st.session_state["all_mappings"], indent=2, ensure_ascii=False),
            file_name="datev_persnr_mappings.json",
            mime="application/json",
            use_container_width=True,
        )

    imp = st.file_uploader("⬆️ Mappings importieren", type=["json"], key="mapimp")
    if imp is not None:
        try:
            data = json.loads(imp.read().decode("utf-8"))
            if isinstance(data, dict):
                st.session_state["all_mappings"].update(data)
                st.success(f"{len(data)} Firma(en) importiert.")
        except Exception as e:
            st.error(f"Import: {e}")

    st.divider()
    st.subheader("Lohnart-Mapping")
    st.dataframe(
        [{"Sp": m["excel_col"], "Header": m["excel_header"], "LA": m["lohnart"]}
         for m in LOHNART_MAPPING],
        hide_index=True, use_container_width=True,
    )

uploads = st.file_uploader("Excel-Dateien", type=["xlsx"], accept_multiple_files=True)
if not uploads:
    st.info("Lade eine oder mehrere .xlsx hoch.")
    st.stop()

generierte = []

for f in uploads:
    parse = parse_excel(f.read())
    jm = monat_jahr_aus_dateiname(f.name) or (2026, 3)
    firma_default = firma_aus_dateiname(f.name)

    st.divider()
    st.subheader(f"📄 {f.name}")

    if parse.globale_warnungen:
        for w in parse.globale_warnungen:
            st.error(w)
        continue

    col_f, col_j, col_m = st.columns([2, 1, 1])
    firma = col_f.text_input("Firma / DATEV-Mandant", value=firma_default, key=f"fi_{f.name}")
    jahr = col_j.number_input("Jahr", value=jm[0], min_value=2000, max_value=2100,
                              step=1, key=f"y_{f.name}")
    monat = col_m.number_input("Monat", value=jm[1], min_value=1, max_value=12,
                               step=1, key=f"m_{f.name}")

    firma_map = st.session_state["all_mappings"].setdefault(firma, {})

    st.markdown("##### Personalnummer-Mapping")
    st.caption("Trag pro Mitarbeiter die DATEV-PersNr ein. Wird in der Session gespeichert.")

    # PersNr-Editor: pro Mitarbeiter ein text_input in zwei Spalten
    for ma in parse.mitarbeiter:
        cols = st.columns([3, 1, 4])
        cols[0].write(ma.name + (f"  *(Info: {ma.info[:40]})*" if ma.info else ""))
        default = firma_map.get(ma.name, ma.pers_nr or "")
        pn = cols[1].text_input("PersNr", value=default,
                                key=f"pn_{f.name}_{ma.name}",
                                label_visibility="collapsed",
                                placeholder=ma.pers_nr or "—")
        cols[2].caption(f"Excel-Tab: {ma.pers_nr or '—'}")
        pn = pn.strip()
        if pn:
            firma_map[ma.name] = pn
            ma.pers_nr = pn
        elif ma.name in firma_map:
            del firma_map[ma.name]
            ma.pers_nr = None

    csv_text, stat = baue_csv(parse.mitarbeiter, int(jahr), int(monat))
    data = csv_bytes(csv_text, encoding=encoding)
    out_name = f"{firma}_{int(jahr):04d}-{int(monat):02d}_DATEV.csv".replace(" ", "_")
    generierte.append((out_name, data))

    c1, c2, c3 = st.columns(3)
    c1.metric("Mitarbeiter", len(parse.mitarbeiter))
    c2.metric("CSV-Zeilen", stat["zeilen_geschrieben"])
    c3.metric("Kalendertag", stat["kalendertag"])

    st.download_button("⬇️ CSV herunterladen", data=data, file_name=out_name,
                       mime="text/csv", key=f"dl_{f.name}",
                       type="primary", use_container_width=True)

    with st.expander("Werte-Vorschau"):
        zeilen = []
        for ma in parse.mitarbeiter:
            row = {"PersNr": ma.pers_nr or "—", "Name": ma.name}
            for m in LOHNART_MAPPING:
                row[m["lohnart"]] = ma.werte.get(m["lohnart"], "")
            row["Soll-€"] = round(ma.soll_grundgehalt, 2) if ma.soll_grundgehalt else ""
            zeilen.append(row)
        st.dataframe(zeilen, hide_index=True, use_container_width=True)

    with st.expander("Warnungen"):
        if stat["uebersprungen_keine_persnr"]:
            st.warning("Keine PersNr: " + ", ".join(stat["uebersprungen_keine_persnr"]))
        for ma in parse.mitarbeiter:
            lines = []
            if ma.manuell_werte:
                for h, v in ma.manuell_werte.items():
                    lines.append(f"  • {h}: {v} → manuell in DATEV")
            if ma.info:
                lines.append(f"  ℹ {ma.info}")
            if lines:
                st.markdown(f"**{ma.name}**\n\n" + "\n".join(lines))

    with st.expander("CSV-Inhalt"):
        st.code(csv_text or "(leer)", language="csv")


if len(generierte) > 1:
    st.divider()
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in generierte:
            zf.writestr(name, data)
    st.download_button("⬇️ Alle CSVs als ZIP", data=zbuf.getvalue(),
                       file_name="DATEV_CSVs.zip", mime="application/zip",
                       type="primary", use_container_width=True)
