# Datenspeicherungskonzept - Scrum Planning Poker

## Übersicht

SQLite als Datenbank für die interne Anwendung. Einfach zu dockerisieren, keine separate Datenbankinstanz nötig.

## Datenbankschema

### Tabelle: `users`
Speichert alle Teilnehmer, die jemals das Tool genutzt haben.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    session_id TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Felder:**
- `id`: Primärschlüssel
- `name`: Anzeigename des Nutzers (eindeutig)
- `session_id`: Cookie-ID zur Wiedererkennung
- `created_at`: Wann der Nutzer sich das erste Mal angemeldet hat
- `last_seen`: Letzte Aktivität (für optionale Bereinigung)

**Index:**
```sql
CREATE UNIQUE INDEX idx_users_session ON users(session_id);
```

---

### Tabelle: `stories`
Speichert alle Stories mit ihren Metadaten.

```sql
CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    creator_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'voting', 'revealed', 'completed')),
    is_unlocked BOOLEAN DEFAULT 0,
    final_points INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (creator_name) REFERENCES users(name)
);
```

**Felder:**
- `id`: Primärschlüssel
- `title`: Story-Titel
- `description`: Detaillierte Story-Beschreibung
- `creator_name`: Name des Erstellers (kann aufdecken)
- `status`:
  - `active`: Story wurde erstellt, Voting läuft
  - `revealed`: Karten wurden aufgedeckt
  - `completed`: Story ist abgeschlossen mit finaler Punktzahl
- `is_unlocked`: Boolean - wurde die Story durch Notfall-Entsperrung freigeschaltet? (0 = nein, 1 = ja)
- `final_points`: Finale Fibonacci-Zahl (NULL bis Story abgeschlossen)
- `created_at`: Erstellungszeitpunkt
- `completed_at`: Abschlusszeitpunkt

**Index:**
```sql
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_stories_created ON stories(created_at DESC);
```

---

### Tabelle: `votes`
Speichert alle abgegebenen Stimmen (auch bei mehreren Voting-Runden).

```sql
CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    points INTEGER NOT NULL,
    round INTEGER NOT NULL DEFAULT 1,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id),
    FOREIGN KEY (user_name) REFERENCES users(name),
    UNIQUE(story_id, user_name, round)
);
```

**Felder:**
- `id`: Primärschlüssel
- `story_id`: Referenz zur Story
- `user_name`: Name des Voters
- `points`: Abgegebene Fibonacci-Zahl
- `round`: Voting-Runde (1, 2, 3, ...) für Fälle, wo neu abgestimmt wird
- `voted_at`: Zeitpunkt der Stimmabgabe

**Constraint:** Ein User kann pro Story und Runde nur einmal voten.

**Indizes:**
```sql
CREATE INDEX idx_votes_story ON votes(story_id, round);
CREATE INDEX idx_votes_user ON votes(user_name);
```

---

### Tabelle: `unlock_requests`
Speichert, wer eine Story entsperren möchte (Notfall-Feature).

```sql
CREATE TABLE unlock_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id),
    FOREIGN KEY (user_name) REFERENCES users(name),
    UNIQUE(story_id, user_name)
);
```

**Felder:**
- `id`: Primärschlüssel
- `story_id`: Referenz zur Story
- `user_name`: Name des Users, der entsperren möchte
- `requested_at`: Zeitpunkt der Anfrage

**Constraint:** Ein User kann pro Story nur einmal Entsperrung anfordern.

**Indizes:**
```sql
CREATE INDEX idx_unlock_story ON unlock_requests(story_id);
```

**Logik:**
- Wenn ≥ 2 unlock_requests für eine story_id existieren → `stories.is_unlocked = 1`
- Nach Entsperrung kann jeder die Karten aufdecken (nicht nur der Ersteller)
- Requests werden gelöscht, sobald Story `completed` ist

---

## Gültige Fibonacci-Werte

Die erlaubten Punktzahlen sollten in der Anwendungslogik validiert werden:
`[0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]`

Optional: Spezialwerte wie `?` (keine Ahnung) oder `∞` (zu groß) könnten als negative Zahlen kodiert werden (-1, -2).

---

## Wichtige Queries

### Entsperr-Anfragen zählen
```sql
SELECT COUNT(*) as unlock_count
FROM unlock_requests
WHERE story_id = ?;
```

### Entsperr-Anfrage hinzufügen und prüfen
```sql
-- 1. Anfrage hinzufügen
INSERT OR IGNORE INTO unlock_requests (story_id, user_name)
VALUES (?, ?);

-- 2. Zählen
SELECT COUNT(*) FROM unlock_requests WHERE story_id = ?;

-- 3. Falls >= 2: Story entsperren
UPDATE stories SET is_unlocked = 1 WHERE id = ?;
```

### Aktive Story finden
```sql
SELECT * FROM stories
WHERE status IN ('active', 'voting', 'revealed')
ORDER BY created_at DESC
LIMIT 1;
```

### Alle Votes für aktuelle Runde einer Story
```sql
SELECT user_name, points, voted_at
FROM votes
WHERE story_id = ? AND round = ?
ORDER BY voted_at;
```

### Wer hat bereits gevoted (verdeckt)?
```sql
SELECT user_name
FROM votes
WHERE story_id = ? AND round = ?;
```

### Story mit allen Votes abschließen
Bei Abschluss einer Story alle relevanten Daten in einer Abfrage:
```sql
SELECT
    s.id, s.title, s.description, s.creator_name, s.created_at,
    v.user_name, v.points, v.round, v.voted_at
FROM stories s
LEFT JOIN votes v ON s.id = v.story_id
WHERE s.id = ?
ORDER BY v.round, v.voted_at;
```

---

## Status-Transitions

```
active → revealed → completed
   ↓          ↓
   └─────────└──→ (neu voten) → round++, status = active
```

1. Story wird erstellt: `status = 'active'`, `round = 1`
2. User voten, ihre Karten werden in `votes` gespeichert
3. Creator deckt auf: `status = 'revealed'`
4. Zwei Möglichkeiten:
   - **Konsens**: `final_points` wird gesetzt, `status = 'completed'`
   - **Divergenz**: `round++`, `status = 'active'` (neu voten)

---

## Datenmigration und Initialisierung

Bei Appstart sollte geprüft werden:
- Existieren die Tabellen? Falls nein, erstellen
- Gibt es eine "hängende" aktive Story? (Optional: auf completed setzen oder Warnung)

### Schema-Versionierung
Für spätere Erweiterungen (z.B. KI-Voting):
```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Datenschutz und Aufbewahrung

Da nur intern ohne Authentifizierung:
- Namen sind public innerhalb des Teams
- Keine sensiblen Daten
- Optional: Alte Stories nach X Monaten archivieren/löschen
- Optional: Inaktive Users nach X Monaten entfernen
