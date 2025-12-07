# Plan: Einhorn Easter Egg Verbesserungen

## Übersicht

Das Einhorn-Overlay soll länger sichtbar sein und manuell schließbar werden.

**Datei:** `/home/alg/poker/templates/index.html`

---

## Aktuelle Implementierung

**Wo erscheint das Einhorn:**
- Beim WebSocket-Event `cards_revealed` (Zeile 671)
- Wird durch `showUnicorn()` Funktion ausgelöst (Zeile 607)

**Aktuelles Verhalten:**
- Zeigt ein Fullscreen-Overlay mit 🦄 Einhorn-Emoji
- Zufälliger weiser Spruch aus `unicornQuotes` Array
- Sichtbar für **2,5 Sekunden** (Zeile 632: `2500ms`)
- Automatisches Ausblenden + Page Reload
- **KEIN manueller Schließ-Button**

---

## Geplante Änderungen

### 1. Timeout auf 5 Sekunden erhöhen

**Location:** `templates/index.html` Zeile 632

**Änderung:**
```javascript
// VORHER:
}, 2500);

// NACHHER:
}, 5000);
```

**Begründung:** Nutzer sollen mehr Zeit haben, den Spruch zu lesen.

---

### 2. X-Button zum Schließen hinzufügen

#### 2.1 HTML-Struktur erweitern

**Location:** `templates/index.html` Zeile 579-586

**Aktuell:**
```html
<div class="unicorn-overlay" id="unicornOverlay">
    <div class="unicorn-container">
        <div class="unicorn-emoji">🦄</div>
        <div class="unicorn-speech" id="unicornSpeech">
            Die Weisheit der Schätzung offenbart sich...
        </div>
    </div>
</div>
```

**Geplant:**
```html
<div class="unicorn-overlay" id="unicornOverlay">
    <div class="unicorn-container">
        <button class="unicorn-close" id="unicornClose" aria-label="Schließen">✕</button>
        <div class="unicorn-emoji">🦄</div>
        <div class="unicorn-speech" id="unicornSpeech">
            Die Weisheit der Schätzung offenbart sich...
        </div>
    </div>
</div>
```

**Änderungen:**
- Neuer `<button>` mit Klasse `unicorn-close`
- ID `unicornClose` für JavaScript-Zugriff
- ✕ Symbol als Close-Icon
- `aria-label` für Accessibility

#### 2.2 CSS für X-Button

**Location:** `templates/index.html` nach Zeile 344 (innerhalb `<style>`)

**Neues CSS hinzufügen:**
```css
.unicorn-close {
    position: absolute;
    top: 20px;
    right: 20px;
    background: white;
    border: 2px solid #333;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    font-size: 1.5rem;
    font-weight: bold;
    color: #333;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    z-index: 10000;
}

.unicorn-close:hover {
    background: #f44336;
    color: white;
    border-color: #f44336;
    transform: rotate(90deg) scale(1.1);
}

.unicorn-close:active {
    transform: rotate(90deg) scale(0.95);
}
```

**Features:**
- Position: Oben rechts im Viewport
- Kreisförmiger Button (50% border-radius)
- Hover-Effekt: Rot mit Rotation
- Active-Effekt: Leicht verkleinert
- Über dem Einhorn-Container (z-index 10000)

#### 2.3 JavaScript für Schließ-Funktion

**Location:** `templates/index.html` nach Zeile 633 (innerhalb `<script>`)

**Neue Funktion hinzufügen:**
```javascript
function closeUnicorn() {
    console.log('👋 Einhorn wird manuell geschlossen...');
    const overlay = document.getElementById('unicornOverlay');
    overlay.classList.remove('show');

    // Seite nach Animation neu laden
    setTimeout(() => location.reload(), 300);
}

// Event-Listener für X-Button
document.addEventListener('DOMContentLoaded', () => {
    const closeBtn = document.getElementById('unicornClose');
    if (closeBtn) {
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Verhindert Event-Bubbling
            closeUnicorn();
        });
    }

    // Optional: Schließen durch Klick aufs Overlay (außerhalb Container)
    const overlay = document.getElementById('unicornOverlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            // Nur wenn direkt auf Overlay geklickt (nicht auf Container)
            if (e.target === overlay) {
                closeUnicorn();
            }
        });
    }
});
```

**Features:**
- Sofortiges Schließen beim X-Klick
- Optional: Klick außerhalb schließt auch (UX-Standard)
- Gleicher Fade-Out wie automatisches Schließen
- Page-Reload nach 300ms (für Konsistenz)

#### 2.4 showUnicorn() Funktion anpassen

**Location:** `templates/index.html` Zeile 627-632

**Aktuell:**
```javascript
// Nach 2.5 Sekunden ausblenden und Seite neu laden
setTimeout(() => {
    console.log('👋 Einhorn verschwindet...');
    overlay.classList.remove('show');
    setTimeout(() => location.reload(), 300);
}, 2500);
```

**Geplant:**
```javascript
// Nach 5 Sekunden automatisch ausblenden
let unicornTimeout = setTimeout(() => {
    console.log('⏰ Einhorn verschwindet automatisch nach 5s...');
    closeUnicorn();
}, 5000);

// Timeout speichern für manuelles Clearen (falls X gedrückt)
overlay.dataset.timeout = unicornTimeout;
```

**Änderungen:**
- Timeout von 2500ms → 5000ms
- Nutzt `closeUnicorn()` Funktion (DRY-Prinzip)
- Optional: Timeout-ID speichern (für Clearing bei manuellem Schließen)

---

## Alternative Ansätze (nicht umgesetzt)

### Option 1: Kein Auto-Close
- Nur manuelles Schließen via X
- **Nachteil:** User könnte vergessen zu schließen

### Option 2: Konfigurierbarer Timeout
- Admin kann Timeout einstellen
- **Nachteil:** Overengineering für Easter Egg

### Option 3: "Nicht mehr anzeigen" Checkbox
- LocalStorage-basierte Unterdrückung
- **Nachteil:** Nimmt den Spaß weg

---

## Implementierungsschritte (für spätere Umsetzung)

1. **CSS ergänzen** (nach Zeile 344)
   - `.unicorn-close` Styles hinzufügen

2. **HTML erweitern** (Zeile 580)
   - X-Button in `.unicorn-container` einfügen

3. **JavaScript erweitern** (nach Zeile 633)
   - `closeUnicorn()` Funktion hinzufügen
   - Event-Listener registrieren (DOMContentLoaded)

4. **showUnicorn() anpassen** (Zeile 632)
   - Timeout auf 5000ms erhöhen
   - `closeUnicorn()` statt inline Code nutzen

5. **Testen**
   - Story erstellen → voting → reveal
   - Einhorn erscheint
   - X-Button klicken → schließt sofort
   - Warten 5 Sekunden → schließt automatisch
   - Klick außerhalb → schließt auch (optional)

---

## Dateien-Übersicht

| Datei | Zeilen | Änderung |
|-------|--------|----------|
| `templates/index.html` | ~344 (CSS) | + `.unicorn-close` Styles |
| `templates/index.html` | 580 | + `<button class="unicorn-close">` |
| `templates/index.html` | ~633 (JS) | + `closeUnicorn()` Funktion |
| `templates/index.html` | ~633 (JS) | + Event-Listener (DOMContentLoaded) |
| `templates/index.html` | 632 | Timeout 2500 → 5000ms |

---

## Risiken

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| X-Button überlappt Text | Niedrig | Position absolut, Container relativ |
| Event-Listener nicht registriert | Niedrig | DOMContentLoaded nutzen |
| Doppeltes Reload | Niedrig | clearTimeout nutzen |
| Accessibility-Probleme | Mittel | aria-label + Keyboard-Support |

---

## Optionale Erweiterungen

**Für später:**
1. **Keyboard-Support:**
   - ESC-Taste schließt Einhorn
   ```javascript
   document.addEventListener('keydown', (e) => {
       if (e.key === 'Escape' && overlay.classList.contains('show')) {
           closeUnicorn();
       }
   });
   ```

2. **Animation für X-Button:**
   - Pulse-Animation beim Erscheinen
   ```css
   @keyframes pulse {
       0%, 100% { transform: scale(1); }
       50% { transform: scale(1.1); }
   }
   .unicorn-close {
       animation: pulse 2s infinite;
   }
   ```

3. **Sound-Effect:**
   - "Bling" beim Erscheinen (optional)

---

## Geschätzter Aufwand

**Gesamtaufwand:** 15-20 Minuten

- CSS schreiben: 5 min
- HTML anpassen: 2 min
- JavaScript schreiben: 8 min
- Testen: 5 min

---

**Plan erstellt am:** 2025-12-06
**Status:** Bereit zur Umsetzung
**Betroffene Datei:** `templates/index.html`
