# Docker-Architektur Plan für Planning Poker App

## Aktuelle Situation
- Flask-App mit Flask-SocketIO für Echtzeit-Kommunikation
- SQLite-Datenbank (`planning_poker.db`)
- Environment-Variablen in `.env`
- Dependencies: Flask 3.1.2, flask-socketio 5.5.1, python-dotenv, Werkzeug

## Benötigte Dateien

### 1. Dockerfile

```dockerfile
# Multi-stage build für kleineres Image
FROM python:3.12-slim

WORKDIR /app

# Dependencies kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY . .

# Volume für Datenbank-Persistenz
VOLUME /app/data

# Port exposieren (Flask-SocketIO läuft typisch auf 5000)
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# App starten
# Development: python app.py (mit Flask Development Server + SocketIO)
CMD ["python", "app.py"]

# Production (Alternative mit Gunicorn - erfordert Code-Anpassung):
# CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "--log-level", "info", "app:app"]
#
# WICHTIG: Für Gunicorn muss app.py angepasst werden:
# - socketio.run() nur in if __name__ == "__main__"
# - Für Gunicorn: app = socketio.middleware(app) oder
#   direktes WSGI-Interface verwenden
```

### 2. docker-compose.yml

```yaml
version: '3.8'

services:
  poker-app:
    build: .
    container_name: planning-poker
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    env_file:
      - .env
    volumes:
      # Datenbank-Persistenz
      - poker-data:/app/data
      # Für Development: Live-Reload
      # - ./:/app
    restart: unless-stopped
    networks:
      - poker-network

volumes:
  poker-data:
    driver: local

networks:
  poker-network:
    driver: bridge
```

### 3. .dockerignore

```
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Git
.git/
.gitignore

# Environment & Secrets
.env
.env.local

# Database (wird in Volume gespeichert)
*.db
*.db-journal

# IDE
.vscode/
.idea/
.claude/

# Documentation (nur README behalten)
*.md
!README.md
!README_MVP.md

# Logs
*.log
```

**Wichtig:** `.env` wird NICHT ins Image kopiert, sondern zur Runtime via `env_file` in docker-compose.yml geladen.

## Anpassungen an der App

### 4. app.py - Datenbank-Pfad konfigurierbar machen

**Location:** `app.py` Zeile 637

**Aktuell:**
```python
if __name__ == "__main__":
    # Datenbank initialisieren
    print("Initialisiere Datenbank...")
    db.init_db("planning_poker.db")
    print("Starte Flask-App...")
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
```

**Geplant:**
```python
if __name__ == "__main__":
    # Datenbank initialisieren (Pfad aus Umgebungsvariable)
    db_path = os.getenv('DB_PATH', 'planning_poker.db')
    print(f"Initialisiere Datenbank: {db_path}")
    db.init_db(db_path)
    print("Starte Flask-App...")

    # Production: Use Gunicorn instead
    # For now, keep socketio.run for development
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
```

**Wichtig:**
- Für Docker wird `DB_PATH=/app/data/planning_poker.db` in `.env` gesetzt
- Lokal läuft es weiterhin mit `planning_poker.db` im aktuellen Verzeichnis

### 5. .env.example für Docker erweitern

```bash
# Planning Poker - Docker Environment Configuration

# Admin Login Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<generate with: python generate_admin_password.py>

# Flask Secret Key (WICHTIG für Sessions!)
# Generiere mit: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<your-secret-key-here>

# Database Path (für Docker Volume)
DB_PATH=/app/data/planning_poker.db

# Flask Environment
FLASK_ENV=production

# SocketIO Configuration
SOCKETIO_ASYNC_MODE=eventlet
```

**Hinweis:** Vor dem ersten Docker-Start muss das Admin-Passwort generiert werden:
```bash
# Lokal ausführen (nicht im Container)
python generate_admin_password.py
# Hash in .env eintragen
```

### 6. requirements.txt erweitern (für Production)

**Aktuelle requirements.txt:**
```
Flask==3.1.2
flask-socketio==5.5.1
python-dotenv==1.0.1
Werkzeug==3.1.3
```

**Hinzufügen für Docker/Production:**
```
gunicorn==21.2.0
eventlet==0.33.3
```

**Finales requirements.txt:**
```
Flask==3.1.2
flask-socketio==5.5.1
python-dotenv==1.0.1
Werkzeug==3.1.3
gunicorn==21.2.0
eventlet==0.33.3
```

**Warum diese Pakete?**
- `gunicorn`: Production WSGI Server (Alternative zu Flask Development Server)
- `eventlet`: Async Worker für WebSocket-Support mit Gunicorn

### 7. Health-Check Endpoint in app.py

**Location:** `app.py` nach Zeile 459 (nach `/api/status`)

**Hinzufügen:**
```python
@app.route('/health')
def health_check():
    """Health check endpoint für Docker"""
    try:
        # Prüfe ob Datenbank erreichbar ist
        conn = sqlite3.connect(_db_path)
        conn.close()
        return jsonify({
            "status": "healthy",
            "database": "connected"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503
```

**Notwendige Imports am Anfang von app.py:**
```python
import sqlite3  # Für health check
```

**Zugriff auf _db_path:**
```python
from database import _db_path
```

**Alternative (einfacher):**
```python
@app.route('/health')
def health_check():
    """Simple health check für Docker"""
    return jsonify({"status": "healthy"}), 200
```

## Development vs Production Setup

### Development

```yaml
# docker-compose.dev.yml
services:
  poker-app:
    build: .
    volumes:
      - ./:/app
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1
    command: python app.py
```

### Production

- Gunicorn als WSGI-Server mit eventlet worker
- Umgebungsvariablen aus `.env` laden
- Volume für DB-Persistenz
- Restart-Policy
- Evtl. nginx als Reverse Proxy (später)

## Commands

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down

# Mit DB-Volumes löschen
docker-compose down -v

# Development
docker-compose -f docker-compose.dev.yml up
```

## Vorteile dieser Lösung

1. **Isolation**: App läuft in Container, unabhängig vom Host
2. **Portabilität**: Läuft überall wo Docker läuft
3. **Persistenz**: SQLite-DB in Volume gespeichert
4. **Skalierbar**: Basis für spätere Erweiterungen (nginx, Redis)
5. **Development-freundlich**: Separate Dev-Config mit Live-Reload
6. **Production-ready**: Gunicorn + eventlet für WebSocket-Support

## Implementierungsschritte (Reihenfolge)

1. **`.dockerignore` erstellen**
   - venv, __pycache__, etc. ausschließen

2. **`Dockerfile` erstellen**
   - Python 3.12-slim als Base Image
   - Dependencies installieren
   - Volume für /app/data

3. **`docker-compose.yml` erstellen**
   - Service-Definition
   - Volume-Mapping für Datenbank
   - Port 5000 exposieren

4. **`requirements.txt` erweitern**
   - gunicorn und eventlet hinzufügen

5. **`database.py` anpassen**
   - DB-Pfad aus Umgebungsvariable lesen
   - Default: `/app/data/planning_poker.db`

6. **Health-Check-Endpoint hinzufügen**
   - Route `/health` in app.py

7. **`.env` vorbereiten**
   - Admin-Passwort lokal generieren: `python generate_admin_password.py`
   - SECRET_KEY generieren
   - Alle Werte in `.env` eintragen

8. **Testen**
   - `docker-compose build`
   - `docker-compose up -d`
   - Browser: http://localhost:5000
   - Admin-Login testen: http://localhost:5000/admin/login

9. **Volume-Persistenz testen**
   - Container stoppen
   - Container wieder starten
   - Daten sollten erhalten bleiben
