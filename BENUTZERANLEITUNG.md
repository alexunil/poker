# Planning Poker - Benutzeranleitung

## Was ist Planning Poker?

Planning Poker ist eine Technik, mit der Scrum-Teams gemeinsam User Stories schätzen. Jeder gibt verdeckt eine Schätzung ab, dann werden alle Karten gleichzeitig aufgedeckt. Bei unterschiedlichen Meinungen wird diskutiert und erneut geschätzt.

## 🌟 Vorteile gegenüber estimationpoker.de

### Warum dieses Tool statt estimationpoker.de?

**1. Persistente Sessions - Kein Nerv-Faktor** 🎯
- **Hier:** Dein Name bleibt gespeichert - **auch nach Wochen!** Kein nerviges Re-Login.
- **estimationpoker.de:** Musst du dich jedes Mal neu anmelden.

**2. Vollständige Story-Historie** 📚
- **Hier:** Alle Stories, Votes und Kommentare werden **dauerhaft gespeichert**.
- **Admin-Export:** Stories als Markdown exportieren für Dokumentation.
- **estimationpoker.de:** Daten gehen beim Verlassen verloren.

**3. Spectator Mode** 👁️
- **Hier:** Product Owner oder Stakeholder können zuschauen, **ohne zu voten**.
- **estimationpoker.de:** Alle müssen abstimmen oder stören die Zählung.

**4. Smart Features** 🚀
- **Auto-Start Queue:** Stories starten automatisch nacheinander.
- **Auto-Reveal:** Automatisches Aufdecken wenn alle gevoted haben.
- **Alternative Punktzahl:** Bei Divergenz wird auch eine Alternative angeboten.
- **estimationpoker.de:** Keine dieser Funktionen.

**5. Kommentare & Begründungen** 💬
- **Hier:** Nach der Abstimmung können Begründungen, Hinweise und Akzeptanzkriterien festgehalten werden.
- **estimationpoker.de:** Keine Kommentarfunktion.

**6. Datenschutz & Kontrolle** 🔒
- **Hier:** Selbst gehostet, **eure Daten bleiben bei euch**.
- **Keine Tracking-Cookies**, keine externe Abhängigkeit.
- **estimationpoker.de:** Drittanbieter-Service, keine Kontrolle über Daten.

**7. Admin-Dashboard** 📊
- **Hier:** Überblick über alle Stories, User-Aktivität, Statistiken.
- **Export-Funktion** für Backups und Dokumentation.
- **estimationpoker.de:** Keine Admin-Funktionen.

**8. Modernes Design** 🎨
- **Hier:** Responsive, modern, Dark-Mode-fähig (via Pico.css).
- **Einhorn-Easteregg** beim Aufdecken 🦄
- **estimationpoker.de:** Veraltetes UI.

**9. Offline-fähig** 🌐
- **Hier:** Läuft im internen Netzwerk - **funktioniert ohne Internet**.
- **estimationpoker.de:** Braucht Internetverbindung.

**10. Open Source & Anpassbar** ⚙️
- **Hier:** Code einsehbar, anpassbar an eure Bedürfnisse.
- **estimationpoker.de:** Closed Source, keine Anpassungen möglich.

### Fazit

Dieses Tool ist speziell für Teams entwickelt, die **professionell arbeiten** und ihre Daten **unter Kontrolle** haben wollen. Perfekt für regelmäßige Scrum-Teams mit wiederkehrenden Estimation Sessions.

---

## Erste Schritte

### 1. Namen eingeben (nur beim ersten Mal)
Wenn du das Tool zum ersten Mal besuchst, erscheint ein **Pop-up in der Mitte des Bildschirms**, das dich nach deinem Namen fragt.

**So geht's:**
1. Gib einfach deinen Vornamen oder einen Spitznamen ein
2. Das Tool speichert deinen Namen automatisch
3. Beim nächsten Besuch wirst du sofort erkannt - kein Login nötig!

## Eine Story schätzen

### 2. Neue Story anlegen

**Wann?** Wenn noch keine Story aktiv ist, siehst du einen großen Button "Neue Story anlegen".

**So geht's:**
1. Klicke auf den großen Button "Neue Story anlegen"
2. Gib einen **Titel** ein (z.B. "User kann sich einloggen")
3. Optional: Schreibe eine **Beschreibung** mit Details zur Story (großes Textfeld)
4. Klicke auf **"Story starten & Schätzung freigeben"**

**Wichtig:** Sobald eine Story aktiv ist, wird der Button "Neue Story anlegen" für alle ausgegraut - bis die aktuelle Story abgeschlossen ist!

### 3. Deine Schätzung abgeben

Du siehst jetzt:
- Den Story-Titel und die Beschreibung (groß und prominent)
- **Große, klickbare Buttons** mit Fibonacci-Zahlen: **0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89**
- Eine Teilnehmerliste mit Live-Status:
  - Name ohne Symbol = Person hat noch nicht geschätzt
  - Name mit **grünem Haken ✓** oder Kartensymbol = Person hat geschätzt (Wert ist verdeckt!)

**So schätzt du:**
1. Wähle eine Zahl, die deiner Meinung nach zur Story passt
2. Klicke auf den entsprechenden Button
3. **Visuelles Feedback**: Der Button wird hervorgehoben (z.B. farbig umrandet)
4. Ein **Haken-Symbol erscheint** - deine Karte ist abgelegt!
5. Deine gewählte Zahl verschwindet (verdeckt)
6. Die anderen sehen nur, dass du gevoted hast, aber **nicht welche Zahl**

**Du kannst deine Meinung ändern:** Klicke einfach auf eine andere Zahl, solange die Karten noch nicht aufgedeckt wurden.

**Echtzeit-Updates:** Die Teilnehmerliste aktualisiert sich automatisch - du siehst sofort, wenn jemand seine Karte legt. Kein Neuladen nötig!

### 4. Karten aufdecken

#### Normaler Fall: Story-Ersteller deckt auf

**Wenn du die Story erstellt hast**, siehst du zusätzlich einen hervorgehobenen Button **"Karten aufdecken!"**

Du musst nicht warten, bis alle gevoted haben - du kannst jederzeit aufdecken!

Nach dem Klick passiert ein **dramatischer Moment**:
1. Ein **Einhorn erscheint** mit einem weisen Spruch in einer Sprechblase (nur zur Unterhaltung 🦄)
2. Nach 2-3 Sekunden werden alle Karten gleichzeitig eingeblendet!

#### Notfall: Story-Ersteller ist nicht verfügbar

**Problem:** Der Story-Ersteller musste dringend weg, hat kein Internet mehr, oder ist aus anderen Gründen nicht verfügbar.

**Lösung - Story entsperren:**
1. Alle anderen Teilnehmer sehen einen Button **"Story entsperren"**
2. Du klickst auf "Story entsperren"
3. Du siehst, wie viele andere ebenfalls entsperren möchten (z.B. "1 von 2 nötigen Stimmen")
4. Sobald **mindestens 2 Personen** auf "Entsperren" geklickt haben:
   - Die Story wird entsperrt
   - Jetzt kann jeder die Karten aufdecken
   - Das verhindert, dass die Story blockiert bleibt

**Hinweis:** Dieses Feature ist nur für Notfälle gedacht. Normalerweise sollte der Story-Ersteller aufdecken!

### 5. Ergebnis ansehen

Nach dem Aufdecken seht ihr alle:
- Eine **Liste mit Namen und ihren gewählten Zahlen**
- Ein **Balkendiagramm** oder Streudiagramm, das die Verteilung der Schätzungen visualisiert
- Das Ergebnis der Schätzung

**Es gibt drei mögliche Ergebnisse:**

#### ✅ Perfekter Konsens
Alle haben die gleiche Zahl gewählt.

**Was du siehst:**
- Große, **grüne Nachricht**: "KONSENS ERREICHT! Vorgeschlagene Punktzahl: [Wert]"
- Button: "Story abschließen"

Die Story wird mit diesem Wert abgeschlossen. ✓

#### ✅ Fast-Konsens
Fast alle haben die gleiche Zahl, nur eine Person weicht um genau eine Fibonacci-Zahl ab.

**Beispiel:** Vier Personen wählen "5", eine Person wählt "3" oder "8"

**Was du siehst:**
- Große, **grüne Nachricht**: "KONSENS ERREICHT! Vorgeschlagene Punktzahl: 5"
- Button: "Story abschließen"

Die Story wird mit der Mehrheitszahl abgeschlossen. ✓

#### 🔄 Divergenz
Die Meinungen gehen auseinander.

**Beispiel:** Jemand wählt "2", jemand "8", jemand "13"

**Was du siehst:**
- Große, **orangefarbene Nachricht**: "KEIN KONSENS. Höchster Wert: 13"
- Zwei Buttons:
  - **"Story mit 13 Punkten abschließen"**: Akzeptiere den höchsten Wert
  - **"Neu abstimmen (Start neue Runde)"**: Diskutiert kurz und stimmt erneut ab

Bei "Neu abstimmen" startet Runde 2 - gleicher Ablauf wie vorher.

## Tipps

### Was bedeuten die Fibonacci-Zahlen?
- **0**: Trivial, fast kein Aufwand
- **1**: Sehr klein, schnell erledigt
- **2, 3**: Kleine Aufgabe
- **5**: Mittlere Aufgabe
- **8, 13**: Größere Aufgabe
- **21+**: Sehr große Aufgabe (sollte vielleicht aufgeteilt werden!)

### Gute Praxis
- **Verdeckt voten**: Lass dich nicht von anderen beeinflussen, wähle deine eigene Einschätzung
- **Bei großer Divergenz**: Lasst die Personen mit der höchsten und niedrigsten Schätzung ihre Sichtweise erklären
- **Große Stories aufteilen**: Wenn ihr oft bei 21+ landet, ist die Story vielleicht zu groß

## Häufige Fragen

**Q: Kann ich meine Schätzung ändern?**
A: Ja, solange die Karten noch nicht aufgedeckt wurden, kannst du einfach eine andere Zahl wählen.

**Q: Muss ich warten, bis alle gevoted haben?**
A: Nein! Der Story-Ersteller kann jederzeit aufdecken. Aber meistens wartet man aus Höflichkeit. 😊

**Q: Was passiert, wenn ich während der Abstimmung die Seite aktualisiere?**
A: Dein Vote ist bereits gespeichert. Nach dem Neuladen siehst du den aktuellen Stand. Normalerweise musst du aber gar nicht neu laden - alles aktualisiert sich automatisch in Echtzeit!

**Q: Wo finde ich alte Stories?**
A: (Falls implementiert) Unter der aktiven Story gibt es eine Liste der abgeschlossenen Stories mit ihren finalen Punktzahlen.

**Q: Können mehrere Teams gleichzeitig das Tool nutzen?**
A: Aktuell nicht - es gibt nur eine aktive Story zur gleichen Zeit. Für mehrere Teams bräuchte man separate Räume (zukünftige Erweiterung).

**Q: Was passiert, wenn der Story-Ersteller plötzlich weg ist und nicht aufdecken kann?**
A: Kein Problem! Mindestens 2 andere Teilnehmer können die Story "entsperren", indem sie auf den Button "Story entsperren" klicken. Danach kann jeder aufdecken.

**Q: Was hat es mit dem Einhorn beim Aufdecken auf sich?**
A: Das ist nur ein kleiner Gag zur Auflockerung! Das Einhorn erscheint kurz mit einem weisen Spruch, bevor die Ergebnisse gezeigt werden. Pure Unterhaltung! 🦄

## Benutzeroberfläche im Überblick

Das Tool ist bewusst **minimalistisch** gestaltet - keine Menüs, keine Ablenkungen. Du siehst immer nur das, was gerade wichtig ist:

- **Große, klare Buttons** für alle wichtigen Aktionen
- **Farbcodierung**: Grün = Konsens/Erfolg, Orange = Diskussion nötig
- **Echtzeit-Updates**: Keine F5 nötig - alles passiert live
- **Mobile-freundlich**: Funktioniert auf Handy, Tablet und Desktop

## Probleme?

Falls etwas nicht funktioniert:
1. Versuche die Seite neu zu laden (F5)
2. Prüfe, ob dein Browser aktuell ist (Chrome, Firefox, Safari, Edge)
3. Kontaktiere den Administrator

---

**Viel Erfolg beim Schätzen! 🎯**
