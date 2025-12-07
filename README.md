# 🃏 Planning Poker

Eine moderne, Echtzeit-fähige Planning Poker Web-Anwendung für agile Scrum-Teams. Schätzt User Stories gemeinsam mit der Fibonacci-Sequenz und dokumentiert eure Entscheidungen.

## ✨ Features

### Kernfunktionalität
- **Echtzeit-Abstimmungen** mit WebSockets - alle Teilnehmer sehen Updates live
- **Fibonacci-Schätzung** (1, 2, 3, 5, 8, 13, 21, 34, 55, 89)
- **Multi-Round Support** - bei Divergenz kann erneut abgestimmt werden
- **Konsens-Erkennung** - automatische Erkennung von perfektem und Fast-Konsens
- **Story-Verwaltung** - Titel, Beschreibung, automatische Warteschlange

### Erweiterte Features
- **Admin Dashboard** mit Übersicht aller Stories, Votes und Benutzer
- **Story-Kommentare** - kategorisierte Kommentare (Begründung, Ausführung, Akzeptanzkriterien)
- **Markdown Export** - alle Stories mit kompletten Voting-Daten exportierbar
- **Zuschauer-Modus** - Teilnehmer können zuschauen ohne abzustimmen
- **Persistente Daten** - SQLite-Datenbank mit vollständiger Voting-Historie
- **Permanente Sessions** - keine Timeout, 10 Jahre Cookie-Gültigkeit
- **Easter Egg** - optionales Einhorn beim Aufdecken der Karten 🦄

### Konfigurierbar
- Einhorn Easter Egg aktivieren/deaktivieren
- Einhorn Anzeigedauer konfigurierbar
- Zuschauer-Modus Feature ein-/ausblendbar

## 🚀 Schnellstart

### Voraussetzungen
- Python 3.12+
- pip

### Lokale Installation

1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd poker
   ```

2. **Virtual Environment erstellen**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # oder
   venv\Scripts\activate  # Windows
   ```

3. **Dependencies installieren**
   ```bash
   pip install -r requirements.txt
   ```

4. **Umgebungsvariablen konfigurieren**
   ```bash
   cp .env.example .env
   ```

   Bearbeite `.env` und setze mindestens:
   ```bash
   # Generiere einen Secret Key
   python -c "import secrets; print(secrets.token_hex(32))"
   # Füge den Key in .env ein
   SECRET_KEY=<dein-generierter-key>

   # Generiere Admin-Passwort Hash
   python generate_admin_password.py
   # Füge den Hash in .env ein
   ADMIN_PASSWORD_HASH=<generierter-hash>
   ```

5. **Datenbank initialisieren**
   ```bash
   python -c "import database as db; db.init_db()"
   ```

6. **App starten**
   ```bash
   python app.py
   ```

7. **Browser öffnen**
   ```
   http://localhost:5000
   ```

### Docker Installation

1. **Docker Compose starten**
   ```bash
   docker-compose up -d
   ```

2. **Admin-Passwort setzen** (beim ersten Start)
   ```bash
   docker-compose exec poker python generate_admin_password.py
   # Hash in .env eintragen
   docker-compose restart
   ```

3. **App ist erreichbar**
   ```
   http://localhost:5000
   ```

## 📖 Verwendung

### Für Teilnehmer

1. **Namen eingeben** beim ersten Besuch
2. **Story erstellen** mit Titel und optionaler Beschreibung
3. **Abstimmen** durch Klick auf eine Fibonacci-Zahl
4. **Warten** bis der Story-Ersteller die Karten aufdeckt
5. **Konsens erreichen** oder neue Runde starten

### Zuschauer-Modus
Aktiviere den Zuschauer-Modus in deinem Profil, um Abstimmungen zu beobachten ohne selbst abzustimmen.

### Story-Kommentare
Nach Abschluss einer Story können alle Teilnehmer Kommentare hinzufügen:
- **Begründung** - Warum diese Punktzahl?
- **Hinweise zur Ausführung** - Was muss beachtet werden?
- **Akzeptanzkriterien** - Wann ist die Story fertig?
- **Allgemeine Anmerkungen** - Sonstiges

### Admin-Bereich

**Zugriff:** `http://localhost:5000/admin`

Features:
- Übersicht aller Stories mit allen Voting-Runden
- User-Aktivität und Statistiken
- Markdown-Export aller abgeschlossenen Stories
- Logout-Funktion

**Export-Datei** enthält:
- Story-Details (Titel, Beschreibung, Punkte, Zeitstempel)
- Alle Voting-Runden mit Teilnehmer:innen und Punkten
- Statistiken pro Runde (Durchschnitt, Min, Max)
- Alle Kommentare gruppiert nach Typ

## ⚙️ Konfiguration

Erstelle eine `.env` Datei (siehe `.env.example`):

```bash
# Flask Secret Key (WICHTIG!)
SECRET_KEY=<generiert-mit-secrets.token_hex(32)>

# Admin Zugangsdaten
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<generiert-mit-generate_admin_password.py>

# Datenbank Pfad
DB_PATH=planning_poker.db

# Feature Toggles
ENABLE_UNICORN=false                 # Einhorn Easter Egg aktivieren
UNICORN_DISPLAY_SECONDS=3           # Anzeigedauer in Sekunden
ENABLE_SPECTATOR_MODE=true          # Zuschauer-Modus aktivieren
```

## 🏗️ Architektur

### Tech Stack
- **Backend:** Flask 3.1.2
- **Echtzeit:** Flask-SocketIO 5.5.1 (WebSockets)
- **Datenbank:** SQLite 3
- **Frontend:** Vanilla JavaScript, Pico CSS 1.x
- **Deployment:** Docker, Gunicorn, Eventlet

### Projektstruktur
```
poker/
├── app.py                  # Haupt-Flask-App
├── database.py             # SQLite Datenbank-Layer
├── utils.py                # Helper-Funktionen
├── voting_logic.py         # Konsens-Algorithmen
├── templates/              # Jinja2 Templates
│   ├── index.html         # Hauptseite
│   ├── admin_dashboard.html
│   ├── story_detail.html
│   └── anleitung.html
├── static/
│   ├── css/style.css      # Custom Styles
│   └── js/app.js          # WebSocket Client
├── .env.example           # Umgebungsvariablen Template
├── requirements.txt       # Python Dependencies
├── Dockerfile
└── docker-compose.yml
```

### Datenbank-Schema
- **users** - Teilnehmer mit Session-IDs
- **stories** - User Stories mit Status (pending, voting, revealed, completed)
- **votes** - Alle Abstimmungen mit Runden-Zuordnung
- **story_comments** - Kommentare zu Stories
- **events** - Event-Log für Aktivitäten
- **unlock_requests** - (Future Feature)

## 🔒 Sicherheit

- **Session Management:** Sichere Flask-Sessions mit Secret Key
- **Admin Auth:** Passwort-Hashing mit Werkzeug
- **Input Validation:** Form-Validierung und SQL-Injection-Schutz
- **CORS:** Konfigurierbar für WebSockets
- **Docker:** Isolierte Umgebung, Non-Root User

## 🧪 Testing

```bash
# App-Import testen
python -c "import app; print('✅ App OK')"

# Datenbank-Funktionen testen
python -c "import database as db; db.init_db('test.db'); print('✅ DB OK')"

# Voting Logic testen
python -c "from voting_logic import check_consensus; print(check_consensus([5,5,5]))"
```

## 📊 Voting-Logik

### Konsens-Typen

1. **Perfekter Konsens** ✅
   - Alle Teilnehmer haben die gleiche Zahl gewählt
   - Story wird mit diesem Wert vorgeschlagen

2. **Fast-Konsens** ✅
   - Nur eine Person weicht um eine Fibonacci-Zahl ab
   - Mehrheitswert wird vorgeschlagen

3. **Divergenz** 🔄
   - Verschiedene Schätzungen
   - **Empfohlen:** Höchster Wert (konservative Schätzung)
   - **Alternative:** Zweithäufigster Wert (falls vorhanden)
   - Möglichkeit für neue Abstimmungsrunde

### Outlier-Logik
Bei Divergenz wird der zweithäufigste Wert als Alternative angeboten, falls:
- Mindestens 2 Personen diesen Wert gewählt haben
- Er sich vom höchsten Wert unterscheidet

## 🐛 Troubleshooting

### Session verloren nach Neustart
- **Problem:** SECRET_KEY nicht gesetzt oder ändert sich
- **Lösung:** Setze einen festen SECRET_KEY in `.env`

### Admin-Login funktioniert nicht
- **Problem:** ADMIN_PASSWORD_HASH nicht korrekt gesetzt
- **Lösung:** `python generate_admin_password.py` ausführen und Hash in `.env` eintragen

### WebSocket-Verbindung schlägt fehl
- **Problem:** CORS oder Firewall
- **Lösung:** Prüfe `cors_allowed_origins` in `app.py`

### Datenbank-Fehler
- **Problem:** Alte Schema-Version
- **Lösung:** Datenbank löschen und neu initialisieren (⚠️ Datenverlust!)
  ```bash
  rm planning_poker.db
  python -c "import database as db; db.init_db()"
  ```

## 🗺️ Roadmap / Zukünftige Features

- [ ] KI-Teilnehmer mit Begründung der Schätzungen
- [ ] Export als CSV/JSON/Excel
- [ ] Story-Import aus Jira/GitHub Issues
- [ ] Team-Statistiken und Velocity-Tracking
- [ ] Mehrsprachigkeit (i18n)
- [ ] Custom Fibonacci-Sequenzen
- [ ] Story-Kategorien und Tags

## 📝 License

Dieses Projekt ist für interne Verwendung konzipiert.

## 🤝 Contributing

Dies ist ein internes Tool. Bei Fragen oder Feature-Requests bitte an das Entwicklungsteam wenden.

## 🙏 Danksagungen

- **Pico CSS** - Minimalistisches CSS Framework
- **Flask-SocketIO** - WebSocket Support für Flask
- **Claude Code** - Entwicklungsassistenz

---

**Version:** 1.0.0
**Letztes Update:** Dezember 2024
