# Plan: Spielfläche mit fester Größe und Empty State

## Übersicht

Die Spielfläche (`.game-table`) soll immer sichtbar sein mit konstanter Größe. Wenn keine Story aktiv ist, soll dort "No story to estimate, yet." angezeigt werden.

**Datei:** `/home/alg/poker/templates/index.html`

---

## Problem-Analyse

### Aktuelles Verhalten

**HTML-Struktur (Zeile 416-505):**
```html
<!-- SPIELTISCH - Aktive Story (Voting oder Revealed) -->
{% if story %}
<div class="game-table">
    <h3>🎯 {{ story.title }} <small>(Runde {{ story.round }})</small></h3>
    <!-- Story-Details, Voting-Buttons, etc. -->
</div>
{% endif %}
```

**Probleme:**
1. ❌ `.game-table` wird nur gerendert wenn `story` existiert
2. ❌ Wenn keine Story → Spielfläche ist komplett leer
3. ❌ Layout "springt" wenn Story erstellt/abgeschlossen wird
4. ❌ Keine visuelle Orientierung für neue User

**CSS (Zeile 168-180):**
```css
.game-table {
    background: var(--card-background-color);
    border: 2px solid var(--primary);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
```

- ✅ Gutes Styling vorhanden
- ❌ Keine `min-height` → Größe variiert stark

---

## Geplante Lösung

### Ziel
1. ✅ `.game-table` ist **immer** sichtbar
2. ✅ Feste Mindesthöhe (`min-height`) für konstante Größe
3. ✅ Empty State: "No story to estimate, yet." wenn keine aktive Story
4. ✅ Smooth Layout ohne "Springen"

---

## Implementierung

### 1. CSS erweitern

**Location:** `templates/index.html` Zeile 168-180

**VORHER:**
```css
.game-table {
    background: var(--card-background-color);
    border: 2px solid var(--primary);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
```

**NACHHER:**
```css
.game-table {
    background: var(--card-background-color);
    border: 2px solid var(--primary);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    min-height: 400px; /* Konstante Mindesthöhe */
    position: relative; /* Für zentriertes Empty State */
}
```

**Änderungen:**
- `min-height: 400px` - Spielfläche hat immer mindestens 400px Höhe
- `position: relative` - Für Zentrierung des Empty States

---

### 2. Empty State CSS hinzufügen

**Location:** Nach `.game-table` Styles (nach Zeile 180)

**Neues CSS:**
```css
/* Empty State für leere Spielfläche */
.game-table-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 350px;
    text-align: center;
}

.game-table-empty-content {
    color: var(--muted-color);
}

.game-table-empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
    opacity: 0.5;
}

.game-table-empty-text {
    font-size: 1.2rem;
    font-style: italic;
}

.game-table-empty-hint {
    font-size: 0.9rem;
    margin-top: 0.5rem;
    opacity: 0.7;
}
```

**Features:**
- Flexbox-Zentrierung (vertikal + horizontal)
- Gedämpfte Farben für "leeren" Zustand
- Großes Icon (🃏 oder 🎯)
- Hint-Text für User-Guidance

---

### 3. HTML-Struktur umbauen

**Location:** `templates/index.html` Zeile 416-505

**VORHER:**
```html
<!-- SPIELTISCH - Aktive Story (Voting oder Revealed) -->
{% if story %}
<div class="game-table">
    <h3>🎯 {{ story.title }} <small>(Runde {{ story.round }})</small></h3>
    <!-- Story Content -->
</div>
{% endif %}
```

**NACHHER:**
```html
<!-- SPIELTISCH - Immer sichtbar -->
<div class="game-table">
    {% if story %}
        <!-- Aktive Story: Voting oder Revealed -->
        <h3>🎯 {{ story.title }} <small>(Runde {{ story.round }})</small></h3>
        {% if story.description %}
        <p style="margin: 0.5rem 0 1rem 0; font-size: 0.9rem;">{{ story.description }}</p>
        {% endif %}
        <div class="story-meta" style="margin-bottom: 1rem;">Erstellt von: {{ story.creator }}</div>

        {% if story.status == 'voting' %}
            <!-- Voting Phase -->
            <h4>Deine Schätzung</h4>
            <form method="POST" action="/vote">
                <div class="card-container">
                    {% for num in fibonacci %}
                    <button type="submit" name="points" value="{{ num }}" class="poker-card">
                        {{ num }}
                    </button>
                    {% endfor %}
                </div>
            </form>

            <h4 style="margin-top: 1rem;">Gelegte Karten ({{ votes|length }}/{{ users|length }})</h4>
            <div class="voted-cards">
                {% for name, vote_data in votes.items() %}
                <div class="voted-card-wrapper">
                    <div class="poker-card back">🎴</div>
                    <div class="voted-card-name">{{ name }}</div>
                </div>
                {% endfor %}
            </div>

            {% if user.name == story.creator %}
            <div style="margin-top: 1rem;">
                <button onclick="revealCards()">🔓 Karten aufdecken!</button>
            </div>
            {% endif %}

        {% elif story.status == 'revealed' %}
            <!-- Revealed Phase -->
            <h4>Ergebnisse</h4>

            <div class="voted-cards">
                {% for name, vote_data in votes.items() %}
                <div class="voted-card-wrapper">
                    <div class="poker-card revealed">{{ vote_data.points }}</div>
                    <div class="voted-card-name">{{ name }}</div>
                </div>
                {% endfor %}
            </div>

            {% if consensus_type == 'consensus' %}
            <div class="consensus">
                <h4>✅ KONSENS ERREICHT!</h4>
                <p style="font-size: 2rem; margin: 0.5rem 0;">{{ suggested_points }}</p>
                <p style="font-size: 0.9rem;">Alle haben die gleiche Zahl gewählt.</p>
            </div>
            <form method="POST" action="/complete_story">
                <input type="hidden" name="final_points" value="{{ suggested_points }}">
                <button type="submit">Story mit {{ suggested_points }} Punkten abschließen</button>
            </form>

            {% elif consensus_type == 'near_consensus' %}
            <div class="consensus">
                <h4>✅ KONSENS ERREICHT!</h4>
                <p style="font-size: 2rem; margin: 0.5rem 0;">{{ suggested_points }}</p>
                <p style="font-size: 0.9rem;">Fast alle haben die gleiche Zahl (nur einer weicht um 1 ab).</p>
            </div>
            <form method="POST" action="/complete_story">
                <input type="hidden" name="final_points" value="{{ suggested_points }}">
                <button type="submit">Story mit {{ suggested_points }} Punkten abschließen</button>
            </form>

            {% else %}
            <div class="divergence">
                <h4>🔄 KEIN KONSENS</h4>
                <p style="font-size: 2rem; margin: 0.5rem 0;">Höchster Wert: {{ suggested_points }}</p>
                <p style="font-size: 0.9rem;">Die Meinungen gehen auseinander.</p>
            </div>
            <form method="POST" action="/complete_story" style="display: inline; margin-right: 0.5rem;">
                <input type="hidden" name="final_points" value="{{ suggested_points }}">
                <button type="submit" class="secondary">Story mit {{ suggested_points }} Punkten abschließen</button>
            </form>
            <form method="POST" action="/new_round" style="display: inline;">
                <button type="submit">Neu abstimmen (Runde {{ story.round + 1 }})</button>
            </form>
            {% endif %}
        {% endif %}

    {% else %}
        <!-- Empty State: Keine aktive Story -->
        <div class="game-table-empty">
            <div class="game-table-empty-content">
                <div class="game-table-empty-icon">🎯</div>
                <div class="game-table-empty-text">No story to estimate, yet.</div>
                <div class="game-table-empty-hint">Erstelle eine neue Story oder starte eine wartende Story.</div>
            </div>
        </div>
    {% endif %}
</div>
```

**Änderungen:**
1. `.game-table` ist nun **außerhalb** des `{% if story %}` Blocks
2. `{% if story %}` ist jetzt **innerhalb** des `.game-table`
3. `{% else %}` Block zeigt Empty State an
4. Gesamter Story-Content bleibt identisch (nur verschoben)

---

## Alternative Empty State Designs

### Option 1: Minimalistisch (geplant)
```html
<div class="game-table-empty">
    <div class="game-table-empty-content">
        <div class="game-table-empty-icon">🎯</div>
        <div class="game-table-empty-text">No story to estimate, yet.</div>
        <div class="game-table-empty-hint">Erstelle eine neue Story oder starte eine wartende Story.</div>
    </div>
</div>
```

### Option 2: Mit Call-to-Action
```html
<div class="game-table-empty">
    <div class="game-table-empty-content">
        <div class="game-table-empty-icon">🃏</div>
        <div class="game-table-empty-text">No story to estimate, yet.</div>
        <div class="game-table-empty-hint">
            <p>Erstelle deine erste Story um zu starten!</p>
            <button onclick="document.querySelector('.story-form-collapsible').open = true">
                ➕ Story erstellen
            </button>
        </div>
    </div>
</div>
```
**Vorteil:** Direkter CTA für neue User
**Nachteil:** Mehr Code, könnte überflüssig sein

### Option 3: Mit Pending Stories Hinweis
```html
<div class="game-table-empty">
    <div class="game-table-empty-content">
        {% if pending_stories %}
            <div class="game-table-empty-icon">⏳</div>
            <div class="game-table-empty-text">Keine aktive Story.</div>
            <div class="game-table-empty-hint">
                Es warten {{ pending_stories|length }} Stories auf Abstimmung. Scrolle nach unten!
            </div>
        {% else %}
            <div class="game-table-empty-icon">🎯</div>
            <div class="game-table-empty-text">No story to estimate, yet.</div>
            <div class="game-table-empty-hint">Erstelle eine neue Story um zu starten.</div>
        {% endif %}
    </div>
</div>
```
**Vorteil:** Kontextsensitiv
**Nachteil:** Komplexer

**Empfehlung:** Option 1 (minimalistisch) für MVP, später ggf. erweitern.

---

## Höhen-Kalkulation

**Warum `min-height: 400px`?**

Voting Phase Komponenten:
- Story-Titel + Meta: ~80px
- "Deine Schätzung" Heading: ~30px
- Card Container (Fibonacci-Karten): ~150px
- "Gelegte Karten" Section: ~100px
- Buttons: ~40px
- **Gesamt:** ~400px

**Empty State:**
- Icon: ~64px (4rem)
- Text: ~30px
- Hint: ~20px
- Padding/Margin: ~286px (Rest)
- **Gesamt:** ~400px

→ **400px ist gute Balance:** Groß genug für Content, nicht zu dominant

---

## Responsive Anpassungen (optional)

**Für Mobile:**
```css
@media (max-width: 768px) {
    .game-table {
        min-height: 300px; /* Kleiner auf Mobile */
    }

    .game-table-empty-icon {
        font-size: 3rem; /* Kleineres Icon */
    }
}
```

---

## Implementierungsschritte

### Schritt 1: CSS anpassen (5 min)
1. `.game-table` erweitern (Zeile 168-180)
   - `min-height: 400px` hinzufügen
   - `position: relative` hinzufügen

2. `.game-table-empty` Styles hinzufügen (nach Zeile 180)
   - Empty State CSS einfügen

### Schritt 2: HTML umstrukturieren (10 min)
1. `.game-table` öffnenden Tag VOR `{% if story %}` verschieben (Zeile 418)
2. `{% else %}` Block mit Empty State einfügen (nach Zeile 503)
3. `.game-table` schließenden Tag NACH `{% endif %}` verschieben (nach Zeile 505)

### Schritt 3: Testen (5 min)
- Ohne Story → Empty State sichtbar
- Mit Story → Normaler Content
- Story abschließen → Empty State erscheint
- Layout springt nicht
- Mobile-Ansicht testen

---

## Visuelle Vorher/Nachher

### VORHER
```
┌──────────────────────────────────────┐
│  🃏 Planning Poker                   │
│  Willkommen, Alice!                  │
│                                      │
│  [Nichts hier - komplett leer]      │
│                                      │
│                                      │
│  ➕ Neue Story erstellen             │
└──────────────────────────────────────┘
```
Problem: Großer leerer Raum, unklarer Zustand

### NACHHER
```
┌──────────────────────────────────────┐
│  🃏 Planning Poker                   │
│  Willkommen, Alice!                  │
│                                      │
│ ┌────────────────────────────────┐  │
│ │                                │  │
│ │            🎯                  │  │
│ │  No story to estimate, yet.    │  │
│ │  Erstelle eine neue Story...   │  │
│ │                                │  │
│ └────────────────────────────────┘  │
│                                      │
│  ➕ Neue Story erstellen             │
└──────────────────────────────────────┘
```
Besser: Klarer Empty State, konsistente Größe

---

## Betroffene Zeilen

| Bereich | Zeilen | Änderung |
|---------|--------|----------|
| CSS `.game-table` | 168-180 | + `min-height: 400px`, `position: relative` |
| CSS neu | ~181 | + `.game-table-empty` Styles (~30 Zeilen) |
| HTML Struktur | 416-505 | `.game-table` außerhalb `{% if story %}`, + Empty State |

---

## Risiken und Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| min-height zu groß | Niedrig | Mittel | 400px ist basierend auf Voting-Content |
| Empty State schlecht lesbar | Niedrig | Niedrig | Klare Typografie, guter Kontrast |
| Layout bricht auf Mobile | Mittel | Mittel | Responsive Media Queries testen |
| Story-Content überschreitet min-height | Niedrig | Keiner | min-height wächst automatisch mit |

---

## Zukünftige Erweiterungen

1. **Animationen:**
   - Fade-In beim Wechsel Empty ↔ Story
   - Pulsing Icon im Empty State

2. **Dynamische Hints:**
   - Verschiedene Texte je nach Kontext
   - Zufällige motivierende Sprüche

3. **Skeleton Loader:**
   - Während Story lädt: Skeleton statt Empty State

4. **Gamification:**
   - "Schätze deine erste Story!" Badge

---

## Geschätzter Aufwand

**Gesamtaufwand:** 20 Minuten

- CSS schreiben: 5 min
- HTML umstrukturieren: 10 min
- Testing: 5 min

---

## Zusammenfassung

**Was ändert sich:**
1. ✅ `.game-table` ist immer sichtbar (nicht mehr conditional)
2. ✅ Feste Mindesthöhe von 400px
3. ✅ Empty State: "No story to estimate, yet."
4. ✅ Kein Layout-Springen mehr

**Warum ist das besser:**
- Konsistente UI (vorhersagbares Layout)
- Bessere UX für neue User (klarer Zustand)
- Professioneller Look (kein leerer Raum)
- Einfacher zu warten (HTML-Struktur klarer)

---

**Plan erstellt am:** 2025-12-06
**Status:** Bereit zur Umsetzung
**Betroffene Datei:** `templates/index.html`
