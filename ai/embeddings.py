"""
Embedding-Generierung für Planning Poker Daten
Unterstützt verschiedene Embedding-Provider (OpenAI, Ollama, etc.)
"""

import json
import struct
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import urllib.request
import urllib.error


class EmbeddingProvider(ABC):
    """Basis-Klasse für Embedding-Provider"""

    @abstractmethod
    def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """
        Generiert ein Embedding für den gegebenen Text

        Args:
            text: Text für Embedding-Generierung

        Returns:
            Tuple von (embedding_vector, dimension)
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Gibt den Namen des verwendeten Modells zurück"""
        pass

    @abstractmethod
    def get_max_tokens(self) -> int:
        """Gibt die maximale Token-Anzahl zurück"""
        pass

    def encode_embedding(self, embedding: List[float]) -> bytes:
        """
        Enkodiert Embedding-Vektor als Bytes für Datenbank-Speicherung

        Args:
            embedding: Liste von Float-Werten

        Returns:
            Bytes-Repräsentation
        """
        # Speichere als Float32 Bytes
        return struct.pack(f'{len(embedding)}f', *embedding)

    def decode_embedding(self, embedding_bytes: bytes) -> List[float]:
        """
        Dekodiert Embedding-Bytes zurück zu Float-Liste

        Args:
            embedding_bytes: Bytes-Repräsentation

        Returns:
            Liste von Float-Werten
        """
        num_floats = len(embedding_bytes) // 4  # 4 bytes per float32
        return list(struct.unpack(f'{num_floats}f', embedding_bytes))

    def batch_generate_embeddings(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[Tuple[List[float], int]]:
        """
        Generiert Embeddings für mehrere Texte

        Args:
            texts: Liste von Texten
            show_progress: Wenn True, wird Fortschritt ausgegeben

        Returns:
            Liste von (embedding_vector, dimension) Tuples
        """
        results = []
        total = len(texts)

        for i, text in enumerate(texts):
            if show_progress and i % 10 == 0:
                print(f"Generating embeddings: {i}/{total}")

            embedding, dimension = self.generate_embedding(text)
            results.append((embedding, dimension))

        return results


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Embedding-Provider für OpenAI API
    Benötigt API-Key in Environment Variable OPENAI_API_KEY
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        api_base: str = "https://api.openai.com/v1"
    ):
        """
        Args:
            api_key: OpenAI API Key (oder aus ENV)
            model: Zu verwendendes Modell
            api_base: API Basis-URL
        """
        import os
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API Key not provided and OPENAI_API_KEY not set")

        self.model = model
        self.api_base = api_base
        self._model_dimensions = {
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'text-embedding-ada-002': 1536,
        }

    def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """Generiert Embedding via OpenAI API"""
        url = f"{self.api_base}/embeddings"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        data = {
            'input': text,
            'model': self.model
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                embedding = result['data'][0]['embedding']
                return embedding, len(embedding)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"OpenAI API error: {e.code} - {error_body}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    def get_model_name(self) -> str:
        return f"openai_{self.model}"

    def get_max_tokens(self) -> int:
        # OpenAI Embedding-Modelle haben 8191 Token Limit
        return 8191


class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Embedding-Provider für Ollama (lokale Modelle)
    Benötigt laufenden Ollama-Server
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        api_base: str = "http://localhost:11434"
    ):
        """
        Args:
            model: Ollama Modell-Name (z.B. 'nomic-embed-text', 'mxbai-embed-large')
            api_base: Ollama Server URL
        """
        self.model = model
        self.api_base = api_base

    def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """Generiert Embedding via Ollama API"""
        url = f"{self.api_base}/api/embeddings"
        headers = {'Content-Type': 'application/json'}
        data = {
            'model': self.model,
            'prompt': text
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                embedding = result['embedding']
                return embedding, len(embedding)
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection error: {str(e)}. Is Ollama running?")
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    def get_model_name(self) -> str:
        return f"ollama_{self.model}"

    def get_max_tokens(self) -> int:
        # Ollama Modelle haben typischerweise 2048 Token Context
        return 2048


class SentenceTransformerProvider(EmbeddingProvider):
    """
    Embedding-Provider für sentence-transformers (HuggingFace)
    Vollständig lokal, Open Source, keine API nötig
    """

    def __init__(self, model: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        """
        Args:
            model: HuggingFace Modell-Name
                   - all-MiniLM-L6-v2: 384 dim, 80MB, schnell (default)
                   - paraphrase-multilingual-MiniLM-L12-v2: 384 dim, mehrsprachig
                   - all-mpnet-base-v2: 768 dim, 420MB, beste Qualität
            device: 'cpu' oder 'cuda' (falls GPU verfügbar)
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model
        self.device = device
        self.model = SentenceTransformer(model, device=device)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """Generiert Embedding via sentence-transformers"""
        try:
            # Encode gibt numpy array zurück
            embedding = self.model.encode(text, convert_to_numpy=True)
            # Konvertiere zu Python Liste
            embedding_list = embedding.tolist()
            return embedding_list, len(embedding_list)
        except Exception as e:
            raise RuntimeError(f"Failed to generate embedding: {str(e)}")

    def get_model_name(self) -> str:
        return f"sentence_transformers_{self.model_name}"

    def get_max_tokens(self) -> int:
        # Die meisten sentence-transformer Modelle haben 256-512 Token Limit
        return self.model.max_seq_length if hasattr(self.model, 'max_seq_length') else 256

    def batch_generate_embeddings(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[Tuple[List[float], int]]:
        """
        Optimierte Batch-Verarbeitung für sentence-transformers
        Schneller als einzelne Aufrufe
        """
        # sentence-transformers hat native Batch-Unterstützung
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
            batch_size=32
        )

        results = []
        for embedding in embeddings:
            embedding_list = embedding.tolist()
            results.append((embedding_list, len(embedding_list)))

        return results


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock-Provider für Tests und Entwicklung
    Generiert deterministische Fake-Embeddings
    """

    def __init__(self, dimension: int = 384):
        """
        Args:
            dimension: Dimension der generierten Embeddings
        """
        self.dimension = dimension

    def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """Generiert deterministisches Fake-Embedding basierend auf Text-Hash"""
        # Nutze Hash des Textes für deterministische Werte
        text_hash = hash(text)

        # Generiere Pseudo-Random Embedding basierend auf Hash
        embedding = []
        for i in range(self.dimension):
            # Einfache Pseudo-Random-Funktion
            value = ((text_hash + i * 7919) % 10000) / 10000.0 - 0.5
            embedding.append(value)

        return embedding, self.dimension

    def get_model_name(self) -> str:
        return f"mock_embedding_{self.dimension}"

    def get_max_tokens(self) -> int:
        return 512


class EmbeddingGenerator:
    """
    High-Level Interface für Embedding-Generierung
    Verwaltet Provider und speichert in Datenbank
    """

    def __init__(self, provider: EmbeddingProvider):
        """
        Args:
            provider: Embedding-Provider Instanz
        """
        self.provider = provider

    def generate_and_store(
        self,
        chunk_id: int,
        text: str,
        db_module=None
    ) -> Optional[int]:
        """
        Generiert Embedding und speichert es in der Datenbank

        Args:
            chunk_id: ID des Text-Chunks
            text: Text für Embedding
            db_module: database_ai Modul (für Storage)

        Returns:
            ID des erstellten Embeddings oder None bei Fehler
        """
        try:
            # Generiere Embedding
            embedding_vector, dimension = self.provider.generate_embedding(text)

            # Enkodiere für Datenbank
            embedding_bytes = self.provider.encode_embedding(embedding_vector)

            # Speichere in Datenbank (wenn Modul übergeben)
            if db_module:
                embedding_id = db_module.create_embedding(
                    chunk_id=chunk_id,
                    embedding_model=self.provider.get_model_name(),
                    embedding_vector=embedding_bytes,
                    embedding_dimension=dimension
                )
                return embedding_id

            return None

        except Exception as e:
            print(f"Error generating embedding for chunk {chunk_id}: {e}")
            return None

    def batch_generate_and_store(
        self,
        chunks: List[Dict[str, Any]],
        db_module=None,
        show_progress: bool = True
    ) -> List[Optional[int]]:
        """
        Generiert Embeddings für mehrere Chunks und speichert sie

        Args:
            chunks: Liste von Chunk-Dicts mit 'id' und 'chunk_text'
            db_module: database_ai Modul
            show_progress: Fortschritt anzeigen

        Returns:
            Liste von Embedding-IDs (oder None bei Fehlern)
        """
        results = []
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            if show_progress and i % 10 == 0:
                print(f"Processing chunks: {i}/{total}")

            embedding_id = self.generate_and_store(
                chunk_id=chunk['id'],
                text=chunk['chunk_text'],
                db_module=db_module
            )
            results.append(embedding_id)

        return results

    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Berechnet Cosine-Similarity zwischen zwei Embeddings

        Args:
            embedding1: Erstes Embedding
            embedding2: Zweites Embedding

        Returns:
            Similarity-Score zwischen -1 und 1
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimension")

        # Dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Magnitudes
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def find_similar_chunks(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[Tuple[int, List[float]]],
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Tuple[int, float]]:
        """
        Findet ähnlichste Chunks basierend auf Embedding-Similarity

        Args:
            query_embedding: Query-Embedding
            candidate_embeddings: Liste von (chunk_id, embedding) Tuples
            top_k: Anzahl Top-Ergebnisse
            min_similarity: Minimale Similarity für Ergebnisse

        Returns:
            Liste von (chunk_id, similarity) Tuples, sortiert nach Similarity
        """
        similarities = []

        for chunk_id, candidate_embedding in candidate_embeddings:
            similarity = self.cosine_similarity(query_embedding, candidate_embedding)

            if similarity >= min_similarity:
                similarities.append((chunk_id, similarity))

        # Sortiere nach Similarity (höchste zuerst)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]


class EmbeddingProviderFactory:
    """Factory für einfache Erstellung von Embedding-Providern"""

    @staticmethod
    def create_provider(
        provider_type: str,
        **kwargs
    ) -> EmbeddingProvider:
        """
        Erstellt einen Embedding-Provider

        Args:
            provider_type: Typ des Providers ('openai', 'ollama', 'sentence_transformers', 'mock')
            **kwargs: Provider-spezifische Parameter

        Returns:
            EmbeddingProvider-Instanz
        """
        providers = {
            'openai': OpenAIEmbeddingProvider,
            'ollama': OllamaEmbeddingProvider,
            'sentence_transformers': SentenceTransformerProvider,
            'sentence-transformers': SentenceTransformerProvider,  # Alias
            'huggingface': SentenceTransformerProvider,  # Alias
            'mock': MockEmbeddingProvider,
        }

        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider type: {provider_type}")

        return provider_class(**kwargs)

    @staticmethod
    def create_default(prefer_local: bool = False) -> EmbeddingProvider:
        """
        Erstellt einen Default-Provider

        Args:
            prefer_local: Wenn True, werden lokale Provider bevorzugt

        Returns:
            EmbeddingProvider-Instanz
        """
        import os

        if prefer_local:
            # 1. Versuche sentence-transformers (am einfachsten)
            try:
                provider = SentenceTransformerProvider()
                # Quick check
                provider.generate_embedding("test")
                return provider
            except:
                pass

            # 2. Versuche Ollama
            try:
                provider = OllamaEmbeddingProvider()
                # Quick connectivity check
                provider.generate_embedding("test")
                return provider
            except:
                pass

        # Versuche OpenAI
        if os.getenv('OPENAI_API_KEY'):
            try:
                return OpenAIEmbeddingProvider()
            except:
                pass

        # Fallback auf Mock
        print("Warning: Using MockEmbeddingProvider. Configure a real provider:")
        print("  - pip install sentence-transformers (lokale Open Source)")
        print("  - ollama pull nomic-embed-text (lokale Open Source)")
        print("  - export OPENAI_API_KEY=... (Cloud)")
        return MockEmbeddingProvider()


# Convenience-Funktionen
def create_generator(provider_type: str = 'mock', **kwargs) -> EmbeddingGenerator:
    """
    Erstellt einen EmbeddingGenerator mit dem angegebenen Provider

    Args:
        provider_type: Typ des Providers ('openai', 'ollama', 'mock')
        **kwargs: Provider-spezifische Parameter

    Returns:
        EmbeddingGenerator-Instanz
    """
    provider = EmbeddingProviderFactory.create_provider(provider_type, **kwargs)
    return EmbeddingGenerator(provider)
