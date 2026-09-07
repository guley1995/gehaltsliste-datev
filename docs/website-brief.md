# Brief für den Website-Agent: „Gehaltsliste → DATEV" als Produkt veröffentlichen

**Auftrag:** Das bestehende Tool „Gehaltsliste → DATEV Lohn und Gehalt" auf der Hue.IT-Website
veröffentlichen, und zwar an zwei Stellen:

1. **Unter „Leistungen"** als eigenes Produkt / Angebot.
2. **Als Case Study** (Praxisbeispiel Mietwagen- und Taxi-Unternehmen).

Absender: Hue.IT, Tagline „DATEV-Tools für Lohnbüros". Sprache: Deutsch, Du oder Sie wie auf
der restlichen Website. Tonalität: sachlich, konkret, keine Marketing-Floskeln.
Zielgruppe: Lohnbüros und Steuerkanzleien, die DATEV Lohn und Gehalt nutzen und
Mandanten mit Stundenlöhnern (Mietwagen, Taxi, Gastro, Logistik) abrechnen.

---

## 1. Was das Produkt ist (nur diese Fakten verwenden)

Alle Punkte sind im Code verifiziert. Nichts darüber hinaus behaupten.

**Problem:** Mandanten liefern monatlich eine Excel-Gehaltsliste (Stunden, Zuschläge, Vorschüsse,
Trinkgeld, Verpflegungspauschale usw.). Das Lohnbüro tippt diese Werte pro Mitarbeiter
und pro Lohnart in die DATEV-Monatserfassungsmaske. Bei 10 Lohnarten und 20 bis 40
Fahrern sind das mehrere hundert Eingaben pro Mandant und Monat, mit Tippfehlerrisiko.

**Lösung:** Web-Tool, das die Excel-Liste in eine DATEV-ASCII-Importdatei umwandelt.
Das Lohnbüro importiert die Datei in DATEV Lohn und Gehalt
(Erfassen → Bewegungsdaten → Importieren → Monatserfassung). Einmalige Einrichtung
eines Import-Profils pro Mandant, danach monatlich: Excel hochladen, prüfen, CSV laden, importieren.

**Funktionen, die es wirklich gibt:**

- Excel-Upload mit automatischer Erkennung von Firma, Monat und Jahr aus dem Dateinamen.
- Prüfung der Excel-Struktur (Spaltenüberschriften) vor der Umwandlung. Falsche Vorlage wird abgewiesen.
- Mapping von zehn Lohnarten (Stundenlohn, Nacht-, Sonntags-, Feiertagszuschläge, Urlaub,
  Vorschuss, einbehaltenes Bargeld, Verpflegungspauschale, Trinkgeld). Mapping pro Mandant anpassbar.
- Automatische Umrechnung Urlaub von Euro in Stunden über den Stundensatz.
- Plausibilitätsprüfung: Soll-Grundgehalt gegen Stunden mal Stundensatz, Abweichungen werden angezeigt.
- Hinweis auf Werte, die bewusst nicht importiert werden (Krank-Tage gehören in den DATEV-Kalender).
- Vorschau aller Werte pro Mitarbeiter vor dem Download.
- Personalnummern-Zuordnung (Name → DATEV-PersNr) pro Mandant, mit Bulk-Eingabe, gespeichert im Browser.
- Mehrere Mandanten parallel, Mehrfach-Upload, Backup und Wiederherstellung der Zuordnungen als JSON.
- Taxi-Variante: Stundenlohn-Änderungen werden zusätzlich als Stammdaten-Import geschrieben
  (historisiert, ab Monat gültig), plus Bewegungsdaten in einem ZIP.
- **Datenschutz:** Läuft komplett im Browser. Excel-Dateien und Lohndaten werden nie auf einen
  Server hochgeladen. Passwortschutz.

**Was es nicht ist:** Keine DATEV-Schnittstelle über das Rechenzentrum, kein DATEV-Partnerprodukt.
Es erzeugt eine Importdatei, die das Lohnbüro selbst einspielt. Das bitte auch so sagen,
das ist für Kanzleien eher ein Vertrauensvorteil als ein Nachteil.

---

## 2. Einsparung: Rechenmodell, keine erfundenen Zahlen

Die Website soll eine Einsparung in Stunden und Euro nennen. Die konkreten Zahlen
müssen von Hue.IT bestätigt werden (siehe offene Punkte unten). Bis dahin nur das
Modell und ein klar als Beispiel gekennzeichneter Rechenfall verwenden.

**Formel pro Mandant und Monat:**

```
Zeit vorher  = Mitarbeiter × Lohnarten pro MA × Sekunden pro Eingabe  + Kontrollzeit
Zeit nachher = Upload + Prüfen der Vorschau + Import                   (Fix, wenige Minuten)
Ersparnis    = (Zeit vorher − Zeit nachher) × 12 Monate × Stundensatz Lohnbüro
```

**Beispielrechnung (Annahmen, auf der Website als Beispiel kennzeichnen):**

| Größe | Annahme |
|---|---|
| Mitarbeiter pro Mandant | 25 |
| Lohnarten pro Mitarbeiter mit Wert | 6 |
| Manuelle Eingabe je Wert inkl. Navigation | 20 s |
| Kontrolle nach manueller Eingabe | 15 min |
| Zeit mit Tool (Upload, Vorschau, Import) | 10 min |
| Stundensatz Lohnsachbearbeitung | 60 € |

Ergebnis: vorher rund 65 min, nachher rund 10 min, Ersparnis rund 55 min pro Mandant und Monat.
Bei fünf Mandanten dieser Größe rund 55 Stunden und rund 3.300 € pro Jahr, dazu weniger
Tippfehler und Korrekturläufe. **Diese Zahlen sind ein Rechenbeispiel, keine Messung.**

**Formulierung auf der Seite:** „Beispiel: Bei 25 Mitarbeitern spart ein Lohnbüro rund
55 Minuten pro Mandant und Monat" ist erlaubt. „Unsere Kunden sparen 3.300 € im Jahr"
ist nicht erlaubt, solange es keine bestätigte Messung gibt.
Optional: einen kleinen Rechner auf der Seite einbauen, in dem der Besucher
Mitarbeiterzahl und Stundensatz selbst einträgt.

---

## 3. Seite „Leistungen": Struktur

**Titel:** Gehaltsliste → DATEV: Monatswerte importieren statt abtippen

**Untertitel:** Excel-Lohnliste vom Mandanten in eine DATEV-Importdatei für Lohn und Gehalt umwandeln.
Läuft im Browser, ohne Upload von Lohndaten.

**Abschnitte:**

1. Das Problem (3 bis 4 Sätze, siehe oben).
2. So funktioniert es (3 Schritte: Excel hochladen, Vorschau prüfen, CSV in DATEV importieren).
3. Was geprüft wird (Struktur, Plausibilität, fehlende Personalnummern).
4. Datenschutz (Browser-only, kein Server, Passwort).
5. Einsparung (Rechenbeispiel oder Rechner, Abschnitt 2).
6. Für wen: Lohnbüros und Kanzleien mit Stundenlohn-Mandanten. Branchen: Mietwagen, Taxi,
   Gastronomie, Logistik. Jede Branche mit fester Excel-Vorlage ist machbar.
7. Einführung: Einmalige Einrichtung des Import-Profils in DATEV pro Mandant
   (Anleitung wird mitgeliefert), Anpassung des Lohnarten-Mappings an den Mandanten.
8. Call to Action: Demo-Termin oder Test mit einer echten Gehaltsliste des Interessenten.

**Nicht auf die Seite:** Live-URL und Passwort des bestehenden Tools. Das ist die Instanz
für Bestandskunden, kein öffentliches Demo.

---

## 4. Case Study: Struktur

**Titel-Vorschlag:** Mietwagen-Mandant: von der Excel-Gehaltsliste zum DATEV-Import in zehn Minuten

**Kunde:** Bitte anonymisieren („Mietwagen- und Shuttle-Unternehmen in Bayern mit rund
[N] Fahrern"), außer Hue.IT bestätigt schriftlich, dass der Firmenname genannt werden darf.
Keine erfundenen Zitate. Wenn ein Zitat gewünscht ist, muss es der Kunde freigeben.

**Aufbau:**

1. Ausgangslage: Monatliche Excel-Liste mit Stunden, vier Zuschlagsarten, Urlaub in Euro,
   Vorschüssen, Bargeld, Verpflegungspauschale und Trinkgeld. Alles wurde von Hand in die
   DATEV-Monatserfassung getippt. Krank-Tage separat im Kalender.
2. Besondere Anforderungen aus dem Projekt (alle real):
   - Urlaub steht in Euro in der Excel, DATEV will Stunden. Umrechnung über den Stundensatz.
   - Excel-interne Kontrollsumme (Grundgehalt) darf nicht importiert werden, dient nur dem Abgleich.
   - Krank-Tage dürfen nicht über den Import laufen, sondern werden im DATEV-Kalender gepflegt.
   - Das DATEV-Feld „Stundenanzahl" hat ein hartes 24-Stunden-Limit. Monatsstunden müssen
     in das Feld „Wert" geschrieben werden. Das war ein echter Stolperstein bei der Einrichtung.
   - Mehrere Mandanten mit unterschiedlichen Berater- und Mandantennummern und eigenen
     Personalnummern-Zuordnungen.
   - Zweiter Mandant (Taxi) mit anderer Excel-Struktur und monatlich wechselnden Stundenlöhnen.
     Lösung: Stundenlöhne gehen als historisierte Stammdaten in DATEV, Bewegungsdaten separat.
3. Lösung: Das Tool, Ablauf in drei Schritten, Screenshot der Vorschau
   (Screenshots nur mit unkenntlich gemachten Namen und Beträgen).
4. Ergebnis: Rechenbeispiel aus Abschnitt 2, plus qualitativ: keine Tippfehler mehr bei
   den Zuschlägen, Abgleich über Kontrollsumme, Lohnbüro braucht keine DATEV-Kenntnisse
   der Mandanten-Excel.
5. Zeitraum: Erstversion Mai 2026, produktiv seit Juni 2026, Taxi-Variante Juni 2026
   (aus der Entwicklungshistorie, bei Bedarf von Hue.IT bestätigen lassen).
6. Ausblick, nur ein Satz und klar als Planung markiert: Digitaler Personalfragebogen
   in mehreren Sprachen mit Prüfungen (IBAN, Steuer-ID, SV-Nummer) und Stammdaten-Import
   für neue Mitarbeiter ist in Planung. **Nicht als verfügbares Produkt darstellen.**

---

## 5. SEO und Begriffe

Suchbegriffe, die natürlich im Text vorkommen sollen: DATEV Lohn und Gehalt Import,
Monatserfassung importieren, ASCII-Import Lohn und Gehalt, Gehaltsliste Excel DATEV,
Lohnbüro Automatisierung, Stundenlohn Mandanten, Taxi Lohnabrechnung DATEV,
Mietwagen Lohnabrechnung DATEV.

Nicht verwenden: „DATEV-zertifiziert", „DATEV-Schnittstelle", „DATEV-Partner".
Das Tool ist keines davon. „DATEV" nur als Produktnamen des Zielsystems nennen,
Markenhinweis im Footer, falls die Website das für andere Produkte auch macht.

---

## 6. Offene Punkte, die Hue.IT vor Veröffentlichung beantworten muss

- [ ] Reale Zahlen für die Einsparung: Anzahl Mandanten, Mitarbeiter pro Mandant,
      gemessene Minuten vorher und nachher, Stundensatz. Sonst bleibt es beim Rechenbeispiel.
- [ ] Darf der Kundenname in der Case Study genannt werden? Schriftliche Freigabe.
- [ ] Kundenzitat gewünscht? Dann vom Kunden freigeben lassen.
- [ ] Preis oder Preismodell (pro Mandant, pro Monat, Einrichtungspauschale)? Ohne Preis
      nur „Anfrage".
- [ ] Screenshots: wer stellt anonymisierte Screenshots der Vorschau bereit?
- [ ] Soll die Zeile zum Ausblick (Personalfragebogen) überhaupt rein?

---

## 7. Lieferung durch den Website-Agent

- Leistungsseite als fertige Seite im Stil der bestehenden Leistungen.
- Case Study als fertige Seite, Kunde anonymisiert, Platzhalter für Zahlen und Zitat
  sichtbar markiert, bis die offenen Punkte geklärt sind.
- Beide Seiten intern verlinkt (Leistung ↔ Case Study), Case Study auf der Startseite
  oder in der Case-Study-Übersicht eingebunden.
- Vor Veröffentlichung: Freigabe durch Hue.IT, besonders für Zahlen, Kundenname, Screenshots.
