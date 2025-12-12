"""
SQLite Database Layer für Planning Poker
Verwaltet Persistenz von Users, Stories und Votes
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


# Globale Verbindung
_db_path = None


def init_db(db_path: str = "planning_poker.db"):
    """
    Initialisiert die Datenbank und erstellt das Schema
    """
    global _db_path
    _db_path = db_path

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Schema-Version Tabelle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Users Tabelle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            session_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_session
        ON users(session_id)
    """)

    # Stories Tabelle (mit 'pending' statt 'active' für Konsistenz)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            creator_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'voting', 'revealed', 'completed')),
            round INTEGER NOT NULL DEFAULT 1,
            is_unlocked BOOLEAN DEFAULT 0,
            final_points INTEGER,
            source TEXT DEFAULT 'manual' CHECK(source IN ('manual', 'jira_archive')),
            jira_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (creator_name) REFERENCES users(name)
        )
    """)

    # Migration: auto_start Feld hinzufügen (BEFORE indexes!)
    try:
        cursor.execute("SELECT auto_start FROM stories LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE stories ADD COLUMN auto_start BOOLEAN DEFAULT 0")
        print("✅ Migration: auto_start Spalte hinzugefügt")

    # Migration: source Feld zu Stories hinzufügen (BEFORE indexes!)
    try:
        cursor.execute("SELECT source FROM stories LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE stories ADD COLUMN source TEXT DEFAULT 'manual'")
        print("✅ Migration: source Spalte hinzugefügt")

    # Migration: jira_key Feld zu Stories hinzufügen (BEFORE indexes!)
    try:
        cursor.execute("SELECT jira_key FROM stories LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE stories ADD COLUMN jira_key TEXT")
        print("✅ Migration: jira_key Spalte hinzugefügt")

    # Now create indexes (after migrations ensured columns exist)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stories_status
        ON stories(status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stories_created
        ON stories(created_at DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stories_source
        ON stories(source)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stories_jira_key
        ON stories(jira_key)
    """)

    # Votes Tabelle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            points INTEGER NOT NULL,
            round INTEGER NOT NULL DEFAULT 1,
            voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (story_id) REFERENCES stories(id),
            FOREIGN KEY (user_name) REFERENCES users(name),
            UNIQUE(story_id, user_name, round)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_votes_story
        ON votes(story_id, round)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_votes_user
        ON votes(user_name)
    """)

    # Unlock Requests Tabelle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unlock_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (story_id) REFERENCES stories(id),
            FOREIGN KEY (user_name) REFERENCES users(name),
            UNIQUE(story_id, user_name)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_unlock_story
        ON unlock_requests(story_id)
    """)

    # Story Comments Tabelle
    cursor.execute("""
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
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_story
        ON story_comments(story_id, created_at DESC)
    """)

    # Events Tabelle (für Event Log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_timestamp
        ON events(timestamp DESC)
    """)

    # AI Estimations Tabelle (für AI-Begründungen)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_estimations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER NOT NULL,
            vote_id INTEGER,
            reasoning TEXT NOT NULL,
            similar_stories TEXT,
            model_used TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
            FOREIGN KEY (vote_id) REFERENCES votes(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_estimations_story
        ON ai_estimations(story_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_estimations_vote
        ON ai_estimations(vote_id)
    """)

    # Schema-Version setzen
    cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")

    # Migration: is_spectator Feld zu Users hinzufügen
    try:
        cursor.execute("SELECT is_spectator FROM users LIMIT 1")
    except sqlite3.OperationalError:
        # Spalte existiert nicht, füge sie hinzu
        cursor.execute("ALTER TABLE users ADD COLUMN is_spectator BOOLEAN DEFAULT 0")
        print("✅ Migration: is_spectator Spalte hinzugefügt")

    conn.commit()
    conn.close()

    print(f"✅ Database initialized: {db_path}")


@contextmanager
def get_db():
    """Context Manager für Datenbankverbindungen"""
    if not _db_path:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> Dict:
    """Konvertiert eine SQLite Row zu einem Dictionary"""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


# ============================================================================
# USER FUNCTIONS
# ============================================================================


def get_user_by_session(session_id: str) -> Optional[Dict]:
    """Gibt User anhand der Session-ID zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_user_by_name(name: str) -> Optional[Dict]:
    """Gibt User anhand des Namens zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def create_user(name: str, session_id: str) -> int:
    """Erstellt einen neuen User und gibt die ID zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, session_id, last_seen) VALUES (?, ?, ?)",
                (name, session_id, datetime.now()),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # User mit diesem Namen existiert bereits
            # Update session_id und last_seen
            cursor.execute(
                "UPDATE users SET session_id = ?, last_seen = ? WHERE name = ?",
                (session_id, datetime.now(), name),
            )
            conn.commit()
            user = get_user_by_name(name)
            return user["id"] if user else None


def update_user_last_seen(session_id: str) -> bool:
    """Aktualisiert den last_seen Timestamp"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_seen = ? WHERE session_id = ?",
            (datetime.now(), session_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def toggle_spectator_mode(session_id: str) -> bool:
    """Togglet den Spectator-Modus für einen User"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_spectator = NOT is_spectator WHERE session_id = ?",
            (session_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_active_users_count() -> int:
    """Gibt die Anzahl der aktiven (nicht-Spectator) Users zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_spectator = 0")
        row = cursor.fetchone()
        return row["count"] if row else 0


def check_all_active_users_voted(story_id: int, round_num: int) -> bool:
    """Prüft ob alle aktiven (nicht-Spectator) Users für eine Story abgestimmt haben"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Anzahl aktiver Users
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE is_spectator = 0")
        active_count = cursor.fetchone()["count"]

        # Anzahl Votes von aktiven Users
        cursor.execute(
            """SELECT COUNT(*) as count FROM votes v
               JOIN users u ON v.user_name = u.name
               WHERE v.story_id = ? AND v.round = ? AND u.is_spectator = 0""",
            (story_id, round_num),
        )
        vote_count = cursor.fetchone()["count"]

        return active_count > 0 and active_count == vote_count


def get_all_users() -> List[Dict]:
    """Gibt alle Users zurück (für Admin-Dashboard)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [row_to_dict(row) for row in cursor.fetchall()]


# ============================================================================
# STORY FUNCTIONS
# ============================================================================


def get_story_by_id(story_id: int) -> Optional[Dict]:
    """Gibt Story anhand der ID zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_active_story() -> Optional[Dict]:
    """Gibt die aktive Story zurück (voting oder revealed, ohne Archive)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM stories
               WHERE status IN ('voting', 'revealed')
               AND (source IS NULL OR source != 'jira_archive')
               ORDER BY created_at DESC
               LIMIT 1"""
        )
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_pending_stories() -> List[Dict]:
    """Gibt alle Stories mit Status 'pending' zurück (ohne Archive)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM stories
               WHERE status = 'pending' AND (source IS NULL OR source != 'jira_archive')
               ORDER BY created_at ASC"""
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


def get_story_history(limit: int = 3) -> List[Dict]:
    """Gibt die letzten abgeschlossenen Stories zurück (ohne Archive)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM stories
               WHERE status = 'completed' AND (source IS NULL OR source != 'jira_archive')
               ORDER BY completed_at DESC
               LIMIT ?""",
            (limit,),
        )
        stories = [row_to_dict(row) for row in cursor.fetchall()]

        # Für jede Story die Votes und Kommentare laden
        for story in stories:
            story["all_votes"] = get_all_story_votes(story["id"])
            story["comments"] = get_story_comments(story["id"])
            story["comment_count"] = len(story["comments"])

        return stories


def create_story(
    title: str,
    description: str,
    creator_name: str,
    auto_start: bool = False,
    source: str = 'manual',
    jira_key: str = None,
    status: str = 'pending',
    final_points: int = None,
    completed_at: datetime = None
) -> int:
    """Erstellt eine neue Story und gibt die ID zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO stories
               (title, description, creator_name, status, round, auto_start, source, jira_key, final_points, created_at, completed_at)
               VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
            (title, description, creator_name, status, auto_start, source, jira_key, final_points, datetime.now(), completed_at),
        )
        conn.commit()
        return cursor.lastrowid


def get_next_auto_start_story() -> Optional[Dict[str, Any]]:
    """Holt die nächste Story mit auto_start=1 (älteste zuerst)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM stories
               WHERE status = 'pending' AND auto_start = 1
               ORDER BY created_at ASC
               LIMIT 1"""
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_story_status(story_id: int, status: str) -> bool:
    """Aktualisiert den Status einer Story"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE stories SET status = ? WHERE id = ?", (status, story_id))
        conn.commit()
        return cursor.rowcount > 0


def update_story_round(story_id: int, round_num: int) -> bool:
    """Aktualisiert die Runde einer Story"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE stories SET round = ? WHERE id = ?", (round_num, story_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def start_voting(story_id: int) -> bool:
    """Setzt Story-Status auf 'voting'"""
    return update_story_status(story_id, "voting")


def complete_story(story_id: int, final_points: int) -> bool:
    """Schließt eine Story ab mit finalen Punkten"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE stories
               SET status = 'completed', final_points = ?, completed_at = ?
               WHERE id = ?""",
            (final_points, datetime.now(), story_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def withdraw_story(story_id: int) -> bool:
    """
    Stellt eine aktive Story zurück in die Queue (pending).
    Löscht alle Votes der aktuellen Runde und setzt die Story auf pending.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Hole aktuelle Story-Daten
        cursor.execute("SELECT round FROM stories WHERE id = ?", (story_id,))
        row = cursor.fetchone()
        if not row:
            return False

        current_round = row["round"]

        # Lösche Votes der aktuellen Runde
        cursor.execute(
            "DELETE FROM votes WHERE story_id = ? AND round = ?",
            (story_id, current_round)
        )

        # Setze Story zurück auf pending
        cursor.execute(
            "UPDATE stories SET status = 'pending' WHERE id = ?",
            (story_id,)
        )

        conn.commit()
        return cursor.rowcount > 0


def delete_story(story_id: int) -> bool:
    """
    Löscht eine Story permanent aus der Datenbank.
    Sollte nur für pending Stories verwendet werden.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Sicherheitscheck: Nur pending Stories löschen
        cursor.execute(
            "SELECT status FROM stories WHERE id = ?",
            (story_id,)
        )
        row = cursor.fetchone()
        if not row or row["status"] != "pending":
            return False

        # Lösche zuerst alle Votes (falls vorhanden)
        cursor.execute("DELETE FROM votes WHERE story_id = ?", (story_id,))

        # Lösche die Story
        cursor.execute("DELETE FROM stories WHERE id = ?", (story_id,))

        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# VOTE FUNCTIONS
# ============================================================================


def get_story_votes(story_id: int, round_num: int) -> Dict[str, Dict]:
    """Gibt alle Votes für eine Story in einer bestimmten Runde zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT user_name, points, voted_at
               FROM votes
               WHERE story_id = ? AND round = ?
               ORDER BY voted_at""",
            (story_id, round_num),
        )
        result = {}
        for row in cursor.fetchall():
            result[row["user_name"]] = {
                "points": row["points"],
                "round": round_num,
                "voted_at": row["voted_at"],
            }
        return result


def get_all_story_votes(story_id: int) -> List[Dict]:
    """Gibt alle Votes für eine Story (alle Runden) als Liste zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT user_name as name, points, round, voted_at
               FROM votes
               WHERE story_id = ?
               ORDER BY round, voted_at""",
            (story_id,),
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


def cast_vote(story_id: int, user_name: str, points: int, round_num: int) -> bool:
    """Gibt eine Stimme ab (oder aktualisiert sie)"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO votes (story_id, user_name, points, round, voted_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(story_id, user_name, round)
                   DO UPDATE SET points = ?, voted_at = ?""",
                (
                    story_id,
                    user_name,
                    points,
                    round_num,
                    datetime.now(),
                    points,
                    datetime.now(),
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error casting vote: {e}")
            return False


def clear_votes_for_round(story_id: int, round_num: int) -> bool:
    """Löscht alle Votes für eine bestimmte Runde (bei neuem Round)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM votes WHERE story_id = ? AND round = ?", (story_id, round_num)
        )
        conn.commit()
        return True


def get_user_vote_history(user_name: str) -> List[Dict]:
    """Gibt alle Votes eines Users zurück (für Admin-Dashboard)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT v.*, s.title as story_title
               FROM votes v
               JOIN stories s ON v.story_id = s.id
               WHERE v.user_name = ?
               ORDER BY v.voted_at DESC""",
            (user_name,),
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


# ============================================================================
# UNLOCK FUNCTIONS (für zukünftiges Feature)
# ============================================================================


def add_unlock_request(story_id: int, user_name: str) -> bool:
    """Fügt eine Unlock-Anfrage hinzu"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO unlock_requests (story_id, user_name, requested_at)
                   VALUES (?, ?, ?)""",
                (story_id, user_name, datetime.now()),
            )
            conn.commit()

            # Prüfen ob >= 2 Anfragen
            count = get_unlock_count(story_id)
            if count >= 2:
                unlock_story(story_id)

            return True
        except sqlite3.IntegrityError:
            # User hat bereits Unlock angefordert
            return False


def get_unlock_count(story_id: int) -> int:
    """Gibt die Anzahl der Unlock-Anfragen zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM unlock_requests WHERE story_id = ?",
            (story_id,),
        )
        row = cursor.fetchone()
        return row["count"] if row else 0


def unlock_story(story_id: int) -> bool:
    """Entsperrt eine Story (is_unlocked = 1)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE stories SET is_unlocked = 1 WHERE id = ?", (story_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_unlock_requests(story_id: int) -> bool:
    """Löscht alle Unlock-Anfragen für eine Story"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM unlock_requests WHERE story_id = ?", (story_id,))
        conn.commit()
        return True


# ============================================================================
# EVENT LOG FUNCTIONS
# ============================================================================


def create_event(message: str, event_type: str = "info") -> int:
    """Erstellt ein Event im Event-Log"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (message, event_type, timestamp) VALUES (?, ?, ?)",
            (message, event_type, datetime.now()),
        )
        conn.commit()
        return cursor.lastrowid


def get_recent_events(limit: int = 10) -> List[Dict]:
    """Gibt die letzten N Events zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


def clear_old_events(keep_last: int = 100) -> bool:
    """Löscht alte Events, behält nur die letzten N"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """DELETE FROM events
               WHERE id NOT IN (
                   SELECT id FROM events
                   ORDER BY timestamp DESC
                   LIMIT ?
               )""",
            (keep_last,),
        )
        conn.commit()
        return True


# ============================================================================
# ADMIN DASHBOARD FUNCTIONS
# ============================================================================


def get_all_stories() -> List[Dict]:
    """Gibt alle Stories mit Votes und Kommentaren zurück (für Admin-Dashboard)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM stories
               ORDER BY created_at DESC"""
        )
        stories = [row_to_dict(row) for row in cursor.fetchall()]

        # Für jede Story die Votes und Kommentare laden
        for story in stories:
            story["all_votes"] = get_all_story_votes(story["id"])
            story["comments"] = get_story_comments(story["id"])
            story["comment_count"] = len(story["comments"])

        return stories


def get_all_users_with_activity() -> List[Dict]:
    """Gibt alle Users mit Vote-Aktivität zurück (für Admin-Dashboard)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT
                u.name,
                u.created_at as first_seen,
                u.last_seen,
                COUNT(v.id) as vote_count,
                MAX(v.voted_at) as last_vote
               FROM users u
               LEFT JOIN votes v ON u.name = v.user_name
               GROUP BY u.name
               ORDER BY last_vote DESC NULLS LAST"""
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


def get_stories_without_embeddings() -> Dict[str, Any]:
    """
    Gibt Statistiken über Stories ohne Embeddings zurück

    Returns:
        Dict mit: total_completed, stories_with_embeddings, stories_without_embeddings, story_ids_without_embeddings
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Alle completed Stories zählen
        cursor.execute(
            """SELECT COUNT(*) as count FROM stories
               WHERE status = 'completed' AND final_points IS NOT NULL"""
        )
        total_completed = cursor.fetchone()["count"]

        # Stories mit Embeddings (die Chunks haben)
        cursor.execute(
            """SELECT COUNT(DISTINCT s.id) as count
               FROM stories s
               INNER JOIN ai_chunks c ON c.source_type = 'story' AND c.source_id = s.id
               WHERE s.status = 'completed' AND s.final_points IS NOT NULL"""
        )
        stories_with_embeddings = cursor.fetchone()["count"]

        # IDs der Stories ohne Embeddings
        cursor.execute(
            """SELECT s.id, s.title, s.final_points, s.created_at
               FROM stories s
               WHERE s.status = 'completed'
                 AND s.final_points IS NOT NULL
                 AND NOT EXISTS (
                     SELECT 1 FROM ai_chunks c
                     WHERE c.source_type = 'story' AND c.source_id = s.id
                 )
               ORDER BY s.created_at DESC"""
        )
        stories_without = [row_to_dict(row) for row in cursor.fetchall()]

        return {
            "total_completed": total_completed,
            "stories_with_embeddings": stories_with_embeddings,
            "stories_without_embeddings": len(stories_without),
            "missing_stories": stories_without
        }


# ============================================================================
# COMMENT FUNCTIONS
# ============================================================================


def add_story_comment(
    story_id: int, user_name: str, comment_text: str, comment_type: str = "general"
) -> int:
    """Fügt einen Kommentar zu einer Story hinzu"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO story_comments (story_id, user_name, comment_text, comment_type, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (story_id, user_name, comment_text, comment_type, datetime.now()),
        )
        conn.commit()
        return cursor.lastrowid


def get_story_comments(story_id: int) -> List[Dict]:
    """Gibt alle Kommentare für eine Story zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM story_comments
               WHERE story_id = ?
               ORDER BY created_at DESC""",
            (story_id,),
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


def get_comment_count(story_id: int) -> int:
    """Gibt die Anzahl der Kommentare für eine Story zurück"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count FROM story_comments WHERE story_id = ?",
            (story_id,),
        )
        row = cursor.fetchone()
        return row["count"] if row else 0


# ============================================================================
# AI ESTIMATION FUNCTIONS
# ============================================================================


def save_ai_estimation(
    story_id: int,
    vote_id: Optional[int],
    reasoning: str,
    similar_stories: Optional[str],
    model_used: str
) -> int:
    """
    Speichert eine AI-Schätzungs-Begründung

    Args:
        story_id: Story ID
        vote_id: Vote ID (optional)
        reasoning: AI-Begründung
        similar_stories: JSON mit ähnlichen Stories (optional)
        model_used: Name des verwendeten AI-Modells

    Returns:
        ID der gespeicherten Estimation
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ai_estimations
               (story_id, vote_id, reasoning, similar_stories, model_used)
               VALUES (?, ?, ?, ?, ?)""",
            (story_id, vote_id, reasoning, similar_stories, model_used)
        )
        conn.commit()
        return cursor.lastrowid


def get_ai_estimation_by_story(story_id: int, round_num: Optional[int] = None) -> Optional[Dict]:
    """
    Gibt die AI-Begründung für eine Story zurück

    Args:
        story_id: Story ID
        round_num: Optional - spezifische Runde

    Returns:
        Dict mit Estimation oder None
    """
    with get_db() as conn:
        cursor = conn.cursor()

        if round_num is not None:
            # Hole Estimation für spezifische Runde
            cursor.execute(
                """SELECT ae.*
                   FROM ai_estimations ae
                   JOIN votes v ON ae.vote_id = v.id
                   WHERE ae.story_id = ? AND v.round = ?
                   ORDER BY ae.created_at DESC
                   LIMIT 1""",
                (story_id, round_num)
            )
        else:
            # Hole neueste Estimation
            cursor.execute(
                """SELECT * FROM ai_estimations
                   WHERE story_id = ?
                   ORDER BY created_at DESC
                   LIMIT 1""",
                (story_id,)
            )

        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_ai_estimation_by_vote(vote_id: int) -> Optional[Dict]:
    """
    Gibt die AI-Begründung für einen Vote zurück

    Args:
        vote_id: Vote ID

    Returns:
        Dict mit Estimation oder None
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM ai_estimations
               WHERE vote_id = ?
               LIMIT 1""",
            (vote_id,)
        )
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def delete_ai_estimations_by_story(story_id: int) -> bool:
    """Löscht alle AI-Estimations für eine Story"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM ai_estimations WHERE story_id = ?",
            (story_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
