"""
Datenbank-Erweiterungen für KI-Funktionalität
Verwaltet Embeddings, Chunks und AI-Kontext
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager


# Globale Verbindung (wird von database.py geerbt)
_db_path = None


def init_ai_db(db_path: str = "planning_poker.db"):
    """
    Initialisiert die KI-Datenbank-Erweiterungen
    Erstellt Tabellen für Chunks, Embeddings und AI-Kontext
    """
    global _db_path
    _db_path = db_path

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Chunks Tabelle - Speichert verarbeitete Text-Chunks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('story', 'vote', 'comment', 'event')),
            source_id INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_strategy TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_source
        ON ai_chunks(source_type, source_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_created
        ON ai_chunks(created_at DESC)
    """)

    # Embeddings Tabelle - Speichert Vektor-Embeddings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding_vector BLOB NOT NULL,
            embedding_dimension INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chunk_id) REFERENCES ai_chunks(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_chunk
        ON ai_embeddings(chunk_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_model
        ON ai_embeddings(embedding_model)
    """)

    # AI Context Tabelle - Speichert AI-generierte Kontextdaten
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_type TEXT NOT NULL,
            context_key TEXT NOT NULL,
            context_data TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            UNIQUE(context_type, context_key)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_context_type
        ON ai_context(context_type, created_at DESC)
    """)

    # Processing Queue - Für asynchrone Verarbeitung
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_processing_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            processing_type TEXT NOT NULL CHECK(processing_type IN ('chunk', 'embed', 'analyze')),
            status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
            priority INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_queue_status
        ON ai_processing_queue(status, priority DESC, created_at)
    """)

    conn.commit()
    conn.close()

    print(f"✅ AI Database extensions initialized: {db_path}")


@contextmanager
def get_ai_db():
    """Context Manager für AI-Datenbankverbindungen"""
    if not _db_path:
        raise RuntimeError("AI Database not initialized. Call init_ai_db() first.")

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
# CHUNK FUNCTIONS
# ============================================================================


def create_chunk(
    source_type: str,
    source_id: int,
    chunk_text: str,
    chunk_index: int,
    chunk_strategy: str,
    metadata: Optional[str] = None,
) -> int:
    """Erstellt einen neuen Text-Chunk"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ai_chunks
               (source_type, source_id, chunk_text, chunk_index, chunk_strategy, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (source_type, source_id, chunk_text, chunk_index, chunk_strategy, metadata),
        )
        conn.commit()
        return cursor.lastrowid


def get_chunks_by_source(source_type: str, source_id: int) -> List[Dict]:
    """Gibt alle Chunks für eine bestimmte Quelle zurück"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM ai_chunks
               WHERE source_type = ? AND source_id = ?
               ORDER BY chunk_index""",
            (source_type, source_id),
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


def get_chunk_by_id(chunk_id: int) -> Optional[Dict]:
    """Gibt einen Chunk anhand der ID zurück"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ai_chunks WHERE id = ?", (chunk_id,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def delete_chunks_by_source(source_type: str, source_id: int) -> bool:
    """Löscht alle Chunks für eine bestimmte Quelle"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM ai_chunks WHERE source_type = ? AND source_id = ?",
            (source_type, source_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def update_chunk_timestamp(chunk_id: int) -> bool:
    """Aktualisiert den updated_at Timestamp eines Chunks"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ai_chunks SET updated_at = ? WHERE id = ?",
            (datetime.now(), chunk_id),
        )
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# EMBEDDING FUNCTIONS
# ============================================================================


def create_embedding(
    chunk_id: int,
    embedding_model: str,
    embedding_vector: bytes,
    embedding_dimension: int,
) -> int:
    """Erstellt ein neues Embedding für einen Chunk"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ai_embeddings
               (chunk_id, embedding_model, embedding_vector, embedding_dimension)
               VALUES (?, ?, ?, ?)""",
            (chunk_id, embedding_model, embedding_vector, embedding_dimension),
        )
        conn.commit()
        return cursor.lastrowid


def get_embedding_by_chunk(chunk_id: int, model: Optional[str] = None) -> Optional[Dict]:
    """Gibt das Embedding für einen Chunk zurück"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        if model:
            cursor.execute(
                """SELECT * FROM ai_embeddings
                   WHERE chunk_id = ? AND embedding_model = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (chunk_id, model),
            )
        else:
            cursor.execute(
                """SELECT * FROM ai_embeddings
                   WHERE chunk_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (chunk_id,),
            )
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_all_embeddings(model: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """Gibt alle Embeddings zurück (optional gefiltert nach Modell)"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        if model:
            cursor.execute(
                """SELECT e.*, c.chunk_text, c.source_type, c.source_id
                   FROM ai_embeddings e
                   JOIN ai_chunks c ON e.chunk_id = c.id
                   WHERE e.embedding_model = ?
                   ORDER BY e.created_at DESC
                   LIMIT ?""",
                (model, limit),
            )
        else:
            cursor.execute(
                """SELECT e.*, c.chunk_text, c.source_type, c.source_id
                   FROM ai_embeddings e
                   JOIN ai_chunks c ON e.chunk_id = c.id
                   ORDER BY e.created_at DESC
                   LIMIT ?""",
                (limit,),
            )
        return [row_to_dict(row) for row in cursor.fetchall()]


def delete_embeddings_by_model(model: str) -> bool:
    """Löscht alle Embeddings für ein bestimmtes Modell"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM ai_embeddings WHERE embedding_model = ?", (model,)
        )
        conn.commit()
        return cursor.rowcount > 0


# ============================================================================
# CONTEXT FUNCTIONS
# ============================================================================


def set_ai_context(
    context_type: str,
    context_key: str,
    context_data: str,
    metadata: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> bool:
    """Setzt oder aktualisiert AI-Kontext"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ai_context (context_type, context_key, context_data, metadata, expires_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(context_type, context_key)
               DO UPDATE SET context_data = ?, metadata = ?, created_at = ?, expires_at = ?""",
            (
                context_type,
                context_key,
                context_data,
                metadata,
                expires_at,
                context_data,
                metadata,
                datetime.now(),
                expires_at,
            ),
        )
        conn.commit()
        return True


def get_ai_context(context_type: str, context_key: str) -> Optional[Dict]:
    """Gibt AI-Kontext zurück"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM ai_context
               WHERE context_type = ? AND context_key = ?
               AND (expires_at IS NULL OR expires_at > ?)""",
            (context_type, context_key, datetime.now()),
        )
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def get_all_context_by_type(context_type: str) -> List[Dict]:
    """Gibt alle Kontexte eines Typs zurück"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM ai_context
               WHERE context_type = ?
               AND (expires_at IS NULL OR expires_at > ?)
               ORDER BY created_at DESC""",
            (context_type, datetime.now()),
        )
        return [row_to_dict(row) for row in cursor.fetchall()]


def delete_expired_context() -> int:
    """Löscht abgelaufene Kontexte"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM ai_context WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (datetime.now(),),
        )
        conn.commit()
        return cursor.rowcount


# ============================================================================
# PROCESSING QUEUE FUNCTIONS
# ============================================================================


def enqueue_processing(
    source_type: str,
    source_id: int,
    processing_type: str,
    priority: int = 0,
) -> int:
    """Fügt ein Item zur Verarbeitungs-Queue hinzu"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ai_processing_queue
               (source_type, source_id, processing_type, status, priority)
               VALUES (?, ?, ?, 'pending', ?)""",
            (source_type, source_id, processing_type, priority),
        )
        conn.commit()
        return cursor.lastrowid


def get_next_queue_item(processing_type: Optional[str] = None) -> Optional[Dict]:
    """Gibt das nächste Item aus der Queue zurück"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        if processing_type:
            cursor.execute(
                """SELECT * FROM ai_processing_queue
                   WHERE status = 'pending' AND processing_type = ?
                   ORDER BY priority DESC, created_at ASC
                   LIMIT 1""",
                (processing_type,),
            )
        else:
            cursor.execute(
                """SELECT * FROM ai_processing_queue
                   WHERE status = 'pending'
                   ORDER BY priority DESC, created_at ASC
                   LIMIT 1"""
            )
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def update_queue_status(
    queue_id: int,
    status: str,
    error_message: Optional[str] = None,
) -> bool:
    """Aktualisiert den Status eines Queue-Items"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        now = datetime.now()

        if status == "processing":
            cursor.execute(
                "UPDATE ai_processing_queue SET status = ?, started_at = ? WHERE id = ?",
                (status, now, queue_id),
            )
        elif status in ("completed", "failed"):
            cursor.execute(
                """UPDATE ai_processing_queue
                   SET status = ?, completed_at = ?, error_message = ?
                   WHERE id = ?""",
                (status, now, error_message, queue_id),
            )
        else:
            cursor.execute(
                "UPDATE ai_processing_queue SET status = ? WHERE id = ?",
                (status, queue_id),
            )

        conn.commit()
        return cursor.rowcount > 0


def get_queue_stats() -> Dict[str, int]:
    """Gibt Statistiken über die Processing Queue zurück"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT status, COUNT(*) as count
               FROM ai_processing_queue
               GROUP BY status"""
        )
        stats = {row["status"]: row["count"] for row in cursor.fetchall()}
        return stats


def clear_completed_queue_items(older_than_hours: int = 24) -> int:
    """Löscht abgeschlossene Queue-Items älter als X Stunden"""
    with get_ai_db() as conn:
        cursor = conn.cursor()
        cutoff = datetime.now().timestamp() - (older_than_hours * 3600)
        cursor.execute(
            """DELETE FROM ai_processing_queue
               WHERE status IN ('completed', 'failed')
               AND completed_at < datetime(?, 'unixepoch')""",
            (cutoff,),
        )
        conn.commit()
        return cursor.rowcount
