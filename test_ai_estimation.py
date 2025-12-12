#!/usr/bin/env python3
"""
Test AI-gestützte Story-Schätzung mit Claude
"""

import os
import sys
import numpy as np
from anthropic import Anthropic

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_all_stories
from ai.embeddings import create_generator
from ai.database_ai import init_ai_db, get_chunks_by_source, get_embedding_by_chunk


def find_similar_stories_with_points(query_text: str, limit: int = 5):
    """
    Findet ähnliche Archive-Stories mit Story Points
    """
    # Initialisierung
    init_db()
    init_ai_db()

    # Embedding Generator
    generator = create_generator('sentence_transformers')

    # Query Embedding generieren
    query_embedding, _ = generator.provider.generate_embedding(query_text)

    # Alle Archive-Stories mit Story Points holen
    all_stories = get_all_stories()
    archive_stories = [
        s for s in all_stories
        if s.get('source') == 'jira_archive' and s.get('final_points')
    ]

    print(f"📚 {len(archive_stories)} Archive-Stories mit Story Points verfügbar")

    # Similarity berechnen
    similarities = []

    for story in archive_stories:
        # Chunks für diese Story holen
        chunks = get_chunks_by_source('story', story['id'])

        if not chunks:
            continue

        # Embedding für ersten Chunk holen (Title)
        chunk_id = chunks[0]['id']
        embedding_data = get_embedding_by_chunk(chunk_id)

        if not embedding_data:
            continue

        # Embedding deserialisieren
        story_emb_vector = generator.provider.decode_embedding(embedding_data['embedding_vector'])

        # Cosine Similarity berechnen
        story_emb = np.array(story_emb_vector)
        query_emb = np.array(query_embedding)

        similarity = np.dot(query_emb, story_emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(story_emb)
        )

        similarities.append({
            'story': story,
            'similarity': similarity
        })

    # Sortieren nach Similarity
    similarities.sort(key=lambda x: x['similarity'], reverse=True)

    return similarities[:limit]


def estimate_with_claude(story_title: str, story_description: str, similar_stories: list, api_key: str):
    """
    Nutzt Claude um Story Points zu schätzen
    """
    client = Anthropic(api_key=api_key)

    # Kontext aus ähnlichen Stories erstellen
    context = "Hier sind ähnliche Stories mit ihren Story Points:\n\n"

    for i, sim in enumerate(similar_stories, 1):
        story = sim['story']
        similarity = sim['similarity']
        points = story.get('final_points', '?')
        title = story.get('title', 'Untitled')

        context += f"{i}. [{points} SP] (Ähnlichkeit: {similarity:.2f}) - {title}\n"

    # Prompt erstellen
    prompt = f"""Du bist ein erfahrener Scrum Master und schätzt User Stories in Story Points (Fibonacci: 1, 2, 3, 5, 8, 13, 21).

{context}

Basierend auf diesen ähnlichen Stories, schätze bitte die folgende neue Story:

**Titel:** {story_title}
**Beschreibung:** {story_description}

Gib deine Schätzung im folgenden Format zurück:

STORY POINTS: [Zahl]

BEGRÜNDUNG:
[Deine Begründung basierend auf den ähnlichen Stories]

VERGLEICH:
[Vergleiche die neue Story mit den ähnlichsten Archive-Stories]
"""

    # Claude fragen
    message = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def main():
    print("="*60)
    print("AI-GESTÜTZTE STORY-SCHÄTZUNG MIT CLAUDE")
    print("="*60)

    # API Key prüfen
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY nicht gesetzt!")
        print("   export ANTHROPIC_API_KEY='sk-...'")
        return 1

    print("✅ ANTHROPIC_API_KEY gefunden\n")

    # Test-Story
    test_stories = [
        {
            'title': 'OAuth2 Authentication mit JWT Tokens implementieren',
            'description': 'Implementiere ein OAuth2 Authentifizierungssystem mit JWT Tokens. Nutzer sollen sich mit Google und GitHub anmelden können. Tokens sollen 24h gültig sein und automatisch refreshed werden.'
        },
        {
            'title': 'Datenbank Migration von MySQL auf PostgreSQL',
            'description': 'Migriere alle Tabellen von MySQL auf PostgreSQL. Schema muss angepasst werden, Indizes müssen neu erstellt werden. Datenmigration muss ohne Downtime erfolgen.'
        },
        {
            'title': 'Bewertungsformular mit Sternen und Text',
            'description': 'Einfaches Formular wo Nutzer eine Bewertung mit 1-5 Sternen und optionalem Textkommentar abgeben können. Sollte responsiv sein.'
        }
    ]

    # Nutzer kann wählen
    print("Wähle eine Test-Story:\n")
    for i, story in enumerate(test_stories, 1):
        print(f"{i}. {story['title']}")
    print(f"{len(test_stories)+1}. Eigene Story eingeben\n")

    try:
        choice = int(input("Deine Wahl (1-4): "))

        if choice <= len(test_stories):
            story = test_stories[choice - 1]
            story_title = story['title']
            story_description = story['description']
        else:
            story_title = input("\nStory Titel: ")
            story_description = input("Story Beschreibung: ")

    except (ValueError, KeyboardInterrupt):
        print("\nAbgebrochen.")
        return 0

    print("\n" + "="*60)
    print("SCHÄTZE STORY")
    print("="*60)
    print(f"Titel: {story_title}")
    print(f"Beschreibung: {story_description}")
    print()

    # Ähnliche Stories finden
    print("🔍 Suche ähnliche Archive-Stories...")
    similar = find_similar_stories_with_points(
        f"{story_title} {story_description}",
        limit=5
    )

    if not similar:
        print("❌ Keine ähnlichen Stories gefunden!")
        return 1

    print(f"✅ {len(similar)} ähnliche Stories gefunden\n")

    # Top 3 anzeigen
    print("Top 3 ähnliche Stories:")
    for i, sim in enumerate(similar[:3], 1):
        story = sim['story']
        print(f"  {i}. [{story['final_points']} SP] {story['title'][:60]}")
        print(f"     Ähnlichkeit: {sim['similarity']:.3f}")
    print()

    # Claude fragen
    print("🤖 Frage Claude nach Schätzung...")
    try:
        estimation = estimate_with_claude(
            story_title,
            story_description,
            similar,
            api_key
        )

        print("\n" + "="*60)
        print("CLAUDE'S SCHÄTZUNG")
        print("="*60)
        print(estimation)
        print("="*60)

    except Exception as e:
        print(f"❌ Fehler bei Claude API: {e}")
        return 1

    print("\n✅ Schätzung abgeschlossen!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
