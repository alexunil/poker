"""
Beispiel-Code für die Verwendung des AI-Moduls
Zeigt typische Workflows und Use Cases
"""

import sys
import os

# Füge Parent-Directory zum Path hinzu
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def example_1_basic_preprocessing():
    """Beispiel 1: Basis Preprocessing einer Story"""
    print("=" * 60)
    print("Beispiel 1: Story Preprocessing")
    print("=" * 60)

    from database import init_db, get_all_stories
    from ai.preprocessing import get_preprocessor

    # Setup
    init_db("planning_poker.db")
    preprocessor = get_preprocessor()

    # Hole erste Story
    stories = get_all_stories()
    if not stories:
        print("Keine Stories gefunden!")
        return

    story = stories[0]
    print(f"\nOriginal Story:")
    print(f"  Title: {story['title']}")
    print(f"  Description: {story.get('description', 'N/A')[:100]}...")

    # Preprocessing
    cleaned = preprocessor.preprocess_story(story, include_votes=True)

    print(f"\nCleaned Story:")
    print(f"  Word Count: {cleaned['word_count']}")
    print(f"  Text Length: {cleaned['text_length']}")
    print(f"\nCombined Text:\n{cleaned['combined_text'][:200]}...")


def example_2_chunking_strategies():
    """Beispiel 2: Verschiedene Chunking-Strategien"""
    print("\n" + "=" * 60)
    print("Beispiel 2: Chunking Strategien")
    print("=" * 60)

    from ai.chunking import (
        chunk_text,
        ChunkingFactory,
        FixedSizeChunking,
        SentenceChunking,
        StoryChunking
    )

    sample_text = """
    Title: User Authentication System
    Description: Implement a comprehensive user authentication system with the following features:
    - User registration with email verification
    - Secure password hashing using bcrypt
    - JWT-based session management
    - Password reset functionality
    - Two-factor authentication support

    The system should integrate with our existing user database and provide REST API endpoints.
    Voting: Round 1: Alice:5, Bob:8, Charlie:5
    Comments: 2 reasoning comment(s)
    """

    # Strategy 1: Fixed Size
    print("\n1. Fixed Size Chunking (300 chars, 50 overlap):")
    strategy = FixedSizeChunking(chunk_size=300, overlap=50)
    chunks = strategy.chunk(sample_text)
    for chunk in chunks:
        print(f"  Chunk {chunk['index']}: {len(chunk['text'])} chars")

    # Strategy 2: Sentence
    print("\n2. Sentence-based Chunking (3 sentences):")
    strategy = SentenceChunking(max_sentences=3)
    chunks = strategy.chunk(sample_text)
    for chunk in chunks:
        print(f"  Chunk {chunk['index']}: {chunk['sentence_count']} sentences")

    # Strategy 3: Story-aware
    print("\n3. Story-aware Chunking:")
    strategy = StoryChunking()
    chunks = strategy.chunk(sample_text)
    for chunk in chunks:
        print(f"  Chunk {chunk['index']} ({chunk['section']}): {chunk['text'][:50]}...")


def example_3_embedding_generation():
    """Beispiel 3: Embedding-Generierung mit verschiedenen Providern"""
    print("\n" + "=" * 60)
    print("Beispiel 3: Embedding-Generierung")
    print("=" * 60)

    from ai.embeddings import create_generator, EmbeddingProviderFactory

    sample_texts = [
        "User authentication with JWT tokens",
        "Database migration and schema updates",
        "Frontend React component refactoring"
    ]

    # Mock Provider (für Demo)
    print("\nMock Provider:")
    generator = create_generator('mock', dimension=128)
    print(f"  Model: {generator.provider.get_model_name()}")

    for text in sample_texts:
        embedding, dimension = generator.provider.generate_embedding(text)
        print(f"  '{text[:30]}...': {dimension} dimensions")

    # Similarity Berechnung
    print("\nSimilarity Berechnung:")
    emb1, _ = generator.provider.generate_embedding(sample_texts[0])
    emb2, _ = generator.provider.generate_embedding(sample_texts[1])
    emb3, _ = generator.provider.generate_embedding(sample_texts[2])

    sim_1_2 = generator.cosine_similarity(emb1, emb2)
    sim_1_3 = generator.cosine_similarity(emb1, emb3)

    print(f"  Text 1 <-> Text 2: {sim_1_2:.3f}")
    print(f"  Text 1 <-> Text 3: {sim_1_3:.3f}")


def example_4_complete_pipeline():
    """Beispiel 4: Komplette Pipeline von Story zu Embedding"""
    print("\n" + "=" * 60)
    print("Beispiel 4: Komplette Pipeline")
    print("=" * 60)

    from database import init_db, get_all_stories
    from ai.database_ai import init_ai_db, create_chunk, get_chunks_by_source
    from ai.preprocessing import get_preprocessor
    from ai.chunking import chunk_story
    from ai.embeddings import create_generator
    import ai.database_ai as db_ai

    # Setup
    init_db("planning_poker.db")
    init_ai_db("planning_poker.db")

    preprocessor = get_preprocessor()
    generator = create_generator('mock', dimension=384)

    # Hole erste Story
    stories = get_all_stories()
    if not stories:
        print("Keine Stories gefunden!")
        return

    story = stories[0]
    print(f"\nVerarbeite Story: {story['title']}")

    # 1. Preprocessing
    print("  1. Preprocessing...")
    cleaned = preprocessor.preprocess_story(story, include_votes=True)
    print(f"     ✓ {cleaned['word_count']} Wörter")

    # 2. Chunking
    print("  2. Chunking...")
    chunks = chunk_story(cleaned['combined_text'])
    print(f"     ✓ {len(chunks)} Chunks erstellt")

    # 3. Chunks speichern und Embeddings erstellen
    print("  3. Embeddings generieren...")
    for chunk in chunks[:3]:  # Nur erste 3 für Demo
        chunk_id = create_chunk(
            source_type='story',
            source_id=story['id'],
            chunk_text=chunk['text'],
            chunk_index=chunk['index'],
            chunk_strategy='story_aware'
        )

        embedding_id = generator.generate_and_store(
            chunk_id=chunk_id,
            text=chunk['text'],
            db_module=db_ai
        )

        print(f"     ✓ Chunk {chunk['index']}: Embedding {embedding_id}")

    # 4. Chunks abrufen
    print("  4. Gespeicherte Chunks abrufen...")
    stored_chunks = get_chunks_by_source('story', story['id'])
    print(f"     ✓ {len(stored_chunks)} Chunks in DB")


def example_5_similarity_search():
    """Beispiel 5: Semantic Similarity Search"""
    print("\n" + "=" * 60)
    print("Beispiel 5: Similarity Search")
    print("=" * 60)

    from ai.embeddings import create_generator

    generator = create_generator('mock', dimension=384)

    # Sample Stories
    stories = [
        "Implement user authentication with OAuth2",
        "Add password reset functionality",
        "Create admin dashboard for user management",
        "Setup CI/CD pipeline with GitHub Actions",
        "Optimize database query performance"
    ]

    # Query
    query = "user login and authentication"
    print(f"\nQuery: '{query}'")

    # Generiere Embeddings
    query_embedding, _ = generator.provider.generate_embedding(query)
    story_embeddings = []

    for i, story in enumerate(stories):
        embedding, _ = generator.provider.generate_embedding(story)
        story_embeddings.append((i, embedding))

    # Finde ähnlichste Stories
    similar = generator.find_similar_chunks(
        query_embedding=query_embedding,
        candidate_embeddings=story_embeddings,
        top_k=3,
        min_similarity=0.0
    )

    print("\nTop 3 ähnlichste Stories:")
    for story_id, similarity in similar:
        print(f"  {similarity:.3f} - {stories[story_id]}")


def example_6_batch_processing():
    """Beispiel 6: Batch-Verarbeitung mehrerer Stories"""
    print("\n" + "=" * 60)
    print("Beispiel 6: Batch-Verarbeitung")
    print("=" * 60)

    from database import init_db, get_all_stories
    from ai.preprocessing import get_preprocessor

    # Setup
    init_db("planning_poker.db")
    preprocessor = get_preprocessor()

    # Hole alle Stories
    stories = get_all_stories()
    print(f"\nVerarbeite {len(stories)} Stories...")

    # Batch-Preprocessing
    cleaned_stories = preprocessor.batch_preprocess_stories(
        stories,
        include_votes=True
    )

    # Statistiken
    total_words = sum(s['word_count'] for s in cleaned_stories)
    avg_words = total_words / len(cleaned_stories) if cleaned_stories else 0

    print(f"\nStatistiken:")
    print(f"  Total Stories: {len(cleaned_stories)}")
    print(f"  Total Words: {total_words}")
    print(f"  Avg Words/Story: {avg_words:.1f}")

    # Kategorisiere nach Komplexität
    by_complexity = {}
    for story in cleaned_stories:
        metadata = preprocessor.extract_metadata(story)
        complexity = metadata.get('complexity_indicator', 'unknown')
        by_complexity[complexity] = by_complexity.get(complexity, 0) + 1

    print(f"\nKomplexitäts-Verteilung:")
    for complexity, count in sorted(by_complexity.items()):
        print(f"  {complexity}: {count}")


def example_7_mcp_tools():
    """Beispiel 7: MCP Tools Usage (ohne Server)"""
    print("\n" + "=" * 60)
    print("Beispiel 7: MCP Tools")
    print("=" * 60)

    from database import init_db, get_all_stories
    from ai.mcp.tools import (
        calculate_team_velocity,
        analyze_estimation_accuracy,
        identify_controversial_stories
    )

    # Setup
    init_db("planning_poker.db")
    stories = get_all_stories()

    if not stories:
        print("Keine Stories gefunden!")
        return

    # Tool 1: Team Velocity
    print("\n1. Team Velocity (letzte 14 Tage):")
    velocity = calculate_team_velocity(stories, time_period_days=14)
    print(f"   Completed Stories: {velocity['completed_stories']}")
    print(f"   Total Points: {velocity['total_points']}")
    print(f"   Velocity/Day: {velocity['velocity_per_day']}")

    # Tool 2: Estimation Accuracy
    print("\n2. Estimation Accuracy:")
    accuracy = analyze_estimation_accuracy(stories)
    print(f"   Analyzed Stories: {accuracy['analyzed_stories']}")
    print(f"   Avg Difference: {accuracy['avg_difference']}")

    # Tool 3: Controversial Stories
    print("\n3. Controversial Stories (hohe Varianz):")
    controversial = identify_controversial_stories(stories, threshold=2.0)
    if controversial:
        for story in controversial[:3]:  # Top 3
            print(f"   Story {story['story_id']}: σ={story['std_dev']}")
    else:
        print("   Keine kontroversen Stories gefunden")


def main():
    """Führe alle Beispiele aus"""
    print("\n" + "=" * 60)
    print("AI MODULE EXAMPLES")
    print("=" * 60)

    examples = [
        example_1_basic_preprocessing,
        example_2_chunking_strategies,
        example_3_embedding_generation,
        example_4_complete_pipeline,
        example_5_similarity_search,
        example_6_batch_processing,
        example_7_mcp_tools,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n❌ Fehler in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Alle Beispiele abgeschlossen!")
    print("=" * 60)


if __name__ == "__main__":
    main()
