# Plan: Story-Kommentarsystem (Feature 7)

## Übersicht

Jeder Benutzer kann zu abgeschlossenen Stories Kommentare hinzufügen. Diese Kommentare dienen der Dokumentation von:
- Begründungen für die gewählte Punktzahl
- Wichtige Hinweise für die Ausführung
- Akzeptanzkriterien
- Lessons Learned

**Zweck:** Dokumentation für spätere KI-Verarbeitung und Team-Wissenstransfer

---

## Aktuelle Implementierung

### Story-Historie

**Location:** `templates/index.html` (Zeilen ca. 180-210)

Aktuell wird die Story-Historie angezeigt mit:
- Story-Titel
- Finale Punktzahl
- Liste aller Votes
- Status "Abgeschlossen"

**Keine Kommentar-Funktionalität vorhanden.**

### Database Schema

**Location:** `database.py`

Aktuelle Tabellen:
- `users` (Zeile 36-44)
- `stories` (Zeile 52-66)
- `votes` (Zeile 79-91)
- `unlock_requests` (Zeile 104-114)

**Keine `story_comments` Tabelle vorhanden.**

---

## Geplante Änderungen

## 1. Datenbank-Erweiterung

### 1.1 Neue Tabelle: story_comments

**Location:** `database.py` nach Zeile 119 (nach unlock_requests)

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS story_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    comment_text TEXT NOT NULL,
    comment_type TEXT CHECK(comment_type IN ('reasoning', 'execution', 'acceptance', 'general')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id),
    FOREIGN KEY (user_name) REFERENCES users(name)
)
```

**Felder:**
- `id`: Eindeutige Kommentar-ID
- `story_id`: Verweis auf die Story
- `user_name`: Wer hat den Kommentar verfasst
- `comment_text`: Der eigentliche Kommentartext
- `comment_type`: Kategorisierung des Kommentars
  - `reasoning`: Warum dieser Wert?
  - `execution`: Was bei Ausführung beachten?
  - `acceptance`: Akzeptanzkriterien
  - `general`: Allgemeine Anmerkungen
- `created_at`: Zeitstempel

**Index:**
```sql
CREATE INDEX IF NOT EXISTS idx_comments_story
ON story_comments(story_id, created_at DESC)
```

### 1.2 Migration hinzufügen

**Location:** `database.py` in `init_db()` nach Zeile 138

```python
# Migration: story_comments Tabelle hinzufügen
cursor.execute('''
    CREATE TABLE IF NOT EXISTS story_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        story_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        comment_text TEXT NOT NULL,
        comment_type TEXT CHECK(comment_type IN ('reasoning', 'execution', 'acceptance', 'general')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (story_id) REFERENCES stories(id),
        FOREIGN KEY (user_name) REFERENCES users(name)
    )
''')

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_comments_story
    ON story_comments(story_id, created_at DESC)
''')
```

---

## 2. Database Functions

### 2.1 Kommentar hinzufügen

**Location:** `database.py` am Ende (nach Zeile 601)

**Neue Funktion:**
```python
def add_story_comment(story_id: int, user_name: str, comment_text: str, comment_type: str = 'general') -> int:
    """Fügt einen Kommentar zu einer Story hinzu"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO story_comments (story_id, user_name, comment_text, comment_type, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (story_id, user_name, comment_text, comment_type, datetime.now())
        )
        conn.commit()
        return cursor.lastrowid
```

### 2.2 Kommentare einer Story abrufen

```python
def get_story_comments(story_id: int) -> List[Dict]:
    """Gibt alle Kommentare für eine Story zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM story_comments
               WHERE story_id = ?
               ORDER BY created_at DESC''',
            (story_id,)
        )
        return [row_to_dict(row) for row in cursor.fetchall()]
```

### 2.3 Anzahl Kommentare pro Story

```python
def get_comment_count(story_id: int) -> int:
    """Gibt die Anzahl der Kommentare für eine Story zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) as count FROM story_comments WHERE story_id = ?',
            (story_id,)
        )
        row = cursor.fetchone()
        return row['count'] if row else 0
```

### 2.4 Story-Historie mit Kommentaren erweitern

**Ändern:** `get_story_history()` in `database.py` (Zeile 326-343)

**Aktuell:**
```python
def get_story_history(limit: int = 3) -> List[Dict]:
    """Gibt die letzten abgeschlossenen Stories zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM stories
               WHERE status = 'completed'
               ORDER BY completed_at DESC
               LIMIT ?''',
            (limit,)
        )
        stories = [row_to_dict(row) for row in cursor.fetchall()]

        # Für jede Story die Votes laden
        for story in stories:
            story['all_votes'] = get_all_story_votes(story['id'])

        return stories
```

**Geplant:**
```python
def get_story_history(limit: int = 3) -> List[Dict]:
    """Gibt die letzten abgeschlossenen Stories zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT * FROM stories
               WHERE status = 'completed'
               ORDER BY completed_at DESC
               LIMIT ?''',
            (limit,)
        )
        stories = [row_to_dict(row) for row in cursor.fetchall()]

        # Für jede Story die Votes und Kommentare laden
        for story in stories:
            story['all_votes'] = get_all_story_votes(story['id'])
            story['comments'] = get_story_comments(story['id'])  # NEU
            story['comment_count'] = len(story['comments'])      # NEU

        return stories
```

---

## 3. Backend Routes

### 3.1 Story-Detail-Ansicht

**Location:** `app.py` nach Zeile 459 (nach `/api/status`)

**Neue Route:**
```python
@app.route('/story/<int:story_id>')
def story_detail(story_id):
    """Detail-Ansicht einer Story mit Kommentaren"""
    user = get_current_user()
    if not user:
        return redirect(url_for('index'))

    story = db.get_story_by_id(story_id)
    if not story:
        return redirect(url_for('index'))

    # Nur completed Stories dürfen kommentiert werden
    if story['status'] != 'completed':
        return redirect(url_for('index'))

    # Alle Votes und Kommentare laden
    all_votes = db.get_all_story_votes(story_id)
    comments = db.get_story_comments(story_id)

    return render_template('story_detail.html',
                         user=user,
                         story=story,
                         votes=all_votes,
                         comments=comments)
```

### 3.2 Kommentar hinzufügen

**Location:** `app.py` nach story_detail Route

```python
@app.route('/story/<int:story_id>/comment', methods=['POST'])
def add_comment(story_id):
    """Fügt einen Kommentar zu einer Story hinzu"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    story = db.get_story_by_id(story_id)
    if not story or story['status'] != 'completed':
        return jsonify({'error': 'Story not found or not completed'}), 404

    comment_text = request.form.get('comment_text', '').strip()
    comment_type = request.form.get('comment_type', 'general')

    if not comment_text:
        return jsonify({'error': 'Comment text required'}), 400

    # Kommentar speichern
    comment_id = db.add_story_comment(story_id, user['name'], comment_text, comment_type)

    # Event-Log
    add_event(f"💬 {user['name']} hat Kommentar zu '{story['title']}' hinzugefügt", "comment")

    # WebSocket: Benachrichtige alle
    socketio.emit('comment_added', {
        'story_id': story_id,
        'user': user['name'],
        'comment_id': comment_id
    })

    return jsonify({'success': True, 'comment_id': comment_id})
```

### 3.3 Kommentare als JSON abrufen (API)

```python
@app.route('/api/story/<int:story_id>/comments')
def api_story_comments(story_id):
    """API-Endpunkt für Kommentare (JSON)"""
    comments = db.get_story_comments(story_id)
    return jsonify(comments)
```

---

## 4. Frontend - Story-Historie erweitern

### 4.1 Kommentar-Button in Story-Karten

**Location:** `templates/index.html` (Story-Historie-Bereich)

**Aktuell (ca. Zeile 190-210):**
```html
{% for story in story_history %}
<div class="history-item">
    <h4>{{ story.title }}</h4>
    <p><strong>Finale Punktzahl:</strong> {{ story.final_points }}</p>
    <!-- Votes anzeigen -->
</div>
{% endfor %}
```

**Geplant:**
```html
{% for story in story_history %}
<div class="history-item">
    <h4>{{ story.title }}</h4>
    <p><strong>Finale Punktzahl:</strong> {{ story.final_points }}</p>
    <p><strong>Kommentare:</strong> {{ story.comment_count }}</p>

    <!-- Votes anzeigen -->

    <!-- Neuer Button -->
    <div class="history-actions">
        <a href="/story/{{ story.id }}" class="btn btn-secondary">
            💬 Kommentare ansehen/hinzufügen
        </a>
    </div>
</div>
{% endfor %}
```

---

## 5. Frontend - Story-Detail-Seite (NEU)

### 5.1 Neues Template erstellen

**Datei:** `templates/story_detail.html` (NEU)

**Struktur:**
```html
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>{{ story.title }} - Planning Poker</title>
    <!-- CSS ähnlich wie index.html -->
</head>
<body>
    <div class="container">
        <!-- Navigation zurück -->
        <a href="/" class="btn-back">← Zurück zur Übersicht</a>

        <!-- Story-Info -->
        <div class="story-header">
            <h1>{{ story.title }}</h1>
            <p>{{ story.description }}</p>
            <div class="story-meta">
                <span>Erstellt von: {{ story.creator_name }}</span>
                <span>Finale Punktzahl: {{ story.final_points }}</span>
                <span>Abgeschlossen: {{ story.completed_at }}</span>
            </div>
        </div>

        <!-- Alle Votes anzeigen -->
        <div class="votes-section">
            <h2>Abstimmungsergebnisse</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Punktzahl</th>
                        <th>Runde</th>
                    </tr>
                </thead>
                <tbody>
                    {% for vote in votes %}
                    <tr>
                        <td>{{ vote.name }}</td>
                        <td>{{ vote.points }}</td>
                        <td>{{ vote.round }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Kommentare -->
        <div class="comments-section">
            <h2>Kommentare ({{ comments|length }})</h2>

            <!-- Kommentar hinzufügen -->
            <div class="add-comment">
                <h3>Kommentar hinzufügen</h3>
                <form method="POST" action="/story/{{ story.id }}/comment" id="commentForm">
                    <div class="form-group">
                        <label>Kategorie:</label>
                        <select name="comment_type" class="form-control">
                            <option value="general">Allgemein</option>
                            <option value="reasoning">Begründung für Punktzahl</option>
                            <option value="execution">Hinweise zur Ausführung</option>
                            <option value="acceptance">Akzeptanzkriterien</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Kommentar:</label>
                        <textarea name="comment_text"
                                  class="form-control"
                                  rows="5"
                                  placeholder="Dein Kommentar..."
                                  required></textarea>
                    </div>

                    <button type="submit" class="btn btn-primary">
                        💬 Kommentar speichern
                    </button>
                </form>
            </div>

            <!-- Existierende Kommentare -->
            <div class="comments-list" id="commentsList">
                {% if comments %}
                    {% for comment in comments %}
                    <div class="comment-item" data-type="{{ comment.comment_type }}">
                        <div class="comment-header">
                            <strong>{{ comment.user_name }}</strong>
                            <span class="comment-type-badge">{{ comment.comment_type }}</span>
                            <span class="comment-time">{{ comment.created_at }}</span>
                        </div>
                        <div class="comment-text">
                            {{ comment.comment_text }}
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <p class="no-comments">Noch keine Kommentare vorhanden.</p>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        // Form-Submission via AJAX für bessere UX
        document.getElementById('commentForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(e.target);
            const response = await fetch(e.target.action, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                // Reload um neue Kommentare zu zeigen
                window.location.reload();
            } else {
                alert('Fehler beim Speichern des Kommentars');
            }
        });
    </script>
</body>
</html>
```

---

## 6. CSS-Styles

### 6.1 Styles für Kommentare

**Location:** `templates/story_detail.html` (im `<style>` Tag)

```css
.story-header {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
}

.story-meta {
    display: flex;
    gap: 20px;
    margin-top: 10px;
    color: #666;
    font-size: 0.9rem;
}

.votes-section, .comments-section {
    margin-top: 30px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.add-comment {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}

.form-group {
    margin-bottom: 15px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
}

.form-control {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
}

.comment-item {
    padding: 15px;
    border-left: 4px solid #007bff;
    background: #f8f9fa;
    margin-bottom: 15px;
    border-radius: 4px;
}

.comment-item[data-type="reasoning"] {
    border-left-color: #28a745;
}

.comment-item[data-type="execution"] {
    border-left-color: #ffc107;
}

.comment-item[data-type="acceptance"] {
    border-left-color: #dc3545;
}

.comment-header {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 10px;
}

.comment-type-badge {
    background: #007bff;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
}

.comment-time {
    color: #666;
    font-size: 0.85rem;
    margin-left: auto;
}

.comment-text {
    white-space: pre-wrap;
    line-height: 1.6;
}

.btn-back {
    display: inline-block;
    padding: 10px 20px;
    background: #6c757d;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    margin-bottom: 20px;
}

.btn-back:hover {
    background: #5a6268;
}
```

---

## 7. Admin-Dashboard erweitern

### 7.1 Kommentare im Admin-Dashboard anzeigen

**Location:** `templates/admin_dashboard.html`

**Ergänzung bei Story-Anzeige:**
```html
{% for story in stories %}
<div class="story-card">
    <h3>{{ story.title }}</h3>
    <p>Punkte: {{ story.final_points }}</p>
    <p>Kommentare: {{ story.comments|length }}</p>

    <!-- Link zur Detail-Ansicht -->
    <a href="/story/{{ story.id }}" target="_blank">Details & Kommentare</a>
</div>
{% endfor %}
```

---

## 8. WebSocket-Events (Optional)

### 8.1 Real-time Kommentar-Updates

**Location:** `templates/story_detail.html` (JavaScript)

```javascript
// WebSocket für Live-Updates
socket.on('comment_added', function(data) {
    if (data.story_id === {{ story.id }}) {
        // Reload Kommentare-Liste
        location.reload(); // Einfache Variante

        // Oder: Kommentar dynamisch einfügen (komplexer)
    }
});
```

---

## Implementierungsschritte (Reihenfolge)

1. ✅ **Database Migration**
   - Tabelle `story_comments` in `database.py` hinzufügen
   - Index erstellen
   - Database-Funktionen implementieren

2. ✅ **Backend Routes**
   - `/story/<id>` Route für Detail-Ansicht
   - `/story/<id>/comment` POST-Route für neue Kommentare
   - API-Route für Kommentare

3. ✅ **Frontend Template**
   - `story_detail.html` erstellen
   - Formular für Kommentare
   - Anzeige existierender Kommentare

4. ✅ **Story-Historie erweitern**
   - Button "Kommentare ansehen" in index.html
   - Kommentarzähler anzeigen

5. ✅ **Styling**
   - CSS für Kommentare
   - Responsive Design

6. ✅ **Admin-Dashboard**
   - Kommentare im Dashboard anzeigen

7. ⚠️ **Optional: WebSocket**
   - Real-time Updates bei neuen Kommentaren

8. ✅ **Testing**
   - Kommentare hinzufügen
   - Verschiedene Typen testen
   - Mehrere Kommentare pro Story

---

## Vorteile dieser Lösung

1. **Strukturiert**: Kommentare nach Typ kategorisiert
2. **Persistent**: Alles in SQLite gespeichert
3. **User-freundlich**: Einfaches Formular, klare Anzeige
4. **KI-ready**: Strukturierte Daten für spätere KI-Verarbeitung
5. **Nachvollziehbar**: Wer, wann, welcher Typ
6. **Skalierbar**: Kann später um Features erweitert werden (Edit, Delete, Likes)

---

## Zukünftige Erweiterungen (nicht in Feature 7)

- Kommentare bearbeiten/löschen
- Kommentare liken/upvoten
- Kommentare durchsuchen/filtern
- Markdown-Support für Kommentare
- Kommentar-Benachrichtigungen
- KI-Integration: Automatische Zusammenfassung aller Kommentare
