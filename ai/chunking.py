"""
Text-Chunking Strategien für Planning Poker Daten
Teilt große Texte in sinnvolle Chunks für Embeddings auf
"""

import re
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class ChunkingStrategy(ABC):
    """Basis-Klasse für Chunking-Strategien"""

    @abstractmethod
    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Teilt Text in Chunks auf

        Args:
            text: Zu chunkender Text
            metadata: Optionale Metadaten für die Chunks

        Returns:
            Liste von Chunk-Dicts mit 'text', 'index' und optionalen Metadaten
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Gibt den Namen der Strategie zurück"""
        pass


class FixedSizeChunking(ChunkingStrategy):
    """
    Teilt Text in Chunks fester Größe auf
    Einfach aber effektiv für gleichmäßige Verarbeitung
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        """
        Args:
            chunk_size: Maximale Anzahl Zeichen pro Chunk
            overlap: Überlappung zwischen Chunks (für Kontext)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not text:
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Wenn nicht am Ende, versuche an Wort-Grenze zu brechen
            if end < len(text):
                # Suche nächstes Leerzeichen rückwärts
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_data = {
                    'text': chunk_text,
                    'index': index,
                    'start_pos': start,
                    'end_pos': end,
                }
                if metadata:
                    chunk_data['metadata'] = metadata

                chunks.append(chunk_data)
                index += 1

            # Nächster Start mit Überlappung
            start = end - self.overlap if self.overlap > 0 else end

        return chunks

    def get_strategy_name(self) -> str:
        return f"fixed_size_{self.chunk_size}_{self.overlap}"


class SentenceChunking(ChunkingStrategy):
    """
    Teilt Text in Satz-basierte Chunks auf
    Respektiert semantische Grenzen besser
    """

    def __init__(self, max_sentences: int = 5, max_chunk_size: int = 1000):
        """
        Args:
            max_sentences: Maximale Anzahl Sätze pro Chunk
            max_chunk_size: Maximale Größe eines Chunks (Fallback)
        """
        self.max_sentences = max_sentences
        self.max_chunk_size = max_chunk_size
        # Einfaches Satz-Ende Pattern
        self.sentence_pattern = re.compile(r'[.!?]+[\s\n]+')

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not text:
            return []

        # Teile in Sätze
        sentences = self._split_sentences(text)

        chunks = []
        current_chunk = []
        current_length = 0
        index = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # Prüfe ob wir einen neuen Chunk starten müssen
            if (len(current_chunk) >= self.max_sentences or
                current_length + sentence_length > self.max_chunk_size) and current_chunk:

                # Speichere aktuellen Chunk
                chunk_text = ' '.join(current_chunk).strip()
                if chunk_text:
                    chunk_data = {
                        'text': chunk_text,
                        'index': index,
                        'sentence_count': len(current_chunk),
                    }
                    if metadata:
                        chunk_data['metadata'] = metadata

                    chunks.append(chunk_data)
                    index += 1

                # Starte neuen Chunk
                current_chunk = []
                current_length = 0

            current_chunk.append(sentence)
            current_length += sentence_length

        # Letzten Chunk hinzufügen
        if current_chunk:
            chunk_text = ' '.join(current_chunk).strip()
            if chunk_text:
                chunk_data = {
                    'text': chunk_text,
                    'index': index,
                    'sentence_count': len(current_chunk),
                }
                if metadata:
                    chunk_data['metadata'] = metadata

                chunks.append(chunk_data)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Teilt Text in Sätze auf"""
        # Split an Satzzeichen
        parts = self.sentence_pattern.split(text)

        # Entferne leere Strings und trimme
        sentences = [s.strip() for s in parts if s.strip()]

        return sentences

    def get_strategy_name(self) -> str:
        return f"sentence_{self.max_sentences}"


class ParagraphChunking(ChunkingStrategy):
    """
    Teilt Text in Absatz-basierte Chunks auf
    Gut für strukturierte Texte mit klaren Absätzen
    """

    def __init__(self, max_paragraphs: int = 3, max_chunk_size: int = 1500):
        """
        Args:
            max_paragraphs: Maximale Anzahl Absätze pro Chunk
            max_chunk_size: Maximale Größe eines Chunks (Fallback)
        """
        self.max_paragraphs = max_paragraphs
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not text:
            return []

        # Teile in Absätze (bei Doppel-Newline)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        # Falls keine Absätze gefunden, versuche Single-Newline
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        # Falls immer noch ein einzelner Block, nutze Fallback
        if len(paragraphs) == 1 and len(text) > self.max_chunk_size:
            # Fallback auf Fixed-Size
            fallback = FixedSizeChunking(chunk_size=self.max_chunk_size, overlap=100)
            return fallback.chunk(text, metadata)

        chunks = []
        current_chunk = []
        current_length = 0
        index = 0

        for paragraph in paragraphs:
            para_length = len(paragraph)

            # Prüfe ob wir einen neuen Chunk starten müssen
            if (len(current_chunk) >= self.max_paragraphs or
                current_length + para_length > self.max_chunk_size) and current_chunk:

                # Speichere aktuellen Chunk
                chunk_text = '\n\n'.join(current_chunk).strip()
                if chunk_text:
                    chunk_data = {
                        'text': chunk_text,
                        'index': index,
                        'paragraph_count': len(current_chunk),
                    }
                    if metadata:
                        chunk_data['metadata'] = metadata

                    chunks.append(chunk_data)
                    index += 1

                # Starte neuen Chunk
                current_chunk = []
                current_length = 0

            current_chunk.append(paragraph)
            current_length += para_length

        # Letzten Chunk hinzufügen
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk).strip()
            if chunk_text:
                chunk_data = {
                    'text': chunk_text,
                    'index': index,
                    'paragraph_count': len(current_chunk),
                }
                if metadata:
                    chunk_data['metadata'] = metadata

                chunks.append(chunk_data)

        return chunks

    def get_strategy_name(self) -> str:
        return f"paragraph_{self.max_paragraphs}"


class StoryChunking(ChunkingStrategy):
    """
    Spezialisierte Chunking-Strategie für Planning Poker Stories
    Respektiert die Struktur von Title/Description/Comments
    """

    def __init__(self, chunk_description: bool = True, max_description_chunk_size: int = 800):
        """
        Args:
            chunk_description: Wenn True, wird lange Description in Chunks aufgeteilt
            max_description_chunk_size: Maximale Größe für Description-Chunks
        """
        self.chunk_description = chunk_description
        self.max_description_chunk_size = max_description_chunk_size

    def chunk(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Erwartet kombinierten Text im Format:
        Title: ...
        Description: ...
        Voting: ...
        Comments: ...
        """
        if not text:
            return []

        chunks = []
        index = 0

        # Parse die verschiedenen Sections
        sections = self._parse_story_sections(text)

        # Title ist immer ein eigener Chunk (wichtigster Kontext)
        if sections.get('title'):
            chunks.append({
                'text': f"Title: {sections['title']}",
                'index': index,
                'section': 'title',
                'metadata': metadata,
            })
            index += 1

        # Description kann in mehrere Chunks aufgeteilt werden
        if sections.get('description'):
            description = sections['description']

            if self.chunk_description and len(description) > self.max_description_chunk_size:
                # Teile lange Description auf
                desc_chunker = SentenceChunking(max_sentences=5, max_chunk_size=self.max_description_chunk_size)
                desc_chunks = desc_chunker.chunk(description)

                for desc_chunk in desc_chunks:
                    chunks.append({
                        'text': f"Description: {desc_chunk['text']}",
                        'index': index,
                        'section': 'description',
                        'sub_index': desc_chunk['index'],
                        'metadata': metadata,
                    })
                    index += 1
            else:
                # Description als ein Chunk
                chunks.append({
                    'text': f"Description: {description}",
                    'index': index,
                    'section': 'description',
                    'metadata': metadata,
                })
                index += 1

        # Voting und Comments als separate Chunks
        if sections.get('voting'):
            chunks.append({
                'text': f"Voting: {sections['voting']}",
                'index': index,
                'section': 'voting',
                'metadata': metadata,
            })
            index += 1

        if sections.get('comments'):
            chunks.append({
                'text': f"Comments: {sections['comments']}",
                'index': index,
                'section': 'comments',
                'metadata': metadata,
            })
            index += 1

        return chunks

    def _parse_story_sections(self, text: str) -> Dict[str, str]:
        """Parsed kombinierten Story-Text in Sections"""
        sections = {}

        # Einfaches Pattern-Matching für die Sections
        patterns = {
            'title': r'Title:\s*(.+?)(?=\n|Description:|Voting:|Comments:|$)',
            'description': r'Description:\s*(.+?)(?=Voting:|Comments:|$)',
            'voting': r'Voting:\s*(.+?)(?=Comments:|$)',
            'comments': r'Comments:\s*(.+?)$',
        }

        for section_name, pattern in patterns.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                sections[section_name] = match.group(1).strip()

        return sections

    def get_strategy_name(self) -> str:
        return "story_aware"


class ChunkingFactory:
    """Factory für einfache Erstellung von Chunking-Strategien"""

    @staticmethod
    def create_strategy(
        strategy_type: str,
        **kwargs
    ) -> ChunkingStrategy:
        """
        Erstellt eine Chunking-Strategie

        Args:
            strategy_type: Typ der Strategie ('fixed', 'sentence', 'paragraph', 'story')
            **kwargs: Parameter für die Strategie

        Returns:
            ChunkingStrategy-Instanz
        """
        strategies = {
            'fixed': FixedSizeChunking,
            'sentence': SentenceChunking,
            'paragraph': ParagraphChunking,
            'story': StoryChunking,
        }

        strategy_class = strategies.get(strategy_type.lower())
        if not strategy_class:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        return strategy_class(**kwargs)

    @staticmethod
    def get_default_for_content_type(content_type: str) -> ChunkingStrategy:
        """
        Gibt eine empfohlene Default-Strategie für einen Content-Type zurück

        Args:
            content_type: Typ des Contents ('story', 'comment', 'generic')

        Returns:
            ChunkingStrategy-Instanz
        """
        defaults = {
            'story': StoryChunking(chunk_description=True),
            'comment': SentenceChunking(max_sentences=3),
            'generic': FixedSizeChunking(chunk_size=500, overlap=50),
        }

        return defaults.get(content_type, defaults['generic'])


# Convenience-Funktionen
def chunk_story(story_text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Chunked eine Story mit der Story-spezifischen Strategie"""
    strategy = StoryChunking()
    return strategy.chunk(story_text, metadata)


def chunk_text(
    text: str,
    strategy_type: str = 'fixed',
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Chunked Text mit der angegebenen Strategie

    Args:
        text: Zu chunkender Text
        strategy_type: Typ der Strategie ('fixed', 'sentence', 'paragraph', 'story')
        metadata: Optionale Metadaten
        **kwargs: Parameter für die Strategie

    Returns:
        Liste von Chunks
    """
    strategy = ChunkingFactory.create_strategy(strategy_type, **kwargs)
    return strategy.chunk(text, metadata)
