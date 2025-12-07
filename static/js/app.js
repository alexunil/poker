const socket = io();

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
    console.log('👋 Einhorn wird manuell geschlossen...');
    const overlay = document.getElementById('unicornOverlay');
    overlay.classList.remove('show');

    // Seite nach Animation neu laden
    setTimeout(() => location.reload(), 300);
}

function showUnicorn() {
    console.log('🦄 EINHORN WIRD ANGEZEIGT!');
    const overlay = document.getElementById('unicornOverlay');
    const speech = document.getElementById('unicornSpeech');

    if (!overlay) {
        console.log('⚠️ Einhorn ist deaktiviert oder Overlay nicht gefunden');
        location.reload();
        return;
    }

    // Zufälliger Spruch
    const randomQuote = unicornQuotes[Math.floor(Math.random() * unicornQuotes.length)];
    console.log('💬 Einhorn sagt:', randomQuote);
    speech.textContent = randomQuote;

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
    // Einhorn nur zeigen wenn aktiviert
    const enableUnicorn = document.body.dataset.enableUnicorn === 'true';
    if (enableUnicorn) {
        showUnicorn(); // 🦄 Einhorn beim Aufdecken!
    } else {
        console.log('⚠️ Einhorn ist deaktiviert, reloade direkt');
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
    // Nicht reloaden wenn Einhorn gerade angezeigt wird
    const overlay = document.getElementById('unicornOverlay');
    if (overlay && overlay.classList.contains('show')) {
        console.log('⏸️ Reload unterdrückt - Einhorn ist sichtbar');
        return;
    }
    location.reload();
});
socket.on('user_updated', () => {
    console.log('👤 Event: user_updated');
    location.reload();
});

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
