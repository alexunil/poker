# AI Module für Planning Poker

Dieses Modul bietet KI-Funktionalität für Planning Poker mit sauberer Trennung vom Haupt-Codebase.

## Architektur

```
ai/
├── __init__.py              # Modul-Initialisierung
├── database_ai.py           # DB-Schema für Embeddings & Chunks
├── preprocessing.py         # Datenbereinigung
├── chunking.py              # Text-Chunking Strategien
├── embeddings.py            # Embedding-Generierung
└── mcp/                     # MCP Server
    ├── __init__.py
    ├── server.py            # MCP Server Implementierung
    └── tools.py             # MCP Tool Definitions
```

## Dependencies

Das AI-Modul hat **nur** eine Abhängigkeit:
- `database.py` (für Zugriff auf Planning Poker Daten)

Externe APIs (optional):
- OpenAI API (für text-embedding-3-small)
- Ollama (für lokale Embeddings)

## Verwendung

### 1. Datenbank Initialisierung

```python
from ai.database_ai import init_ai_db

# Initialisiere AI-Datenbank-Erweiterungen
init_ai_db("planning_poker.db")
```

### 2. Data Preprocessing

```python
from ai.preprocessing import get_preprocessor
from database import get_all_stories, init_db

# Initialisiere Datenbanken
init_db("planning_poker.db")

# Hole Preprocessor
preprocessor = get_preprocessor()

# Lade und bereinige Stories
stories = get_all_stories()
cleaned_story = preprocessor.preprocess_story(stories[0], include_votes=True)

print(cleaned_story['combined_text'])
print(f"Words: {cleaned_story['word_count']}")
```

### 3. Text Chunking

```python
from ai.chunking import chunk_story, chunk_text, ChunkingFactory

# Story-spezifisches Chunking
story_text = "Title: User Authentication\nDescription: Implement login..."
chunks = chunk_story(story_text)

for chunk in chunks:
    print(f"Chunk {chunk['index']}: {chunk['section']}")
    print(chunk['text'][:100])

# Generisches Chunking
strategy = ChunkingFactory.create_strategy(
    'sentence',
    max_sentences=5,
    max_chunk_size=1000
)
chunks = strategy.chunk("Your text here...")

# Fixed-size Chunking
chunks = chunk_text(
    "Your text here...",
    strategy_type='fixed',
    chunk_size=500,
    overlap=50
)
```

### 4. Embedding-Generierung

```python
from ai.embeddings import create_generator, EmbeddingProviderFactory
from ai.database_ai import init_ai_db, create_chunk, get_ai_db
import ai.database_ai as db_ai

# Initialisiere
init_ai_db("planning_poker.db")

# Erstelle Embedding-Generator
# Option 1: Mock (für Tests)
generator = create_generator('mock', dimension=384)

# Option 2: OpenAI (benötigt OPENAI_API_KEY)
# generator = create_generator('openai', model='text-embedding-3-small')

# Option 3: Ollama (benötigt laufenden Ollama Server)
# generator = create_generator('ollama', model='nomic-embed-text')

# Erstelle Chunk
chunk_id = create_chunk(
    source_type='story',
    source_id=1,
    chunk_text="User Story: Implement authentication system",
    chunk_index=0,
    chunk_strategy='story_aware'
)

# Generiere und speichere Embedding
embedding_id = generator.generate_and_store(
    chunk_id=chunk_id,
    text="User Story: Implement authentication system",
    db_module=db_ai
)

print(f"Created embedding: {embedding_id}")
```

### 5. Komplette Pipeline

```python
from database import init_db, get_all_stories
from ai.database_ai import init_ai_db, create_chunk, enqueue_processing
from ai.preprocessing import get_preprocessor
from ai.chunking import chunk_story
from ai.embeddings import create_generator
import ai.database_ai as db_ai

# Setup
init_db("planning_poker.db")
init_ai_db("planning_poker.db")

preprocessor = get_preprocessor()
generator = create_generator('mock')  # Nutze 'openai' oder 'ollama' in Produktion

# Verarbeite alle Stories
stories = get_all_stories()

for story in stories:
    # 1. Preprocessing
    cleaned = preprocessor.preprocess_story(story, include_votes=True)

    # 2. Chunking
    chunks = chunk_story(cleaned['combined_text'])

    # 3. Chunks speichern und Embeddings erstellen
    for chunk in chunks:
        chunk_id = create_chunk(
            source_type='story',
            source_id=story['id'],
            chunk_text=chunk['text'],
            chunk_index=chunk['index'],
            chunk_strategy='story_aware',
            metadata=chunk.get('metadata')
        )

        # Embedding generieren
        generator.generate_and_store(
            chunk_id=chunk_id,
            text=chunk['text'],
            db_module=db_ai
        )

    print(f"Processed story {story['id']}: {len(chunks)} chunks")
```

### 6. MCP Server

Der MCP Server ermöglicht KI-Assistenten Zugriff auf Planning Poker Daten.

```python
from ai.mcp.server import create_server

# Erstelle Server
server = create_server(db_path="planning_poker.db")

# Starte im stdio-Modus (für MCP-Integration)
server.run_stdio()
```

#### Verfügbare MCP Tools:

1. **search_stories** - Suche Stories nach Titel, Beschreibung oder Status
2. **get_story** - Hole detaillierte Story-Informationen
3. **get_statistics** - Hole Statistiken über Stories, Votes, Users
4. **get_user_activity** - Hole Voting-Aktivität eines Users
5. **find_similar_stories** - Finde ähnliche Stories (benötigt Embeddings)

#### MCP Server als Standalone:

```bash
# In separatem Terminal
python -m ai.mcp.server
```

## Environment Variables

```bash
# Für OpenAI Embeddings
export OPENAI_API_KEY="sk-..."

# Für Ollama (Server muss laufen)
# Standard: http://localhost:11434
export OLLAMA_HOST="http://localhost:11434"
```

## Embedding-Provider Vergleich

| Provider | Vorteile | Nachteile | Use Case |
|----------|----------|-----------|----------|
| **Mock** | Keine Kosten, schnell | Keine echten Embeddings | Tests, Development |
| **OpenAI** | Beste Qualität | Kosten, API-Key nötig | Produktion (Cloud) |
| **Ollama** | Kostenlos, privat | Langsamer, benötigt Hardware | Produktion (On-Premise) |

### Empfohlene Ollama Modelle:

```bash
# Installiere Ollama: https://ollama.ai

# Kleines, schnelles Modell (270 MB)
ollama pull nomic-embed-text

# Großes, genaues Modell (669 MB)
ollama pull mxbai-embed-large
```

## Chunking-Strategien

### Fixed Size
```python
from ai.chunking import FixedSizeChunking

strategy = FixedSizeChunking(chunk_size=500, overlap=50)
chunks = strategy.chunk(text)
```

### Sentence-based
```python
from ai.chunking import SentenceChunking

strategy = SentenceChunking(max_sentences=5, max_chunk_size=1000)
chunks = strategy.chunk(text)
```

### Paragraph-based
```python
from ai.chunking import ParagraphChunking

strategy = ParagraphChunking(max_paragraphs=3)
chunks = strategy.chunk(text)
```

### Story-aware (empfohlen für Planning Poker)
```python
from ai.chunking import StoryChunking

strategy = StoryChunking(chunk_description=True)
chunks = strategy.chunk(combined_story_text)
```

## Similarity Search

```python
from ai.embeddings import create_generator
from ai.database_ai import get_all_embeddings
import ai.database_ai as db_ai

generator = create_generator('mock')

# Generiere Query-Embedding
query = "authentication system"
query_embedding, _ = generator.provider.generate_embedding(query)

# Hole alle gespeicherten Embeddings
embeddings = get_all_embeddings(limit=100)

# Dekodiere Embeddings
candidates = []
for emb in embeddings:
    vector = generator.provider.decode_embedding(emb['embedding_vector'])
    candidates.append((emb['chunk_id'], vector))

# Finde ähnlichste Chunks
similar = generator.find_similar_chunks(
    query_embedding=query_embedding,
    candidate_embeddings=candidates,
    top_k=5,
    min_similarity=0.5
)

for chunk_id, similarity in similar:
    print(f"Chunk {chunk_id}: {similarity:.3f}")
```

## Asynchrone Verarbeitung

```python
from ai.database_ai import enqueue_processing, get_next_queue_item, update_queue_status

# Story zur Verarbeitung einreihen
queue_id = enqueue_processing(
    source_type='story',
    source_id=42,
    processing_type='embed',
    priority=1
)

# Worker-Loop (separater Prozess)
while True:
    item = get_next_queue_item(processing_type='embed')
    if not item:
        break

    try:
        update_queue_status(item['id'], 'processing')

        # Verarbeite Item
        # ... (Chunking, Embedding, etc.)

        update_queue_status(item['id'], 'completed')
    except Exception as e:
        update_queue_status(item['id'], 'failed', error_message=str(e))
```

## Best Practices

1. **Immer Preprocessing vor Chunking**: Bereinige Daten zuerst
2. **Story-aware Chunking für Stories**: Respektiert Struktur
3. **Batch-Processing für Effizienz**: Nutze `batch_generate_embeddings`
4. **Ollama für On-Premise**: Wenn Datenschutz wichtig ist
5. **OpenAI für beste Qualität**: In Cloud-Umgebungen
6. **Mock für Tests**: Schnell und deterministisch

## Troubleshooting

### Ollama Connection Error
```bash
# Prüfe ob Ollama läuft
ollama list

# Starte Ollama
ollama serve
```

### OpenAI API Error
```bash
# Prüfe API Key
echo $OPENAI_API_KEY

# Test mit curl
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Import Errors
```python
# Stelle sicher dass das ai/ Verzeichnis im Python Path ist
import sys
sys.path.insert(0, '/path/to/poker')
```

## Nächste Schritte

1. **Daten importieren**: Importiere vorhandene Stories
2. **Embeddings generieren**: Laufe Pipeline über alle Daten
3. **MCP Server testen**: Teste Tools mit MCP Client
4. **Semantic Search**: Implementiere Similarity-basierte Suche
5. **AI Participant**: Nutze Embeddings für KI-Schätzungen

## Support

Bei Fragen oder Problemen siehe:
- `CLAUDE.md` für Projekt-Übersicht
- `DATABASE_SCHEMA.md` für DB-Details
- OpenAI Docs: https://platform.openai.com/docs/guides/embeddings
- Ollama Docs: https://github.com/ollama/ollama
