# Planning Poker - Vollständige Implementierung

Funktionierende Version mit SQLite-Datenbank, WebSockets und Admin-Dashboard.

## Features

✅ Namen eingeben (Session-basiert)
✅ Story erstellen (Titel + Beschreibung)
✅ Fibonacci-Voting (0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89)
✅ Teilnehmerliste mit Live-Status
✅ Aufdecken (nur Ersteller)
✅ Automatische Konsens-Erkennung:
  - Vollständiger Konsens (alle gleich)
  - Fast-Konsens (nur einer weicht um 1 Fibonacci-Zahl ab)
  - Divergenz (neu abstimmen oder höchsten Wert nehmen)
✅ Mehrere Voting-Runden
✅ **2-Spalten-Design** 🎨
  - Linke Spalte (1/3): Teammitglieder-Liste + Event-Log + Link zur Anleitung
  - Rechte Spalte (2/3): Story-Liste, Kartenauswahl, Ergebnisse
  - Responsive: Auf Mobil übereinander
✅ **Story-Historie** (max 3 neueste abgeschlossene Stories)
✅ **Event-Log** (letzte 10 Aktivitäten mit farbigen Indikatoren)
✅ **Karten-Visualisierung** (echte Poker-Karten statt einfacher Buttons)
  - Verdeckte Karten während Voting (🎴)
  - Aufgedeckte Karten mit Punktzahl
  - Hover-Effekt für Kartenauswahl
✅ **WebSockets für Echtzeit-Updates** 🎉
  - Kein manuelles Neuladen mehr!
  - Sofortige Updates wenn jemand votet
  - Live-Verbindungsstatus (🟢 Live verbunden)
  - Alle Events werden in Echtzeit synchronisiert

✅ **Einhorn Easter Egg** 🦄
  - Erscheint beim Aufdecken der Karten
  - 10 verschiedene weise Sprüche (zufällig ausgewählt)
  - Floating-Animation + Bounce-In-Effekt
  - Verschwindet nach 2.5 Sekunden

✅ **SQLite-Datenbank für Persistenz** 💾
  - Alle Stories, Votes und User-Daten werden persistent gespeichert
  - Daten bleiben bei Neustart erhalten
  - Admin-Dashboard für Story-Historie und User-Aktivität

✅ **Notfall-Entsperrung** 🔓
  - Mindestens 2 Teilnehmer können Story entsperren
  - Verhindert blockierte Stories wenn Ersteller offline geht

✅ **Spectator-Modus** 👁️
  - User können als Zuschauer teilnehmen ohne zu voten
  - Toggle zwischen aktiver Teilnahme und Beobachtung

✅ **Auto-Start Feature** ⚡
  - Stories können automatisch starten wenn vorherige abgeschlossen
  - Nahtloser Workflow für Sprint Planning

## Noch nicht implementiert

❌ Docker-Setup
❌ AI-Teilnehmer mit Schätzungsbegründung

## Installation & Start

```bash
# Virtual Environment erstellen
python3 -m venv venv

# Virtual Environment aktivieren
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# Admin-Passwort generieren (einmalig)
python generate_admin_password.py
# Trage den generierten Hash in .env ein (siehe .env.example)

# Server starten
python app.py
```

Dann öffne: http://localhost:5000

**Schnellstart (ohne venv aktivieren):**
```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python app.py
```

## Verwendung

1. **Namen eingeben** - beim ersten Besuch
2. **Story erstellen** - Titel und optional Beschreibung
3. **Voten** - Klicke auf eine Fibonacci-Zahl
4. **Aufdecken** - nur der Story-Ersteller sieht den Button
5. **Ergebnis** - Konsens wird automatisch erkannt
6. **Abschließen oder neu voten** - je nach Ergebnis

## Hinweise

- Alle Daten werden persistent in SQLite gespeichert (planning_poker.db)
- Echtzeit-Updates via WebSockets - kein manuelles Neuladen nötig
- Für mehrere Teilnehmer einfach mehrere Browser-Tabs öffnen
- Nur eine Story kann gleichzeitig aktiv sein (in Voting/Revealed-Status)
- Admin-Dashboard verfügbar unter `/admin/login`

## Nächste Schritte

- [x] WebSockets für Echtzeit-Updates ✅
- [x] Datenbank für Persistenz ✅
- [x] Notfall-Entsperrung ✅
- [x] Easter Eggs ✅
- [x] Admin-Dashboard ✅
- [x] Spectator-Modus ✅
- [x] Auto-Start Feature ✅
- [ ] Docker-Setup
- [ ] AI-Teilnehmer mit Schätzungsbegründung
- [ ] Unit Tests
- [ ] Multi-Team Support (separate Räume)
