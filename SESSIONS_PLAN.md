# Plan: Permanente Sessions (Feature 9)

## Übersicht

Sessions sollen **niemals** ablaufen, sodass User auch nach Wochen/Monaten automatisch wieder erkannt werden, ohne ihren Namen erneut eingeben zu müssen.

**Anforderung (feature9.md):**
> "Es soll keinen Timeout von sessions geben! Auch wenn ich nach zwei Wochen wieder reinkomme möchte ich nicht meinen Namen angeben müssen."

---

## Aktuelles Verhalten

### Session-Konfiguration

**Location:** `app.py` Zeile 23

```python
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
```

**Problem:** Sessions laufen nach 30 Minuten ab!

### Wo session.permanent gesetzt wird

1. **User-Registrierung** (`app.py:212`)
   ```python
   session.permanent = True  # Session bleibt für 30 Minuten erhalten
   ```

2. **Admin-Login** (`app.py:661`)
   ```python
   session.permanent = True
   ```

3. **Admin-Dashboard** (`app.py:684`)
   ```python
   session.permanent = True  # Session läuft ab nach PERMANENT_SESSION_LIFETIME
   ```

**Aktuelles Verhalten:**
- User registriert sich → Session wird erstellt
- Nach 30 Minuten Inaktivität → Session läuft ab
- User muss Namen erneut eingeben

---

## Gewünschtes Verhalten

**Sessions sollen praktisch für immer gültig bleiben:**
- User registriert sich einmal
- Cookie bleibt für sehr lange Zeit gültig (z.B. 10 Jahre)
- Auch nach Wochen/Monaten wird User automatisch erkannt
- Nur bei explizitem Cookie-Löschen muss Name neu eingegeben werden

---

## Lösung

### Option 1: Sehr lange Session-Lifetime (Empfohlen)

**Vorteile:**
- Einfache Implementierung
- Nutzt Flask's Session-Mechanismus
- Cookie-basiert, funktioniert browser-übergreifend
- Sicher (signed cookies)

**Implementierung:**
```python
# Session-Lifetime auf 10 Jahre setzen
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=3650)
```

**Warum 10 Jahre?**
- Praktisch "für immer" im Kontext einer internen App
- Browser-Cookies können theoretisch unbegrenzt leben
- Realistisch werden Cookies vorher gelöscht (Browser-Reset, neue Installation)

### Option 2: Unendliche Lifetime (Technisch problematisch)

**Problem:** Flask/Werkzeug unterstützt keine "unendlichen" Sessions direkt.

**Workaround:**
```python
from datetime import datetime

# Sehr weit in der Zukunft (Jahr 2099)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=365 * 75)
```

### Option 3: Keine Session-Expiration (Nicht empfohlen)

**Theoretisch:** `session.permanent = False` → Session lebt bis Browser geschlossen wird

**Problem:** Bei Browser-Neustart gehen Sessions verloren → nicht erwünscht!

---

## Implementierungsschritte

### 1. Session-Lifetime anpassen

**Location:** `app.py` Zeile 23

**Aktuell:**
```python
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
```

**Geplant:**
```python
# Sessions bleiben für 10 Jahre gültig (praktisch permanent)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=3650)
```

**Alternative (aus .env konfigurierbar):**
```python
# Session-Lifetime in Tagen (default: 10 Jahre)
session_lifetime_days = int(os.getenv("SESSION_LIFETIME_DAYS", "3650"))
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=session_lifetime_days)
```

### 2. Kommentare aktualisieren

**Locations:**
- `app.py:212` - Bei set_name()
- `app.py:661` - Bei admin_login()
- `app.py:684` - Bei admin_dashboard()

**Aktuell:**
```python
session.permanent = True  # Session bleibt für 30 Minuten erhalten
```

**Geplant:**
```python
session.permanent = True  # Session bleibt für sehr lange Zeit erhalten (10 Jahre)
```

### 3. Admin-Session-Lifetime (Optional unterschiedlich)

**Überlegung:** Admin-Sessions sollten evtl. DOCH ablaufen aus Sicherheitsgründen?

**Option A: Admin auch permanent**
- Einfach, konsistent
- Akzeptabel für interne Tools ohne öffentlichen Zugang

**Option B: Admin hat kürzere Lifetime**
```python
# Admin-spezifische Session-Konfiguration
ADMIN_SESSION_LIFETIME = timedelta(hours=24)  # 1 Tag

# Bei admin_login:
session.permanent = True
session.permanent_session_lifetime = ADMIN_SESSION_LIFETIME  # Flask unterstützt das NICHT direkt!
```

**Problem:** Flask unterstützt keine per-Session Lifetime-Konfiguration!

**Lösung:** Eigenes Feld in Session + manuelle Prüfung
```python
# Bei admin_login:
session['is_admin'] = True
session['admin_login_time'] = datetime.now().isoformat()

# Bei admin_required decorator:
if 'admin_login_time' in session:
    login_time = datetime.fromisoformat(session['admin_login_time'])
    if datetime.now() - login_time > timedelta(hours=24):
        # Session abgelaufen
        session.pop('is_admin', None)
        return redirect(url_for('admin_login'))
```

**Empfehlung für MVP:** Admin-Sessions auch permanent lassen (einfacher)

---

## .env.example Erweitern (Optional)

**Location:** `.env.example` nach Zeile 18

**Hinzufügen:**
```bash
# Session Lifetime (in Tagen)
# Default: 3650 Tage (10 Jahre) - praktisch permanent
# Setze auf kleineren Wert für kürzere Sessions
SESSION_LIFETIME_DAYS=3650
```

---

## Sicherheitsüberlegungen

### Ist das sicher?

**Kontext:** Interne Tool ohne öffentlichen Zugang

**Argumente für permanente Sessions:**
1. ✅ **Kein öffentlicher Zugang** - Tool läuft nur im internen Netzwerk
2. ✅ **Keine sensiblen Daten** - Planning Poker schätzt nur Story Points
3. ✅ **Keine Authentifizierung nötig** - per Design (siehe idee.md)
4. ✅ **Convenience wichtiger als Security** - User-Experience steht im Vordergrund
5. ✅ **Signed Cookies** - Flask signiert Session-Cookies, können nicht gefälscht werden

**Potenzielle Risiken:**
- ⚠️ **Shared Computers** - Jemand könnte fremde Session nutzen
  - **Mitigation:** Interne Team-Tool, vertrauenswürdige Umgebung
- ⚠️ **Cookie-Theft** - Bei XSS-Attacke könnten Cookies gestohlen werden
  - **Mitigation:** Flask setzt HttpOnly-Flag, moderne Browser schützen

**Admin-Sessions:**
- ⚠️ **Admin-Zugriff bleibt offen** - Admin kann für immer eingeloggt bleiben
  - **Mitigation:** Admin-Dashboard ist read-only (keine destruktiven Aktionen)
  - **Alternative:** Separate kürzere Lifetime für Admin (siehe oben)

### Best Practices

**Aktuell gut:**
- ✅ Cookies sind signiert (SECRET_KEY)
- ✅ HttpOnly flag (Flask default)
- ✅ SameSite protection (Flask 3.x default)

**Optional zusätzlich:**
```python
app.config.update(
    SESSION_COOKIE_SECURE=True,  # Nur über HTTPS (wenn verfügbar)
    SESSION_COOKIE_HTTPONLY=True,  # Kein JavaScript-Zugriff
    SESSION_COOKIE_SAMESITE='Lax'  # CSRF-Schutz
)
```

---

## Testing-Plan

### 1. User-Session-Persistenz

**Test:**
1. App starten
2. Namen eingeben (z.B. "Alice")
3. Browser NICHT schließen, aber 35+ Minuten warten
4. Seite neu laden (F5)
5. **Erwartung:** Alice ist immer noch eingeloggt (keine Namenseingabe nötig)

**Vor der Änderung:** Session läuft nach 30 Minuten ab → muss Namen neu eingeben
**Nach der Änderung:** Session bleibt bestehen → automatisch eingeloggt

### 2. Browser-Neustart

**Test:**
1. App starten
2. Namen eingeben (z.B. "Bob")
3. Browser komplett schließen
4. Browser neu öffnen, zur App navigieren
5. **Erwartung:** Bob ist immer noch eingeloggt

**Funktioniert nur wenn:** `session.permanent = True` gesetzt ist (bereits der Fall)

### 3. Cookie-Inspektion

**Browser DevTools → Application → Cookies**

**Vorher:**
- `session` Cookie
- Expires: In 30 Minuten

**Nachher:**
- `session` Cookie
- Expires: In ~10 Jahren (Jahr 2034+)

### 4. Admin-Session

**Test:**
1. Als Admin einloggen
2. 25+ Minuten warten
3. Admin-Dashboard neu laden
4. **Erwartung:** Immer noch eingeloggt

---

## Rollback-Plan

Falls Probleme auftreten:

**Schneller Rollback:**
```python
# In app.py Zeile 23 zurückändern:
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
```

**Server neu starten** → alte Session-Lifetime aktiv

---

## Dokumentation aktualisieren

### OPERATIONS.md

**Location:** Nach Zeile 209 (Session-Beschreibung)

**Hinzufügen:**
```markdown
### Session-Verhalten

- **User-Sessions:** Bleiben für 10 Jahre gültig (praktisch permanent)
- **Cookie-basiert:** Nutzer werden über Browser-Cookie wiedererkannt
- **Keine automatische Abmeldung:** Sessions laufen nicht ab
- **Manuelles Löschen:** User kann sich "abmelden" durch Cookie-Löschen im Browser
```

### README_MVP.md

**Location:** Nach Zeile 107 (Hinweise-Sektion)

**Ergänzen:**
```markdown
- Sessions bleiben praktisch für immer gültig (10 Jahre)
- Einmal registriert, wirst du automatisch wiedererkannt
- Auch nach Wochen ohne Nutzung kein erneuter Login nötig
```

---

## Alternative: Session in Datenbank speichern (Für Zukunft)

**Aktuell:** Sessions sind cookie-basiert (clientseitig gespeichert)

**Alternative:** Flask-Session Extension mit Server-Side Storage

**Vorteile:**
- Mehr Kontrolle über Sessions
- Kann Sessions serverseitig invalidieren
- Bessere Skalierbarkeit bei vielen Usern

**Implementierung (später):**
```python
from flask_session import Session

app.config["SESSION_TYPE"] = "sqlalchemy"
app.config["SESSION_SQLALCHEMY"] = db
Session(app)
```

**Für Feature 9:** NICHT nötig, Cookie-basiert funktioniert perfekt

---

## Zusammenfassung

### Minimale Änderung (Empfohlen)

**Datei:** `app.py`

**Zeile 23 ändern:**
```python
# Vorher:
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

# Nachher:
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=3650)  # 10 Jahre
```

**3 Kommentare aktualisieren:** Zeile 212, 661, 684

**Fertig!** ✅

### Erweiterte Änderung (Optional)

+ `.env.example` erweitern (SESSION_LIFETIME_DAYS)
+ `app.py` konfigurierbar machen (aus .env lesen)
+ Dokumentation aktualisieren

---

## Checklist für Implementierung

- [ ] `app.py:23` - Session-Lifetime auf 10 Jahre setzen
- [ ] `app.py:212` - Kommentar aktualisieren
- [ ] `app.py:661` - Kommentar aktualisieren
- [ ] `app.py:684` - Kommentar aktualisieren
- [ ] Testing: 35+ Minuten warten, Session sollte bestehen bleiben
- [ ] Testing: Browser neu starten, Session sollte bestehen bleiben
- [ ] (Optional) `.env.example` erweitern
- [ ] (Optional) `OPERATIONS.md` aktualisieren
- [ ] (Optional) `README_MVP.md` aktualisieren
