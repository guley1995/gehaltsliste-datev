"""
Gehaltsliste → DATEV Lohn und Gehalt (Monatserfassung) CSV.

Workflow:
1. Excel hochladen → Parser extrahiert pro Mitarbeiter die Monatswerte.
2. UI: Beraternr, Mandantennr und PersNr pro Mitarbeiter eintragen
   (oder per JSON-Mapping importieren — persistiert im Browser-LocalStorage).
3. Download als 9-Spalten-CSV mit Header-Zeile (BeraterNr;MandNr;MM/JJJJ).
4. In DATEV: Erfassen → Bewegungsdaten → Importieren → Tab Monatserfassung.

Streamlit-Eigenheit: st.data_editor hängt in stlite/Pyodide, daher Layout
mit st.text_input pro Mitarbeiter.
"""
import hashlib
import io
import json
import re
import zipfile

import streamlit as st

from config import LOGO_TAGLINE, LOGO_TEXT, LOGO_URL, PASSWORT_AKTIV, PASSWORT_HASH
from mapping import LOHNART_MAPPING, MANUELL_IN_DATEV
from parser import firma_aus_dateiname, monat_jahr_aus_dateiname, parse_excel
from writer import MODUS_KALENDER, MODUS_MONAT, EncodingError, baue_csv, csv_bytes

st.set_page_config(page_title="Gehaltsliste → DATEV", layout="wide")

# ─── Logo / Header ────────────────────────────────────────────────────
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
      <div style="color:#888;font-size:13px;">{LOGO_TAGLINE}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Passwort-Vorhang (clientseitig, "Schutz light") ──────────────────
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

# ─── LocalStorage-Bridge via JS-Komponente ────────────────────────────
LOCAL_STORAGE_KEY = "gehaltsliste_datev_mappings_v1"


def _ls_persist(data: dict) -> None:
    """Schreibt Mappings in LocalStorage des Browsers via JS-Snippet (best effort).
    Wirft keine Exception wenn LocalStorage nicht verfügbar."""
    import streamlit.components.v1 as components

    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    components.html(
        f"""
        <script>
        try {{
            window.parent.localStorage.setItem(
                "{LOCAL_STORAGE_KEY}",
                {json.dumps(payload)}
            );
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


# ─── Session State Init ───────────────────────────────────────────────
if "all_mappings" not in st.session_state:
    st.session_state["all_mappings"] = {}
if "all_mandanten" not in st.session_state:
    # { firma: {"beraternr": "1479590", "mandantennr": "10010"} }
    st.session_state["all_mandanten"] = {}


def _alles_persistieren():
    """LocalStorage-Update: speichert all_mappings + all_mandanten zusammen."""
    payload = {
        "mappings": st.session_state["all_mappings"],
        "mandanten": st.session_state["all_mandanten"],
    }
    _ls_persist(payload)


def _auto_save_widget():
    """File System Access API Widget für Auto-Save in einen lokalen Ordner.
    User wählt einmal einen Ordner (idealerweise iCloud/OneDrive-synced),
    danach schreibt die App bei jeder Änderung automatisch ein JSON-Backup
    in diesen Ordner. Browser muss File System Access unterstützen (Chrome/Edge).
    """
    import streamlit.components.v1 as components
    components.html(
        f"""
        <style>
          :root {{ color-scheme: dark light; }}
          body {{ margin: 0; padding: 8px 0; font-family: -apple-system, system-ui, sans-serif; }}
          .row {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
          button.cn {{ padding: 4px 10px; border-radius: 6px; border: 1px solid #888; background: #0f62fe; color: white; cursor: pointer; font-size: 12px; }}
          button.cn:hover {{ filter: brightness(1.1); }}
          .status {{ color: #888; font-size: 12px; margin-top: 4px; }}
          .ok {{ color: #00a651; }}
          .err {{ color: #d32f2f; }}
        </style>
        <div>
          <div class="row">
            <button class="cn" id="connect">📁 Mit Ordner verbinden</button>
            <span id="state">…</span>
          </div>
          <div class="status" id="info">Auto-Save schreibt bei jeder Änderung ein <code>datev_backup.json</code> in den gewählten Ordner.</div>
        </div>
        <script>
        (function() {{
          const LS_KEY = "{LOCAL_STORAGE_KEY}";
          const IDB_NAME = "gehaltsliste_autosave";
          const IDB_STORE = "handles";
          const HANDLE_KEY = "dirHandle";
          const FILE_NAME = "datev_backup.json";
          const POLL_MS = 1500;

          const supported = !!(window.showDirectoryPicker);
          const $state = document.getElementById('state');
          const $info = document.getElementById('info');
          const $btn = document.getElementById('connect');

          if (!supported) {{
            $btn.disabled = true;
            $state.innerHTML = '<span class="err">Browser ohne File System Access API — nutze Chrome/Edge.</span>';
            return;
          }}

          // IndexedDB-Helpers
          function idb(mode) {{
            return new Promise((res, rej) => {{
              const req = indexedDB.open(IDB_NAME, 1);
              req.onupgradeneeded = () => req.result.createObjectStore(IDB_STORE);
              req.onsuccess = () => {{
                const tx = req.result.transaction(IDB_STORE, mode);
                res(tx.objectStore(IDB_STORE));
              }};
              req.onerror = () => rej(req.error);
            }});
          }}
          async function saveHandle(h) {{ const s = await idb('readwrite'); s.put(h, HANDLE_KEY); }}
          async function loadHandle() {{
            const s = await idb('readonly');
            return new Promise((res, rej) => {{
              const r = s.get(HANDLE_KEY); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
            }});
          }}
          async function clearHandle() {{ const s = await idb('readwrite'); s.delete(HANDLE_KEY); }}

          // File-Schreibe
          let currentHandle = null;
          let lastWritten = null;
          async function writeBackup() {{
            if (!currentHandle) return;
            try {{
              const perm = await currentHandle.queryPermission({{mode:'readwrite'}});
              if (perm !== 'granted') return;
              const raw = window.parent.localStorage.getItem(LS_KEY);
              if (!raw || raw === lastWritten) return;
              const fh = await currentHandle.getFileHandle(FILE_NAME, {{create:true}});
              const w = await fh.createWritable();
              await w.write(raw); await w.close();
              lastWritten = raw;
              const ts = new Date().toLocaleTimeString('de-DE');
              $info.innerHTML = `✅ Letzte Speicherung: ${{ts}} — <code>${{currentHandle.name}}/${{FILE_NAME}}</code>`;
            }} catch (e) {{
              $info.innerHTML = `<span class="err">Fehler beim Schreiben: ${{e.message}}</span>`;
            }}
          }}

          async function setStatus() {{
            if (!currentHandle) {{
              $state.innerHTML = '<span class="err">nicht verbunden</span>';
              $btn.textContent = '📁 Mit Ordner verbinden';
              return;
            }}
            const perm = await currentHandle.queryPermission({{mode:'readwrite'}});
            if (perm === 'granted') {{
              $state.innerHTML = `<span class="ok">✅ verbunden mit <b>${{currentHandle.name}}</b></span>`;
              $btn.textContent = '🔌 Trennen';
            }} else {{
              $state.innerHTML = `<span class="err">Permission abgelaufen — klick neu verbinden</span>`;
              $btn.textContent = `🔑 ${{currentHandle.name}} neu autorisieren`;
            }}
          }}

          async function connect() {{
            try {{
              if (currentHandle) {{
                // Bereits verbunden — trennen
                await clearHandle();
                currentHandle = null;
                lastWritten = null;
                await setStatus();
                return;
              }}
              const h = await window.showDirectoryPicker({{mode:'readwrite'}});
              await saveHandle(h);
              currentHandle = h;
              await setStatus();
              await writeBackup();
            }} catch (e) {{
              if (e.name !== 'AbortError') {{
                $info.innerHTML = `<span class="err">${{e.message}}</span>`;
              }}
            }}
          }}

          $btn.addEventListener('click', connect);

          // Boot: vorhandenes Handle laden
          loadHandle().then(h => {{
            currentHandle = h || null;
            setStatus();
          }});

          // Poll LocalStorage: bei Änderung schreiben
          setInterval(writeBackup, POLL_MS);
        }})();
        </script>
        """,
        height=100,
    )


def _enter_zu_naechstem_input():
    """JS-Snippet: Enter im text_input → blur + Fokus zum nächsten text_input.
    Fragil, weil Streamlit keine stabilen DOM-Anchors hat — wir filtern grob
    auf inputs mit dem Attribute aria-label='PersNr'."""
    import streamlit.components.v1 as components
    components.html(
        """
        <script>
        (function() {
          const attach = () => {
            const doc = window.parent.document;
            const inputs = Array.from(doc.querySelectorAll('input[type="text"], input[type="number"]'))
              .filter(i => (i.getAttribute('aria-label') || '').toLowerCase().includes('persnr'));
            inputs.forEach((inp, i) => {
              if (inp.dataset.entHandler) return;
              inp.dataset.entHandler = '1';
              inp.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  e.stopPropagation();
                  const all = Array.from(doc.querySelectorAll('input[type="text"]'))
                    .filter(i => (i.getAttribute('aria-label') || '').toLowerCase().includes('persnr'));
                  const idx = all.indexOf(inp);
                  inp.blur();
                  setTimeout(() => {
                    const next = all[idx + 1];
                    if (next) next.focus();
                  }, 120);
                }
              });
            });
          };
          attach();
          // Re-attach nach Streamlit-Reruns (DOM wird neu gebaut)
          setInterval(attach, 1500);
        })();
        </script>
        """,
        height=0,
    )


st.title("Gehaltsliste → DATEV Lohn und Gehalt")
st.caption("Excel hochladen → CSV erzeugen. Daten bleiben im Browser.")


# ─── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    # ── Status oben (kompakt) ─────────────────────────────────────────
    n_mandanten = len(st.session_state["all_mandanten"])
    n_mappings = len(st.session_state["all_mappings"])
    n_pers = sum(len(v) for v in st.session_state["all_mappings"].values())
    st.markdown(
        f"📊 **{n_mandanten}** Mandanten · **{n_pers}** Personalnummern "
        f"in {n_mappings} Firmen"
    )
    st.caption(
        "Daten leben im Browser-LocalStorage. Backup (JSON) regelmäßig "
        "in iCloud/Drive ablegen — sonst weg bei Browser-Reset."
    )

    # Auto-Save Widget (File System Access API, Chrome/Edge)
    _auto_save_widget()

    if st.session_state["all_mappings"] or st.session_state["all_mandanten"]:
        export_data = {
            "mappings": st.session_state["all_mappings"],
            "mandanten": st.session_state["all_mandanten"],
        }
        from datetime import date
        st.download_button(
            "⬇️ Backup als JSON (manuell)",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name=f"datev_backup_{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True,
            help="Manueller Download. Wenn oben Auto-Save in einen "
                 "Ordner aktiv ist, ist das nicht nötig.",
        )

    st.divider()

    # ── Setup (Import + Liste + Einstellungen) ────────────────────────
    with st.expander("📤 Mandanten + Einstellungen", expanded=(n_mandanten == 0)):
        st.caption(
            "EINE JSON enthält Berater-Nr, Mandanten-Nr UND PersNr "
            "für alle Firmen — einmal hochladen, alles ist drin."
        )
        col_imp, col_mode = st.columns([3, 2])
        with col_imp:
            imp = st.file_uploader(
                "JSON wählen", type=["json"], key="mapimp", label_visibility="collapsed"
            )
        with col_mode:
            import_mode = st.radio(
                "Import-Modus", ["Nur Neues", "Überschreiben"],
                index=0, key="imp_mode", label_visibility="collapsed",
                help="**Nur Neues**: vorhandene Mandanten/PersNr werden NICHT "
                     "geändert, nur neue kommen dazu. **Überschreiben**: alle "
                     "Werte aus der JSON ersetzen die in der Session.",
            )
        if imp is not None:
            try:
                data = json.loads(imp.read().decode("utf-8"))
                if not (isinstance(data, dict) and "mappings" in data):
                    if isinstance(data, dict):
                        data = {"mappings": data, "mandanten": {}}
                    else:
                        raise ValueError("Erwartet: {mappings: ..., mandanten: ...}")

                new_mappings = data.get("mappings") or {}
                new_mandanten = data.get("mandanten") or {}
                overwrite = import_mode.startswith("Über")

                stats = {"mand_neu": 0, "mand_skip": 0,
                         "pers_neu": 0, "pers_skip": 0}

                # Mandanten mergen
                for firma, meta in new_mandanten.items():
                    if firma in st.session_state["all_mandanten"] and not overwrite:
                        stats["mand_skip"] += 1
                    else:
                        if firma not in st.session_state["all_mandanten"]:
                            stats["mand_neu"] += 1
                        st.session_state["all_mandanten"][firma] = meta

                # PersNr-Mappings mergen (Deep-Merge auf Name-Ebene)
                for firma, namen_dict in new_mappings.items():
                    bestehende = st.session_state["all_mappings"].setdefault(firma, {})
                    for name, pn in namen_dict.items():
                        if name in bestehende and not overwrite:
                            stats["pers_skip"] += 1
                        else:
                            if name not in bestehende:
                                stats["pers_neu"] += 1
                            bestehende[name] = pn

                _alles_persistieren()
                st.session_state["last_export_warn"] = False  # neuer Stand

                msg = (
                    f"✅ **{stats['mand_neu']} neue Mandanten** + "
                    f"**{stats['pers_neu']} neue Personalnummern** hinzugefügt."
                )
                if stats["mand_skip"] or stats["pers_skip"]:
                    msg += (
                        f"  \n_Übersprungen (schon vorhanden): "
                        f"{stats['mand_skip']} Mandanten, {stats['pers_skip']} PersNr._"
                    )
                st.success(msg)
            except Exception as e:
                st.error(f"Import: {e}")

        if st.session_state["all_mappings"] or st.session_state["all_mandanten"]:
            st.markdown("**Geladene Mandanten:**")
            alle = sorted(set(st.session_state["all_mandanten"]) |
                          set(st.session_state["all_mappings"]))
            for fname_ in alle:
                cols = st.columns([3, 1])
                meta = st.session_state["all_mandanten"].get(fname_, {})
                n_p_firma = len(st.session_state["all_mappings"].get(fname_, {}))
                meta_str = (
                    f" — B {meta.get('beraternr','?')}/M {meta.get('mandantennr','?')}"
                    if meta else " — (keine Nr)"
                )
                cols[0].caption(f"**{fname_}**{meta_str} · {n_p_firma} PersNr")
                if cols[1].button("🗑", key=f"del_{fname_}"):
                    st.session_state["all_mappings"].pop(fname_, None)
                    st.session_state["all_mandanten"].pop(fname_, None)
                    _alles_persistieren()
                    st.rerun()

        st.divider()
        modus_label = st.radio(
            "DATEV-Profil-Typ",
            options=["Monatserfassung (9 Spalten)", "Kalendererfassung (11 Spalten)"],
            index=0,
            help="Monatserfassung = Standard.",
        )
        modus = MODUS_MONAT if modus_label.startswith("Monat") else MODUS_KALENDER
        encoding = st.selectbox(
            "Encoding",
            ["cp1252", "utf-8"],
            index=0,
            help="DATEV erwartet ANSI/CP1252. Bei Umlautproblemen UTF-8.",
        )

    with st.expander("📋 Lohnart-Mapping ansehen"):
        st.dataframe(
            [{"Sp": m["excel_col"], "Header": m["excel_header"], "LA": m["lohnart"]}
             for m in LOHNART_MAPPING],
            hide_index=True, use_container_width=True,
        )
        st.caption("Nicht in CSV (in DATEV manuell pflegen):")
        st.dataframe(
            [{"Sp": u["excel_col"], "Header": u["excel_header"], "LA": u["lohnart"]}
             for u in MANUELL_IN_DATEV],
            hide_index=True, use_container_width=True,
        )

    with st.expander("📖 DATEV-Profil einrichten (einmalig pro Mandant)"):
        st.markdown(
            """
**Einmalig pro Mandant** in DATEV ein ASCII-Importprofil für
Monatserfassung anlegen — ca. 10 Min. Danach läuft jeder Monatslauf
in unter einer Minute.

---

### Schritt 1: Wizard öffnen

```
DATEV Lohn und Gehalt
  → Mandant öffnen
  → Extras → ASCII-Import Assistent
  → "Neu"
```

### Schritt 2: Format-Einstellungen

| Feld | Wert |
|---|---|
| Profilname | z.B. `Huen Monat` |
| Feldtrennzeichen | **Strichpunkt** `;` |
| Datensatztrennzeichen | **Enter/Return** |
| Kommazeichen bei Zahlen | **`,`** |
| Trennz. Zeitangaben Echtminuten | **`:`** |

### Schritt 3: „Aufbau des Datensatzes" — die 9 Spalten

| Spaltennr | Feldinhalt |
|:---:|---|
| 1 | **Personalnummer** |
| 2 | **Lohnartennummer** |
| 3 | **Stundenanzahl** |
| 4 | **Tagesanzahl** |
| 5 | **Wert** |
| 6 | **Abweichender Faktor** |
| 7 | **Abweichende Lohnveränderung** |
| 8 | **Kostenstellennummer** |
| 9 | **Kostenträger** |

**Wichtig:** KEIN Kalendertag, KEIN Ausfallschlüssel. → Profil speichern.

### Wichtige Eigenheit des CSV-Formats

Die App schreibt **alle Werte (Stunden UND EUR) in Spalte 5 (Wert)** —
Spalte 3 (Stundenanzahl) bleibt leer. Das DATEV-Feld „Stundenanzahl"
hat ein hartes 24h-Limit (auch wenn der Name irreführend ist).
Stunden über 24h wären sonst abgewiesen. DATEV erkennt anhand der
Lohnart, ob ein Wert Std oder EUR ist (zeigt in der Maske die richtige
Einheit).

### Schritt 4: Monatlicher Import

```
Erfassen → Bewegungsdaten → Importieren
  → Hersteller: das angelegte Profil (z.B. „Huen Monat")
  → Tab "Monatserfassung" (nicht Kalendererfassung!)
  → Datei: die hier heruntergeladene CSV
  → Übernehmen
```

---

### Häufige Fehler

| Code | Bedeutung | Lösung |
|---|---|---|
| LN01465 | Beraternummer ungültig | Header-Zeile fehlt — Beraternr in der App eintragen |
| LN00252 | Wert nicht numerisch | Spalten verschoben, meist Folge von fehlendem Header |
| LN07951 | Ungültiges Abrechnungsdatum | DATEV-Mandant auf den Excel-Monat zurückstellen |
| LN01473 | Tagesstunden 0–24 | Profil falsch angelegt: Spalte 3 darf nicht „Tagesstunden" sein |
| LN07945 | Format passt nicht | Anzahl Spalten im Profil stimmt nicht (9 erwartet) |

### Tutorials mit Screenshots

- [PlanD-Anleitung](https://help.pland.app/de/articles/146082-zeiterfassung-in-datev-lohn-und-gehalt-importieren)
- [SaaS DATEV-Import](https://hilfe.saas.de/hilfesaas_v2/urlaubsverwaltung/datev-ascii-import)
- [DATEV-Community Thread 77249](https://www.datev-community.de/t5/Personalwirtschaft/Lohn-Gehalt-Stundendaten-ASCII-Import/td-p/77249)

### Wer hilft

- **DATEV-Hotline:** 0911/319-0 → Personalwirtschaft
- **Hue.IT:** Screenshot der Fehlermeldung + Beschreibung → wir passen Profil oder CSV an
"""
        )


# ─── Excel-Upload ─────────────────────────────────────────────────────
uploads = st.file_uploader("Excel-Dateien (eine pro Mandant/Monat)",
                           type=["xlsx"], accept_multiple_files=True)
if not uploads:
    st.info("Lade eine oder mehrere .xlsx hoch.")
    st.stop()


# ─── Hilfsfunktionen ──────────────────────────────────────────────────
INTEGER_PERSNR_RE = re.compile(r"^\d+$")


def _fuzzy_match_mandant(extracted: str, mandanten_dict: dict):
    """Findet einen passenden Mandanten-Key basierend auf dem aus der
    Excel extrahierten Kurzform-Namen (z.B. 'Wittys' → 'Wittys Shuttleservice GmbH').
    Reihenfolge: exact > case-insensitive > startswith > contains."""
    if not extracted or not mandanten_dict:
        return None
    el = extracted.lower().strip()
    if extracted in mandanten_dict:
        return extracted
    for key in mandanten_dict:
        if key.lower() == el:
            return key
    for key in mandanten_dict:
        if key.lower().startswith(el):
            return key
    for key in mandanten_dict:
        if el in key.lower():
            return key
    return None


def _persnr_ist_integer(pn: str) -> bool:
    return bool(INTEGER_PERSNR_RE.match((pn or "").strip()))


def _bulk_parse(text: str) -> dict:
    """Parst Textarea 'Name;PersNr' oder 'Name\\tPersNr' -> {name: persnr}."""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        for sep in (";", "\t", ",", "|"):
            if sep in line:
                parts = [p.strip() for p in line.split(sep, 1)]
                if len(parts) == 2 and parts[0]:
                    out[parts[0]] = parts[1]
                break
    return out


# ─── Pro Excel-Datei ──────────────────────────────────────────────────
generierte = []

for idx, f in enumerate(uploads):
    parse = parse_excel(f.read())
    jm = monat_jahr_aus_dateiname(f.name) or (2026, 3)
    firma_extracted = firma_aus_dateiname(f.name)
    # Fuzzy-Match: wenn 'Wittys' aus Excel-Name zu 'Wittys Shuttleservice GmbH'
    # im Mandanten-Dict passt, nimm den vollen DATEV-Namen
    matched = _fuzzy_match_mandant(firma_extracted, st.session_state["all_mandanten"])
    firma_default = matched or firma_extracted

    st.divider()
    st.subheader(f"📄 {f.name}")

    if parse.globale_warnungen:
        for w in parse.globale_warnungen:
            st.error(w)
        continue

    col_f, col_j, col_m = st.columns([2, 1, 1])
    firma = col_f.text_input("Firma / DATEV-Mandant", value=firma_default,
                             key=f"fi_{idx}_{f.name}")
    jahr = col_j.number_input("Jahr", value=jm[0], min_value=2000, max_value=2100,
                              step=1, key=f"y_{idx}_{f.name}")
    monat = col_m.number_input("Monat", value=jm[1], min_value=1, max_value=12,
                               step=1, key=f"m_{idx}_{f.name}")

    firma_map = st.session_state["all_mappings"].setdefault(firma, {})
    mandant_meta = st.session_state["all_mandanten"].setdefault(firma, {})

    # ── Berater-Nr & Mandanten-Nr (Pflicht für DATEV-Header) ──────────
    col_b, col_mn = st.columns([1, 1])
    beraternr_default = mandant_meta.get("beraternr", "")
    mandantennr_default = mandant_meta.get("mandantennr", "")
    beraternr_input = col_b.text_input(
        "Beraternummer (für CSV-Header)",
        value=beraternr_default,
        key=f"ber_{idx}_{f.name}",
        placeholder="z.B. 1479590",
        help="DATEV erwartet die Beraternummer in der 1. CSV-Zeile. "
             "Steht oben in DATEV LuG in der Titelleiste (vor dem Schrägstrich).",
    )
    mandantennr_input = col_mn.text_input(
        "Mandantennummer (für CSV-Header)",
        value=mandantennr_default,
        key=f"mdt_{idx}_{f.name}",
        placeholder="z.B. 10010",
        help="DATEV erwartet die Mandantennummer in der 1. CSV-Zeile. "
             "Steht in der Titelleiste hinter dem Schrägstrich.",
    )
    # Persistieren bei Änderung
    if (beraternr_input.strip() != beraternr_default or
            mandantennr_input.strip() != mandantennr_default):
        if beraternr_input.strip() or mandantennr_input.strip():
            mandant_meta["beraternr"] = beraternr_input.strip()
            mandant_meta["mandantennr"] = mandantennr_input.strip()
        else:
            st.session_state["all_mandanten"].pop(firma, None)
        _alles_persistieren()

    if not beraternr_input.strip() or not mandantennr_input.strip():
        st.warning(
            "⚠️ Ohne Berater- und Mandantennummer in der CSV-Header-Zeile "
            "lehnt DATEV den Import mit Fehler **LN01465** ab. Bitte oben "
            "ausfüllen (Werte stehen in DATEV LuG in der Titelleiste, z.B. "
            "`1479590 / 10010 FahrFlex GmbH`)."
        )

    # ── Übersprungene Mitarbeiter PROMINENT oben anzeigen (#3) ────────
    keine_persnr = [ma for ma in parse.mitarbeiter if not firma_map.get(ma.name) and not ma.pers_nr]
    keine_werte = []  # wird unten nach CSV-Erzeugung gefüllt
    info_mitarbeiter = [ma for ma in parse.mitarbeiter if ma.info]
    plausibilitaets_warnungen = [ma for ma in parse.mitarbeiter if ma.warnungen]

    if keine_persnr or info_mitarbeiter or plausibilitaets_warnungen:
        with st.container():
            if keine_persnr:
                st.warning(
                    "⚠️ **Mitarbeiter werden übersprungen, weil keine PersNr eingetragen ist:**  \n"
                    + "  \n".join(
                        f"• **{ma.name}**" + (f" — *Info: {ma.info}*" if ma.info else "")
                        for ma in keine_persnr
                    )
                    + "  \n\nBitte unten PersNr eintragen oder Mitarbeiter manuell in DATEV erfassen "
                      "(z.B. bei Festbezüglern wie Nebenjobbern)."
                )
            if plausibilitaets_warnungen:
                st.warning(
                    "⚠️ **Plausibilitäts-Warnungen** (Excel-Wert weicht von Stunden × Satz ab):  \n"
                    + "  \n".join(
                        f"• **{ma.name}**: " + " ".join(ma.warnungen)
                        for ma in plausibilitaets_warnungen
                    )
                )
            if info_mitarbeiter:
                with st.expander(f"ℹ️ {len(info_mitarbeiter)} Mitarbeiter mit Info-Notizen aus Spalte W"):
                    for ma in info_mitarbeiter:
                        st.markdown(f"- **{ma.name}**: {ma.info}")

    # ── Bulk-Eingabe (#7) ─────────────────────────────────────────────
    with st.expander("💡 Bulk-Eingabe: alle PersNr auf einmal"):
        st.caption(
            "Format pro Zeile: `Name;PersNr` (oder Tab/Komma/Pipe als Trenner). "
            "Z.B. aus DATEV-Mitarbeiterliste kopieren. Namen werden exakt verglichen."
        )
        bulk = st.text_area("Bulk", height=120, key=f"bulk_{idx}_{f.name}",
                            label_visibility="collapsed",
                            placeholder="Alit Caka;47\nAmar Drozak;12\n...")
        if st.button("Übernehmen", key=f"bulk_apply_{idx}_{f.name}"):
            bulk_map = _bulk_parse(bulk)
            matched, unmatched = 0, []
            ma_namen = {ma.name for ma in parse.mitarbeiter}
            for name, pn in bulk_map.items():
                if name in ma_namen:
                    firma_map[name] = pn
                    # Widget-State aktualisieren, damit text_input neu rendert
                    st.session_state[f"pn_{idx}_{f.name}_{name}"] = pn
                    matched += 1
                else:
                    unmatched.append(name)
            _alles_persistieren()
            if matched:
                st.success(f"{matched} PersNr übernommen.")
            if unmatched:
                st.warning("Nicht zugeordnet (Name nicht in Excel): " + ", ".join(unmatched))
            st.rerun()

    st.markdown("##### Personalnummer-Mapping")
    st.caption(
        "Trag pro Mitarbeiter die DATEV-PersNr ein. "
        "Wird in der Session + LocalStorage gespeichert."
    )

    # ── PersNr-Editor pro Mitarbeiter ─────────────────────────────────
    changed_any = False
    for ma in parse.mitarbeiter:
        cols = st.columns([3, 1, 4])
        cols[0].write(ma.name + (f"  *(Info: {ma.info[:40]})*" if ma.info else ""))
        default = firma_map.get(ma.name, ma.pers_nr or "")
        pn = cols[1].text_input(
            "PersNr",
            value=default,
            key=f"pn_{idx}_{f.name}_{ma.name}",
            label_visibility="collapsed",
            placeholder=ma.pers_nr or "—",
        )
        # ── PersNr-Format-Validierung (#5) ──
        tag = ""
        if pn.strip() and not _persnr_ist_integer(pn.strip()):
            tag = "⚠️ nicht ganzzahlig"
        cols[2].caption(
            f"Excel-Tab: {ma.pers_nr or '—'}" + (f"  · **{tag}**" if tag else "")
        )
        pn = pn.strip()
        if pn:
            if firma_map.get(ma.name) != pn:
                firma_map[ma.name] = pn
                changed_any = True
            ma.pers_nr = pn
        elif ma.name in firma_map:
            del firma_map[ma.name]
            changed_any = True
            ma.pers_nr = None

    # PersNr nochmal auf alle Mitarbeiter applizieren (nach Editor)
    for ma in parse.mitarbeiter:
        ma.pers_nr = firma_map.get(ma.name) or ma.pers_nr

    if changed_any:
        _alles_persistieren()

    # ── CSV bauen ─────────────────────────────────────────────────────
    csv_text, stat = baue_csv(
        parse.mitarbeiter, int(jahr), int(monat),
        beraternr=beraternr_input.strip(),
        mandantennr=mandantennr_input.strip(),
        modus=modus,
    )
    try:
        data = csv_bytes(csv_text, encoding=encoding)
        encoding_err = None
    except EncodingError as e:
        data = csv_bytes(csv_text, encoding="utf-8")  # Fallback fürs Download
        encoding_err = str(e)

    out_name = f"{firma}_{int(jahr):04d}-{int(monat):02d}_DATEV.csv".replace(" ", "_")
    generierte.append((out_name, data))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mitarbeiter", len(parse.mitarbeiter))
    c2.metric("CSV-Zeilen", stat["zeilen_geschrieben"])
    c3.metric("Übersprungen",
              len(stat["uebersprungen_keine_persnr"]) + len(stat["uebersprungen_keine_werte"]))
    c4.metric("Kalendertag", stat["kalendertag"])

    if encoding_err:
        st.error(
            f"❌ **Encoding-Problem mit {encoding}:** {encoding_err}\n\n"
            f"Die Datei wurde notfalls als UTF-8 ausgegeben. Wenn DATEV das nicht "
            f"akzeptiert, in der Sidebar Encoding auf `utf-8` umstellen "
            f"(beide Seiten konsistent)."
        )

    st.download_button("⬇️ CSV herunterladen", data=data, file_name=out_name,
                       mime="text/csv", key=f"dl_{idx}_{f.name}",
                       type="primary", use_container_width=True)

    st.success(
        f"**So importierst du `{out_name}` in DATEV Lohn und Gehalt:**\n\n"
        f"1. DATEV LuG öffnen, **Mandant {firma}** wählen\n"
        f"2. Menü **`Erfassen → Bewegungsdaten → Importieren`**\n"
        f"3. **Importprofil wählen** (einmalig vorher angelegt unter "
        f"`Extras → ASCII-Import Assistent`: 11 Spalten, Trennzeichen Semikolon, "
        f"Encoding ANSI/CP1252)\n"
        f"4. Heruntergeladene CSV auswählen → **Importieren**\n\n"
        f"⚠️ Krank-Tage werden separat in DATEV-Kalender gepflegt (nicht in CSV)."
    )

    with st.expander("Werte-Vorschau"):
        zeilen = []
        for ma in parse.mitarbeiter:
            row = {"PersNr": ma.pers_nr or "—", "Name": ma.name}
            for m in LOHNART_MAPPING:
                row[m["lohnart"]] = ma.werte.get(m["lohnart"], "")
            row["Soll-€"] = round(ma.soll_grundgehalt, 2) if ma.soll_grundgehalt else ""
            zeilen.append(row)
        st.dataframe(zeilen, hide_index=True, use_container_width=True)

    with st.expander("Manuell-Hinweise & Warnungen"):
        if stat["uebersprungen_keine_persnr"]:
            st.warning("Übersprungen — keine PersNr: " + ", ".join(stat["uebersprungen_keine_persnr"]))
        gab_was = False
        for ma in parse.mitarbeiter:
            lines = []
            if ma.manuell_werte:
                for h, v in ma.manuell_werte.items():
                    lines.append(f"  • {h}: {v} → manuell in DATEV")
            if ma.info:
                lines.append(f"  ℹ Notiz aus Excel-Spalte W (Freitext): {ma.info}")
            if lines:
                st.markdown(f"**{ma.name}** (PersNr {ma.pers_nr or '—'})\n\n" + "\n".join(lines))
                gab_was = True
        if not gab_was:
            st.success("Keine zusätzlichen Hinweise.")

    with st.expander("CSV-Inhalt"):
        st.code(csv_text or "(leer)", language="csv")


# ─── Multi-File ZIP ───────────────────────────────────────────────────
if len(generierte) > 1:
    st.divider()
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in generierte:
            zf.writestr(name, data)
    st.download_button("⬇️ Alle CSVs als ZIP", data=zbuf.getvalue(),
                       file_name="DATEV_CSVs.zip", mime="application/zip",
                       type="primary", use_container_width=True)

# ─── JS-Hook: Enter springt zum nächsten PersNr-Feld ─────────────────
_enter_zu_naechstem_input()


# ─── Beim ersten Aufruf: LocalStorage einmal laden ─────────────────────
# Wir nutzen einen kleinen Hack: ein verstecktes Component holt Daten aus
# LocalStorage und schreibt sie via st.experimental_set_query_params.
# Aber Streamlit-Komponenten können nicht direkt session_state setzen,
# daher fallback: User lädt JSON-Datei aus Sidebar bei Bedarf.
# LocalStorage-Persistenz funktioniert SCHREIBEND via _ls_persist(),
# LESEN beim Start zeigen wir in einer Hint-Box wenn was vorhanden:
if not st.session_state.get("ls_hint_shown"):
    st.session_state["ls_hint_shown"] = True
    import streamlit.components.v1 as components
    components.html(
        f"""
        <script>
        try {{
            const raw = window.parent.localStorage.getItem("{LOCAL_STORAGE_KEY}");
            if (raw) {{
                const banner = window.parent.document.createElement("div");
                banner.style.cssText = "position:fixed;bottom:12px;right:12px;z-index:9999;"
                    + "background:#0f62fe;color:white;padding:10px 14px;border-radius:8px;"
                    + "font-family:system-ui;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,0.2);"
                    + "max-width:320px;cursor:pointer;";
                banner.innerHTML = "💾 Gespeicherte Mappings im Browser gefunden.<br>"
                    + "Lade sie über die Sidebar via <b>'Mappings importieren'</b> "
                    + "→ erst dazu in dieser Session: hier den JSON kopieren.<br>"
                    + "<small>Klicken zum Schließen.</small>";
                banner.onclick = () => banner.remove();
                window.parent.document.body.appendChild(banner);
                // Lege JSON zum manuellen Download in ein hidden <a>
                const blob = new Blob([raw], {{type: "application/json"}});
                const dl = window.parent.document.createElement("a");
                dl.href = URL.createObjectURL(blob);
                dl.download = "datev_persnr_mappings_aus_browser.json";
                dl.style.cssText = "display:block;color:white;text-decoration:underline;margin-top:6px;";
                dl.textContent = "📥 Browser-Backup als JSON runterladen";
                banner.appendChild(dl);
            }}
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )
