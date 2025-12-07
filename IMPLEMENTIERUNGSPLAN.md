# Implementierungsplan: SQLite-Migration + Admin-Dashboard (Feature 3)

## Übersicht

Dieser Plan beschreibt die schrittweise Migration von der aktuellen In-Memory-Lösung zu einer persistenten SQLite-Datenbank sowie die Implementierung des Admin-Dashboards (Feature 3).

**Status:** Planung (nicht umgesetzt)
**Geschätzter Aufwand:** 3-5 Tage
**Risiko:** Mittel (Breaking Change für laufende Sessions)

---

## Phase 1: SQLite-Datenbank-Migration

### 1.1 Analyse der aktuellen Datenstrukturen

**Aktueller Zustand (app.py:14-21):**

```python
users = {}              # session_id: {"name": "Alice", "last_seen": datetime}
stories = []            # Liste aller Stories
active_story_id = None  # ID der aktiven Story
votes = {}              # story_id: {user_name: {"points": 5, "round": 1}}
story_history = []      # Letzte 3 abgeschlossene Stories
event_log = []          # Letzte 10 Events
story_counter = 0       # Auto-Increment Counter
```

**Mapping zu Datenbank-Schema:**

| In-Memory | DB-Tabelle | Notizen |
|-----------|-----------|---------|
| `users` | `users` | session_id → name Mapping |
| `stories` | `stories` | Alle Stories (inkl. Historie) |
| `votes` | `votes` | Story-ID + User-Name + Round |
| `active_story_id` | Query auf `stories.status IN ('voting', 'revealed')` | Kein eigenes Feld nötig |
| `story_history` | Query auf `stories WHERE status='completed' ORDER BY completed_at DESC LIMIT 3` | Wird zu Query |
| `event_log` | OPTIONAL: Eigene `events` Tabelle | Später, initial weiter in-memory |
| `story_counter` | SQLite AUTOINCREMENT | Automatisch |

### 1.2 Datenbankschema erstellen

**Aufgaben:**

1. **Neue Datei erstellen:** `database.py`
   - SQLite-Verbindung initialisieren
   - Tabellen erstellen (CREATE TABLE IF NOT EXISTS)
   - Schema-Versionierung implementieren

2. **Schema aus DATABASE_CONCEPT.md umsetzen:**
   - Tabelle `users`
   - Tabelle `stories` (mit Status: 'pending', 'voting', 'revealed', 'completed')
   - Tabelle `votes`
   - Tabelle `unlock_requests` (für zukünftiges Feature)
   - Tabelle `schema_version`

3. **Indizes anlegen:**
   - `idx_users_session` auf users(session_id)
   - `idx_stories_status` auf stories(status)
   - `idx_stories_created` auf stories(created_at DESC)
   - `idx_votes_story` auf votes(story_id, round)
   - `idx_votes_user` auf votes(user_name)
   - `idx_unlock_story` auf unlock_requests(story_id)

**Dateistruktur:**
```
database.py          # DB-Initialisierung + Schema
models.py            # Optional: ORM-ähnliche Funktionen
```

### 1.3 Data Access Layer (DAL) implementieren

**Neue Funktionen in `database.py`:**

**User-Funktionen:**
- `get_user_by_session(session_id)` → User-Dict oder None
- `get_user_by_name(name)` → User-Dict oder None
- `create_user(name, session_id)` → User-ID
- `update_user_last_seen(session_id)` → Bool
- `get_all_users()` → Liste von Users (für Admin-Dashboard)

**Story-Funktionen:**
- `get_story_by_id(story_id)` → Story-Dict oder None
- `get_active_story()` → Story-Dict oder None (WHERE status IN ('voting', 'revealed'))
- `get_pending_stories()` → Liste von Stories (WHERE status='pending')
- `get_story_history(limit=3)` → Liste der letzten abgeschlossenen Stories
- `create_story(title, description, creator_name)` → Story-ID
- `update_story_status(story_id, status)` → Bool
- `update_story_round(story_id, round)` → Bool
- `complete_story(story_id, final_points)` → Bool
- `start_voting(story_id)` → Bool (Status: pending → voting)

**Vote-Funktionen:**
- `get_story_votes(story_id, round)` → Dict {user_name: {"points": X, "voted_at": T}}
- `cast_vote(story_id, user_name, points, round)` → Bool
- `clear_votes_for_round(story_id, round)` → Bool (bei neuem Round)
- `get_user_vote_history(user_name)` → Liste aller Votes (für Admin-Dashboard)

**Unlock-Funktionen (für zukünftiges Feature):**
- `add_unlock_request(story_id, user_name)` → Bool
- `get_unlock_count(story_id)` → Int
- `unlock_story(story_id)` → Bool (is_unlocked = 1)
- `clear_unlock_requests(story_id)` → Bool

### 1.4 App.py refactoring

**Schrittweise Umstellung:**

1. **Import hinzufügen:**
   ```python
   from database import init_db, get_user_by_session, create_story, ...
   ```

2. **Initialisierung (am Anfang von `if __name__ == '__main__'`):**
   ```python
   init_db('planning_poker.db')
   ```

3. **Route-by-Route ersetzen:**

   **Beispiel: `/set_name`**
   - Vorher: `users[session_id] = {"name": name, ...}`
   - Nachher: `create_user(name, session_id)`

   **Beispiel: `/create_story`**
   - Vorher: `stories.append(new_story)`
   - Nachher: `create_story(title, description, user['name'])`

   **Beispiel: `/vote`**
   - Vorher: `votes[story_id][user_name] = {...}`
   - Nachher: `cast_vote(story_id, user_name, points, round)`

   **Beispiel: `index()` Route**
   - Vorher: `active_story = get_active_story()` (in-memory)
   - Nachher: `active_story = get_active_story()` (DB-Query)

4. **WebSocket-Events beibehalten:**
   - Gleiche Events, nur Daten kommen aus DB statt RAM

5. **Session-Handling anpassen:**
   - `get_current_user()` muss nun DB abfragen statt `users` dict

### 1.5 Migration bestehender Daten

**Problem:** Bei Deployment geht alles verloren (aktuell in-memory)

**Lösung für Deployment:**
- Sauberer Cut: App herunterfahren, DB initialisieren, neu starten
- Downtime akzeptieren (internes Tool)

**Optional (falls Daten migriert werden sollen):**
- Export-Skript für In-Memory → JSON
- Import-Skript JSON → SQLite
- **Nicht empfohlen** (zu komplex für MVP)

### 1.6 Testing-Strategie

**Manuelle Tests:**
1. User registrieren → DB prüfen (sqlite3 CLI)
2. Story erstellen → DB prüfen
3. Voting → Votes in DB prüfen
4. Reveal → Status-Update prüfen
5. Complete → final_points + completed_at prüfen
6. Neustart → Daten bleiben erhalten ✅

**Automatisierte Tests (optional):**
- Unit-Tests für database.py Funktionen
- Integration-Tests für Routes

### 1.7 Datensicherung

**Nach Migration:**
- SQLite-Datei: `planning_poker.db`
- Speicherort: `/opt/planning-poker/planning_poker.db`

**Backup-Strategie:**
```bash
# Tägliches Backup via Cronjob
0 2 * * * cp /opt/planning-poker/planning_poker.db /backup/planning_poker_$(date +\%Y\%m\%d).db
```

**In OPERATIONS.md ergänzen:**
- Backup-Kommandos
- Restore-Prozedur
- DB-Integrität prüfen: `sqlite3 planning_poker.db "PRAGMA integrity_check;"`

---

## Phase 2: Admin-Dashboard (Feature 3)

### 2.1 Requirements-Analyse

**Aus feature3.md:**
1. Admin-Account mit Login (Zugangsdaten in .env)
2. Login-Seite
3. Admin-Dashboard mit:
   - Komplette Historie vergangener Abstimmungen
   - Liste aller bisherigen Abstimmer + letzte Aktivität

**Zusätzliche Features:**
- Logout-Funktion
- Session-Timeout für Admin
- Schutz der Admin-Routes (Decorator)

### 2.2 Authentifizierung implementieren

**Neue Abhängigkeiten:**

```txt
# In requirements.txt ergänzen:
python-dotenv==1.0.0
werkzeug==3.0.1  # Für Passwort-Hashing
```

**Neue Datei: `.env` (NICHT in Git!):**
```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<bcrypt-hash>
```

**Passwort-Hash generieren:**
```python
# Einmaliges Skript: generate_admin_password.py
from werkzeug.security import generate_password_hash
password = input("Admin-Passwort eingeben: ")
print(generate_password_hash(password))
```

**Neue Funktionen in `app.py`:**

```python
from dotenv import load_dotenv
from werkzeug.security import check_password_hash
import os

load_dotenv()

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')

def is_admin():
    """Prüft ob aktueller User Admin ist"""
    return session.get('is_admin', False)

def admin_required(f):
    """Decorator für Admin-Routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function
```

### 2.3 Admin-Routes erstellen

**Neue Routes in `app.py`:**

1. **`/admin/login` (GET + POST)**
   - Template: `templates/admin_login.html`
   - POST: Username + Passwort prüfen
   - Bei Erfolg: `session['is_admin'] = True`
   - Redirect zu `/admin/dashboard`

2. **`/admin/logout` (POST)**
   - `session.pop('is_admin', None)`
   - Redirect zu `/`

3. **`/admin/dashboard` (GET)**
   - Decorator: `@admin_required`
   - Template: `templates/admin_dashboard.html`
   - Daten laden:
     - Alle Stories: `get_all_stories()`
     - Alle User mit letzter Aktivität: `get_all_users_with_activity()`

**Neue DB-Funktionen:**

```python
# In database.py ergänzen:

def get_all_stories():
    """Alle Stories mit Votes"""
    # SELECT stories + JOIN votes
    # Gruppiert nach Story mit allen Teilnehmern

def get_all_users_with_activity():
    """Alle User mit letzter Vote-Aktivität"""
    # SELECT users LEFT JOIN votes
    # Gruppiert nach User, MAX(voted_at) als last_activity
```

### 2.4 Admin-Templates erstellen

**Template-Struktur:**

```
templates/
  admin_login.html       # Login-Formular
  admin_dashboard.html   # Dashboard mit Tabellen
  admin_base.html        # Base-Template für Admin-Bereich
```

**admin_login.html:**
- Einfaches Formular: Username + Passwort
- CSRF-Protection (Flask-WTF optional)
- Fehler-Anzeige bei falschen Credentials

**admin_dashboard.html:**
- Navbar mit Logout-Button
- Zwei Haupt-Bereiche:
  1. **Story-Historie:**
     - Tabelle: Titel, Ersteller, Status, Final Points, Teilnehmer, Datum
     - Filter: Nach Datum, Ersteller
     - Sortierung: Neueste zuerst
  2. **User-Aktivität:**
     - Tabelle: Name, Erste Teilnahme, Letzte Abstimmung, Anzahl Votes
     - Sortierung: Nach letzter Aktivität

### 2.5 Security-Überlegungen

**Wichtig:**
1. `.env` in `.gitignore` aufnehmen
2. Admin-Session-Timeout: 30 Minuten
3. Rate-Limiting für Login (optional, später)
4. HTTPS in Produktion (siehe OPERATIONS.md)

**Session-Timeout implementieren:**
```python
from datetime import timedelta

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    session.permanent = True  # Session läuft ab nach PERMANENT_SESSION_LIFETIME
    ...
```

### 2.6 Deployment-Anpassungen

**Neue Datei: `.env.example`**
```env
# Copy to .env and set your values
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<generate with generate_admin_password.py>
```

**OPERATIONS.md ergänzen:**
- Admin-Setup-Anleitung
- Passwort-Hash generieren
- .env-Datei erstellen

---

## Phase 3: Integration und Testing

### 3.1 Integrations-Reihenfolge

**Empfohlene Reihenfolge:**

1. **SQLite-Grundgerüst** (1-2 Tage)
   - `database.py` erstellen
   - Schema anlegen
   - Basis-Funktionen testen

2. **Route-Migration** (1-2 Tage)
   - Eine Route nach der anderen umstellen
   - Nach jeder Route manuell testen
   - WebSocket-Events prüfen

3. **Admin-Auth** (0.5 Tage)
   - .env-Setup
   - Login/Logout implementieren
   - Decorator testen

4. **Admin-Dashboard** (1 Tag)
   - DB-Queries für Dashboard
   - Templates erstellen
   - Daten korrekt anzeigen

5. **Dokumentation** (0.5 Tage)
   - OPERATIONS.md aktualisieren
   - README_MVP.md anpassen
   - Migration-Guide für Deployment

### 3.2 Test-Checklist

**Funktionale Tests:**

- [ ] User registriert sich → DB-Eintrag vorhanden
- [ ] User mit Cookie kommt zurück → Wird erkannt
- [ ] Story erstellen → Status 'pending' in DB
- [ ] Voting starten → Status 'voting'
- [ ] Vote abgeben → votes-Tabelle gefüllt
- [ ] Karten aufdecken → Status 'revealed'
- [ ] Story abschließen → Status 'completed', final_points gesetzt
- [ ] Neue Runde → round++, Votes gelöscht
- [ ] App-Neustart → Alle Daten noch da ✅
- [ ] WebSocket-Updates funktionieren
- [ ] Admin-Login → Session gesetzt
- [ ] Admin-Dashboard → Daten korrekt
- [ ] Admin-Logout → Session gelöscht
- [ ] Nicht-Admin versucht Dashboard → Redirect zu Login

**Performance-Tests:**
- [ ] 50 Stories in DB → Dashboard lädt schnell
- [ ] 20 gleichzeitige Verbindungen → Keine Locks

**Security-Tests:**
- [ ] Ohne Admin-Session → Dashboard nicht erreichbar
- [ ] Falsches Passwort → Login verweigert
- [ ] .env nicht in Git

### 3.3 Rollback-Plan

**Falls Migration fehlschlägt:**

1. Alte Version wiederherstellen:
   ```bash
   git checkout <previous-commit>
   systemctl restart planning-poker
   ```

2. DB-Datei löschen (falls korrupt):
   ```bash
   rm planning_poker.db
   ```

3. In-Memory-Modus beibehalten bis Fehler gefunden

---

## Phase 4: Deployment

### 4.1 Deployment-Schritte

**Vorbereitung:**
1. Code in Git committen
2. Backup des aktuellen Stands erstellen
3. Downtime ankündigen (internes Tool)

**Auf Server:**
```bash
# 1. App stoppen
sudo systemctl stop planning-poker

# 2. Code aktualisieren
cd /opt/planning-poker
git pull origin main

# 3. Dependencies aktualisieren
source venv/bin/activate
pip install -r requirements.txt

# 4. .env-Datei erstellen
cp .env.example .env
nano .env  # Passwort-Hash eintragen

# 5. Admin-Passwort generieren
python generate_admin_password.py

# 6. DB initialisieren (erstellt Tabellen)
python -c "from database import init_db; init_db('planning_poker.db')"

# 7. Berechtigungen setzen
chown www-data:www-data planning_poker.db
chmod 644 planning_poker.db

# 8. App starten
sudo systemctl start planning-poker

# 9. Status prüfen
sudo systemctl status planning-poker
tail -f /var/log/syslog
```

### 4.2 Post-Deployment Verifikation

**Checkliste:**
- [ ] App startet ohne Fehler
- [ ] DB-Datei existiert: `ls -lh planning_poker.db`
- [ ] Schema korrekt: `sqlite3 planning_poker.db ".schema"`
- [ ] User kann sich registrieren
- [ ] Story kann erstellt werden
- [ ] Admin-Login funktioniert
- [ ] Dashboard zeigt Daten

### 4.3 Monitoring

**Neue Überwachungspunkte:**
- DB-Dateigröße: `du -h planning_poker.db`
- DB-Integrität: `sqlite3 planning_poker.db "PRAGMA integrity_check;"`
- Anzahl Stories: `sqlite3 planning_poker.db "SELECT COUNT(*) FROM stories;"`
- Anzahl Users: `sqlite3 planning_poker.db "SELECT COUNT(*) FROM users;"`

---

## Anhang: Dateiänderungen Übersicht

### Neue Dateien

| Datei | Zweck |
|-------|-------|
| `database.py` | DB-Initialisierung + DAL |
| `.env` | Admin-Credentials (NICHT in Git) |
| `.env.example` | Template für .env |
| `generate_admin_password.py` | Passwort-Hash-Generator |
| `templates/admin_login.html` | Admin-Login-Seite |
| `templates/admin_dashboard.html` | Admin-Dashboard |
| `planning_poker.db` | SQLite-Datenbank (erstellt bei init) |

### Geänderte Dateien

| Datei | Änderungen |
|-------|-----------|
| `app.py` | - Imports ergänzt<br>- In-Memory dicts entfernt<br>- Routes auf DB-Calls umgestellt<br>- Admin-Routes hinzugefügt<br>- Admin-Decorator |
| `requirements.txt` | + python-dotenv<br>+ werkzeug |
| `.gitignore` | + .env<br>+ *.db |
| `OPERATIONS.md` | + DB-Backup-Sektion<br>+ Admin-Setup |
| `README_MVP.md` | + Persistenz-Info<br>+ Admin-Feature |

### Gelöschte/Deprecated

| Code | Status |
|------|--------|
| `users = {}` | Ersetzt durch DB |
| `stories = []` | Ersetzt durch DB |
| `votes = {}` | Ersetzt durch DB |
| `story_history = []` | Ersetzt durch Query |
| `story_counter = 0` | Ersetzt durch AUTOINCREMENT |
| `/reset` Route | Optional entfernen (Admin-Dashboard stattdessen) |

---

## Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Datenverlust bei Migration | Niedrig | Hoch | Backup + Downtime akzeptieren |
| DB-Locks bei Concurrent Access | Mittel | Mittel | SQLite WAL-Mode aktivieren |
| Passwort in .env vergessen | Mittel | Hoch | .env.example + Doku |
| Schema-Änderungen später | Hoch | Niedrig | schema_version Tabelle nutzen |
| Performance bei vielen Stories | Niedrig | Mittel | Indizes + Pagination im Dashboard |

---

## Zeitplan (Schätzung)

| Phase | Aufwand | Abhängigkeiten |
|-------|---------|----------------|
| 1.1-1.3 DB-Setup + DAL | 1 Tag | - |
| 1.4 App.py Refactoring | 1-2 Tage | 1.1-1.3 |
| 1.6-1.7 Testing + Doku | 0.5 Tage | 1.4 |
| 2.2-2.3 Admin-Auth | 0.5 Tage | 1.4 |
| 2.4 Admin-Templates | 0.5 Tage | 2.2-2.3 |
| 3.1-3.2 Integration Tests | 0.5 Tage | Alle vorigen |
| 4.1-4.3 Deployment | 0.5 Tage | 3.1-3.2 |
| **GESAMT** | **4-5 Tage** | |

---

## Next Steps (wenn Umsetzung startet)

1. ✅ Diesen Plan reviewen und absegnen
2. Branch erstellen: `git checkout -b feature/sqlite-migration`
3. `database.py` erstellen (Phase 1.2)
4. Schema testen mit Dummy-Daten
5. Erste Route migrieren (z.B. `/set_name`)
6. Schritt für Schritt fortfahren

---

**Plan erstellt am:** 2025-12-06
**Status:** Bereit zur Umsetzung
**Review:** Ausstehend
