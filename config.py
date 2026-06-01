"""
App-Konfiguration. Hier kannst du das Passwort und Logo-Einstellungen ändern.

Passwort-Änderung:
  1. python3 -c "import hashlib; print(hashlib.sha256('NEUES_PASSWORT'.encode()).hexdigest())"
  2. Den ausgegebenen Hash unten in PASSWORT_HASH einsetzen
  3. Commit + Push
"""

# Aktuelles Passwort: "huelohn2026" — bitte ändern!
PASSWORT_HASH = "1325efcdaa4ba5a4a76602d9590586d45415f583dfba4334054b29e3b638557a"

# Wenn True, wird vor der App ein Passwort-Vorhang gezeigt.
# Achtung: Der Hash steht im (public) Repo, daher Schutz light — nicht Tresor.
PASSWORT_AKTIV = True

# Logo-Konfiguration. Wenn LOGO_URL gesetzt ist, wird das Bild angezeigt.
# Sonst Text-Logo "Hue.IT".
LOGO_URL = ""  # z.B. "https://hue.it/logo.png" oder relative URL "./logo.png"
LOGO_TEXT = "Hue.IT"
LOGO_TAGLINE = "DATEV-Tools für Lohnbüros"
