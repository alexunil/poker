# Planning Poker - Deployment Guide

## Überblick

Dieses Dokument beschreibt, wie du die Planning Poker Applikation deployst:
- **Lokal**: Zwei Instanzen (Stage + Production) auf einem Server
- **Remote**: Deployment auf einem anderen Server für dein Team

## 🚀 Quick Start: Multi-Instance Setup (Stage + Production)

### 1. Umgebungsvariablen konfigurieren

Erstelle zwei `.env` Dateien basierend auf den Templates:

```bash
# Production Environment
cp .env.prod.example .env.prod

# Stage Environment
cp .env.stage.example .env.stage
```

### 2. Admin-Passwort generieren

Für beide Environments brauchst du ein Admin-Passwort:

```bash
# Generiere einen Hash für dein gewünschtes Passwort
python generate_admin_password.py
```

Das Script fragt dich nach deinem gewünschten Passwort und gibt einen Hash aus.

### 3. .env Dateien ausfüllen

Bearbeite beide `.env` Dateien:

**`.env.prod`** (Production):
```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<der-generierte-hash-aus-schritt-2>
SECRET_KEY=<generiere-mit-python -c "import secrets; print(secrets.token_hex(32))">
DB_PATH=/app/data/planning_poker.db
FLASK_ENV=production
```

**`.env.stage`** (Stage/Testing):
```bash
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<der-generierte-hash-aus-schritt-2>
SECRET_KEY=<ein-anderer-secret-key>
DB_PATH=/app/data/planning_poker.db
FLASK_ENV=development
```

**Wichtig:**
- Jede Instanz braucht einen **eigenen SECRET_KEY**!
- Du kannst das gleiche Admin-Passwort für beide verwenden, oder unterschiedliche

### 4. Docker Images bauen und starten

```bash
# Beide Instanzen bauen und im Hintergrund starten
docker-compose -f docker-compose-multi.yml up -d --build
```

### 5. Zugriff auf die Instanzen

Nach dem Start sind beide Instanzen erreichbar:

- **Production**: http://localhost:5000
- **Stage (Testing)**: http://localhost:5001

**Admin-Dashboards:**
- Production Admin: http://localhost:5000/admin
- Stage Admin: http://localhost:5001/admin

### 6. Status prüfen

```bash
# Container Status anzeigen
docker-compose -f docker-compose-multi.yml ps

# Logs anzeigen
docker-compose -f docker-compose-multi.yml logs -f

# Nur Production Logs
docker logs planning-poker-prod -f

# Nur Stage Logs
docker logs planning-poker-stage -f
```

## 📦 Deployment auf einen Remote Server

### Voraussetzungen auf dem Remote Server

1. **Docker installiert**: [Installation Guide](https://docs.docker.com/engine/install/)
2. **Docker Compose installiert**: [Installation Guide](https://docs.docker.com/compose/install/)
3. **Git** (optional, aber empfohlen)

### Option A: Deployment via Git (empfohlen)

#### 1. Repository auf Remote Server klonen

```bash
# Auf dem Remote Server
ssh user@remote-server

# Repository klonen (wenn in Git vorhanden)
git clone <dein-repo-url> /opt/planning-poker
cd /opt/planning-poker
```

#### 2. .env Dateien konfigurieren

```bash
# Auf dem Remote Server
cp .env.prod.example .env.prod
cp .env.stage.example .env.stage

# Passwort-Hash generieren
python3 generate_admin_password.py

# .env Dateien bearbeiten
nano .env.prod
nano .env.stage
```

#### 3. Starten

```bash
# Auf dem Remote Server
docker-compose -f docker-compose-multi.yml up -d --build
```

#### 4. Firewall/Ports öffnen

```bash
# Beispiel für ufw (Ubuntu)
sudo ufw allow 5000/tcp  # Production
sudo ufw allow 5001/tcp  # Stage
```

### Option B: Deployment via Dateitransfer (ohne Git)

#### 1. Projekt-Dateien packen

Auf deinem lokalen Rechner:

```bash
# Alle notwendigen Dateien packen
tar -czf planning-poker.tar.gz \
  app.py \
  database.py \
  utils.py \
  voting_logic.py \
  generate_admin_password.py \
  requirements.txt \
  Dockerfile \
  .dockerignore \
  docker-compose-multi.yml \
  .env.prod.example \
  .env.stage.example \
  templates/ \
  static/ \
  BENUTZERANLEITUNG.md
```

#### 2. Auf Remote Server übertragen

```bash
# Via SCP
scp planning-poker.tar.gz user@remote-server:/tmp/

# Auf Remote Server einloggen
ssh user@remote-server

# Entpacken
sudo mkdir -p /opt/planning-poker
sudo tar -xzf /tmp/planning-poker.tar.gz -C /opt/planning-poker
cd /opt/planning-poker
```

#### 3. Konfiguration und Start

Folge dann den Schritten aus Option A (ab Schritt 2).

### 🌐 Zugriff über Netzwerk

Nachdem die Container auf dem Remote Server laufen, können deine Kollegen zugreifen:

- **Production**: http://remote-server-ip:5000
- **Stage**: http://remote-server-ip:5001

**Beispiel:**
Wenn dein Server die IP `192.168.1.100` hat:
- Production: http://192.168.1.100:5000
- Stage: http://192.168.1.100:5001

**Mit Hostnamen/DNS:**
- Production: http://planning-poker.your-company.local:5000
- Stage: http://planning-poker-stage.your-company.local:5001

## 🔄 Updates und Wartung

### Applikation aktualisieren

#### Via Git:

```bash
cd /opt/planning-poker
git pull origin main
docker-compose -f docker-compose-multi.yml up -d --build
```

#### Via Dateitransfer:

1. Neues Archiv erstellen und übertragen (wie oben)
2. Container stoppen
3. Dateien entpacken
4. Container neu bauen und starten

```bash
cd /opt/planning-poker
docker-compose -f docker-compose-multi.yml down
# ... neue Dateien entpacken ...
docker-compose -f docker-compose-multi.yml up -d --build
```

### Container neustarten

```bash
# Beide Instanzen neustarten
docker-compose -f docker-compose-multi.yml restart

# Nur Production neustarten
docker restart planning-poker-prod

# Nur Stage neustarten
docker restart planning-poker-stage
```

### Container stoppen/starten

```bash
# Beide stoppen
docker-compose -f docker-compose-multi.yml stop

# Beide starten
docker-compose -f docker-compose-multi.yml start

# Beide stoppen und entfernen (Daten bleiben erhalten!)
docker-compose -f docker-compose-multi.yml down
```

## 💾 Datenbank-Backup

### Backup erstellen

```bash
# Production Datenbank sichern
docker cp planning-poker-prod:/app/data/planning_poker.db ./backup-prod-$(date +%Y%m%d).db

# Stage Datenbank sichern
docker cp planning-poker-stage:/app/data/planning_poker.db ./backup-stage-$(date +%Y%m%d).db
```

### Backup wiederherstellen

```bash
# Container stoppen
docker stop planning-poker-prod

# Backup zurückspielen
docker cp ./backup-prod-20250101.db planning-poker-prod:/app/data/planning_poker.db

# Container starten
docker start planning-poker-prod
```

### Automatisches Backup (Cronjob)

Erstelle ein Backup-Script `/opt/planning-poker/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/planning-poker/backups"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# Production Backup
docker cp planning-poker-prod:/app/data/planning_poker.db \
  $BACKUP_DIR/prod-$DATE.db

# Stage Backup
docker cp planning-poker-stage:/app/data/planning_poker.db \
  $BACKUP_DIR/stage-$DATE.db

# Alte Backups löschen (älter als 30 Tage)
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

Mache es ausführbar und füge zu Crontab hinzu:

```bash
chmod +x /opt/planning-poker/backup.sh

# Täglich um 2 Uhr nachts
crontab -e
# Füge hinzu:
0 2 * * * /opt/planning-poker/backup.sh
```

## 🔍 Monitoring und Logs

### Logs anzeigen

```bash
# Beide Instanzen (live)
docker-compose -f docker-compose-multi.yml logs -f

# Nur Production
docker logs planning-poker-prod -f

# Nur Stage
docker logs planning-poker-stage -f

# Letzte 100 Zeilen
docker logs planning-poker-prod --tail 100
```

### Container-Status

```bash
# Übersicht
docker-compose -f docker-compose-multi.yml ps

# Detaillierte Infos
docker inspect planning-poker-prod
docker inspect planning-poker-stage
```

### Ressourcen-Nutzung

```bash
# CPU und RAM
docker stats planning-poker-prod planning-poker-stage
```

## 🛡️ Sicherheit

### Empfehlungen für Production

1. **Reverse Proxy verwenden** (nginx/Caddy)
   - HTTPS einrichten
   - Domain statt IP verwenden

2. **Firewall konfigurieren**
   - Nur notwendige Ports öffnen
   - Zugriff auf Admin-Dashboard beschränken

3. **Regelmäßige Backups**
   - Automatisiertes Backup (siehe oben)
   - Backups an sicheren Ort speichern

4. **Updates**
   - Regelmäßig Docker Images aktualisieren
   - Python-Dependencies aktuell halten

### Beispiel nginx Reverse Proxy

`/etc/nginx/sites-available/planning-poker`:

```nginx
server {
    listen 80;
    server_name planning-poker.your-company.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name planning-poker-stage.your-company.com;

    location / {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Beispiel HAProxy Reverse Proxy

**WICHTIG für WebSocket:** HAProxy benötigt erhöhte Timeouts für WebSocket-Verbindungen!

`/etc/haproxy/haproxy.cfg`:

```haproxy
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000

# Frontend für Production
frontend planning_poker_prod
    bind *:80
    # Optional: bind *:443 ssl crt /path/to/cert.pem

    acl is_prod hdr(host) -i planning-poker.your-company.com
    use_backend poker_prod_backend if is_prod

# Frontend für Stage
frontend planning_poker_stage
    bind *:8080
    # Optional: andere Domain/Port

    acl is_stage hdr(host) -i planning-poker-stage.your-company.com
    use_backend poker_stage_backend if is_stage

# Backend für Production - MIT WEBSOCKET TIMEOUTS!
backend poker_prod_backend
    mode http
    balance roundrobin

    # WICHTIG: WebSocket Timeouts erhöhen!
    timeout server 3600s    # 1 Stunde
    timeout tunnel 3600s    # 1 Stunde für WebSocket
    timeout client 3600s    # 1 Stunde

    # WebSocket Header
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Forwarded-Proto https if { ssl_fc }

    # Server
    server poker_prod 127.0.0.1:5000 check

# Backend für Stage - MIT WEBSOCKET TIMEOUTS!
backend poker_stage_backend
    mode http
    balance roundrobin

    # WICHTIG: WebSocket Timeouts erhöhen!
    timeout server 3600s    # 1 Stunde
    timeout tunnel 3600s    # 1 Stunde für WebSocket
    timeout client 3600s    # 1 Stunde

    # WebSocket Header
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Forwarded-Proto https if { ssl_fc }

    # Server
    server poker_stage 127.0.0.1:5001 check
```

**Erklärung der Timeouts:**

- **`timeout client 3600s`**: Client → HAProxy (Browser bleibt verbunden)
- **`timeout server 3600s`**: HAProxy → Backend Server (Flask-App)
- **`timeout tunnel 3600s`**: Spezifisch für WebSocket/Tunnel-Verbindungen

**Warum 1 Stunde (3600s)?**
- Planning Poker Sessions können länger dauern (Diskussionen, Pausen)
- WebSocket-Verbindungen sind idle während Diskussionen
- Flask-SocketIO sendet Heartbeats, aber bei langen Pausen reicht das nicht

**Alternative: Kürzere Timeouts mit Heartbeats**
Wenn du kürzere Timeouts bevorzugst (z.B. 600s = 10 Minuten), stelle sicher dass Flask-SocketIO Ping-Pong aktiviert ist:

In `app.py` ist dies bereits konfiguriert:
```python
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,      # Server wartet 60s auf Pong
    ping_interval=25      # Server sendet alle 25s ein Ping
)
```

Mit diesen Werten sollten auch 600s Timeout ausreichen.

**HAProxy Konfiguration testen:**

```bash
# Konfiguration prüfen
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# HAProxy neustarten
sudo systemctl restart haproxy

# Status prüfen
sudo systemctl status haproxy

# Logs live anzeigen
sudo tail -f /var/log/haproxy.log
```

**Häufiger Fehler ohne erhöhte Timeouts:**

Ohne die erhöhten Timeouts siehst du im Browser-Developer-Tools (Console):
```
WebSocket connection to 'ws://...' failed: Connection closed before receiving handshake response
```

Oder die WebSocket-Verbindung bricht nach 50 Sekunden ab (Standard-Timeout).

## 🐛 Troubleshooting

### Container startet nicht

```bash
# Logs prüfen
docker logs planning-poker-prod

# Häufige Probleme:
# - .env Datei fehlt oder fehlerhaft
# - SECRET_KEY nicht gesetzt
# - Port bereits belegt
```

### Port bereits belegt

```bash
# Prüfen welcher Prozess den Port nutzt
sudo lsof -i :5000
sudo lsof -i :5001

# Anderen Port verwenden (docker-compose-multi.yml bearbeiten)
```

### Datenbank-Fehler

```bash
# Container stoppen
docker stop planning-poker-prod

# Volume prüfen
docker volume inspect poker-prod-data

# Backup zurückspielen (siehe oben)
```

### WebSocket-Verbindung schlägt fehl

**Symptome:**
- WebSocket-Verbindung bricht nach ~50 Sekunden ab
- Browser-Console zeigt: `WebSocket connection closed`
- Live-Updates funktionieren nicht (keine Echtzeit-Synchronisation)

**Diagnose:**

```bash
# Browser Developer Tools öffnen (F12) → Console Tab
# Suche nach Fehlern wie:
# "WebSocket connection to 'ws://...' failed"
# "Connection closed before receiving handshake response"
```

**Lösungen:**

1. **HAProxy Timeouts zu niedrig** (häufigstes Problem!)
   ```bash
   # Prüfe HAProxy Konfiguration
   grep -A 5 "timeout" /etc/haproxy/haproxy.cfg

   # Stelle sicher dass im Backend:
   # timeout server 3600s
   # timeout tunnel 3600s
   # timeout client 3600s

   # Nach Änderung neu laden
   sudo systemctl reload haproxy
   ```

2. **nginx: WebSocket-Upgrade Header fehlen**
   ```nginx
   # In nginx Config prüfen:
   proxy_http_version 1.1;
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   ```

3. **Firewall blockiert WebSocket**
   ```bash
   # Prüfe ob Port offen ist
   sudo ufw status
   sudo iptables -L -n

   # Port öffnen
   sudo ufw allow 5000/tcp
   ```

4. **Flask-SocketIO läuft nicht**
   ```bash
   # Prüfe Container-Logs
   docker logs planning-poker-prod | grep -i websocket
   docker logs planning-poker-prod | grep -i socket.io

   # Sollte zeigen:
   # "WebSocket transport"
   # "Socket.IO is running in eventlet mode"
   ```

5. **Browser-Kompatibilität**
   - Verwende modernen Browser (Chrome, Firefox, Safari, Edge)
   - Deaktiviere Browser-Erweiterungen die WebSocket blockieren könnten
   - Teste in Incognito-Modus

**Test-URL für WebSocket:**

```bash
# Von einem Client-Rechner testen
curl -i -N -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://your-server:5000/socket.io/

# Erwartete Antwort: HTTP 101 Switching Protocols
```

## 📋 Cheat Sheet

```bash
# --- LOKALES SETUP ---
# Beide Instanzen starten
docker-compose -f docker-compose-multi.yml up -d

# Beide Instanzen stoppen
docker-compose -f docker-compose-multi.yml down

# Logs live anzeigen
docker-compose -f docker-compose-multi.yml logs -f

# --- REMOTE DEPLOYMENT ---
# Dateien übertragen
scp planning-poker.tar.gz user@server:/tmp/

# Auf Server starten
ssh user@server
cd /opt/planning-poker
docker-compose -f docker-compose-multi.yml up -d --build

# --- WARTUNG ---
# Backup erstellen
docker cp planning-poker-prod:/app/data/planning_poker.db ./backup.db

# Update durchführen
git pull && docker-compose -f docker-compose-multi.yml up -d --build

# --- MONITORING ---
# Status prüfen
docker ps
docker stats

# Logs der letzten 100 Zeilen
docker logs planning-poker-prod --tail 100
```

## 🎯 Nächste Schritte

Nach dem Deployment:

1. **Admin-Zugang testen**: http://your-server:5000/admin
2. **Erste Story erstellen**: Teste die Funktionalität
3. **Team einladen**: Teile die URL mit deinen Kollegen
4. **Anleitung zeigen**: http://your-server:5000/anleitung

## 📞 Support

Bei Problemen:
1. Logs prüfen (siehe oben)
2. OPERATIONS.md lesen für technische Details
3. BENUTZERANLEITUNG.md für User-Fragen
