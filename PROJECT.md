# Scrum Planning Poker - Vollständige Projektbeschreibung

## Projektziel

Ein internes Web-Tool für agile Teams zur gemeinsamen Schätzung von User Stories mittels Planning Poker. Das Tool ermöglicht simultanes, anonymes Voting mit Fibonacci-Zahlen und unterstützt den gesamten Schätzungsprozess von der Story-Erstellung bis zur finalen Punktvergabe.

## Technologie-Stack

- **Backend**: Python mit Flask Framework
- **Datenbank**: SQLite
- **Frontend**: HTML, JavaScript, CSS mit modernem Framework (Bootstrap/Tailwind/Pico.css)
- **Real-time Updates**: WebSockets oder Server-Sent Events (SSE)
- **Deployment**: Docker & Docker Compose
- **Zielumgebung**: Internes Netzwerk, keine externe Erreichbarkeit

## Kernfunktionalität

### 1. Benutzer-Verwaltung (Session-basiert)
- **Erster Besuch**: Zentrierte, modale Box (Pop-up) fordert zur Eingabe des Namens auf
- Name wird sofort in persistentem Cookie und Backend-Session gespeichert
- Cookie-basierte Wiedererkennung für alle zukünftigen Besuche
- Keine Passwörter, keine Authentifizierung (nur internes Tool)
- Alle Teilnehmer sehen sich gegenseitig in Echtzeit

### 2. Story-Lifecycle

#### Phase 1: Story-Erstellung
- Jeder Nutzer kann eine neue Story anlegen (wenn keine aktiv ist)
- **Formular-Design**:
  - Titel: Kurzes, hervorgehobenes Eingabefeld (erforderlich)
  - Beschreibung: Großes, gut formatiertes Textfeld (optional, eventuell Markdown-Unterstützung)
  - Submit-Button: "Story starten & Schätzung freigeben"
- **Wichtig**: Nur eine Story kann gleichzeitig aktiv sein
- Solange eine Story aktiv ist, ist der Button "Neue Story anlegen" für alle ausgegraut/ausgeblendet

#### Phase 2: Voting (verdeckt)
- **Kartenwahl-Interface**:
  - Große, klickbare Buttons für Fibonacci-Werte: 0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ? (optional)
  - KEIN Dropdown oder Textfeld - nur Buttons für schnelle Auswahl
  - Gewählte Karte wird deutlich hervorgehoben (andere Farbe oder Rahmen)
  - Sofortiges visuelles Feedback nach Klick (Haken-Symbol)
  - Gewählte Zahl verschwindet nach Absenden (verdeckt bis Aufdecken)
- **Verdeckt**: Andere sehen nur, wer bereits gevoted hat, nicht die Werte
- **Teilnehmerliste mit Echtzeit-Status**:
  - Alle eingeloggten Benutzer werden angezeigt
  - Visueller Status neben jedem Namen:
    - **Wartet**: Name ohne Symbol
    - **Geschätzt**: Grünes Haken-Symbol oder Kartensymbol
  - Automatische Updates (WebSockets oder AJAX-Polling alle 3 Sekunden)
- Kein Zwang zu warten: Story-Ersteller kann jederzeit aufdecken

#### Phase 3: Aufdecken
- **Nur der Story-Ersteller** sieht den hervorgehobenen Button "Karten aufdecken!"
- **Notfall-Entsperrung**: Falls der Ersteller nicht verfügbar ist (z.B. Internet-Ausfall, dringend weg):
  - Alle anderen Teilnehmer sehen einen Button "Story entsperren"
  - Sobald **mindestens 2 Personen** auf "Entsperren" klicken, wird die Story entsperrt
  - Danach kann jeder die Karten aufdecken
  - Verhindert Blockierung durch abwesenden Ersteller
- Nach Klick: **Dramatischer Moment** - Ergebnisse werden gleichzeitig und visuell ansprechend eingeblendet
- **Easter Egg**: Kurze Animation mit einem Einhorn, das einen weisen/witzigen Spruch in einer Sprechblase zeigt
  - Nur zur Auflockerung, verschwindet nach 2-3 Sekunden
  - Sprüche können variieren (z.B. "Die Weisheit der Schätzung offenbart sich...", "Das Einhorn hat gesprochen!", etc.)
- **Ergebnis-Darstellung**:
  - Liste der Namen mit ihren geschätzten Werten
  - Visualisierung: Einfaches Balkendiagramm oder Streudiagramm der Punkteverteilung
  - Hilft, die Verteilung der Schätzungen schnell zu erfassen

#### Phase 4: Auswertung & Abschluss

**Automatische Konsens-Erkennung mit visuellem Feedback:**

- **Fall 1 - Vollständiger Konsens**: Alle haben die gleiche Zahl gewählt
  - → Große, **grüne Nachricht**: "KONSENS ERREICHT! Vorgeschlagene Punktzahl: [Wert]"
  - → Button: "Story abschließen"

- **Fall 2 - Fast-Konsens**: Nur eine Person weicht ab, und zwar nur um eine Fibonacci-Zahl
  - → Große, **grüne Nachricht**: "KONSENS ERREICHT! Vorgeschlagene Punktzahl: [Mehrheitswert]"
  - → Button: "Story abschließen"

- **Fall 3 - Divergenz**: Alle anderen Fälle
  - → Große, **orangefarbene Nachricht**: "KEIN KONSENS. Höchster Wert: [Wert]"
  - → Zwei Button-Optionen:
    - "Story mit [X] Punkten abschließen"
    - "Neu abstimmen (Start neue Runde)"
  - → Bei "Neu abstimmen": Runde 2 beginnt (gleicher Prozess)

### 3. Datenpersistenz

**Was wird gespeichert:**
- Alle Stories mit Titel, Beschreibung und Ersteller
- Finale Punktzahl jeder Story
- Alle Voting-Runden mit Teilnehmer-Namen und abgegebenen Punkten
- Zeitstempel für Erstellung und Abschluss

**Datenbank-Schema**: Siehe `DATABASE_CONCEPT.md`

## UX-Prinzipien

### Single-View-Fokus
Die Hauptseite zeigt immer genau einen von drei Zuständen:

1. **Keine aktive Story**
   - Großer Call-to-Action: "Neue Story anlegen"
   - Optional: Liste der letzten abgeschlossenen Stories

2. **Aktive Story (Voting-Phase)**
   - Story-Titel und -Beschreibung prominent
   - Kartenwahl (Fibonacci-Buttons)
   - Teilnehmerliste mit Status (wer hat gevoted?)
   - Falls Story-Ersteller: "Karten aufdecken"-Button

3. **Aufgedeckt/Ergebnis**
   - Alle Votes anzeigen (Name + Punkte)
   - Konsens-Ergebnis oder Vorschlag für Punktzahl
   - Optionen: "Story abschließen" oder "Neu abstimmen"

### Design-Prinzipien
- **Minimalismus**: Keine unnötigen Menüs oder Ablenkungen
- **Klare Statusanzeige**: Sofort erkennbar, in welcher Phase man sich befindet
- **Moderne Ästhetik**: Sauberes Design mit modernem CSS-Framework (Bootstrap/Tailwind/Pico.css)
- **Schnell**: Niedrige Ladezeiten, responsive
- **Mobile First**: Responsive Design für Tablet/Smartphone (Schätzrunden oft spontan und von verschiedenen Geräten)
- **Visuelles Feedback**: Sofortige Rückmeldung bei jeder Benutzeraktion ohne Neuladen
- **Farbcodierung**: Grün für Konsens, Orange für Diskussionsbedarf, klare visuelle Hierarchie

## Technische Architektur

### Backend-Struktur
```
poker/
├── app.py                    # Flask App, Routes, WebSocket Handler
├── database.py               # SQLite Database Layer (CRUD Operations)
├── utils.py                  # Helper Functions (get_current_user, etc.)
├── voting_logic.py           # Business Logic (Konsens-Prüfung, Fibonacci)
├── generate_admin_password.py # Admin-Passwort Hash Generator
├── templates/                # HTML-Templates (Jinja2)
│   ├── index.html            # Haupt-Single-Page
│   ├── admin_login.html      # Admin Login
│   └── admin_dashboard.html  # Admin Dashboard
├── static/                   # Static Assets
│   ├── css/
│   │   └── style.css         # Alle Styles (extrahiert aus Templates)
│   └── js/
│       └── app.js            # Client-seitiges JavaScript (WebSocket, UI)
├── .env                      # Environment Variables (SECRET_KEY, DB_PATH)
└── planning_poker.db         # SQLite Datenbank (persistent)
```

### Real-time Communication
- **Bevorzugt: Flask-SocketIO** (WebSockets) für echte Echtzeit-Updates
- **Alternativ**: AJAX-Polling alle 3 Sekunden (wenn WebSockets nicht verfügbar)
- **Wichtig**: Kein manuelles Neuladen der Seite erforderlich!
- Events:
  - `user_joined`: Neuer Teilnehmer
  - `vote_submitted`: Jemand hat gevoted (zeige ✓)
  - `unlock_requested`: Jemand möchte Story entsperren
  - `story_unlocked`: Story wurde durch 2+ Personen entsperrt
  - `cards_revealed`: Story-Ersteller deckt auf
  - `story_completed`: Story abgeschlossen
  - `new_round`: Neu abstimmen gestartet

### Docker Setup
```
poker/
├── Dockerfile           # Python + Flask
├── docker-compose.yml   # App-Service + Volume für SQLite
├── requirements.txt     # Python-Dependencies
└── .dockerignore
```

## Zukünftige Erweiterungen

- **KI-Voting**: Ein KI-Agent stimmt mit ab und begründet seine Schätzung
- **Story-Historie**: Detaillierte Ansicht vergangener Stories mit Analytics
- **Export**: Stories und Votes als CSV/JSON exportieren
- **Team-Verwaltung**: Mehrere Teams mit separaten Räumen
- **Mehr Easter Eggs**: Verschiedene Einhorn-Animationen, zusätzliche weise Sprüche, thematische Variationen

## Nicht-funktionale Anforderungen

- **Verfügbarkeit**: Nur im internen Netzwerk erreichbar
- **Sicherheit**: Keine Authentifizierung nötig (vertrauenswürdiges Netzwerk)
- **Performance**: Unterstützt bis zu ~20 simultane Nutzer pro Story
- **Browser-Kompatibilität**: Moderne Browser (Chrome, Firefox, Safari, Edge)
- **Mobile**: Responsive Design für Tablet/Smartphone-Nutzung

## Deployment-Strategie

1. Docker Image bauen
2. Container mit Volume für SQLite-Persistenz starten
3. Interner Port-Zugang oder Reverse Proxy
4. Optional: Backup-Skript für Datenbank
