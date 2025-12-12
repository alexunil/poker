const socket = io();

// Global flag to prevent reloads while unicorn is showing
let unicornIsActive = false;

// Weise Einhorn-Sprüche
const unicornQuotes = [
    "Die Weisheit der Schätzung offenbart sich...",
    "Das Einhorn hat gesprochen!",
    "Möge die Fibonacci-Kraft mit euch sein!",
    "Konsens ist der Weg zur Erleuchtung.",
    "Story Points sind wie Magie - manchmal unerwartet!",
    "Ein weises Team schätzt gemeinsam.",
    "Die Karten lügen nie... oder doch?",
    "Perfektion ist keine Fibonacci-Zahl.",
    "Schätzen ist eine Kunst, keine Wissenschaft!",
    "Das Einhorn nickt weise...",
    "Agile Weisheit kommt von Innen... oder vom Einhorn.",
    "13 Story Points? Das Einhorn ist beeindruckt!",
    "Manchmal ist 5 größer als 8 - im Herzen.",
    "Story Points sind keine Stunden - merkt euch das!",
    "Das Einhorn sieht Potenzial in eurer Schätzung.",
    "Velocity ist wichtig, aber Qualität ist wichtiger.",
    "In der Ruhe liegt die Kraft der guten Schätzung.",
    "Fibonacci würde stolz auf euch sein!",
    "Konsens bedeutet nicht, dass alle Recht haben.",
    "Das Einhorn segnet diese Abstimmung!"
];

function closeUnicorn() {
    console.log('👋 Einhorn wird geschlossen...');
    const overlay = document.getElementById('unicornOverlay');
    overlay.classList.remove('show');
    unicornIsActive = false;

    // Seite nach Animation neu laden
    setTimeout(() => location.reload(), 300);
}

function showUnicorn(quoteFromServer) {
    console.log('🦄 EINHORN WIRD ANGEZEIGT!');
    unicornIsActive = true; // Set flag IMMEDIATELY to prevent race conditions

    const overlay = document.getElementById('unicornOverlay');
    const speech = document.getElementById('unicornSpeech');

    if (!overlay) {
        console.log('⚠️ Einhorn ist deaktiviert oder Overlay nicht gefunden');
        unicornIsActive = false;
        location.reload();
        return;
    }

    // Verwende Spruch vom Server (damit alle denselben sehen)
    // Falls Server keinen Spruch sendet, verwende Fallback aus lokalem Array
    const quote = quoteFromServer || unicornQuotes[Math.floor(Math.random() * unicornQuotes.length)];
    console.log('💬 Einhorn sagt:', quote);
    speech.textContent = quote;

    // Einhorn anzeigen
    overlay.classList.add('show');
    console.log('✅ Einhorn Overlay angezeigt');

    // Anzeigedauer aus Body-Attribut lesen (default: 3 Sekunden)
    const displaySeconds = parseInt(document.body.dataset.unicornDisplaySeconds || '3', 10);
    const displayMs = displaySeconds * 1000;

    // Nach konfigurierter Zeit automatisch ausblenden
    setTimeout(() => {
        console.log(`⏰ Einhorn verschwindet automatisch nach ${displaySeconds}s...`);
        closeUnicorn();
    }, displayMs);
}

function revealCards() {
    console.log('🔓 Karten werden aufgedeckt...');
    fetch('/reveal', { method: 'POST' })
        .then(response => {
            console.log('✅ Reveal erfolgreich');
            // WebSocket Event wird das Einhorn triggern
        })
        .catch(error => {
            console.error('❌ Fehler beim Aufdecken:', error);
            location.reload();
        });
}

socket.on('connect', () => {
    document.getElementById('connection-status').innerHTML = '🟢 Live verbunden';
});

socket.on('disconnect', () => {
    document.getElementById('connection-status').innerHTML = '🔴 Verbindung unterbrochen';
});

// Alle Events führen zu Page Reload
socket.on('story_created', () => {
    console.log('📝 Event: story_created');
    location.reload();
});
socket.on('voting_started', () => {
    console.log('🎯 Event: voting_started');
    location.reload();
});
socket.on('vote_submitted', () => {
    console.log('🃏 Event: vote_submitted');
    location.reload();
});
socket.on('cards_revealed', (data) => {
    console.log('🔓 Event: cards_revealed', data);
    // Einhorn nur zeigen wenn Server würfelt dass es erscheinen soll
    const enableUnicorn = document.body.dataset.enableUnicorn === 'true';
    const shouldShow = data.show_unicorn === true;

    if (enableUnicorn && shouldShow) {
        console.log('🎲 Einhorn-Würfel: JA! Einhorn erscheint!');
        showUnicorn(data.unicorn_quote); // 🦄 Einhorn mit Server-Spruch!
    } else {
        if (enableUnicorn && !shouldShow) {
            console.log('🎲 Einhorn-Würfel: NEIN. Kein Einhorn dieses Mal.');
        } else {
            console.log('⚠️ Einhorn ist deaktiviert, reloade direkt');
        }
        location.reload();
    }
});
socket.on('story_completed', () => {
    console.log('✅ Event: story_completed');
    location.reload();
});
socket.on('new_round', () => {
    console.log('🔄 Event: new_round');
    location.reload();
});
socket.on('story_reset', () => {
    console.log('🔁 Event: story_reset');
    location.reload();
});
socket.on('event_added', () => {
    console.log('📢 Event: event_added');
    // Nicht reloaden wenn Einhorn gerade angezeigt wird (Flag-basiert)
    if (unicornIsActive) {
        console.log('⏸️ Reload unterdrückt - Einhorn ist aktiv');
        return;
    }
    location.reload();
});
socket.on('user_updated', () => {
    console.log('👤 Event: user_updated');
    location.reload();
});
socket.on('story_withdrawn', () => {
    console.log('↩️ Event: story_withdrawn');
    location.reload();
});
socket.on('story_deleted', () => {
    console.log('🗑️ Event: story_deleted');
    location.reload();
});

// Delete Story Funktion mit Bestätigung
function deleteStory(storyId, storyTitle) {
    if (confirm(`Story "${storyTitle}" wirklich löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden.`)) {
        fetch(`/delete_story/${storyId}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('✅ Story erfolgreich gelöscht');
                    // WebSocket wird das Update triggern
                } else {
                    console.error('❌ Fehler beim Löschen:', data.error);
                    alert('Fehler beim Löschen: ' + (data.error || 'Unbekannter Fehler'));
                    location.reload();
                }
            })
            .catch(error => {
                console.error('❌ Netzwerkfehler beim Löschen:', error);
                alert('Fehler beim Löschen der Story');
                location.reload();
            });
    }
}

// Story Dialog Funktionen
// hasActiveVoting wird von HTML data-attribute gelesen
let hasActiveVoting = false;

function showStoryDialog(event) {
    event.preventDefault();

    // Validierung
    const form = document.getElementById('storyForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    // hasActiveVoting von body data-attribute lesen
    hasActiveVoting = document.body.dataset.hasActiveVoting === 'true';

    const dialog = document.getElementById('storyDialog');
    const title = document.getElementById('storyDialogTitle');
    const text = document.getElementById('storyDialogText');
    const yesBtn = document.getElementById('dialogYes');

    if (hasActiveVoting) {
        title.textContent = 'Story zur Auto-Queue hinzufügen?';
        text.textContent = 'Es läuft bereits eine Abstimmung. Soll die Story automatisch starten, wenn die aktuelle abgeschlossen ist?';
    } else {
        title.textContent = 'Story sofort abstimmen?';
        text.textContent = 'Soll die Story sofort zur Abstimmung gestellt werden?';
    }

    // Ja-Button fokussieren (für Enter-Shortcut)
    dialog.classList.add('show');
    setTimeout(() => yesBtn.focus(), 100);
}

function submitStoryDialog(confirmed) {
    const dialog = document.getElementById('storyDialog');
    const form = document.getElementById('storyForm');

    if (hasActiveVoting) {
        // Bei aktiver Voting: auto_start setzen
        document.getElementById('auto_start').value = confirmed ? 'true' : 'false';
        document.getElementById('start_immediately').value = 'false';
    } else {
        // Keine Voting aktiv: start_immediately setzen
        document.getElementById('start_immediately').value = confirmed ? 'true' : 'false';
        document.getElementById('auto_start').value = 'false';
    }

    dialog.classList.remove('show');
    form.submit();
}

// Event-Listener für Einhorn X-Button
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

// ============================================================================
// AI REASONING MODAL
// ============================================================================

function showAiReasoning(storyId) {
    const modal = document.getElementById('ai-reasoning-modal');
    const content = document.getElementById('ai-reasoning-content');

    // Modal anzeigen
    modal.style.display = 'flex';

    // Loading anzeigen
    content.innerHTML = '<div class="loading">Lade Begründung...</div>';

    // API Call
    fetch(`/api/ai-reasoning/${storyId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('AI-Begründung nicht verfügbar');
            }
            return response.json();
        })
        .then(data => {
            // Render reasoning
            content.innerHTML = renderAiReasoning(data);
        })
        .catch(error => {
            content.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--error-color);">
                    <p>❌ Fehler beim Laden der Begründung</p>
                    <p style="font-size: 0.9rem; color: var(--muted-color);">${error.message}</p>
                </div>
            `;
        });
}

function closeAiReasoning() {
    const modal = document.getElementById('ai-reasoning-modal');
    modal.style.display = 'none';
}

function renderAiReasoning(data) {
    let html = '';

    // Reasoning Text
    html += `
        <div class="reasoning-section">
            <h4>📝 Begründung</h4>
            <div class="reasoning-text">${escapeHtml(data.reasoning)}</div>
        </div>
    `;

    // Similar Stories
    if (data.similar_stories && data.similar_stories.length > 0) {
        html += `
            <div class="reasoning-section">
                <h4>🔍 Ähnliche Stories</h4>
                <ul class="similar-stories">
        `;

        data.similar_stories.forEach(story => {
            const similarity = (story.similarity * 100).toFixed(0);
            html += `
                <li class="similar-story-item">
                    <div class="story-title">
                        ${escapeHtml(story.title)}
                        <span class="similarity-badge">${similarity}% ähnlich</span>
                    </div>
                    <div class="story-meta">
                        ${story.points} Story Points
                    </div>
                </li>
            `;
        });

        html += `
                </ul>
            </div>
        `;
    }

    // Model Info
    html += `
        <div class="reasoning-section" style="border-top: 1px solid var(--border-color); padding-top: 1rem; margin-top: 1rem;">
            <p style="font-size: 0.85rem; color: var(--muted-color); margin: 0;">
                Geschätzt mit: ${escapeHtml(data.model_used)}
            </p>
        </div>
    `;

    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Modal schließen bei ESC-Taste
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAiReasoning();
    }
});

// Modal schließen bei Klick auf Overlay
document.addEventListener('click', (e) => {
    const modal = document.getElementById('ai-reasoning-modal');
    if (e.target === modal) {
        closeAiReasoning();
    }
});
