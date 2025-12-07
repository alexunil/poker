# Operations-Anleitung - Planning Poker

## Überblick

Diese Anleitung beschreibt die Installation, den Betrieb und die Datenverwaltung der Planning Poker Webanwendung.

---

## System-Anforderungen

- **Python**: Version 3.8 oder höher
- **Betriebssystem**: Linux, macOS oder Windows
- **RAM**: Mindestens 512 MB (empfohlen: 1 GB)
- **Festplattenspeicher**: 100 MB

---

## Installation auf einem neuen Server

### 1. Repository klonen / Dateien übertragen

```bash
# Option A: Mit Git (falls Repository vorhanden)
git clone <repository-url> /opt/planning-poker
cd /opt/planning-poker

# Option B: Dateien manuell übertragen
scp -r ./poker/* user@server:/opt/planning-poker/
ssh user@server
cd /opt/planning-poker
```

### 2. Python-Umgebung einrichten

```bash
# Python-Version prüfen
python3 --version

# Virtual Environment erstellen
python3 -m venv venv

# Virtual Environment aktivieren
# Auf Linux/macOS:
source venv/bin/activate
# Auf Windows:
# venv\Scripts\activate
```

### 3. Abhängigkeiten installieren

```bash
# Dependencies aus requirements.txt installieren
pip install -r requirements.txt
```

Benötigte Pakete:
- Flask 3.1.2
- flask-socketio 5.5.1

### 4. Firewall konfigurieren

```bash
# Port 5000 für die Applikation öffnen
# Beispiel für UFW (Ubuntu/Debian):
sudo ufw allow 5000/tcp

# Beispiel für firewalld (CentOS/RHEL):
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

---

## Anwendung starten

### Manueller Start (Development)

```bash
# Virtual Environment aktivieren
source venv/bin/activate

# Applikation starten
python app.py
```

Die Anwendung ist dann erreichbar unter:
- Lokal: `http://localhost:5000`
- Netzwerk: `http://<server-ip>:5000`

### Start mit nohup (Background-Prozess)

```bash
# Im Hintergrund starten, Log-Ausgabe in datei
nohup python app.py > planning-poker.log 2>&1 &

# Prozess-ID speichern
echo $! > planning-poker.pid

# Logs anzeigen
tail -f planning-poker.log
```

### Systemd Service (Production-Setup)

Erstelle eine Service-Datei: `/etc/systemd/system/planning-poker.service`

```ini
[Unit]
Description=Planning Poker Web Application
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/planning-poker
Environment="PATH=/opt/planning-poker/venv/bin"
ExecStart=/opt/planning-poker/venv/bin/python /opt/planning-poker/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Service verwalten:

```bash
# Service aktivieren und starten
sudo systemctl enable planning-poker
sudo systemctl start planning-poker

# Status prüfen
sudo systemctl status planning-poker

# Logs anzeigen
sudo journalctl -u planning-poker -f

# Neustarten
sudo systemctl restart planning-poker

# Stoppen
sudo systemctl stop planning-poker
```

---

## Anwendung stoppen

### Manueller Stop

```bash
# Prozess finden
ps aux | grep app.py

# Prozess beenden (PID ersetzen)
kill <PID>

# Oder mit gespeicherter PID-Datei
kill $(cat planning-poker.pid)
```

### Mit Systemd

```bash
sudo systemctl stop planning-poker
```

---

## Datenspeicherung

### ✅ SQLite-Datenbank (Persistent)

Die Anwendung verwendet SQLite für persistente Datenspeicherung. Alle Daten bleiben bei Neustart erhalten.

**Datenbank-Datei:** `planning_poker.db` (im Projektverzeichnis)

### Was wird persistent gespeichert:

Die Datenbank enthält folgende Tabellen (siehe `database.py`):

1. **users** - Alle registrierten Teilnehmer
   - Name, Session-ID, Spectator-Status
   - Erstellt/Zuletzt gesehen Timestamps

2. **stories** - Alle Stories (pending, voting, revealed, completed)
   - Titel, Beschreibung, Ersteller
   - Status, Runde, finale Punktzahl
   - Auto-Start Flag, Unlock-Status

3. **votes** - Alle Abstimmungen
   - Story-ID, User-Name, Punktzahl, Runde
   - Zeitstempel jeder Abstimmung

4. **unlock_requests** - Notfall-Entsperrungen
   - Wer hat Entsperrung angefordert
   - Für welche Story

5. **events** - Event-Log (persistent)
   - Nachricht, Event-Typ (join, vote, reveal, etc.)
   - Zeitstempel jedes Events
   - Wird bei Neustart beibehalten

6. **schema_version** - Datenbank-Migrationen
   - Versionierung für Schema-Updates

### Datenbank-Backup

```bash
# Backup erstellen
cp planning_poker.db planning_poker.db.backup

# Mit Timestamp
cp planning_poker.db "planning_poker_$(date +%Y%m%d_%H%M%S).db"

# Restore
cp planning_poker.db.backup planning_poker.db
```

### Datenbank zurücksetzen

```bash
# Anwendung stoppen
sudo systemctl stop planning-poker

# Datenbank löschen
rm planning_poker.db

# Anwendung starten (erstellt neue leere DB)
sudo systemctl start planning-poker
```

---

## Monitoring und Logs

### Logs prüfen

**Bei Systemd-Service:**
```bash
sudo journalctl -u planning-poker -f
```

**Bei nohup/manuellem Start:**
```bash
tail -f planning-poker.log
```

### Wichtige Log-Ereignisse

- Server-Start: `Running on http://0.0.0.0:5000`
- WebSocket-Verbindungen
- Fehler bei Vote-Submissions
- Story-Erstellungen

### Anwendungsstatus prüfen

```bash
# HTTP-Endpunkt testen
curl http://localhost:5000

# API-Status-Endpunkt (wenn verfügbar)
curl http://localhost:5000/api/status

# Prozess prüfen
ps aux | grep app.py
```

---

## Reverse Proxy Setup (Optional)

Für produktiven Einsatz mit Nginx:

### Nginx-Konfiguration

```nginx
server {
    listen 80;
    server_name planning-poker.example.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket Support
    location /socket.io {
        proxy_pass http://localhost:5000/socket.io;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Troubleshooting

### Anwendung startet nicht

**Problem:** `Address already in use`

```bash
# Port 5000 freigeben
lsof -ti:5000 | xargs kill -9
```

**Problem:** `ModuleNotFoundError: No module named 'flask'`

```bash
# Virtual Environment aktivieren
source venv/bin/activate
# Dependencies neu installieren
pip install -r requirements.txt
```

### Verbindungsprobleme

**WebSocket funktioniert nicht:**
- Firewall-Regeln prüfen
- Browser-Console auf Fehler prüfen
- Nginx WebSocket-Konfiguration prüfen (falls verwendet)

**Cookies werden nicht gesetzt:**
- HTTPS vs HTTP prüfen
- Browser-Privacy-Einstellungen
- Session-Secret in `app.py` (wird automatisch generiert)

### Performance-Probleme

- RAM-Nutzung prüfen: `free -h`
- CPU-Last prüfen: `top` oder `htop`
- Anzahl gleichzeitiger Verbindungen limitieren

---

## Wartung

### Updates einspielen

```bash
# Anwendung stoppen
sudo systemctl stop planning-poker

# Code aktualisieren
cd /opt/planning-poker
git pull  # oder Dateien manuell kopieren

# Dependencies aktualisieren
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Anwendung starten
sudo systemctl start planning-poker
```

### Bereinigung

```bash
# Alte Log-Dateien entfernen
find /opt/planning-poker -name "*.log" -mtime +30 -delete

# Python-Cache löschen
find /opt/planning-poker -type d -name __pycache__ -exec rm -r {} +
```

---

## Sicherheitshinweise

### Aktuelle Sicherheitslücken (MVP)

1. **Keine Authentifizierung:** Jeder kann sich als beliebiger User ausgeben
2. **Kein HTTPS:** Unverschlüsselte Übertragung
3. **Keine Rate-Limiting:** Anfällig für Missbrauch
4. **CORS offen:** `cors_allowed_origins="*"` (Zeile 12 in app.py)

### Empfohlene Maßnahmen für Produktion

- HTTPS mit Let's Encrypt einrichten
- Rate Limiting implementieren
- CORS auf bekannte Domains beschränken
- Input-Validierung verstärken
- Session-Timeout implementieren

---

## Kontakt und Support

Bei Problemen siehe:
- `README_MVP.md` für Funktionsbeschreibung
- `BENUTZERANLEITUNG.md` für Anwenderdokumentation
- `PROJECT.md` für technische Details
- GitHub Issues: https://github.com/anthropics/claude-code/issues

---

## Zusammenfassung - Schnellstart

```bash
# 1. Projekt-Verzeichnis erstellen
cd /opt/planning-poker

# 2. Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Starten
python app.py

# 5. Admin-Passwort generieren (einmalig)
python generate_admin_password.py
# Hash in .env eintragen (siehe .env.example)

# 6. Browser öffnen
# http://localhost:5000
```

**✅ Daten werden persistent in SQLite gespeichert** (`planning_poker.db`)
