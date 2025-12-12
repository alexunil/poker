#!/usr/bin/env python3
"""
Setup-Skript für AI-Modul
Initialisiert Datenbank und bietet Utility-Funktionen
"""

import sys
import os
import argparse

# Füge Parent-Directory zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def init_database(db_path: str = "planning_poker.db"):
    """Initialisiert AI-Datenbank"""
    from database import init_db
    from ai.database_ai import init_ai_db

    print(f"Initialisiere Datenbanken in {db_path}...")

    # Haupt-Datenbank
    init_db(db_path)

    # AI-Erweiterungen
    init_ai_db(db_path)

    print("✅ Datenbanken initialisiert")


def process_all_stories(
    db_path: str = "planning_poker.db",
    provider: str = "mock",
    strategy: str = "story"
):
    """Verarbeitet alle Stories mit Chunking und Embeddings"""
    from database import init_db, get_all_stories
    from ai.database_ai import init_ai_db, create_chunk, get_chunks_by_source
    from ai.preprocessing import get_preprocessor
    from ai.chunking import chunk_story, chunk_text
    from ai.embeddings import create_generator
    import ai.database_ai as db_ai

    print(f"\nVerarbeite alle Stories...")
    print(f"  Provider: {provider}")
    print(f"  Strategy: {strategy}")

    # Setup
    init_db(db_path)
    init_ai_db(db_path)

    preprocessor = get_preprocessor()
    generator = create_generator(provider)

    # Hole Stories
    stories = get_all_stories()
    print(f"\n{len(stories)} Stories gefunden")

    total_chunks = 0
    total_embeddings = 0

    for i, story in enumerate(stories, 1):
        print(f"\n[{i}/{len(stories)}] Story {story['id']}: {story['title'][:50]}")

        # Prüfe ob bereits verarbeitet
        existing = get_chunks_by_source('story', story['id'])
        if existing:
            print(f"  ⏩ Bereits {len(existing)} Chunks vorhanden, überspringe...")
            continue

        try:
            # Preprocessing
            cleaned = preprocessor.preprocess_story(story, include_votes=True)

            # Chunking
            if strategy == 'story':
                chunks = chunk_story(cleaned['combined_text'])
            else:
                chunks = chunk_text(cleaned['combined_text'], strategy_type=strategy)

            # Chunks speichern und Embeddings erstellen
            for chunk in chunks:
                chunk_id = create_chunk(
                    source_type='story',
                    source_id=story['id'],
                    chunk_text=chunk['text'],
                    chunk_index=chunk['index'],
                    chunk_strategy=strategy
                )

                embedding_id = generator.generate_and_store(
                    chunk_id=chunk_id,
                    text=chunk['text'],
                    db_module=db_ai
                )

                if embedding_id:
                    total_embeddings += 1

                total_chunks += 1

            print(f"  ✅ {len(chunks)} Chunks, {len(chunks)} Embeddings")

        except Exception as e:
            print(f"  ❌ Fehler: {e}")
            continue

    print(f"\n{'=' * 60}")
    print(f"Verarbeitung abgeschlossen!")
    print(f"  Total Chunks: {total_chunks}")
    print(f"  Total Embeddings: {total_embeddings}")
    print(f"{'=' * 60}")


def show_statistics(db_path: str = "planning_poker.db"):
    """Zeigt Statistiken über verarbeitete Daten"""
    from database import init_db
    from ai.database_ai import init_ai_db, get_ai_db

    init_db(db_path)
    init_ai_db(db_path)

    print("\n" + "=" * 60)
    print("AI-MODUL STATISTIKEN")
    print("=" * 60)

    with get_ai_db() as conn:
        cursor = conn.cursor()

        # Chunks
        cursor.execute("SELECT COUNT(*) as count FROM ai_chunks")
        chunk_count = cursor.fetchone()['count']

        cursor.execute("SELECT source_type, COUNT(*) as count FROM ai_chunks GROUP BY source_type")
        chunks_by_type = {row['source_type']: row['count'] for row in cursor.fetchall()}

        # Embeddings
        cursor.execute("SELECT COUNT(*) as count FROM ai_embeddings")
        embedding_count = cursor.fetchone()['count']

        cursor.execute("SELECT embedding_model, COUNT(*) as count FROM ai_embeddings GROUP BY embedding_model")
        embeddings_by_model = {row['embedding_model']: row['count'] for row in cursor.fetchall()}

        # Queue
        cursor.execute("SELECT status, COUNT(*) as count FROM ai_processing_queue GROUP BY status")
        queue_by_status = {row['status']: row['count'] for row in cursor.fetchall()}

    print("\nChunks:")
    print(f"  Total: {chunk_count}")
    for source_type, count in chunks_by_type.items():
        print(f"    {source_type}: {count}")

    print("\nEmbeddings:")
    print(f"  Total: {embedding_count}")
    for model, count in embeddings_by_model.items():
        print(f"    {model}: {count}")

    print("\nProcessing Queue:")
    if queue_by_status:
        for status, count in queue_by_status.items():
            print(f"    {status}: {count}")
    else:
        print("    (leer)")

    print("=" * 60)


def test_embedding_provider(provider: str = "mock"):
    """Testet einen Embedding-Provider"""
    from ai.embeddings import create_generator

    print(f"\nTeste Embedding-Provider: {provider}")

    try:
        generator = create_generator(provider)
        print(f"✅ Provider erstellt: {generator.provider.get_model_name()}")

        # Test-Embedding
        print("Generiere Test-Embedding...")
        text = "Test embedding for planning poker story"
        embedding, dimension = generator.provider.generate_embedding(text)

        print(f"✅ Embedding generiert:")
        print(f"   Dimension: {dimension}")
        print(f"   First 5 values: {embedding[:5]}")

        # Similarity-Test
        print("\nTeste Similarity-Berechnung...")
        emb2, _ = generator.provider.generate_embedding("Similar test text")
        similarity = generator.cosine_similarity(embedding, emb2)
        print(f"✅ Similarity: {similarity:.4f}")

        print(f"\n✅ Provider '{provider}' funktioniert!")
        return True

    except Exception as e:
        print(f"\n❌ Provider-Test fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_ai_data(db_path: str = "planning_poker.db", confirm: bool = False):
    """Löscht alle AI-Daten (Chunks, Embeddings, Queue)"""
    from ai.database_ai import init_ai_db, get_ai_db

    if not confirm:
        response = input("\n⚠️  WARNUNG: Alle AI-Daten werden gelöscht! Fortfahren? (yes/no): ")
        if response.lower() != 'yes':
            print("Abgebrochen.")
            return

    init_ai_db(db_path)

    print("\nLösche AI-Daten...")

    with get_ai_db() as conn:
        cursor = conn.cursor()

        # Lösche in richtiger Reihenfolge (wegen Foreign Keys)
        cursor.execute("DELETE FROM ai_embeddings")
        embeddings_deleted = cursor.rowcount
        print(f"  ✓ {embeddings_deleted} Embeddings gelöscht")

        cursor.execute("DELETE FROM ai_chunks")
        chunks_deleted = cursor.rowcount
        print(f"  ✓ {chunks_deleted} Chunks gelöscht")

        cursor.execute("DELETE FROM ai_context")
        context_deleted = cursor.rowcount
        print(f"  ✓ {context_deleted} Context-Einträge gelöscht")

        cursor.execute("DELETE FROM ai_processing_queue")
        queue_deleted = cursor.rowcount
        print(f"  ✓ {queue_deleted} Queue-Einträge gelöscht")

        conn.commit()

    print("\n✅ Cleanup abgeschlossen")


def main():
    parser = argparse.ArgumentParser(description="AI-Modul Setup und Verwaltung")
    parser.add_argument(
        '--db',
        default='planning_poker.db',
        help='Pfad zur Datenbank (default: planning_poker.db)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Kommandos')

    # Init Command
    subparsers.add_parser('init', help='Initialisiere AI-Datenbank')

    # Process Command
    process_parser = subparsers.add_parser('process', help='Verarbeite alle Stories')
    process_parser.add_argument(
        '--provider',
        choices=['mock', 'openai', 'ollama', 'sentence_transformers'],
        default='mock',
        help='Embedding-Provider (default: mock)'
    )
    process_parser.add_argument(
        '--strategy',
        choices=['story', 'fixed', 'sentence', 'paragraph'],
        default='story',
        help='Chunking-Strategy (default: story)'
    )

    # Stats Command
    subparsers.add_parser('stats', help='Zeige Statistiken')

    # Test Command
    test_parser = subparsers.add_parser('test', help='Teste Embedding-Provider')
    test_parser.add_argument(
        '--provider',
        choices=['mock', 'openai', 'ollama', 'sentence_transformers'],
        default='mock',
        help='Zu testender Provider (default: mock)'
    )

    # Cleanup Command
    cleanup_parser = subparsers.add_parser('cleanup', help='Lösche alle AI-Daten')
    cleanup_parser.add_argument(
        '--yes',
        action='store_true',
        help='Bestätigung überspringen'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute Command
    if args.command == 'init':
        init_database(args.db)

    elif args.command == 'process':
        process_all_stories(args.db, args.provider, args.strategy)

    elif args.command == 'stats':
        show_statistics(args.db)

    elif args.command == 'test':
        test_embedding_provider(args.provider)

    elif args.command == 'cleanup':
        cleanup_ai_data(args.db, args.yes)


if __name__ == "__main__":
    main()
