UX-Kernprinzip: Fokus und Klarheit
Das Hauptziel ist, die aktuelle Story und den Schätzungsprozess in den Mittelpunkt zu stellen.

Single-View-Fokus: Die Hauptseite sollte immer die aktive Story zeigen. Keine unnötigen Menüs oder Ablenkungen.

Minimalistische Ästhetik: Verwenden Sie ein klares, modernes Design (z.B. mit einem Framework wie Bootstrap, Tailwind CSS oder Pico.css), um die Ladezeiten niedrig und die Oberfläche sauber zu halten.

Klare Statusanzeige: Der aktuelle Zustand des Systems muss sofort ersichtlich sein:

Keine aktive Story: Großer Call-to-Action (CTA): "Neue Story anlegen".

Aktive Story (Warten auf Schätzung): Fokus auf die Kartenwahl und die Teilnehmerliste.

Abgestimmt/Aufgedeckt: Fokus auf die Ergebnisse und die Optionen "Nein, neu abstimmen" oder "Ja, Story abschließen".

2. 📝 Story-Erstellung und -Verwaltung
Formular-Fokus: Das Formular zur Story-Erstellung sollte einfach und klar sein.

Titel: Kurzes, hervorgehobenes Eingabefeld.

Beschreibung: Großes, gut formatiertes Textfeld (eventuell Markdown-Unterstützung).

CTA: Ein einziger, klarer Button: "Story starten & Schätzung freigeben".

Keine Ablenkung: Solange eine Story aktiv ist, sollte der Button "Neue Story anlegen" für alle außer dem Story-Ersteller (oder nur für Admins, wenn Sie später welche einführen) ausgegraut oder ausgeblendet sein, um der Regel "nur eine aktive Story gleichzeitig" zu entsprechen.

3. 🃏 Der Schätzungsprozess (Voting-View)
Dies ist die wichtigste Ansicht und muss hochgradig interaktiv sein.

A. Kartenwahl (Input für den Benutzer)
Feste Fibonacci-Buttons: Anstatt eines Dropdowns oder eines Textfeldes, verwenden Sie große, klickbare Schaltflächen für die Fibonacci-Werte (z.B. 1, 2, 3, 5, 8, 13, 21, ?).

Visuelles Feedback: Wenn ein Benutzer eine Karte wählt, muss die gewählte Karte deutlich hervorgehoben werden (z.B. durch eine andere Farbe oder einen Rahmen) und das System muss schnell (ohne Neuladen) anzeigen, dass der Vote abgegeben ist (z.B. mit einem Haken-Symbol).

Verdeckte Karten: Sobald die Karte gewählt wurde, sollte die gewählte Zahl nicht mehr sichtbar sein, bis die Story aufgedeckt wird.

B. Teilnehmer- und Statusanzeige (Output für alle)
Teilnehmerliste: Eine Liste aller eingeloggten Benutzer (erkannt über Cookie).

Visueller Status: Neben jedem Namen sollte ein klarer Indikator sein, ob die Person bereits geschätzt hat:

Wartet: Name ohne Symbol.

Geschätzt (Verdeckt): Grünes Haken-Symbol oder ein "Karte gelegt"-Symbol (z.B. ein Kartensymbol).

Echtzeit-Update: Die Teilnehmerliste sollte automatisch aktualisiert werden (über WebSockets oder regelmäßiges AJAX/Fetch-Polling), damit alle sofort sehen, wer seine Karte gelegt hat.

4. 🔓 Das Aufdecken (Reveal-View)
Klarer CTA für den Ersteller: Nur der Ersteller der Story sieht einen hervorgehobenen Button: "Karten aufdecken!".

Dramatischer Moment: Nach dem Klick des Erstellers sollten die Ergebnisse gleichzeitig und visuell ansprechend eingeblendet werden.

Ergebnisse: Liste der Namen und der von ihnen geschätzten Werte.

Visualisierung: Ein einfaches Balkendiagramm oder ein Streudiagramm der abgegebenen Punkte kann helfen, die Verteilung schnell zu erfassen.

Entscheidungs-Feedback
Basierend auf Ihrer Regel (fast alle gleich oder nur einer eins daneben) muss das System eine klare Empfehlung aussprechen:

Fall 1 (Konsens): Große, grüne Nachricht: "KONSENS ERREICHT! Vorgeschlagene Punktzahl: [Wert]"

Aktion: Button: "Story abschließen"

Fall 2 (Diskussion nötig): Große, orangefarbene Nachricht: "KEIN KONSENS. Höchster Wert: [Wert]"

Aktion: Button: "Neu abstimmen (Start neue Runde)"

5. 🛠️ Technische UX-Umsetzung (Flask & Cookie)
Cookie-Prompt: Beim ersten Besuch: Eine zentrierte, modale Box (Pop-up) mit der Eingabeaufforderung für den Namen. Speichern Sie den Namen sofort in einem persistenten Cookie und im Backend in der Session.

Asynchrone Kommunikation: Verwenden Sie Flask-SocketIO oder mindestens periodisches AJAX-Polling (z.B. alle 3 Sekunden), um den Status der Teilnehmerliste und den Wechsel zum "Aufdecken"-Modus in Echtzeit zu aktualisieren, ohne dass Benutzer die Seite neu laden müssen. Dies ist für das Erlebnis am wichtigsten!

Mobile Optimierung: Stellen Sie sicher, dass das Design responsive ist (auch auf dem Handy nutzbar), da Schätzrunden oft spontan und von verschiedenen Geräten aus gemacht werden.
