"""
MCP Tool Definitions für Planning Poker
Definiert wiederverwendbare Tool-Handlers
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


def calculate_team_velocity(
    stories: List[Dict[str, Any]],
    time_period_days: int = 14
) -> Dict[str, Any]:
    """
    Berechnet die Team-Velocity basierend auf abgeschlossenen Stories

    Args:
        stories: Liste von Story-Dicts
        time_period_days: Zeitraum in Tagen

    Returns:
        Velocity-Statistiken
    """
    cutoff_date = datetime.now() - timedelta(days=time_period_days)

    completed_stories = [
        s for s in stories
        if s['status'] == 'completed' and
        s.get('completed_at') and
        s.get('final_points') is not None
    ]

    # Filtere nach Zeitraum
    recent_stories = []
    for story in completed_stories:
        try:
            completed_at = datetime.fromisoformat(story['completed_at'])
            if completed_at >= cutoff_date:
                recent_stories.append(story)
        except (ValueError, TypeError):
            pass

    if not recent_stories:
        return {
            "period_days": time_period_days,
            "completed_stories": 0,
            "total_points": 0,
            "velocity_per_day": 0
        }

    total_points = sum(s['final_points'] for s in recent_stories)

    return {
        "period_days": time_period_days,
        "completed_stories": len(recent_stories),
        "total_points": total_points,
        "velocity_per_day": round(total_points / time_period_days, 2)
    }


def analyze_estimation_accuracy(
    stories: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analysiert Genauigkeit von Schätzungen
    Vergleicht erste Runde mit finaler Schätzung

    Args:
        stories: Liste von Story-Dicts mit Votes

    Returns:
        Analyse-Ergebnisse
    """
    accuracy_data = []

    for story in stories:
        if story['status'] != 'completed' or not story.get('final_points'):
            continue

        votes = story.get('all_votes', [])
        if not votes:
            continue

        # Hole erste Runde
        first_round_votes = [v for v in votes if v.get('round', 1) == 1]
        if not first_round_votes:
            continue

        # Durchschnitt erste Runde
        avg_first = sum(v['points'] for v in first_round_votes) / len(first_round_votes)
        final = story['final_points']

        difference = abs(final - avg_first)
        accuracy_data.append({
            'story_id': story['id'],
            'first_estimate': avg_first,
            'final_points': final,
            'difference': difference
        })

    if not accuracy_data:
        return {
            "analyzed_stories": 0,
            "avg_difference": 0
        }

    avg_diff = sum(d['difference'] for d in accuracy_data) / len(accuracy_data)

    return {
        "analyzed_stories": len(accuracy_data),
        "avg_difference": round(avg_diff, 2),
        "details": accuracy_data
    }


def identify_controversial_stories(
    stories: List[Dict[str, Any]],
    threshold: float = 3.0
) -> List[Dict[str, Any]]:
    """
    Identifiziert kontroverse Stories (hohe Varianz in Votes)

    Args:
        stories: Liste von Story-Dicts mit Votes
        threshold: Schwellwert für Standardabweichung

    Returns:
        Liste kontroverser Stories
    """
    controversial = []

    for story in stories:
        votes = story.get('all_votes', [])
        if not votes or len(votes) < 2:
            continue

        # Berechne Standardabweichung
        points = [v['points'] for v in votes]
        avg = sum(points) / len(points)
        variance = sum((p - avg) ** 2 for p in points) / len(points)
        std_dev = variance ** 0.5

        if std_dev >= threshold:
            controversial.append({
                'story_id': story['id'],
                'title': story['title'],
                'std_dev': round(std_dev, 2),
                'votes': points
            })

    # Sortiere nach Standardabweichung
    controversial.sort(key=lambda x: x['std_dev'], reverse=True)

    return controversial


def get_user_voting_patterns(
    user_name: str,
    votes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analysiert Voting-Muster eines Users

    Args:
        user_name: Name des Users
        votes: Liste aller Votes des Users

    Returns:
        Muster-Analyse
    """
    if not votes:
        return {
            "user_name": user_name,
            "total_votes": 0
        }

    points = [v['points'] for v in votes]

    # Häufigkeitsverteilung
    point_distribution = {}
    for point in points:
        point_distribution[point] = point_distribution.get(point, 0) + 1

    # Statistiken
    avg_points = sum(points) / len(points)
    most_common = max(point_distribution.items(), key=lambda x: x[1])

    return {
        "user_name": user_name,
        "total_votes": len(votes),
        "avg_points": round(avg_points, 2),
        "most_common_vote": most_common[0],
        "point_distribution": point_distribution
    }


def suggest_story_complexity(
    story_text: str,
    historical_stories: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Schlägt Komplexität für eine Story vor basierend auf historischen Daten
    (Vereinfachte Version ohne ML)

    Args:
        story_text: Text der neuen Story
        historical_stories: Historische Stories mit Final Points

    Returns:
        Komplexitäts-Vorschlag
    """
    # Einfache Heuristiken
    text_length = len(story_text)
    word_count = len(story_text.split())

    # Finde ähnliche Stories basierend auf Länge
    similar_by_length = []
    for story in historical_stories:
        if story['status'] != 'completed' or not story.get('final_points'):
            continue

        story_text_combined = f"{story['title']} {story.get('description', '')}"
        story_length = len(story_text_combined)

        # Ähnlich wenn Länge innerhalb 30% liegt
        if abs(story_length - text_length) / max(text_length, 1) <= 0.3:
            similar_by_length.append(story)

    if similar_by_length:
        avg_points = sum(s['final_points'] for s in similar_by_length) / len(similar_by_length)
        suggested_points = round(avg_points)
    else:
        # Fallback auf simple Heuristik
        if word_count < 20:
            suggested_points = 2
        elif word_count < 50:
            suggested_points = 5
        elif word_count < 100:
            suggested_points = 8
        else:
            suggested_points = 13

    return {
        "suggested_points": suggested_points,
        "confidence": "low" if not similar_by_length else "medium",
        "similar_stories_count": len(similar_by_length),
        "text_metrics": {
            "length": text_length,
            "word_count": word_count
        }
    }


def generate_estimation_report(
    stories: List[Dict[str, Any]],
    time_period_days: int = 30
) -> Dict[str, Any]:
    """
    Generiert umfassenden Estimation-Report

    Args:
        stories: Alle Stories
        time_period_days: Zeitraum für Analyse

    Returns:
        Komplett-Report
    """
    velocity = calculate_team_velocity(stories, time_period_days)
    accuracy = analyze_estimation_accuracy(stories)
    controversial = identify_controversial_stories(stories)

    # Zusätzliche Metriken
    completed_stories = [s for s in stories if s['status'] == 'completed']
    total_points = sum(s.get('final_points', 0) for s in completed_stories if s.get('final_points'))

    return {
        "report_date": datetime.now().isoformat(),
        "time_period_days": time_period_days,
        "velocity": velocity,
        "accuracy": accuracy,
        "controversial_stories": controversial,
        "summary": {
            "total_completed": len(completed_stories),
            "total_points": total_points,
            "avg_points_per_story": round(total_points / len(completed_stories), 2) if completed_stories else 0
        }
    }
