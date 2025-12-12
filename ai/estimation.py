#!/usr/bin/env python3
"""
AI-gestützte Story-Schätzung für Planning Poker
Integriert als virtueller "AI Assistant" Teammitglied
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# AI AVAILABILITY CHECK
# ============================================================================

def check_ai_availability() -> Tuple[bool, Optional[str]]:
    """
    Prüft ob AI-Schätzung verfügbar ist

    Returns:
        (is_available, error_message)
    """
    # 1. Check ANTHROPIC_API_KEY
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return False, "ANTHROPIC_API_KEY not set"

    # 2. Check sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return False, "sentence-transformers not installed"

    # 3. Check Anthropic SDK
    try:
        from anthropic import Anthropic
    except ImportError:
        return False, "anthropic SDK not installed"

    # 4. Check if embeddings exist
    try:
        from ai.database_ai import init_ai_db, get_all_embeddings
        init_ai_db()

        embeddings = get_all_embeddings(limit=1)
        if not embeddings:
            return False, "No embeddings available - run 'python ai/setup_ai.py process' first"
    except Exception as e:
        return False, f"Database error: {e}"

    return True, None


def is_ai_enabled() -> bool:
    """
    Schneller Check ob AI aktiviert ist (ohne Error-Details)
    Cached für Performance
    """
    if not hasattr(is_ai_enabled, '_cached_result'):
        is_ai_enabled._cached_result = check_ai_availability()[0]

    return is_ai_enabled._cached_result


# ============================================================================
# STORY ESTIMATION
# ============================================================================

def find_similar_stories_with_points(
    story_title: str,
    story_description: str,
    limit: int = 5
) -> List[Dict]:
    """
    Findet ähnliche Archive-Stories mit Story Points

    Args:
        story_title: Story Titel
        story_description: Story Beschreibung
        limit: Maximale Anzahl ähnlicher Stories

    Returns:
        Liste von Dicts mit 'story' und 'similarity'
    """
    from database import init_db, get_all_stories
    from ai.embeddings import create_generator
    from ai.database_ai import init_ai_db, get_chunks_by_source, get_embedding_by_chunk

    # Initialisierung
    init_db()
    init_ai_db()

    # Embedding Generator
    generator = create_generator('sentence_transformers')

    # Query Text
    query_text = f"{story_title} {story_description}"

    # Query Embedding generieren
    query_embedding, _ = generator.provider.generate_embedding(query_text)

    # Alle Archive-Stories mit Story Points holen
    all_stories = get_all_stories()
    archive_stories = [
        s for s in all_stories
        if s.get('source') == 'jira_archive' and s.get('final_points')
    ]

    if not archive_stories:
        return []

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
        story_emb_vector = generator.provider.decode_embedding(
            embedding_data['embedding_vector']
        )

        # Cosine Similarity berechnen
        story_emb = np.array(story_emb_vector)
        query_emb = np.array(query_embedding)

        similarity = np.dot(query_emb, story_emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(story_emb)
        )

        similarities.append({
            'story': story,
            'similarity': float(similarity)
        })

    # Sortieren nach Similarity
    similarities.sort(key=lambda x: x['similarity'], reverse=True)

    return similarities[:limit]


def ask_claude_for_estimation(
    story_title: str,
    story_description: str,
    similar_stories: List[Dict]
) -> Dict:
    """
    Fragt Claude nach einer Story-Schätzung

    Args:
        story_title: Story Titel
        story_description: Story Beschreibung
        similar_stories: Ähnliche Stories mit Points

    Returns:
        {
            'points': int,
            'reasoning': str,
            'model_used': str
        }
    """
    from anthropic import Anthropic

    api_key = os.getenv('ANTHROPIC_API_KEY')
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
**Beschreibung:** {story_description or '(keine Beschreibung)'}

Gib deine Schätzung im folgenden Format zurück:

STORY POINTS: [Zahl]

BEGRÜNDUNG:
[Deine Begründung basierend auf den ähnlichen Stories - max 3 Sätze]

VERGLEICH:
[Vergleiche die neue Story mit den 2-3 ähnlichsten Archive-Stories - kurz und prägnant]
"""

    # Claude fragen
    model = "claude-opus-4-5-20251101"

    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text

    # Story Points extrahieren
    points = extract_story_points(response_text)

    return {
        'points': points,
        'reasoning': response_text,
        'model_used': model
    }


def extract_story_points(text: str) -> int:
    """
    Extrahiert Story Points aus Claude's Antwort

    Args:
        text: Claude's Response

    Returns:
        Story Points (Fibonacci Zahl)
    """
    import re

    # Suche nach "STORY POINTS: X"
    match = re.search(r'STORY POINTS:\s*(\d+)', text, re.IGNORECASE)

    if match:
        points = int(match.group(1))

        # Validiere Fibonacci
        fibonacci = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

        if points in fibonacci:
            return points
        else:
            # Runde zu nächster Fibonacci-Zahl
            for fib in fibonacci:
                if fib >= points:
                    return fib
            return fibonacci[-1]

    # Fallback: Suche nach irgendeiner Zahl am Anfang
    match = re.search(r'^\s*(\d+)', text)
    if match:
        return int(match.group(1))

    # Default: 5 (Medium)
    return 5


def estimate_story_with_ai(story_id: int) -> Optional[Dict]:
    """
    Schätzt eine Story mit AI und gibt Vote + Begründung zurück

    Args:
        story_id: Story ID

    Returns:
        {
            'points': int,
            'reasoning': str,
            'similar_stories': List[Dict],
            'model_used': str
        }
        oder None bei Fehler
    """
    try:
        from database import init_db, get_story_by_id

        # Check Availability
        available, error = check_ai_availability()
        if not available:
            print(f"⚠️  AI not available: {error}")
            return None

        # Story laden
        init_db()
        story = get_story_by_id(story_id)

        if not story:
            print(f"⚠️  Story {story_id} not found")
            return None

        # Ähnliche Stories finden
        similar = find_similar_stories_with_points(
            story_title=story['title'],
            story_description=story.get('description', ''),
            limit=5
        )

        if not similar:
            print(f"⚠️  No similar stories found for estimation")
            return None

        # Claude fragen
        estimation = ask_claude_for_estimation(
            story_title=story['title'],
            story_description=story.get('description', ''),
            similar_stories=similar
        )

        # Ergebnis zusammenstellen
        return {
            'points': estimation['points'],
            'reasoning': estimation['reasoning'],
            'similar_stories': similar[:3],  # Nur Top 3
            'model_used': estimation['model_used']
        }

    except Exception as e:
        print(f"❌ AI Estimation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

AI_USER_NAME = "AI Assistant"


def is_ai_user(user_name: str) -> bool:
    """Prüft ob ein User der AI-User ist"""
    return user_name == AI_USER_NAME


def get_ai_user_name() -> str:
    """Gibt den Namen des AI-Users zurück"""
    return AI_USER_NAME
