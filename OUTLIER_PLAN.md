# Plan: Outlier-Value-Option (Feature 6)

## Übersicht

Bei Divergenz soll nicht nur der **höchste Wert** als Option angeboten werden, sondern auch der **nächst-niedrigere Wert** (z.B. Mehrheitswert oder zweithöchster Wert).

**Anforderung (feature6.md):**
> "Wenn nur ein Ausreisser da ist soll es auch die Möglichkeite geben den nächst niedrigeren Wert zu verwenden. Aber optisch soll erkennbar sein das der höchste Wert der priorisierte ist."

---

## Aktuelles Verhalten

### Bei Divergenz

**Beispiel:** Votes: [5, 8, 8, 13]

**Aktuell:**
```
🔄 KEIN KONSENS
Höchster Wert: 13

[Story mit 13 Punkten abschließen]  [Neu abstimmen]
```

Nur **eine** Option: Der höchste Wert (13)

---

## Gewünschtes Verhalten

**Beispiel:** Votes: [5, 8, 8, 13]

**Neu:**
```
🔄 KEIN KONSENS
Empfohlen: 13 (höchster Wert)
Alternative: 8 (Mehrheit: 2 Stimmen)

[Story mit 13 Punkten abschließen]  [Story mit 8 Punkten abschließen]  [Neu abstimmen]
```

**Zwei** Optionen:
1. **Höchster Wert** (13) - optisch priorisiert (Primary Button)
2. **Alternative** (8) - zweithöchster oder Mehrheitswert (Secondary Button)

---

## Implementierung

### 1. Voting Logic erweitern

**Location:** `voting_logic.py`

**Aktuelle Funktion:**
```python
def check_consensus(vote_values: List[int]) -> Tuple[str, Optional[int]]:
    # ...
    # Fall 3: Divergenz - höchster Wert
    return "divergence", max(vote_values)
```

**Geplant:**
```python
def check_consensus(vote_values: List[int]) -> Tuple[str, Optional[int], Optional[int]]:
    """
    Returns:
        Tuple aus (consensus_type, suggested_points, alternative_points)
    """
    # ...
    # Fall 3: Divergenz - höchster Wert + Alternative
    highest_value = max(vote_values)
    alternative_value = calculate_alternative_value(vote_values, highest_value)
    return "divergence", highest_value, alternative_value
```

**Neue Hilfsfunktion:**
```python
def calculate_alternative_value(vote_values: List[int], highest_value: int) -> Optional[int]:
    """
    Berechnet den alternativen Wert bei Divergenz

    Logik:
    1. Mehrheitswert (wenn != highest_value)
    2. Zweithöchster Wert
    3. None (wenn nur ein einziger Vote)
    """
    if len(vote_values) <= 1:
        return None

    counter = Counter(vote_values)
    most_common_value = counter.most_common(1)[0][0]

    # Mehrheitswert als Alternative (wenn != höchster)
    if most_common_value != highest_value and counter[most_common_value] > 1:
        return most_common_value

    # Zweithöchster Wert
    sorted_unique = sorted(set(vote_values), reverse=True)
    if len(sorted_unique) >= 2:
        return sorted_unique[1]

    return None
```

### 2. Template aktualisieren

**Location:** `templates/index.html`

**Aktuelle Divergenz-Anzeige:**
```html
<div class="divergence">
    <h4>🔄 KEIN KONSENS</h4>
    <p>Höchster Wert: {{ suggested_points }}</p>
</div>

<form method="POST" action="/complete_story">
    <input type="hidden" name="final_points" value="{{ suggested_points }}">
    <button type="submit">Story mit {{ suggested_points }} Punkten abschließen</button>
</form>
<form method="POST" action="/new_round">
    <button type="submit">Neu abstimmen</button>
</form>
```

**Geplant:**
```html
<div class="divergence">
    <h4>🔄 KEIN KONSENS</h4>
    <p style="font-size: 1.5rem; margin: 0.5rem 0;">
        <strong>Empfohlen:</strong> {{ suggested_points }} (höchster Wert)
    </p>
    {% if alternative_points and alternative_points != suggested_points %}
    <p style="font-size: 1.2rem; margin: 0.5rem 0; color: var(--muted-color);">
        <strong>Alternative:</strong> {{ alternative_points }}
        {% if vote_distribution %}
        ({{ vote_distribution[alternative_points] }} Stimme{% if vote_distribution[alternative_points] != 1 %}n{% endif %})
        {% endif %}
    </p>
    {% endif %}
</div>

<!-- Primary Button: Höchster Wert (optisch priorisiert) -->
<form method="POST" action="/complete_story" style="display: inline; margin-right: 0.5rem;">
    <input type="hidden" name="final_points" value="{{ suggested_points }}">
    <button type="submit" class="primary-prominent">
        Story mit {{ suggested_points }} Punkten abschließen ⭐
    </button>
</form>

<!-- Secondary Button: Alternative (wenn vorhanden) -->
{% if alternative_points and alternative_points != suggested_points %}
<form method="POST" action="/complete_story" style="display: inline; margin-right: 0.5rem;">
    <input type="hidden" name="final_points" value="{{ alternative_points }}">
    <button type="submit" class="secondary">
        Story mit {{ alternative_points }} Punkten abschließen
    </button>
</form>
{% endif %}

<!-- Neu abstimmen -->
<form method="POST" action="/new_round" style="display: inline;">
    <button type="submit" class="secondary">
        Neu abstimmen (Runde {{ story.round + 1 }})
    </button>
</form>
```

### 3. CSS für visuellen Unterschied

**Location:** `templates/index.html` (im `<style>` Tag)

**Hinzufügen:**
```css
/* Primary Prominent Button - für empfohlenen Wert */
.primary-prominent {
    background: linear-gradient(135deg, var(--primary) 0%, #0056b3 100%);
    color: white;
    font-weight: bold;
    font-size: 1.1rem;
    padding: 0.75rem 1.5rem;
    border: 3px solid var(--primary);
    box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
    transition: all 0.2s;
}

.primary-prominent:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 123, 255, 0.4);
}

.divergence p strong {
    color: var(--primary);
}
```

### 4. Backend - Daten vorbereiten

**Location:** `app.py` (index route)

**Aktuell:**
```python
# Konsens berechnen falls revealed
consensus_type = None
suggested_points = None
if active_story and active_story["status"] == "revealed":
    story_votes = get_story_votes(active_story["id"], active_story["round"])
    if story_votes:
        vote_values = [v["points"] for v in story_votes.values()]
        consensus_type, suggested_points = check_consensus(vote_values)
```

**Geplant:**
```python
# Konsens berechnen falls revealed
consensus_type = None
suggested_points = None
alternative_points = None
vote_distribution = None

if active_story and active_story["status"] == "revealed":
    story_votes = get_story_votes(active_story["id"], active_story["round"])
    if story_votes:
        vote_values = [v["points"] for v in story_votes.values()]
        consensus_type, suggested_points, alternative_points = check_consensus(vote_values)

        # Vote-Verteilung berechnen für Anzeige
        from collections import Counter
        vote_distribution = dict(Counter(vote_values))
```

**Template-Variablen:**
```python
return render_template(
    "index.html",
    # ...
    consensus_type=consensus_type,
    suggested_points=suggested_points,
    alternative_points=alternative_points,  # NEU
    vote_distribution=vote_distribution,     # NEU
    # ...
)
```

### 5. WebSocket-Events anpassen

**Location:** `app.py` (reveal, auto-reveal)

**Alle Stellen wo check_consensus aufgerufen wird:**
- `app.py:241` - Auto-Reveal nach Vote
- `app.py:373` - Manual Reveal

**Anpassen:**
```python
consensus_type, suggested_points, alternative_points = check_consensus(vote_values)

socketio.emit("cards_revealed", {
    "votes": vote_list,
    "consensus_type": consensus_type,
    "suggested_points": suggested_points,
    "alternative_points": alternative_points  # NEU
})
```

---

## Test-Szenarien

### Szenario 1: Klarer Ausreißer (Mehrheit vorhanden)

**Votes:** [5, 8, 8, 8, 13]

**Erwartung:**
- Empfohlen: 13 (höchster)
- Alternative: 8 (Mehrheit: 3 Stimmen)
- 2 Buttons sichtbar

### Szenario 2: Zwei Gruppen

**Votes:** [5, 5, 13, 13]

**Erwartung:**
- Empfohlen: 13 (höchster)
- Alternative: 5 (zweithöchster, 2 Stimmen)
- 2 Buttons sichtbar

### Szenario 3: Alle unterschiedlich

**Votes:** [2, 5, 8, 13, 21]

**Erwartung:**
- Empfohlen: 21 (höchster)
- Alternative: 13 (zweithöchster)
- 2 Buttons sichtbar

### Szenario 4: Nur ein Ausreißer nach oben

**Votes:** [8, 8, 8, 8, 13]

**Erwartung:**
- Empfohlen: 13 (höchster)
- Alternative: 8 (Mehrheit: 4 Stimmen)
- 2 Buttons sichtbar
- **Ideal Case für Feature 6!**

### Szenario 5: Nur 2 Votes, beide unterschiedlich

**Votes:** [5, 13]

**Erwartung:**
- Empfohlen: 13 (höchster)
- Alternative: 5 (zweithöchster)
- 2 Buttons sichtbar

### Szenario 6: Nur 1 Vote

**Votes:** [8]

**Erwartung:**
- Empfohlen: 8
- Alternative: None (keine Alternative vorhanden)
- Nur 1 Button sichtbar

---

## Rückwärtskompatibilität

**Wichtig:** Alle Stellen die check_consensus aufrufen müssen angepasst werden:

**Vorher:**
```python
consensus_type, suggested_points = check_consensus(vote_values)
```

**Nachher:**
```python
consensus_type, suggested_points, alternative_points = check_consensus(vote_values)
```

**Betroffene Dateien:**
- `app.py` (mehrere Stellen)
- Evtl. Tests (falls vorhanden)

---

## Implementierungsschritte

1. ✅ **voting_logic.py**
   - `calculate_alternative_value()` Funktion hinzufügen
   - `check_consensus()` erweitern: 3. Return-Wert `alternative_points`

2. ✅ **app.py - index route**
   - `alternative_points` und `vote_distribution` berechnen
   - An Template übergeben

3. ✅ **app.py - reveal/auto-reveal**
   - check_consensus Aufrufe auf 3 Return-Werte anpassen
   - WebSocket-Events mit alternative_points

4. ✅ **templates/index.html - Divergence-Anzeige**
   - Empfohlen/Alternative Text
   - 2 Buttons (Primary + Secondary)
   - CSS für visual prominence

5. ✅ **Testing**
   - Alle 6 Szenarien durchspielen
   - Visuelle Prüfung der Button-Styles

---

## Zusammenfassung

**Kernänderung:**
- check_consensus gibt jetzt 3 Werte zurück statt 2
- Bei Divergenz: Höchster Wert + Alternative (Mehrheit oder zweithöchster)
- Template zeigt beide Optionen an
- Höchster Wert ist optisch hervorgehoben (Primary Button mit ⭐)

**User Experience:**
- Flexibilität: Team kann wählen zwischen optimistisch (höchster) oder konservativ (Alternative)
- Transparenz: Beide Optionen sind klar sichtbar
- Guidance: Höchster Wert ist empfohlen (visuell priorisiert)
