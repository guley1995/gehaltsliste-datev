"""
Taxi-Lohnliste → DATEV Lohn und Gehalt (Monatserfassung) CSV.

Workflow:
1. Excel-Lohnliste hochladen (Sheet1, Header in Zeile 4)
2. Berater-/Mandantennr eingeben (oder aus JSON laden)
3. PersNr werden direkt aus Excel-Spalte B genommen — kein PersNr-Mapping nötig
4. Download 9-Spalten-CSV mit Header (BeraterNr;MandNr;MM/JJJJ)
5. In DATEV: Erfassen → Bewegungsdaten → Importieren → Tab Monatserfassung

Auto-Save in einen lokalen Ordner via File System Access API (Chrome/Edge).
"""

import hashlib
import io
import json
import re
import zipfile
from datetime import date

import streamlit as st

from config import LOGO_TAGLINE, LOGO_TEXT, LOGO_URL, PASSWORT_AKTIV, PASSWORT_HASH
from mapping import LOHNART_MAPPING, MANUELL_IN_DATEV
from parser import firma_aus_dateiname, monat_jahr_aus_dateiname, parse_excel
from writer import EncodingError, baue_csv, baue_stammdaten_csv, csv_bytes


st.set_page_config(page_title="Taxi-Lohnliste → DATEV", layout="wide")

# ─── Logo ─────────────────────────────────────────────────────────────
if LOGO_URL:
    logo_inner = f'<img src="{LOGO_URL}" alt="{LOGO_TEXT}" style="height:36px;">'
else:
    logo_inner = (
        f'<div style="background:#0f62fe;color:white;padding:6px 14px;border-radius:8px;'
        f'font-weight:700;font-size:18px;letter-spacing:0.5px;">{LOGO_TEXT}</div>'
    )
st.markdown(
    f"""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:4px;">
      {logo_inner}
      <div style="color:#888;font-size:13px;">{LOGO_TAGLINE} · 🚖 Taxi-Variante</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Passwort ─────────────────────────────────────────────────────────
if PASSWORT_AKTIV and not st.session_state.get("auth_ok"):
    st.title("🔒 Zugang")
    st.caption("Bitte Passwort eingeben.")
    pw = st.text_input("Passwort", type="password", key="pw_input")
    if pw:
        if hashlib.sha256(pw.encode()).hexdigest() == PASSWORT_HASH:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Falsches Passwort.")
    st.stop()

# ─── LocalStorage-Bridge ──────────────────────────────────────────────
LOCAL_STORAGE_KEY = "taxi_datev_mandanten_v1"


def _ls_persist(data: dict) -> None:
    import streamlit.components.v1 as components
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    components.html(
        f"""
        <script>
        try {{
            window.parent.localStorage.setItem("{LOCAL_STORAGE_KEY}", {json.dumps(payload)});
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


def _ls_load_at_start() -> dict:
    try:
        from js import localStorage  # type: ignore
        raw = localStorage.getItem(LOCAL_STORAGE_KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {}


# ─── Auto-Save Widget (File System Access API) ────────────────────────
def _auto_save_widget():
    import streamlit.components.v1 as components
    components.html(
        f"""
        <style>
          :root {{ color-scheme: dark light; }}
          body {{ margin: 0; padding: 8px 0; font-family: -apple-system, system-ui, sans-serif; }}
          .row {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
          button.cn {{ padding: 4px 10px; border-radius: 6px; border: 1px solid #888; background: #0f62fe; color: white; cursor: pointer; font-size: 12px; }}
          .status {{ color: #888; font-size: 12px; margin-top: 4px; }}
          .ok {{ color: #00a651; }} .err {{ color: #d32f2f; }}
        </style>
        <div>
          <div class="row">
            <button class="cn" id="connect">📁 Mit Ordner verbinden</button>
            <span id="state">…</span>
          </div>
          <div class="status" id="info">Auto-Save schreibt bei jeder Änderung <code>taxi_datev_backup.json</code> in den Ordner.</div>
        </div>
        <script>
        (function() {{
          const LS_KEY = "{LOCAL_STORAGE_KEY}";
          const IDB_NAME = "taxi_autosave"; const IDB_STORE = "handles"; const HANDLE_KEY = "dirHandle";
          const FILE_NAME = "taxi_datev_backup.json"; const POLL_MS = 1500;
          if (!window.showDirectoryPicker) {{
            document.getElementById('connect').disabled = true;
            document.getElementById('state').innerHTML = '<span class="err">Browser ohne File System Access — Chrome/Edge nutzen.</span>';
            return;
          }}
          function idb(mode) {{
            return new Promise((res, rej) => {{
              const req = indexedDB.open(IDB_NAME, 1);
              req.onupgradeneeded = () => req.result.createObjectStore(IDB_STORE);
              req.onsuccess = () => {{ res(req.result.transaction(IDB_STORE, mode).objectStore(IDB_STORE)); }};
              req.onerror = () => rej(req.error);
            }});
          }}
          async function saveH(h) {{ (await idb('readwrite')).put(h, HANDLE_KEY); }}
          async function loadH() {{ const s = await idb('readonly'); return new Promise((r,e) => {{ const q = s.get(HANDLE_KEY); q.onsuccess=()=>r(q.result); q.onerror=()=>e(q.error); }}); }}
          async function clearH() {{ (await idb('readwrite')).delete(HANDLE_KEY); }}
          let handle = null, lastW = null;
          const $st = document.getElementById('state'), $info = document.getElementById('info'), $btn = document.getElementById('connect');
          async function write() {{
            if (!handle) return;
            try {{
              if ((await handle.queryPermission({{mode:'readwrite'}})) !== 'granted') return;
              const raw = window.parent.localStorage.getItem(LS_KEY);
              if (!raw || raw === lastW) return;
              const fh = await handle.getFileHandle(FILE_NAME, {{create:true}});
              const w = await fh.createWritable(); await w.write(raw); await w.close();
              lastW = raw;
              $info.innerHTML = `✅ ${{new Date().toLocaleTimeString('de-DE')}} — <code>${{handle.name}}/${{FILE_NAME}}</code>`;
            }} catch (e) {{ $info.innerHTML = `<span class="err">${{e.message}}</span>`; }}
          }}
          async function readSync() {{
            if (!handle) return false;
            try {{
              if ((await handle.queryPermission({{mode:'readwrite'}})) !== 'granted') return false;
              const fh = await handle.getFileHandle(FILE_NAME);
              const text = await (await fh.getFile()).text();
              if (!text) return false;
              if (window.parent.localStorage.getItem(LS_KEY) === text) {{ lastW = text; return false; }}
              window.parent.localStorage.setItem(LS_KEY, text); lastW = text; return true;
            }} catch (e) {{ return false; }}
          }}
          async function setStat() {{
            if (!handle) {{ $st.innerHTML = '<span class="err">nicht verbunden</span>'; $btn.textContent='📁 Mit Ordner verbinden'; return; }}
            const p = await handle.queryPermission({{mode:'readwrite'}});
            if (p === 'granted') {{ $st.innerHTML = `<span class="ok">✅ ${{handle.name}}</span>`; $btn.textContent='🔌 Trennen'; }}
            else {{ $st.innerHTML = `<span class="err">Permission abgelaufen</span>`; $btn.textContent=`🔑 ${{handle.name}} neu autorisieren`; }}
          }}
          async function connect() {{
            try {{
              if (handle) {{ await clearH(); handle=null; lastW=null; sessionStorage.removeItem('taxi_autoload_done'); await setStat(); return; }}
              handle = await window.showDirectoryPicker({{mode:'readwrite'}});
              await saveH(handle); await setStat();
              const up = await readSync();
              if (up) {{ sessionStorage.setItem('taxi_autoload_done', '1'); $info.innerHTML = '📥 Geladen — Reload...'; setTimeout(()=>window.parent.location.reload(),600); return; }}
              await write();
            }} catch (e) {{ if (e.name !== 'AbortError') $info.innerHTML = `<span class="err">${{e.message}}</span>`; }}
          }}
          $btn.addEventListener('click', connect);
          (async () => {{
            handle = (await loadH()) || null; await setStat();
            if (!handle) return;
            if (sessionStorage.getItem('taxi_autoload_done')) return;
            const up = await readSync();
            if (up) {{ sessionStorage.setItem('taxi_autoload_done', '1'); $info.innerHTML = '📥 Daten geladen — Reload...'; setTimeout(()=>window.parent.location.reload(),600); }}
            else sessionStorage.setItem('taxi_autoload_done', '1');
          }})();
          setInterval(write, POLL_MS);
        }})();
        </script>
        """,
        height=100,
    )


# ─── Session State Init ───────────────────────────────────────────────
if "mandanten" not in st.session_state:
    st.session_state["mandanten"] = {}  # { firma: {beraternr, mandantennr} }

if "ls_load_done" not in st.session_state:
    st.session_state["ls_load_done"] = True
    _data = _ls_load_at_start()
    if _data and isinstance(_data, dict):
        st.session_state["mandanten"].update(_data.get("mandanten") or {})


def _persist():
    _ls_persist({"mandanten": st.session_state["mandanten"]})


def _fuzzy_mandant(extracted: str, dct: dict):
    if not extracted or not dct:
        return None
    el = extracted.lower().strip()
    if extracted in dct: return extracted
    for k in dct:
        if k.lower() == el: return k
    for k in dct:
        if k.lower().startswith(el): return k
    for k in dct:
        if el in k.lower(): return k
    return None


st.title("Taxi-Lohnliste → DATEV Lohn und Gehalt")
st.caption(
    "Excel-Lohnliste hochladen → CSV erzeugen. PersNr kommen direkt aus der Excel "
    "(Spalte B). Daten bleiben im Browser."
)


# ─── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    n_mand = len(st.session_state["mandanten"])
    st.markdown(f"📊 **{n_mand}** Taxi-Mandanten geladen")
    st.caption("Daten im Browser-LocalStorage. Auto-Save in Ordner empfohlen.")

    _auto_save_widget()

    if st.session_state["mandanten"]:
        st.download_button(
            "⬇️ Backup als JSON (manuell)",
            data=json.dumps({"mandanten": st.session_state["mandanten"]}, indent=2, ensure_ascii=False),
            file_name=f"taxi_datev_backup_{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()
    with st.expander("📤 Mandanten importieren", expanded=(n_mand == 0)):
        st.caption(
            "JSON mit Mandanten (Berater-Nr + Mandanten-Nr pro Firma). "
            "Kannst du aus der Mietwagen-App exportieren — gleiche Mandanten."
        )
        imp = st.file_uploader("JSON wählen", type=["json"], key="mapimp", label_visibility="collapsed")
        if imp is not None:
            try:
                data = json.loads(imp.read().decode("utf-8"))
                if isinstance(data, dict):
                    mandanten = data.get("mandanten") or data
                    if isinstance(mandanten, dict):
                        st.session_state["mandanten"].update(mandanten)
                        _persist()
                        st.success(f"✅ {len(mandanten)} Mandanten geladen.")
                    else:
                        st.error("Format unerkannt.")
                else:
                    st.error("Format unerkannt.")
            except Exception as e:
                st.error(f"Import: {e}")

    st.divider()
    encoding = st.selectbox("Encoding", ["cp1252", "utf-8"], index=0,
                            help="DATEV: ANSI/CP1252. Bei Umlautproblemen UTF-8.")

    with st.expander("📋 Lohnart-Mapping ansehen"):
        st.dataframe(
            [{"Sp": m["excel_col"], "Header": m["excel_header"], "LA": m["lohnart"]}
             for m in LOHNART_MAPPING],
            hide_index=True, use_container_width=True,
        )
        st.caption("**Vermutete** Lohnarten — Buchhalterin soll beim Testimport prüfen, "
                   "speziell LA 1525 (150% Zuschlag) und 1600 (Urlaub direkt als EUR).")

    with st.expander("📖 Wichtige Hinweise"):
        st.markdown(
            """
- **Excel-Format:** Sheet1, Header in Zeile 4, Daten ab Zeile 6
- **PersNr** wird direkt aus Spalte B genommen (kein Mapping nötig wie bei Mietwagen)
- **Stundensatz** (Spalte S) wird bei LA 1000 als Abweichender Faktor mitgegeben
- **Vorschuss / Abschlag** werden als negative Werte gebucht
- **Brutto** (Spalte K) ist nur Kontroll-Summe, nicht importiert
- **Soz.A** wird NICHT importiert — Lohnart unklar, manuell prüfen
- **DATEV-Profil**: gleich wie Mietwagen (Huen Monat 2, 9 Spalten Monatserfassung)
- **Import in DATEV**: Erfassen → Bewegungsdaten → Importieren → Tab Monatserfassung
"""
        )


# ─── Hauptbereich ─────────────────────────────────────────────────────
uploads = st.file_uploader("Taxi-Lohnliste(n) hochladen",
                           type=["xlsx"], accept_multiple_files=True)
if not uploads:
    st.info("Lade eine oder mehrere Taxi-Lohnlisten (.xlsx) hoch.")
    st.stop()

generierte = []

for idx, f in enumerate(uploads):
    parse = parse_excel(f.read())
    jm = monat_jahr_aus_dateiname(f.name) or (2026, 4)
    firma_extracted = firma_aus_dateiname(f.name)
    matched = _fuzzy_mandant(firma_extracted, st.session_state["mandanten"])
    firma_default = matched or firma_extracted

    st.divider()
    st.subheader(f"📄 {f.name}")

    if parse.globale_warnungen:
        for w in parse.globale_warnungen:
            st.error(w)
        continue

    col_f, col_j, col_m = st.columns([2, 1, 1])
    firma = col_f.text_input("Firma / DATEV-Mandant", value=firma_default, key=f"fi_{idx}")
    jahr = col_j.number_input("Jahr", value=jm[0], min_value=2000, max_value=2100, step=1, key=f"y_{idx}")
    monat = col_m.number_input("Monat", value=jm[1], min_value=1, max_value=12, step=1, key=f"m_{idx}")

    meta = st.session_state["mandanten"].setdefault(firma, {})
    col_b, col_mn = st.columns(2)
    beraternr = col_b.text_input("Beraternummer", value=meta.get("beraternr", ""),
                                  key=f"ber_{idx}", placeholder="z.B. 1479590")
    mandantennr = col_mn.text_input("Mandantennummer", value=meta.get("mandantennr", ""),
                                     key=f"mdt_{idx}", placeholder="z.B. 10003")
    if beraternr.strip() != meta.get("beraternr", "") or mandantennr.strip() != meta.get("mandantennr", ""):
        if beraternr.strip() or mandantennr.strip():
            meta["beraternr"] = beraternr.strip()
            meta["mandantennr"] = mandantennr.strip()
        else:
            st.session_state["mandanten"].pop(firma, None)
        _persist()

    if not beraternr.strip() or not mandantennr.strip():
        st.warning("⚠️ Ohne Berater- und Mandantennummer wird der Import in DATEV abgelehnt.")

    # Bewegungsdaten-CSV bauen
    csv_text, stat = baue_csv(parse.mitarbeiter, int(jahr), int(monat),
                              beraternr=beraternr.strip(), mandantennr=mandantennr.strip())
    try:
        data = csv_bytes(csv_text, encoding=encoding)
        encoding_err = None
    except EncodingError as e:
        data = csv_bytes(csv_text, encoding="utf-8")
        encoding_err = str(e)

    out_name = f"{firma}_{int(jahr):04d}-{int(monat):02d}_TAXI_DATEV.csv".replace(" ", "_")
    generierte.append((out_name, data))

    # Stammdaten-CSV bauen (Stundenlohn-Update)
    stamm_text, stamm_stat = baue_stammdaten_csv(parse.mitarbeiter, int(jahr), int(monat))
    try:
        stamm_data = csv_bytes(stamm_text, encoding=encoding)
    except EncodingError:
        stamm_data = csv_bytes(stamm_text, encoding="utf-8")
    stamm_name = f"{firma}_{int(jahr):04d}-{int(monat):02d}_TAXI_STAMM_Stundenlohn.csv".replace(" ", "_")
    generierte.append((stamm_name, stamm_data))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mitarbeiter", len(parse.mitarbeiter))
    c2.metric("Bewegungs-Zeilen", stat["zeilen_geschrieben"])
    c3.metric("Stamm-Zeilen", stamm_stat["zeilen_geschrieben"])
    c4.metric("Abrechnungsmonat", stat["abrechnungsmonat"])

    if encoding_err:
        st.error(f"❌ Encoding: {encoding_err}")

    # Beide CSVs in ein ZIP packen → ein Download-Button
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"1_STAMM_{stamm_name}", stamm_data)
        zf.writestr(f"2_BEWEGUNG_{out_name}", data)
    zip_name = f"{firma}_{int(jahr):04d}-{int(monat):02d}_TAXI_DATEV-Komplett.zip".replace(" ", "_")

    st.download_button(
        "⬇️ Beide CSVs herunterladen (ZIP)",
        data=zip_buf.getvalue(), file_name=zip_name, mime="application/zip",
        key=f"dl_zip_{idx}", type="primary", use_container_width=True,
        help="Enthält Stammdaten-CSV (1_STAMM…) und Bewegungsdaten-CSV (2_BEWEGUNG…). "
             "Reihenfolge im Dateinamen — erst die 1, dann die 2 in DATEV importieren.",
    )

    with st.expander("Einzelne CSVs (optional)"):
        ec1, ec2 = st.columns(2)
        ec1.download_button(
            "1️⃣ Stammdaten-CSV",
            data=stamm_data, file_name=stamm_name, mime="text/csv",
            key=f"dl_stamm_{idx}", use_container_width=True,
        )
        ec2.download_button(
            "2️⃣ Bewegungsdaten-CSV",
            data=data, file_name=out_name, mime="text/csv",
            key=f"dl_{idx}", use_container_width=True,
        )

    st.info(
        f"**Import-Reihenfolge in DATEV für {firma}:**\n\n"
        f"1️⃣ **Stammdaten-CSV** → `Stammdaten → ASCII-Import-Assistent` → Stunden-/Tagelöhne\n\n"
        f"2️⃣ **Bewegungsdaten-CSV** → `Erfassen → Bewegungsdaten → Importieren` → Hersteller `Huen Monat 2` → Tab Monatserfassung\n\n"
        f"DATEV rechnet danach automatisch: Stunden × Stundenlohn = Brutto."
    )

    with st.expander("Werte-Vorschau"):
        zeilen = []
        for ma in parse.mitarbeiter:
            row = {"PersNr": ma.pers_nr or "—", "Name": ma.name, "Std-Satz": ma.stundensatz}
            for m in LOHNART_MAPPING:
                row[f'{m["lohnart"]}'] = ma.werte.get(m["lohnart"], "")
            row["Brutto-Soll"] = round(ma.soll_brutto, 2) if ma.soll_brutto else ""
            zeilen.append(row)
        st.dataframe(zeilen, hide_index=True, use_container_width=True)

    with st.expander("Warnungen & manuelle Nachträge"):
        if stat["uebersprungen_keine_persnr"]:
            st.warning("Ohne PersNr übersprungen: " + ", ".join(stat["uebersprungen_keine_persnr"]))
        gab_was = False
        for ma in parse.mitarbeiter:
            lines = []
            if ma.manuell_werte:
                for h, v in ma.manuell_werte.items():
                    lines.append(f"  • {h}: {v} → manuell in DATEV")
            if ma.warnungen:
                for w in ma.warnungen:
                    lines.append(f"  ⚠ {w}")
            if ma.info:
                lines.append(f"  ℹ {ma.info}")
            if lines:
                st.markdown(f"**{ma.name}** (PersNr {ma.pers_nr or '—'})\n\n" + "\n".join(lines))
                gab_was = True
        if not gab_was:
            st.success("Keine Warnungen.")

    with st.expander("CSV-Inhalt"):
        st.code(csv_text or "(leer)", language="csv")


if len(generierte) > 1:
    st.divider()
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in generierte:
            zf.writestr(name, data)
    st.download_button("⬇️ Alle CSVs als ZIP", data=zbuf.getvalue(),
                       file_name="Taxi_DATEV_CSVs.zip", mime="application/zip",
                       type="primary", use_container_width=True)
