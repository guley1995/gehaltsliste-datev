"""Gehaltsliste → DATEV CSV. text_input pro Mitarbeiter (data_editor hängt in stlite)."""
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


def _ls_bridge():
    """JS-Schnipsel, der LocalStorage-Mappings liest und an Streamlit zurückgibt
    sowie aktuelle Mappings nach LocalStorage schreibt. Geht in einem
    hidden iframe-Component, daher per JS->Parent-PostMessage."""
    pass  # placeholder — gleich konkret


def _ls_persist(data: dict) -> None:
    """Schreibt Mappings in LocalStorage via JS-Snippet (best effort)."""
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


def _ls_load_into_session():
    """Beim ersten Seitenaufruf: lädt LocalStorage-Mappings in die Session.
    Setzt session_state['all_mappings_loaded']=True nach Versuch."""
    import streamlit.components.v1 as components

    components.html(
        f"""
        <script>
        try {{
            const raw = window.parent.localStorage.getItem("{LOCAL_STORAGE_KEY}");
            if (raw) {{
                const ev = new CustomEvent("gehaltsliste-ls-loaded", {{ detail: raw }});
                window.parent.document.dispatchEvent(ev);
            }}
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


st.title("Gehaltsliste → DATEV Lohn und Gehalt")
st.caption("Excel hochladen → CSV erzeugen. Daten bleiben im Browser.")


# ─── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Einstellungen")

    modus_label = st.radio(
        "DATEV-Profil-Typ",
        options=["Monatserfassung (9 Spalten)", "Kalendererfassung (11 Spalten)"],
        index=0,
        help=(
            "**Monatserfassung** = monatliche Lohnart-Summen, ohne "
            "Tageslimit. Profil im DATEV ohne Kalendertag/Ausfallschlüssel "
            "konfiguriert.\n\n"
            "**Kalendererfassung** = tagesbezogene Buchungen, max. 24 h "
            "pro Stunden-Feld. Profil im DATEV mit Kalendertag-Spalte."
        ),
    )
    modus = MODUS_MONAT if modus_label.startswith("Monat") else MODUS_KALENDER

    encoding = st.selectbox(
        "Encoding",
        ["cp1252", "utf-8"],
        index=0,
        help="DATEV erwartet meist ANSI/CP1252. Wenn die App bei Sonderzeichen "
             "(z.B. Šarić) einen Encoding-Fehler meldet, hier auf utf-8 wechseln.",
    )

    st.divider()
    st.subheader("PersNr-Mappings")
    n_firmen = len(st.session_state["all_mappings"])
    n_pers = sum(len(v) for v in st.session_state["all_mappings"].values())
    st.caption(
        f"Aktuell: **{n_firmen} Firma(en)**, {n_pers} Einträge.\n\n"
        "Sicherung mit Export/Import (JSON) — z.B. in iCloud/Drive ablegen."
    )

    if st.session_state["all_mappings"] or st.session_state["all_mandanten"]:
        export_data = {
            "mappings": st.session_state["all_mappings"],
            "mandanten": st.session_state["all_mandanten"],
        }
        st.download_button(
            "⬇️ Mappings + Mandanten exportieren",
            data=json.dumps(export_data, indent=2, ensure_ascii=False),
            file_name="datev_persnr_mappings.json",
            mime="application/json",
            use_container_width=True,
        )

    imp = st.file_uploader("⬆️ Importieren", type=["json"], key="mapimp")
    if imp is not None:
        try:
            data = json.loads(imp.read().decode("utf-8"))
            # Neues Format: {"mappings": {...}, "mandanten": {...}}
            if isinstance(data, dict) and "mappings" in data:
                st.session_state["all_mappings"].update(data.get("mappings") or {})
                st.session_state["all_mandanten"].update(data.get("mandanten") or {})
                _alles_persistieren()
                st.success(f"{len(data.get('mappings') or {})} Firma(en) importiert.")
            # Altes Format: {Firma: {Name: PersNr}}
            elif isinstance(data, dict):
                st.session_state["all_mappings"].update(data)
                _alles_persistieren()
                st.success(f"{len(data)} Firma(en) importiert (Mandanten-Meta fehlt — bitte ergänzen).")
            else:
                st.error("Erwartet: {mappings: ..., mandanten: ...}")
        except Exception as e:
            st.error(f"Import: {e}")

    if st.session_state["all_mappings"]:
        with st.expander("Mappings ansehen / löschen"):
            for fname_ in list(st.session_state["all_mappings"].keys()):
                cols = st.columns([3, 1])
                meta = st.session_state["all_mandanten"].get(fname_, {})
                meta_str = f" — Berater {meta.get('beraternr','?')}/Mandant {meta.get('mandantennr','?')}" if meta else ""
                cols[0].write(
                    f"**{fname_}** — {len(st.session_state['all_mappings'][fname_])} Einträge{meta_str}"
                )
                if cols[1].button("🗑", key=f"del_{fname_}"):
                    del st.session_state["all_mappings"][fname_]
                    st.session_state["all_mandanten"].pop(fname_, None)
                    _alles_persistieren()
                    st.rerun()

    st.divider()
    st.subheader("Lohnart-Mapping")
    st.dataframe(
        [{"Sp": m["excel_col"], "Header": m["excel_header"], "LA": m["lohnart"]}
         for m in LOHNART_MAPPING],
        hide_index=True, use_container_width=True,
    )

    st.subheader("Manuell in DATEV")
    st.caption("NICHT in CSV — über DATEV-Maske/Kalender pflegen.")
    st.dataframe(
        [{"Sp": u["excel_col"], "Header": u["excel_header"], "LA": u["lohnart"]}
         for u in MANUELL_IN_DATEV],
        hide_index=True, use_container_width=True,
    )

    st.divider()
    with st.expander("📖 DATEV-Profil einrichten (einmalig pro Mandant)"):
        st.markdown(
            """
**Bevor der erste Import funktioniert**, musst du in DATEV Lohn und Gehalt
**einmal pro Mandant** ein ASCII-Importprofil anlegen.
Dauer: ca. 20 Min. Danach läuft jeder Monatslauf automatisch.

---

### Schritt 1: Assistent öffnen

```
DATEV Lohn und Gehalt öffnen
  → Mandant öffnen (z.B. Wittys)
  → Menüleiste oben:  Extras
                        └→ ASCII-Import Assistent
```

Beim ersten Aufruf: Profil-Übersicht ist leer. Klick **„Neu"** /
**„Hinzufügen"**.

### Schritt 2: Profil-Grunddaten

| Was DATEV fragt | Was du einträgst |
|---|---|
| Profilname | `Mietwagen Monatswerte` (oder ähnlich) |
| Was wird importiert? | **Bewegungsdaten** |
| Importart | **ASCII / Trennzeichen-getrennt** |

### Schritt 3: Datei-Format

| Feld | Wert |
|---|---|
| Feldtrennzeichen | **Semikolon** `;` |
| Stringbegrenzer | (keiner / leer) |
| Datensatztrennzeichen | **Enter/Return** |
| Zeichensatz | **ANSI / Windows-1252 / CP1252** |
| Datumsformat | **TT.MM.JJJJ** |
| Dezimaltrennzeichen | **Komma** |

> **Wichtig:** Die CSV beginnt mit einer **Header-Zeile**
> `Beraternr;Mandantennr;MM/JJJJ` (z.B. `1479590;10010;05/2026`),
> danach kommen die Datenzeilen. Das macht diese App automatisch,
> wenn du oben Berater-Nr und Mandanten-Nr einträgst.

### Schritt 4: Feldzuordnung (das Wichtigste)

Hier sagst du DATEV, welche Spalte unserer CSV welches DATEV-Feld ist.

**Variante A — Monatserfassung (Recommended, 9 Spalten):**
Lohnart-Summen für den ganzen Monat, ohne Tageslimit.

| CSV-Spalte | DATEV-Feld |
|:---:|---|
| 1 | **Personalnummer** |
| 2 | **Lohnartennummer** |
| 3 | **Stundenanzahl** |
| 4 | **Tagesanzahl** |
| 5 | **Wert / Betrag** |
| 6 | **Abweichender Faktor** |
| 7 | **Abweichende Lohnveränderung** |
| 8 | **Kostenstellennummer** |
| 9 | **Kostenträger** |

Wichtig: **KEIN Kalendertag, KEIN Ausfallschlüssel.**

**Variante B — Kalendererfassung (11 Spalten):**
Tagesbezogene Buchung mit max. 24 h pro Stundenfeld.

| CSV-Spalte | DATEV-Feld |
|:---:|---|
| 1 | Personalnummer |
| 2 | **Kalendertag** |
| 3 | **Ausfallschlüssel** |
| 4 | Lohnartennummer |
| 5 | Stundenanzahl (Tagesstunden, max. 24) |
| 6–11 | Tage, Wert, Faktor, LohnVer, KostST, KostTr |

In der Sidebar oben kannst du zwischen beiden Modi wechseln — der CSV-Output passt sich an.

→ **Profil speichern.** Fertig.

---

### Schritt 5: Monatlicher Import

```
DATEV Lohn und Gehalt
  → Mandant öffnen
  → Erfassen → Bewegungsdaten → Importieren
  → Profil auswählen: „Mietwagen Monatswerte"
  → Datei auswählen: die hier heruntergeladene .csv
  → Importieren
```

DATEV zeigt „X Sätze erfolgreich importiert" — Monatserfassung ist
befüllt.

---

### Tutorials mit Screenshots (externe Quellen)

- **[PlanD-Anleitung mit Screenshots](https://help.pland.app/de/articles/146082-zeiterfassung-in-datev-lohn-und-gehalt-importieren)** — sehr ausführlich, identisches Konzept
- **[SaaS DATEV-Import](https://hilfe.saas.de/hilfesaas_v2/urlaubsverwaltung/datev-ascii-import)** — 6-Schritt-Anleitung
- **[DATEV-Community Thread 77249](https://www.datev-community.de/t5/Personalwirtschaft/Lohn-Gehalt-Stundendaten-ASCII-Import/td-p/77249)** — andere Lohnbüros mit gleicher Frage
- **[Offizielle DATEV-Hilfecenter Doknr. 9219371](https://apps.datev.de/help-center/documents/9219371)** — Original-Doku (Login nötig)

### Troubleshooting

- **„LN01143" Fehlermeldung** beim Import → Personalnummer in der CSV ist
  in DATEV nicht angelegt. Mitarbeiter-Stamm prüfen.
- **„Lohnart nicht im Lohnartenstamm"** → die LA-Nummer (z.B. 9651) ist
  bei diesem Mandanten nicht angelegt. Stamm: `Stammdaten → Abrechnung
  → Lohnarten` und LA anlegen.
- **Umlaute zerschossen** (`?` statt `ü`) → Encoding stimmt nicht.
  In der Sidebar oben Encoding auf `utf-8` umstellen ODER im DATEV-Profil
  auf ANSI bleiben und unsere CSV als CP1252 (Default) lassen.
- **Datum-Fehler** → DATEV-Profil-Datumsformat muss `TT.MM.JJJJ` sein.

### Wer kann helfen?

- **DATEV-Hotline:** `0911/319-0` → Personalwirtschaft → Lohn und Gehalt.
  Die richten dir das Profil per Bildschirmübertragung in ~15 Min ein.
- **Bei mir** (Hue.IT): Screenshot/Beschreibung der Fehlermeldung
  schicken, dann passen wir das CSV-Format oder das Profil an.
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
            _ls_persist(st.session_state["all_mappings"])
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
        _ls_persist(st.session_state["all_mappings"])

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
