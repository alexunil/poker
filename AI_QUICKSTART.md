# AI-Module Quickstart Guide

Schnelleinstieg für die KI-Funktionalität der Planning Poker Anwendung.

## 🚀 Schnellstart (5 Minuten)

### 1. Datenbank initialisieren

```bash
python ai/setup_ai.py --db planning_poker.db init
```

### 2. Test mit Mock-Provider

```bash
# Teste ob alles funktioniert
python ai/setup_ai.py test --provider mock

# Verarbeite alle Stories mit Mock-Embeddings
python ai/setup_ai.py process --provider mock --strategy story

# Zeige Statistiken
python ai/setup_ai.py stats
```

### 3. Beispiele ausführen

```bash
python ai/examples.py
```

## 🎯 Production Setup

### Option A: sentence-transformers (EMPFOHLEN) ⭐

**Warum empfohlen?** 100% Open Source, keine externen Services, einfachste Installation!

```bash
# 1. Installiere sentence-transformers
pip install sentence-transformers

# 2. Testen (lädt automatisch Modell beim ersten Mal, ~80 MB)
python ai/setup_ai.py test --provider sentence_transformers

# 3. Stories verarbeiten
python ai/setup_ai.py process --provider sentence_transformers --strategy story
```

**Das wars!** Keine Konfiguration, keine API Keys, keine externen Server nötig.

Siehe [LOCAL_EMBEDDINGS.md](LOCAL_EMBEDDINGS.md) für Details und Modell-Auswahl.

### Option B: Ollama (On-Premise Server)

```bash
# 1. Ollama installieren (https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Embedding-Modell herunterladen
ollama pull nomic-embed-text

# 3. Ollama starten (läuft im Hintergrund)
ollama serve

# 4. Testen
python ai/setup_ai.py test --provider ollama

# 5. Stories verarbeiten
python ai/setup_ai.py process --provider ollama --strategy story
```

### Option C: OpenAI (Cloud)

```bash
# 1. API Key generieren auf: https://platform.openai.com/api-keys

# 2. Environment Variable setzen
export OPENAI_API_KEY="sk-..."

# 3. Testen
python ai/setup_ai.py test --provider openai

# 4. Stories verarbeiten
python ai/setup_ai.py process --provider openai --strategy story
```

## 📊 Typische Use Cases

### Use Case 1: Story-Suche mit Semantik

```python
from ai.embeddings import create_generator
from ai.database_ai import get_all_embeddings
import ai.database_ai as db_ai

# Setup
generator = create_generator('openai')  # oder 'ollama'

# Suche ähnliche Stories
query = "authentication and login system"
query_emb, _ = generator.provider.generate_embedding(query)

# Hole alle Embeddings
embeddings = get_all_embeddings(limit=100)

# Finde ähnlichste
candidates = []
for emb in embeddings:
    vector = generator.provider.decode_embedding(emb['embedding_vector'])
    candidates.append((emb['chunk_id'], vector))

similar = generator.find_similar_chunks(query_emb, candidates, top_k=5)

# Zeige Ergebnisse
for chunk_id, similarity in similar:
    chunk = db_ai.get_chunk_by_id(chunk_id)
    print(f"{similarity:.3f} - {chunk['chunk_text'][:80]}")
```

### Use Case 2: Team Velocity Analytics

```python
from database import init_db, get_all_stories
from ai.mcp.tools import calculate_team_velocity, generate_estimation_report

init_db("planning_poker.db")
stories = get_all_stories()

# Velocity letzte 2 Wochen
velocity = calculate_team_velocity(stories, time_period_days=14)
print(f"Velocity: {velocity['velocity_per_day']} points/day")

# Komplett-Report
report = generate_estimation_report(stories, time_period_days=30)
print(report)
```

### Use Case 3: AI-gestützte Story-Schätzung

```python
from ai.mcp.tools import suggest_story_complexity
from database import get_all_stories

stories = get_all_stories()
completed = [s for s in stories if s['status'] == 'completed']

# Neue Story
new_story = """
Title: Implement OAuth2 Authentication
Description: Add OAuth2 support with Google, GitHub and Microsoft providers.
Include refresh token handling and proper error messages.
"""

# Hole Vorschlag
suggestion = suggest_story_complexity(new_story, completed)
print(f"Suggested: {suggestion['suggested_points']} points")
print(f"Confidence: {suggestion['confidence']}")
```

## 🔧 Verwaltungs-Kommandos

```bash
# Datenbank initialisieren
python ai/setup_ai.py init

# Alle Stories verarbeiten
python ai/setup_ai.py process --provider openai

# Statistiken anzeigen
python ai/setup_ai.py stats

# Provider testen
python ai/setup_ai.py test --provider ollama

# Alle AI-Daten löschen
python ai/setup_ai.py cleanup --yes
```

## 🎭 MCP Server

Der MCP Server ermöglicht Claude und anderen AI-Assistenten Zugriff auf Planning Poker Daten.

### Starten

```bash
# Standalone
python -m ai.mcp.server < input.jsonl > output.jsonl

# Oder in Python
from ai.mcp.server import create_server

server = create_server(db_path="planning_poker.db")
server.run_stdio()
```

### Verfügbare Tools

1. **search_stories** - Suche Stories
2. **get_story** - Story-Details
3. **get_statistics** - Statistiken
4. **get_user_activity** - User-Aktivität
5. **find_similar_stories** - Ähnliche Stories

### Beispiel MCP Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_stories",
    "arguments": {
      "query": "authentication",
      "status": "completed",
      "limit": 5
    }
  }
}
```

## 📈 Performance

| Provider | Dimension | Speed | Kosten | Use Case |
|----------|-----------|-------|--------|----------|
| **sentence-transformers** ⭐ | 384 | ~50ms | **Kostenlos** | **Production (empfohlen)** |
| Ollama (nomic) | 768 | ~200ms | Kostenlos | On-Premise Server |
| OpenAI (small) | 1536 | ~50ms | $0.02/1M tokens | Production Cloud |
| OpenAI (large) | 3072 | ~100ms | $0.13/1M tokens | High Precision |
| Mock | 384 | Instant | Kostenlos | Development/Tests |

## 🔍 Troubleshooting

### "OpenAI API Key not found"
```bash
export OPENAI_API_KEY="sk-..."
```

### "Ollama connection error"
```bash
# Prüfe ob Ollama läuft
ollama list

# Starte Ollama
ollama serve

# Ziehe Modell
ollama pull nomic-embed-text
```

### "Database not initialized"
```bash
python ai/setup_ai.py init
```

### "Import Error: No module named 'ai'"
```python
import sys
sys.path.insert(0, '/path/to/poker')
```

## 📚 Weiterführende Dokumentation

- **ai/README.md** - Vollständige API-Dokumentation
- **ai/examples.py** - Code-Beispiele für alle Features
- **CLAUDE.md** - Projekt-Übersicht
- **.env.example** - Konfigurations-Optionen

## 🎯 Nächste Schritte

1. ✅ Datenbank initialisiert
2. ✅ Provider konfiguriert
3. ✅ Stories verarbeitet
4. ⬜ MCP Server eingerichtet
5. ⬜ Semantic Search implementiert
6. ⬜ AI Participant integriert

## 💡 Tipps

- **Development**: Nutze Mock-Provider für schnelle Iteration
- **Production**: Nutze sentence-transformers (Open Source, lokal, kostenlos) ⭐
- **Mehrsprachig**: Nutze `paraphrase-multilingual-MiniLM-L12-v2` Modell
- **Performance**: Batch-Verarbeitung ist bis zu 10x schneller
- **GPU**: Automatisch genutzt falls verfügbar (cuda)
- **Server-Setup**: Nutze Ollama für zentrales Embedding-Management
- **Cloud**: OpenAI nur wenn lokale Lösung nicht möglich

## 🤝 Support

Bei Fragen oder Problemen:
1. Prüfe `ai/README.md` für detaillierte Dokumentation
2. Führe `python ai/examples.py` aus um Beispiele zu sehen
3. Teste Provider mit `python ai/setup_ai.py test`
