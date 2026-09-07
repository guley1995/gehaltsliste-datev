# Brief für den Website-Agent: „Lohnautomatisierung für DATEV Lohn und Gehalt" veröffentlichen

**Auftrag:** Das Angebot von Hue.IT zur Automatisierung der Lohnabrechnung in DATEV Lohn und Gehalt
auf der Website veröffentlichen, an zwei Stellen:

1. **Unter „Leistungen"** als eigenes Produkt.
2. **Als Case Study** (Praxisbeispiel Mietwagen-Unternehmen).

Absender: Hue.IT, Tagline „DATEV-Tools für Lohnbüros". Sprache: Deutsch, Du oder Sie wie auf der
restlichen Website. Tonalität: sachlich, konkret, keine Floskeln.
Zielgruppe: Lohnbüros, Steuerkanzleien und Unternehmen mit eigenem Lohnbüro, die DATEV Lohn und Gehalt
nutzen und Mandanten mit Stundenlöhnern abrechnen (Mietwagen, Gastronomie, Logistik, Reinigung).

---

## 1. Die Kernbotschaft

Drei Sätze, die auf jeder der beiden Seiten vorkommen müssen:

1. **Kein händisches Eintragen mehr von Stunden, Zuschlägen, Vorschüssen und Auslagen in DATEV.**
   Die Monatswerte kommen über eine auf den Mandanten angepasste Schnittstelle in DATEV.
2. **Kein händisches Überarbeiten von Stammdaten mehr.** Stundenlohn, Bankverbindung, Adresse und
   andere Änderungen werden als Stammdaten-Import eingespielt statt in DATEV nachgeklickt.
3. **Neue Mitarbeiter werden automatisiert in DATEV angelegt.** Der Mitarbeiter füllt einen digitalen
   Personalfragebogen aus, die Daten werden geprüft und als Stammdaten in DATEV importiert.

Zusammen: Das Lohnbüro prüft und gibt frei, statt zu tippen.

---

## 2. Die drei Bausteine (nur diese Fakten verwenden)

### Baustein 1: Monatswerte importieren statt abtippen

**Problem:** Mandanten liefern monatlich eine Excel-Gehaltsliste (Stunden, Nacht-, Sonntags- und
Feiertagszuschläge, Urlaub, Vorschüsse, einbehaltenes Bargeld, Verpflegungspauschale, Trinkgeld).
Das Lohnbüro tippt diese Werte pro Mitarbeiter und pro Lohnart in die DATEV-Monatserfassung.
Bei 20 bis 40 Mitarbeitern und mehreren Lohnarten sind das mehrere hundert Eingaben pro Mandant
und Monat, jede mit Tippfehlerrisiko.

**Lösung:** Eine auf die Excel-Vorlage des Mandanten angepasste Schnittstelle wandelt die Liste in
eine DATEV-Importdatei für Lohn und Gehalt um. Das Lohnbüro importiert die Datei in DATEV
(Erfassen → Bewegungsdaten → Importieren). Einmalige Einrichtung pro Mandant, danach monatlich:
Excel hochladen, Vorschau prüfen, importieren.

**Was die Schnittstelle leistet (verifiziert, in Betrieb):**

- Erkennung von Firma, Monat und Jahr aus dem Dateinamen.
- Prüfung der Excel-Struktur vor der Umwandlung. Eine falsche oder veränderte Vorlage wird abgewiesen.
- Lohnarten-Mapping pro Mandant, angepasst an dessen Lohnartenkatalog in DATEV.
- Automatische Umrechnungen, zum Beispiel Urlaub von Euro in Stunden über den Stundensatz.
- Plausibilitätsprüfung: Soll-Grundgehalt gegen Stunden mal Stundensatz, Abweichungen werden angezeigt.
- Hinweis auf Werte, die bewusst nicht importiert werden, weil sie in DATEV woanders gepflegt werden
  (zum Beispiel Krank-Tage im Kalender).
- Vorschau aller Werte pro Mitarbeiter vor dem Download.
- Personalnummern-Zuordnung pro Mandant, mehrere Mandanten parallel, Backup der Zuordnungen.

### Baustein 2: Stammdaten importieren statt nachpflegen

**Problem:** Änderungen an Stammdaten (Stundenlohn ab Monat X, neue Bankverbindung, Umzug) werden in
DATEV pro Mitarbeiter von Hand geändert. Bei Stundenlohn-Anpassungen für 30 Fahrer sind das
30 Mal die gleiche Maske.

**Lösung:** Änderungen kommen als Stammdaten-Importdatei in DATEV Lohn und Gehalt
(ASCII-Import-Assistent → Stammdaten). Stundenlöhne werden historisiert, also gültig ab Monat,
sodass die Abrechnung automatisch den richtigen Satz nimmt. Der Stammdaten-Import in Lohn und Gehalt
wird von Hue.IT bereits produktiv für Stundenlohn-Änderungen genutzt.

### Baustein 3: Mitarbeiter automatisiert anlegen

**Problem:** Die Anlage eines neuen Mitarbeiters dauert mit Rückfragen oft einen halben Tag über
mehrere Tage verteilt: Ausweisfoto per WhatsApp, fehlende Steuer-ID, unleserliche IBAN,
falsche Krankenkasse, dann Abtippen in acht DATEV-Masken.

**Lösung:** Digitaler Personalfragebogen, den der Mitarbeiter selbst ausfüllt:

- Mehrsprachig (Deutsch, Englisch, Türkisch, Arabisch, Rumänisch, Polnisch, Russisch, Ukrainisch),
  Ausgabe an das Lohnbüro immer auf Deutsch.
- Prüfung beim Ausfüllen: IBAN mit Prüfziffer und Anzeige der Bank, Steuer-ID mit Prüfziffer,
  Sozialversicherungsnummer im Abgleich mit Geburtsdatum und Geburtsname, Krankenkasse aus
  Auswahlliste, Postleitzahl gegen Ort, Pflichtfelder je nach Staatsangehörigkeit und Vertragsart,
  Minijob-Grenze gegen Stundensatz und Wochenstunden.
- Die geprüften Daten werden gesammelt und als Stammdaten-Import in DATEV Lohn und Gehalt
  eingespielt. Der Mitarbeiter ist angelegt, die Personalnummer ist gleichzeitig für den
  Monatsimport aus Baustein 1 bekannt.
- Felder, die DATEV nicht per Import annimmt, werden dem Lohnbüro als kurze Nachtrage-Liste angezeigt.

**Hinweis für den Website-Agent:** Baustein 1 und 2 sind in Betrieb. Baustein 3 wird gerade
umgesetzt. Auf der Leistungsseite als Teil des Angebots beschreiben, wie oben.
In der Case Study bei den Ergebnissen nur Baustein 1 und 2 mit Zahlen belegen, Baustein 3 als
nächste Stufe desselben Projekts beschreiben. Keine Ergebniszahlen für Baustein 3 erfinden.

**Datenschutz, für alle Bausteine:** Die Schnittstelle läuft im Browser des Lohnbüros. Excel-Dateien
und Lohndaten werden nicht auf einen Server hochgeladen. Passwortschutz. Das ist ein Vertrauensvorteil
und gehört prominent auf die Seite.

**Was das Angebot nicht ist:** Keine DATEV-Schnittstelle über das Rechenzentrum, kein DATEV-Partnerprodukt.
Es werden Importdateien erzeugt, die das Lohnbüro selbst in DATEV einspielt.
Nicht verwenden: „DATEV-zertifiziert", „DATEV-Schnittstelle", „DATEV-Partner".
„Angepasste Schnittstelle" ist korrekt und gemeint als: pro Mandant auf dessen Excel-Vorlage und
Lohnartenkatalog angepasst.

---

## 3. Einsparung: Rechenmodell, keine erfundenen Zahlen

Die Website soll eine Einsparung in Stunden und Euro nennen. Die konkreten Zahlen müssen von Hue.IT
bestätigt werden (offene Punkte unten). Bis dahin nur das Modell und ein klar als Beispiel
gekennzeichneter Rechenfall.

**Monatswerte (Baustein 1), pro Mandant und Monat:**

```
Zeit vorher  = Mitarbeiter × Lohnarten mit Wert × Sekunden pro Eingabe + Kontrollzeit
Zeit nachher = Upload + Vorschau prüfen + Import
```

| Größe | Annahme |
|---|---|
| Mitarbeiter pro Mandant | 25 |
| Lohnarten mit Wert pro Mitarbeiter | 6 |
| Manuelle Eingabe je Wert inkl. Navigation | 20 s |
| Kontrolle nach manueller Eingabe | 15 min |
| Zeit mit Schnittstelle | 10 min |

Ergebnis: vorher rund 65 min, nachher rund 10 min, Ersparnis rund 55 min pro Mandant und Monat.

**Mitarbeiteranlage (Baustein 3), pro neuem Mitarbeiter:**

| Größe | Annahme |
|---|---|
| Datensammlung mit Rückfragen, manuell | 30 min |
| Erfassung in DATEV, manuell | 20 min |
| Prüfen und Freigeben mit Fragebogen und Import | 10 min |

Ergebnis: rund 40 min Ersparnis pro Neuanlage. Bei Mietwagen-Mandanten mit hoher Fluktuation
kommen schnell 5 bis 10 Neuanlagen pro Monat zusammen.

**Gesamtbeispiel:** Fünf Mandanten mit je 25 Mitarbeitern und zusammen 8 Neuanlagen pro Monat,
Stundensatz Lohnsachbearbeitung 60 €: rund 10 Stunden pro Monat, rund 120 Stunden und rund
7.000 € pro Jahr. **Rechenbeispiel, keine Messung.**

Erlaubt: „Beispiel: Bei 25 Mitarbeitern spart ein Lohnbüro rund 55 Minuten pro Mandant und Monat."
Nicht erlaubt: „Unsere Kunden sparen 7.000 € im Jahr", solange keine bestätigte Messung vorliegt.
Optional: kleiner Rechner auf der Seite, in dem der Besucher Mitarbeiterzahl, Neuanlagen pro Monat
und Stundensatz selbst einträgt.

---

## 4. Seite „Leistungen": Struktur

**Titel:** Lohnabrechnung in DATEV ohne Abtippen: Monatswerte, Stammdaten und neue Mitarbeiter per Import

**Untertitel:** Kein händisches Eintragen von Stunden und Zuschlägen, kein Nachpflegen von Stammdaten,
Mitarbeiter werden über einen digitalen Personalfragebogen automatisiert in DATEV Lohn und Gehalt angelegt.

**Abschnitte:**

1. Die Kernbotschaft (Abschnitt 1) als Einstieg.
2. Die drei Bausteine, je ein Block mit Problem, Lösung, drei bis fünf Stichpunkten (Abschnitt 2).
3. So läuft ein Monat ab: Mandant schickt Excel, Lohnbüro lädt hoch, prüft Vorschau, importiert.
   Neue Mitarbeiter: Link zum Fragebogen, Mitarbeiter füllt aus, Lohnbüro prüft, importiert.
4. Datenschutz (Browser-only, kein Server, Passwort).
5. Einsparung (Rechenbeispiel oder Rechner, Abschnitt 3).
6. Für wen: Lohnbüros und Kanzleien mit Stundenlohn-Mandanten. Jede Branche mit fester Excel-Vorlage.
7. Einführung: Analyse der Excel-Vorlage und des Lohnartenkatalogs, Anpassung der Schnittstelle,
   einmalige Einrichtung der Import-Profile in DATEV (Anleitung wird mitgeliefert), Testmonat parallel
   zur manuellen Erfassung.
8. Call to Action: Test mit einer echten Gehaltsliste des Interessenten.

**Nicht auf die Seite:** Live-URL und Passwort der bestehenden Instanz. Das ist die Instanz für
Bestandskunden, kein öffentliches Demo.

---

## 5. Case Study: Struktur

**Titel-Vorschlag:** Mietwagen-Mandant: von der Excel-Gehaltsliste zum DATEV-Import in zehn Minuten

**Kunde:** Anonymisieren („Mietwagen- und Shuttle-Unternehmen in Bayern mit rund [N] Fahrern"),
außer Hue.IT bestätigt schriftlich, dass der Firmenname genannt werden darf.
Keine erfundenen Zitate. Ein Zitat muss der Kunde freigeben.

**Aufbau:**

1. Ausgangslage: Monatliche Excel-Liste mit Stunden, vier Zuschlagsarten, Urlaub in Euro,
   Vorschüssen, Bargeld, Verpflegungspauschale und Trinkgeld. Alles wurde von Hand in die
   DATEV-Monatserfassung getippt. Stammdaten-Änderungen ebenfalls von Hand.
2. Besondere Anforderungen aus dem Projekt (alle real):
   - Urlaub steht in Euro in der Excel, DATEV will Stunden. Umrechnung über den Stundensatz.
   - Excel-interne Kontrollsumme (Grundgehalt) darf nicht importiert werden, dient nur dem Abgleich.
   - Krank-Tage dürfen nicht über den Import laufen, sondern werden im DATEV-Kalender gepflegt.
   - Das DATEV-Feld „Stundenanzahl" hat ein hartes 24-Stunden-Limit. Monatsstunden müssen in das
     Feld „Wert" geschrieben werden. Echter Stolperstein bei der Einrichtung.
   - Mehrere Mandanten mit eigenen Berater- und Mandantennummern und eigenen Personalnummern-Zuordnungen.
   - Stundenlohn-Änderungen gehen als historisierte Stammdaten in DATEV statt per Hand.
3. Lösung: Die angepasste Schnittstelle, Ablauf in drei Schritten, Screenshot der Vorschau
   (nur mit unkenntlich gemachten Namen und Beträgen).
4. Ergebnis: Rechenbeispiel aus Abschnitt 3 für Monatswerte und Stammdaten, plus qualitativ:
   keine Tippfehler mehr bei den Zuschlägen, Abgleich über Kontrollsumme, Lohnbüro braucht keine
   Kenntnis der Mandanten-Excel.
5. Zeitraum: Erstversion Mai 2026, produktiv seit Juni 2026 (bei Bedarf von Hue.IT bestätigen lassen).
6. Nächste Stufe im selben Projekt: digitaler Personalfragebogen in mehreren Sprachen mit Prüfungen,
   neue Fahrer werden per Stammdaten-Import automatisiert angelegt. Als laufende Umsetzung
   beschreiben, ohne Ergebniszahlen.

---

## 6. SEO und Begriffe

Suchbegriffe, die natürlich im Text vorkommen sollen: DATEV Lohn und Gehalt Import, Monatserfassung
importieren, ASCII-Import Lohn und Gehalt, Stammdaten Import DATEV, Personalfragebogen digital DATEV,
Mitarbeiter anlegen DATEV automatisch, Gehaltsliste Excel DATEV, Lohnbüro Automatisierung,
Mietwagen Lohnabrechnung DATEV.

„DATEV" nur als Produktnamen des Zielsystems nennen, Markenhinweis im Footer, falls die Website
das für andere Produkte auch macht.

---

## 7. Offene Punkte, die Hue.IT vor Veröffentlichung beantworten muss

- [ ] Reale Zahlen für die Einsparung: Anzahl Mandanten, Mitarbeiter pro Mandant, Neuanlagen pro
      Monat, gemessene Minuten vorher und nachher, Stundensatz. Sonst bleibt es beim Rechenbeispiel.
- [ ] Darf der Kundenname in der Case Study genannt werden? Schriftliche Freigabe.
- [ ] Kundenzitat gewünscht? Dann vom Kunden freigeben lassen.
- [ ] Preis oder Preismodell (pro Mandant, pro Monat, Einrichtungspauschale)? Ohne Preis nur „Anfrage".
- [ ] Screenshots: wer stellt anonymisierte Screenshots der Vorschau bereit?
- [ ] Sprachen des Fragebogens: die Liste oben ist ein Vorschlag, bitte bestätigen oder kürzen.

---

## 8. Lieferung durch den Website-Agent

- Leistungsseite als fertige Seite im Stil der bestehenden Leistungen.
- Case Study als fertige Seite, Kunde anonymisiert, Platzhalter für Zahlen und Zitat sichtbar
  markiert, bis die offenen Punkte geklärt sind.
- Beide Seiten intern verlinkt, Case Study auf der Startseite oder in der Case-Study-Übersicht eingebunden.
- Vor Veröffentlichung: Freigabe durch Hue.IT, besonders für Zahlen, Kundenname, Screenshots.
