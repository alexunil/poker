"""
Planning Poker - MVP mit WebSockets und SQLite
Flask-App mit persistenter Datenbank und Admin-Dashboard
"""

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
from functools import wraps
import secrets
import os
import markdown
from datetime import datetime, timedelta

# Database imports
import database as db
from utils import get_current_user, get_active_story, get_pending_stories, get_story_votes
from voting_logic import FIBONACCI, find_majority_value, check_consensus

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
# Sessions bleiben für 10 Jahre gültig (praktisch permanent)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=3650)
socketio = SocketIO(app, cors_allowed_origins="*")

# Admin Configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

# Feature Configuration
ENABLE_UNICORN = os.getenv("ENABLE_UNICORN", "false").lower() == "true"
UNICORN_DISPLAY_SECONDS = int(os.getenv("UNICORN_DISPLAY_SECONDS", "3"))
ENABLE_SPECTATOR_MODE = os.getenv("ENABLE_SPECTATOR_MODE", "true").lower() == "true"


# ============================================================================
# ADMIN AUTHENTICATION
# ============================================================================


def is_admin():
    """Prüft ob aktueller User Admin ist"""
    return session.get("is_admin", False)


def admin_required(f):
    """Decorator für Admin-Routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return decorated_function


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def add_event(message, event_type="info"):
    """Fügt ein Event zum Log hinzu"""
    # Event in Datenbank speichern
    db.create_event(message, event_type)

    # WebSocket: Event broadcasten
    socketio.emit("event_added", {"message": message, "type": event_type})


@app.route("/")
def index():
    user = get_current_user()

    # User hat noch keinen Namen
    if not user:
        return render_template("index.html", need_name=True)

    # Aktive Story holen
    active_story = get_active_story()

    # Konsens berechnen falls revealed
    consensus_type = None
    suggested_points = None
    alternative_points = None
    vote_distribution = None
    if active_story and active_story["status"] == "revealed":
        story_votes = get_story_votes(active_story["id"], active_story["round"])
        if story_votes:
            vote_values = [v["points"] for v in story_votes.values()]
            consensus_type, suggested_points, alternative_points = check_consensus(
                vote_values
            )
            # Vote-Verteilung für Anzeige berechnen
            from collections import Counter

            vote_distribution = dict(Counter(vote_values))

    # Pending stories holen
    pending_stories = get_pending_stories()

    # Story history holen
    story_history = db.get_story_history(limit=3)

    # Alle Users holen für Anzeige
    all_users = db.get_all_users()
    users_dict = {u["session_id"]: u for u in all_users}

    # Anzahl aktiver (nicht-Zuschauer) Users
    active_users_count = db.get_active_users_count()

    # Event Log aus Datenbank laden
    event_log = db.get_recent_events(limit=10)

    # Hauptseite
    return render_template(
        "index.html",
        user=user,
        story=active_story,
        votes=get_story_votes(active_story["id"], active_story["round"])
        if active_story
        else {},
        users=users_dict,
        active_users_count=active_users_count,
        fibonacci=FIBONACCI,
        consensus_type=consensus_type,
        suggested_points=suggested_points,
        alternative_points=alternative_points,
        vote_distribution=vote_distribution,
        story_history=story_history,
        pending_stories=pending_stories,
        event_log=event_log,
        has_active_voting=active_story is not None,
        enable_unicorn=ENABLE_UNICORN,
        unicorn_display_seconds=UNICORN_DISPLAY_SECONDS,
        enable_spectator_mode=ENABLE_SPECTATOR_MODE,
    )


@app.route("/set_name", methods=["POST"])
def set_name():
    name = request.form.get("name", "").strip()
    if name:
        session_id = secrets.token_hex(8)
        session["user_id"] = session_id
        session.permanent = True  # Session bleibt für 10 Jahre erhalten (praktisch permanent)
        db.create_user(name, session_id)
        add_event(f"👋 {name} ist beigetreten", "join")
    return redirect(url_for("index"))


@app.route("/create_story", methods=["POST"])
def create_story():
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    start_immediately = request.form.get("start_immediately", "false") == "true"
    auto_start = request.form.get("auto_start", "false") == "true"

    if title:
        story_id = db.create_story(
            title, description, user["name"], auto_start=auto_start
        )

        add_event(f"📝 {user['name']} hat Story erstellt: {title}", "story_created")

        # Wenn sofort starten gewünscht UND keine aktive Story
        if start_immediately:
            active_story = get_active_story()
            if active_story is None:
                db.start_voting(story_id)
                add_event(f"🎯 Abstimmung für '{title}' gestartet", "voting_started")

                # WebSocket: Voting gestartet
                socketio.emit("voting_started", {"reload": True})
                return redirect(url_for("index"))

        # WebSocket: Benachrichtige alle (Story erstellt)
        socketio.emit("story_created", {"reload": True})

    return redirect(url_for("index"))


@app.route("/start_voting/<int:story_id>", methods=["POST"])
def start_voting(story_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))

    story = db.get_story_by_id(story_id)
    if not story:
        return redirect(url_for("index"))

    # Nur der Ersteller darf die Abstimmung starten
    if story["creator_name"] != user["name"]:
        return redirect(url_for("index"))

    # Prüfe ob bereits eine andere Story in Abstimmung ist
    active_story = get_active_story()
    if active_story is not None:
        return redirect(url_for("index"))

    # Story auf voting setzen
    db.start_voting(story_id)

    add_event(
        f"🎯 {user['name']} hat Abstimmung für '{story['title']}' gestartet",
        "voting_started",
    )

    # WebSocket: Benachrichtige alle
    socketio.emit("voting_started", {"reload": True})

    return redirect(url_for("index"))


@app.route("/vote", methods=["POST"])
def vote():
    user = get_current_user()
    active_story = get_active_story()

    if not user or not active_story:
        return redirect(url_for("index"))

    # Zuschauer können nicht voten
    if user.get("is_spectator"):
        return redirect(url_for("index"))

    points = request.form.get("points")
    try:
        points = int(points)
        if points in FIBONACCI:
            # Vote in DB speichern
            db.cast_vote(
                active_story["id"], user["name"], points, active_story["round"]
            )

            add_event(f"🃏 {user['name']} hat gevoted", "vote")

            # Prüfe ob alle aktiven User abgestimmt haben
            all_voted = db.check_all_active_users_voted(
                active_story["id"], active_story["round"]
            )

            if all_voted:
                # Auto-Reveal: Alle aktiven haben abgestimmt
                db.update_story_status(active_story["id"], "revealed")

                # Konsens berechnen
                story_votes = get_story_votes(active_story["id"], active_story["round"])
                vote_values = [v["points"] for v in story_votes.values()]
                consensus_type, suggested_points, alternative_points = check_consensus(
                    vote_values
                )

                add_event("✨ Auto-Reveal: Alle haben abgestimmt!", "reveal")

                # WebSocket: ERST Einhorn zeigen (cards_revealed)
                vote_list = [
                    {"name": name, "points": v["points"]}
                    for name, v in story_votes.items()
                ]
                socketio.emit(
                    "cards_revealed",
                    {
                        "votes": vote_list,
                        "consensus_type": consensus_type,
                        "suggested_points": suggested_points,
                        "alternative_points": alternative_points,
                    },
                )
            else:
                # WebSocket: Benachrichtige alle (ohne Punkte zu zeigen)
                story_votes = get_story_votes(active_story["id"], active_story["round"])
                all_users = db.get_all_users()
                socketio.emit(
                    "vote_submitted",
                    {
                        "user": user["name"],
                        "vote_count": len(story_votes),
                        "total_users": len(all_users),
                    },
                )
    except (ValueError, TypeError):
        pass

    return redirect(url_for("index"))


@app.route("/reveal", methods=["POST"])
def reveal():
    user = get_current_user()
    active_story = get_active_story()

    if not user or not active_story:
        return jsonify({"error": "Unauthorized"}), 401

    # Nur Ersteller darf aufdecken (oder wenn unlocked)
    if user["name"] != active_story["creator_name"] and not active_story.get(
        "is_unlocked"
    ):
        return jsonify({"error": "Unauthorized"}), 401

    # Status auf revealed setzen
    db.update_story_status(active_story["id"], "revealed")

    # Konsens berechnen
    story_votes = get_story_votes(active_story["id"], active_story["round"])
    vote_values = [v["points"] for v in story_votes.values()]
    consensus_type, suggested_points, alternative_points = check_consensus(vote_values)

    # WebSocket: ERST Einhorn zeigen (cards_revealed)
    vote_list = [
        {"name": name, "points": v["points"]} for name, v in story_votes.items()
    ]
    socketio.emit(
        "cards_revealed",
        {
            "votes": vote_list,
            "consensus_type": consensus_type,
            "suggested_points": suggested_points,
            "alternative_points": alternative_points,
        },
    )

    # DANN Event-Log updaten (sendet event_added)
    add_event(f"🔓 {user['name']} hat Karten aufgedeckt", "reveal")

    return jsonify({"success": True})


@app.route("/complete_story", methods=["POST"])
def complete_story():
    user = get_current_user()
    active_story = get_active_story()

    if not user or not active_story:
        return redirect(url_for("index"))

    # Nur der Ersteller darf die Story abschließen
    if active_story["creator_name"] != user["name"]:
        return redirect(url_for("index"))

    points = request.form.get("final_points")
    try:
        points = int(points)
        # Story als completed markieren mit finalen Punkten
        db.complete_story(active_story["id"], points)

        add_event(
            f"✅ Story '{active_story['title']}' abgeschlossen mit {points} Punkten",
            "completed",
        )

        # Prüfe ob es eine Story mit auto_start gibt
        next_story = db.get_next_auto_start_story()
        if next_story:
            # Starte automatisch die nächste Story
            db.start_voting(next_story["id"])
            add_event(
                f"🎯 Auto-Start: Abstimmung für '{next_story['title']}' gestartet",
                "voting_started",
            )

            # WebSocket: Voting gestartet
            socketio.emit("voting_started", {"reload": True})
        else:
            # WebSocket: Benachrichtige alle (Story completed, keine Auto-Start)
            socketio.emit("story_completed", {"reload": True})
    except (ValueError, TypeError):
        pass

    return redirect(url_for("index"))


@app.route("/new_round", methods=["POST"])
def new_round():
    user = get_current_user()
    active_story = get_active_story()

    if not user or not active_story:
        return redirect(url_for("index"))

    # Nur der Ersteller darf eine neue Runde starten
    if active_story["creator_name"] != user["name"]:
        return redirect(url_for("index"))

    # Runde erhöhen
    new_round_num = active_story["round"] + 1
    db.update_story_round(active_story["id"], new_round_num)
    db.update_story_status(active_story["id"], "voting")

    add_event(f"🔄 Runde {new_round_num} gestartet", "new_round")

    # WebSocket: Benachrichtige alle
    socketio.emit("new_round", {"round": new_round_num})

    return redirect(url_for("index"))


@app.route("/toggle_spectator", methods=["POST"])
def toggle_spectator():
    """Toggle Spectator-Modus für aktuellen User"""
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))

    session_id = session.get("user_id")
    if session_id:
        db.toggle_spectator_mode(session_id)

        # WebSocket: Update alle Clients
        socketio.emit("user_updated", {"reload": True})

    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset():
    """DEPRECATED: Reset wird durch Admin-Dashboard ersetzt"""
    # Diese Route wird beibehalten, tut aber nichts mehr
    # In Zukunft: Redirect zu Admin-Dashboard oder komplett entfernen
    return redirect(url_for("index"))


@app.route("/api/status")
def api_status():
    """API für Live-Updates (optional, für später)"""
    active_story = get_active_story()

    vote_list = []
    vote_count = 0
    if active_story:
        story_votes = get_story_votes(active_story["id"], active_story["round"])
        vote_count = len(story_votes)
        if active_story["status"] == "revealed":
            vote_list = [
                {"name": name, "points": v["points"]} for name, v in story_votes.items()
            ]

    all_users = db.get_all_users()
    return jsonify(
        {
            "story": active_story,
            "votes": vote_list,
            "vote_count": vote_count,
            "users_online": len(all_users),
        }
    )


@app.route("/story/<int:story_id>")
def story_detail(story_id):
    """Detail-Ansicht einer Story mit Kommentaren"""
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))

    story = db.get_story_by_id(story_id)
    if not story:
        return redirect(url_for("index"))

    # Nur completed Stories dürfen kommentiert werden
    if story["status"] != "completed":
        return redirect(url_for("index"))

    # Alle Votes und Kommentare laden
    all_votes = db.get_all_story_votes(story_id)
    comments = db.get_story_comments(story_id)

    return render_template(
        "story_detail.html", user=user, story=story, votes=all_votes, comments=comments
    )


@app.route("/story/<int:story_id>/comment", methods=["POST"])
def add_comment(story_id):
    """Fügt einen Kommentar zu einer Story hinzu"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    story = db.get_story_by_id(story_id)
    if not story or story["status"] != "completed":
        return jsonify({"error": "Story not found or not completed"}), 404

    comment_text = request.form.get("comment_text", "").strip()
    comment_type = request.form.get("comment_type", "general")

    if not comment_text:
        return jsonify({"error": "Comment text required"}), 400

    # Kommentar speichern
    comment_id = db.add_story_comment(story_id, user["name"], comment_text, comment_type)

    # Event-Log
    add_event(
        f"💬 {user['name']} hat Kommentar zu '{story['title']}' hinzugefügt", "comment"
    )

    # WebSocket: Benachrichtige alle
    socketio.emit(
        "comment_added",
        {"story_id": story_id, "user": user["name"], "comment_id": comment_id},
    )

    return jsonify({"success": True, "comment_id": comment_id})


@app.route("/api/story/<int:story_id>/comments")
def api_story_comments(story_id):
    """API-Endpunkt für Kommentare (JSON)"""
    comments = db.get_story_comments(story_id)
    return jsonify(comments)


@app.route("/health")
def health_check():
    """Health check endpoint für Docker"""
    return jsonify({"status": "healthy", "app": "planning-poker"}), 200


@app.route("/anleitung")
def anleitung():
    """Zeigt die Benutzeranleitung als HTML (konvertiert aus Markdown)"""
    try:
        # Markdown-Datei einlesen
        md_file_path = os.path.join(os.path.dirname(__file__), "BENUTZERANLEITUNG.md")
        with open(md_file_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Markdown zu HTML konvertieren
        # Extensions für bessere Formatierung
        md = markdown.Markdown(
            extensions=[
                "extra",  # Tabellen, Definition Lists, etc.
                "codehilite",  # Syntax Highlighting für Code
                "toc",  # Table of Contents
                "nl2br",  # Newline to <br>
            ]
        )
        html_content = md.convert(md_content)

        return render_template("anleitung.html", content=html_content)

    except FileNotFoundError:
        return (
            render_template(
                "anleitung.html",
                content="<h1>Fehler</h1><p>Die Anleitung konnte nicht gefunden werden.</p>",
            ),
            404,
        )
    except Exception as e:
        return (
            render_template(
                "anleitung.html",
                content=f"<h1>Fehler</h1><p>Fehler beim Laden der Anleitung: {str(e)}</p>",
            ),
            500,
        )


@socketio.on("connect")
def handle_connect():
    """Client verbindet sich"""
    user = get_current_user()
    if user:
        emit("connected", {"name": user["name"]})


@socketio.on("disconnect")
def handle_disconnect():
    """Client trennt Verbindung"""
    pass


@socketio.on("request_update")
def handle_request_update():
    """Client fordert aktuellen Status an"""
    user = get_current_user()
    if not user:
        return

    active_story = get_active_story()

    # Sende aktuellen Status
    consensus_type = None
    suggested_points = None
    alternative_points = None
    vote_list = []
    vote_count = 0

    if active_story:
        story_votes = get_story_votes(active_story["id"], active_story["round"])
        vote_count = len(story_votes)

        if active_story["status"] == "revealed" and story_votes:
            vote_values = [v["points"] for v in story_votes.values()]
            consensus_type, suggested_points, alternative_points = check_consensus(
                vote_values
            )
            vote_list = [
                {"name": name, "points": v["points"]} for name, v in story_votes.items()
            ]

    all_users = db.get_all_users()
    emit(
        "status_update",
        {
            "story": active_story,
            "vote_count": vote_count,
            "total_users": len(all_users),
            "votes": vote_list,
            "consensus_type": consensus_type,
            "suggested_points": suggested_points,
            "alternative_points": alternative_points,
        },
    )


# ============================================================================
# ADMIN ROUTES
# ============================================================================


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin Login Seite"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Admin-Credentials prüfen
        if (
            username == ADMIN_USERNAME
            and ADMIN_PASSWORD_HASH
            and check_password_hash(ADMIN_PASSWORD_HASH, password)
        ):
            session["is_admin"] = True
            session.permanent = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", error="Ungültige Zugangsdaten")

    # GET Request - Login-Formular anzeigen
    if is_admin():
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    """Admin Logout"""
    session.pop("is_admin", None)
    return redirect(url_for("index"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin Dashboard mit Story-Historie und User-Aktivität"""
    session.permanent = True  # Session bleibt für 10 Jahre erhalten

    # Alle Stories mit Votes laden
    all_stories = db.get_all_stories()

    # Alle Users mit Aktivität laden
    users_with_activity = db.get_all_users_with_activity()

    return render_template(
        "admin_dashboard.html",
        stories=all_stories,
        users=users_with_activity,
        total_stories=len(all_stories),
        total_users=len(users_with_activity),
    )


@app.route("/admin/export/stories")
@admin_required
def export_stories_markdown():
    """Exportiert alle abgeschlossenen Stories als Markdown-Datei"""
    from flask import make_response

    # Alle abgeschlossenen Stories laden
    all_stories = db.get_all_stories()
    completed_stories = [s for s in all_stories if s["status"] == "completed"]

    # Markdown-Inhalt generieren
    md_content = generate_stories_markdown(completed_stories)

    # Response erstellen mit Markdown-Datei zum Download
    response = make_response(md_content)
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    response.headers[
        "Content-Disposition"
    ] = f"attachment; filename=planning_poker_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    return response


def generate_stories_markdown(stories):
    """Generiert formatiertes Markdown aus Stories"""
    lines = []

    # Header
    lines.append("# Planning Poker - Story Export")
    lines.append("")
    lines.append(f"**Exportiert am:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    lines.append(
        f"**Anzahl Stories:** {len(stories)} (nur abgeschlossene Stories)"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Jede Story
    for idx, story in enumerate(stories, 1):
        lines.append(f"## {idx}. {story['title']}")
        lines.append("")

        # Metadaten
        lines.append("### 📋 Story-Details")
        lines.append("")
        if story.get("description"):
            lines.append(f"**Beschreibung:**")
            lines.append(f"{story['description']}")
            lines.append("")
        lines.append(f"**Ersteller:** {story['creator_name']}")
        lines.append(f"**Finale Punktzahl:** {story['final_points']} Story Points")
        lines.append(f"**Erstellt am:** {story['created_at']}")
        lines.append(f"**Abgeschlossen am:** {story['completed_at']}")
        lines.append(f"**Anzahl Runden:** {story['round']}")
        lines.append("")

        # Abstimmungsergebnisse
        lines.append("### 🗳️ Abstimmungsergebnisse")
        lines.append("")

        if story.get("all_votes"):
            # Gruppiere Votes nach Runde
            from collections import defaultdict

            votes_by_round = defaultdict(list)
            for vote in story["all_votes"]:
                votes_by_round[vote["round"]].append(vote)

            for round_num in sorted(votes_by_round.keys()):
                votes = votes_by_round[round_num]
                lines.append(f"**Runde {round_num}:**")
                lines.append("")

                # Tabelle für bessere Lesbarkeit
                lines.append("| Name | Punkte | Zeitstempel |")
                lines.append("|------|--------|-------------|")
                for vote in sorted(votes, key=lambda v: v.get("voted_at", "")):
                    name = vote.get("name", "N/A")
                    points = vote.get("points", "N/A")
                    timestamp = vote.get("voted_at", "N/A")
                    lines.append(f"| {name} | {points} | {timestamp} |")

                lines.append("")

                # Statistik für diese Runde
                vote_values = [v["points"] for v in votes if "points" in v]
                if vote_values:
                    lines.append(
                        f"- **Durchschnitt:** {sum(vote_values) / len(vote_values):.1f}"
                    )
                    lines.append(f"- **Minimum:** {min(vote_values)}")
                    lines.append(f"- **Maximum:** {max(vote_values)}")
                    lines.append("")
        else:
            lines.append("*Keine Abstimmungsdaten vorhanden.*")
            lines.append("")

        # Kommentare (falls vorhanden)
        if story.get("comments"):
            lines.append("### 💬 Kommentare")
            lines.append("")

            # Gruppiere Kommentare nach Typ
            comment_type_labels = {
                "reasoning": "✅ Begründung für Punktzahl",
                "execution": "⚠️ Hinweise zur Ausführung",
                "acceptance": "📋 Akzeptanzkriterien",
                "general": "💡 Allgemeine Anmerkungen",
            }

            for comment in story["comments"]:
                comment_type = comment.get("comment_type", "general")
                type_label = comment_type_labels.get(comment_type, "💡 Kommentar")
                user_name = comment.get("user_name", "Unbekannt")
                created_at = comment.get("created_at", "")

                lines.append(f"#### {type_label}")
                lines.append(f"**Von:** {user_name} | **Am:** {created_at}")
                lines.append("")
                lines.append(f"{comment.get('comment_text', '')}")
                lines.append("")
        else:
            lines.append("### 💬 Kommentare")
            lines.append("")
            lines.append("*Keine Kommentare vorhanden.*")
            lines.append("")

        # Trennlinie zwischen Stories
        lines.append("---")
        lines.append("")

    # Zusammenfassung am Ende
    lines.append("## 📊 Zusammenfassung")
    lines.append("")
    lines.append(f"- **Gesamt Stories:** {len(stories)}")

    if stories:
        total_points = sum(s["final_points"] for s in stories if s.get("final_points"))
        avg_points = total_points / len(stories) if stories else 0
        lines.append(f"- **Durchschnittliche Story Points:** {avg_points:.1f}")

        total_comments = sum(len(s.get("comments", [])) for s in stories)
        lines.append(f"- **Gesamt Kommentare:** {total_comments}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "*Dieser Export wurde automatisch von Planning Poker generiert.*"
    )

    return "\n".join(lines)


# ============================================================================
# APP INITIALIZATION
# ============================================================================

if __name__ == "__main__":
    # Datenbank initialisieren (Pfad aus Umgebungsvariable)
    db_path = os.getenv("DB_PATH", "planning_poker.db")
    print(f"Initialisiere Datenbank: {db_path}")
    db.init_db(db_path)
    print("Starte Flask-App...")
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
