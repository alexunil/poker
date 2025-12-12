"""
Datenbereinigung und Preprocessing für Planning Poker Stories
Bereitet Rohdaten für Chunking und Embedding vor
"""

import re
import html
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataPreprocessor:
    """
    Bereinigt und standardisiert Daten aus der Planning Poker Datenbank
    """

    def __init__(self):
        self.whitespace_pattern = re.compile(r'\s+')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    def clean_text(self, text: str, preserve_structure: bool = True) -> str:
        """
        Bereinigt Text von HTML, überschüssigem Whitespace und Sonderzeichen

        Args:
            text: Roher Eingabetext
            preserve_structure: Wenn True, werden Zeilenumbrüche erhalten

        Returns:
            Bereinigter Text
        """
        if not text:
            return ""

        # HTML-Entities dekodieren
        text = html.unescape(text)

        # HTML-Tags entfernen (falls vorhanden)
        text = re.sub(r'<[^>]+>', '', text)

        if preserve_structure:
            # Mehrfache Leerzeichen reduzieren, aber Zeilenumbrüche erhalten
            lines = text.split('\n')
            lines = [self.whitespace_pattern.sub(' ', line.strip()) for line in lines]
            text = '\n'.join(line for line in lines if line)
        else:
            # Alle Whitespace-Zeichen zu einzelnen Leerzeichen
            text = self.whitespace_pattern.sub(' ', text)

        # Überschüssige Leerzeichen entfernen
        text = text.strip()

        return text

    def extract_urls(self, text: str) -> List[str]:
        """Extrahiert alle URLs aus einem Text"""
        return self.url_pattern.findall(text)

    def remove_urls(self, text: str, replacement: str = '[URL]') -> str:
        """Entfernt URLs aus Text und ersetzt sie optional mit Platzhalter"""
        return self.url_pattern.sub(replacement, text)

    def preprocess_story(self, story: Dict[str, Any], include_votes: bool = False) -> Dict[str, Any]:
        """
        Bereitet eine Story für KI-Verarbeitung vor

        Args:
            story: Story-Dict aus der Datenbank
            include_votes: Wenn True, werden Voting-Informationen inkludiert

        Returns:
            Preprocessed Story-Dict mit zusätzlichen Metadaten
        """
        result = {
            'id': story['id'],
            'title': self.clean_text(story['title'], preserve_structure=False),
            'description': self.clean_text(story.get('description', ''), preserve_structure=True),
            'creator': story['creator_name'],
            'status': story['status'],
            'final_points': story.get('final_points'),
            'created_at': story['created_at'],
            'completed_at': story.get('completed_at'),
        }

        # Extrahiere URLs aus Description
        if story.get('description'):
            result['urls'] = self.extract_urls(story['description'])
            result['has_urls'] = len(result['urls']) > 0

        # Kombinierter Text für Embedding
        combined_parts = [
            f"Title: {result['title']}",
        ]

        if result['description']:
            combined_parts.append(f"Description: {result['description']}")

        if include_votes and story.get('all_votes'):
            votes = story['all_votes']
            vote_summary = self._summarize_votes(votes)
            combined_parts.append(f"Voting: {vote_summary}")
            result['vote_summary'] = vote_summary

        if story.get('comments'):
            comments = story['comments']
            comment_summary = self._summarize_comments(comments)
            combined_parts.append(f"Comments: {comment_summary}")
            result['comment_summary'] = comment_summary

        result['combined_text'] = '\n'.join(combined_parts)
        result['text_length'] = len(result['combined_text'])
        result['word_count'] = len(result['combined_text'].split())

        return result

    def preprocess_comment(self, comment: Dict[str, Any]) -> Dict[str, Any]:
        """Bereitet einen Kommentar für KI-Verarbeitung vor"""
        return {
            'id': comment['id'],
            'story_id': comment['story_id'],
            'user_name': comment['user_name'],
            'comment_text': self.clean_text(comment['comment_text'], preserve_structure=True),
            'comment_type': comment.get('comment_type', 'general'),
            'created_at': comment['created_at'],
            'text_length': len(comment['comment_text']),
            'word_count': len(comment['comment_text'].split()),
        }

    def preprocess_vote_session(self, story_id: int, votes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bereitet eine komplette Voting-Session für Analyse vor

        Args:
            story_id: ID der Story
            votes: Liste aller Votes für diese Story

        Returns:
            Preprocessed Voting-Session mit Statistiken
        """
        if not votes:
            return {
                'story_id': story_id,
                'vote_count': 0,
                'rounds': 0,
            }

        # Gruppiere Votes nach Runden
        rounds = {}
        for vote in votes:
            round_num = vote.get('round', 1)
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(vote)

        # Analysiere jede Runde
        round_analyses = []
        for round_num, round_votes in sorted(rounds.items()):
            points = [v['points'] for v in round_votes]
            round_analyses.append({
                'round': round_num,
                'voters': [v['user_name'] for v in round_votes],
                'points': points,
                'min': min(points) if points else None,
                'max': max(points) if points else None,
                'avg': sum(points) / len(points) if points else None,
                'consensus': len(set(points)) == 1 if points else False,
            })

        return {
            'story_id': story_id,
            'vote_count': len(votes),
            'rounds': len(rounds),
            'round_analyses': round_analyses,
            'required_re_votes': len(rounds) - 1,
        }

    def _summarize_votes(self, votes: List[Dict[str, Any]]) -> str:
        """Erstellt eine textuelle Zusammenfassung der Votes"""
        if not votes:
            return "No votes yet"

        # Gruppiere nach Runden
        rounds = {}
        for vote in votes:
            round_num = vote.get('round', 1)
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(f"{vote['name']}:{vote['points']}")

        # Erstelle Summary
        parts = []
        for round_num, round_votes in sorted(rounds.items()):
            parts.append(f"Round {round_num}: {', '.join(round_votes)}")

        return "; ".join(parts)

    def _summarize_comments(self, comments: List[Dict[str, Any]]) -> str:
        """Erstellt eine textuelle Zusammenfassung der Kommentare"""
        if not comments:
            return "No comments"

        # Gruppiere nach Typ
        by_type = {}
        for comment in comments:
            comment_type = comment.get('comment_type', 'general')
            if comment_type not in by_type:
                by_type[comment_type] = []
            by_type[comment_type].append(comment)

        parts = []
        for comment_type, type_comments in by_type.items():
            count = len(type_comments)
            parts.append(f"{count} {comment_type} comment(s)")

        return "; ".join(parts)

    def batch_preprocess_stories(
        self,
        stories: List[Dict[str, Any]],
        include_votes: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Verarbeitet mehrere Stories in einem Batch

        Args:
            stories: Liste von Story-Dicts
            include_votes: Wenn True, werden Voting-Informationen inkludiert

        Returns:
            Liste von preprocessed Story-Dicts
        """
        return [self.preprocess_story(story, include_votes) for story in stories]

    def extract_metadata(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrahiert strukturierte Metadaten aus einer Story
        Nützlich für Filtering und Kontext
        """
        metadata = {
            'story_id': story['id'],
            'creator': story.get('creator_name', 'unknown'),
            'status': story['status'],
            'created_at': story['created_at'],
        }

        # Zeitliche Metadaten
        if story.get('completed_at'):
            metadata['completed_at'] = story['completed_at']
            # Berechne Dauer (wenn möglich)
            try:
                created = datetime.fromisoformat(story['created_at'])
                completed = datetime.fromisoformat(story['completed_at'])
                duration_seconds = (completed - created).total_seconds()
                metadata['duration_seconds'] = duration_seconds
            except (ValueError, TypeError):
                pass

        # Komplexitäts-Indikatoren
        if story.get('description'):
            desc_length = len(story['description'])
            metadata['description_length'] = desc_length
            metadata['has_description'] = desc_length > 0
            metadata['complexity_indicator'] = 'high' if desc_length > 500 else 'medium' if desc_length > 200 else 'low'

        # Voting-Metadaten
        if story.get('final_points'):
            metadata['final_points'] = story['final_points']
            metadata['estimate_category'] = self._categorize_estimate(story['final_points'])

        if story.get('all_votes'):
            metadata['vote_count'] = len(story['all_votes'])
            metadata['had_multiple_rounds'] = story.get('round', 1) > 1

        return metadata

    def _categorize_estimate(self, points: int) -> str:
        """Kategorisiert Schätzungen in Größenklassen"""
        if points <= 2:
            return 'trivial'
        elif points <= 5:
            return 'small'
        elif points <= 13:
            return 'medium'
        else:
            return 'large'


# Convenience-Funktion für einfachen Zugriff
_preprocessor_instance = None


def get_preprocessor() -> DataPreprocessor:
    """Gibt Singleton-Instanz des Preprocessors zurück"""
    global _preprocessor_instance
    if _preprocessor_instance is None:
        _preprocessor_instance = DataPreprocessor()
    return _preprocessor_instance
