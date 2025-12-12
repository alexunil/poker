# Multi-stage build für Planning Poker App
FROM python:3.12-slim

WORKDIR /app

# Dependencies kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY . .

# Volume für Datenbank-Persistenz
VOLUME /app/data

# Port exposieren (Flask-SocketIO läuft auf 5000)
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# App starten
# Development: python app.py (mit Flask Development Server + SocketIO)
CMD ["python", "app.py"]

# Production (Alternative mit Gunicorn - erfordert Code-Anpassung):
# CMD ["gunicorn", "--worker-class", "gevent", "-w", "1", "-b", "0.0.0.0:5000", "--log-level", "info", "app:app"]
#
# WICHTIG: Für Gunicorn muss app.py angepasst werden:
# - socketio.run() nur in if __name__ == "__main__"
# - Für Gunicorn: app = socketio.middleware(app) oder
#   direktes WSGI-Interface verwenden
