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
import random
import markdown
from datetime import datetime, timedelta

# Database imports
import database as db
from utils import get_current_user, get_active_story, get_pending_stories, get_story_votes
from voting_logic import FIBONACCI, find_majority_value, check_consensus

# AI imports (optional - graceful degradation if not available)
try:
    from ai.estimation import (
        is_ai_enabled,
        estimate_story_with_ai,
        get_ai_user_name,
        is_ai_user
    )
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️  AI module not available - continuing without AI features")

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
UNICORN_FREQUENCY = int(os.getenv("UNICORN_FREQUENCY", "2"))  # 0-10: Wie oft pro 10 Reveals erscheint das Einhorn
ENABLE_SPECTATOR_MODE = os.getenv("ENABLE_SPECTATOR_MODE", "true").lower() == "true"
ENABLE_AI_ASSISTANT = os.getenv("ENABLE_AI_ASSISTANT", "true").lower() == "true"

# Einhorn-Sprüche (werden vom Server ausgewählt, damit alle dasselbe sehen)
UNICORN_QUOTES = [
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
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def should_show_unicorn():
    """
    Würfelt ob das Einhorn erscheinen soll basierend auf UNICORN_FREQUENCY.

    Returns:
        bool: True wenn Einhorn erscheinen soll, False sonst

    Beispiel:
        UNICORN_FREQUENCY=2 -> 2 von 10 Fällen (20% Wahrscheinlichkeit)
        UNICORN_FREQUENCY=10 -> Immer
        UNICORN_FREQUENCY=0 -> Nie
    """
    if not ENABLE_UNICORN:
        return False

    if UNICORN_FREQUENCY <= 0:
        return False

    if UNICORN_FREQUENCY >= 10:
        return True

    # Würfeln: Zahl zwischen 1-10, erscheint wenn <= UNICORN_FREQUENCY
    roll = random.randint(1, 10)
    return roll <= UNICORN_FREQUENCY


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_ai_user():
    """Initialisiert AI-User beim App-Start"""
    if not ENABLE_AI_ASSISTANT:
        print("ℹ️  AI Assistant disabled via ENABLE_AI_ASSISTANT=false")
        return

    if not AI_AVAILABLE:
        print("⚠️  AI module not available - AI Assistant will not participate")
        db.create_event(
            "⚠️ AI Assistant nicht verfügbar (Modul nicht geladen)",
            "ai_unavailable"
        )
        return

    # Prüfe AI-Verfügbarkeit
    from ai.estimation import check_ai_availability
    available, error = check_ai_availability()

    if not available:
        print(f"⚠️  AI not enabled: {error}")
        db.create_event(
            f"⚠️ AI Assistant nicht verfügbar ({error})",
            "ai_unavailable"
        )
        return

    try:
        # AI User erstellen/aktualisieren
        ai_user_name = get_ai_user_name()
        ai_user = db.get_user_by_name(ai_user_name)

        if not ai_user:
            # Erstelle AI User mit fixer Session ID
            db.create_user(ai_user_name, session_id="ai_assistant_session")
            print(f"✅ AI Assistant initialized: {ai_user_name}")

            # Event hinzufügen
            db.create_event(
                f"🤖 AI Assistant ist dem Team beigetreten",
                "ai_joined"
            )
        else:
            # Update last_seen
            db.update_user_last_seen("ai_assistant_session")
            print(f"✅ AI Assistant active: {ai_user_name}")
    except Exception as e:
        print(f"⚠️  Could not initialize AI user: {e}")
        db.create_event(
            f"⚠️ AI Assistant Fehler: {str(e)}",
            "ai_error"
        )


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


def truncate_title(title: str, max_length: int = 40) -> str:
    """Kürzt Story-Titel auf max_length Zeichen und fügt Anführungszeichen hinzu"""
    if len(title) > max_length:
        return f'"{title[:max_length]}..."'
    return f'"{title}"'


def add_event(message, event_type="info"):
    """Fügt ein Event zum Log hinzu"""
    # Event in Datenbank speichern
    db.create_event(message, event_type)

    # WebSocket: Event broadcasten
    socketio.emit("event_added", {"message": message, "type": event_type})


# ============================================================================
# AI ESTIMATION HELPERS
# ============================================================================


def trigger_ai_estimation(story_id):
    """
    Triggert AI-Schätzung für eine Story im Hintergrund

    Args:
        story_id: Story ID
    """
    if not ENABLE_AI_ASSISTANT:
        return

    if not AI_AVAILABLE:
        print(f"⚠️  AI not available - skipping estimation for story {story_id}")
        return

    if not is_ai_enabled():
        print(f"⚠️  AI not enabled - skipping estimation for story {story_id}")
        return

    print(f"🤖 Triggering AI estimation for story {story_id}...")
    # Background Task starten
    socketio.start_background_task(_estimate_in_background, story_id)


def _estimate_in_background(story_id):
    """
    Background Task: AI-Schätzung durchführen und Vote abgeben

    Args:
        story_id: Story ID
    """
    import json
    import time

    print(f"🤖 AI background task started for story {story_id}")

    try:
        # Event: AI wird befragt
        add_event(
            "🤖 AI Assistant wird befragt...",
            "ai_estimating"
        )
        socketio.emit("ai_status_update", {
            'status': 'estimating',
            'story_id': story_id
        })

        print(f"🤖 Calling estimate_story_with_ai({story_id})...")
        # AI-Schätzung durchführen
        result = estimate_story_with_ai(story_id)

        if not result:
            print(f"⚠️  AI estimation returned no result for story {story_id}")
            add_event(
                "⚠️ AI Assistant konnte keine Schätzung abgeben",
                "ai_error"
            )
            return

        print(f"🤖 AI estimation result: {result.get('points')} SP")

        # Event: AI hat erfolgreich geschätzt
        add_event(
            "✅ AI Assistant wurde erfolgreich befragt",
            "ai_estimated"
        )

        # Aktuelle Runde ermitteln
        story = db.get_story_by_id(story_id)
        if not story or story['status'] != 'voting':
            print(f"⚠️  Story {story_id} not in voting state")
            return

        current_round = story.get('round', 1)

        # Vote abgeben als AI User
        ai_user_name = get_ai_user_name()

        # Prüfe ob AI User existiert, wenn nicht erstelle ihn
        ai_user = db.get_user_by_name(ai_user_name)
        if not ai_user:
            db.create_user(ai_user_name, session_id="ai_assistant_session")

        # Vote abgeben
        success = db.cast_vote(
            story_id=story_id,
            user_name=ai_user_name,
            points=result['points'],
            round_num=current_round
        )

        if not success:
            print(f"❌ Failed to cast AI vote for story {story_id}")
            return

        print(f"✅ AI vote cast successfully: {result['points']} SP")

        # Begründung speichern
        similar_stories_json = json.dumps([
            {
                'title': s['story']['title'],
                'points': s['story']['final_points'],
                'similarity': s['similarity']
            }
            for s in result['similar_stories']
        ])

        db.save_ai_estimation(
            story_id=story_id,
            vote_id=None,  # vote_id ist optional
            reasoning=result['reasoning'],
            similar_stories=similar_stories_json,
            model_used=result['model_used']
        )
        print(f"✅ AI reasoning saved for story {story_id}")

        # Event hinzufügen (ohne Points zu spoilern!)
        add_event(
            "🤖 AI Assistant hat eine Karte gelegt",
            "ai_vote"
        )

        # WebSocket: Alle benachrichtigen
        socketio.emit("vote_submitted", {
            'user': ai_user_name,
            'is_ai': True,
            'reload': True
        })

        print(f"✅ AI estimation completed: {result['points']} SP for story {story_id}")

    except Exception as e:
        print(f"❌ AI estimation failed for story {story_id}: {e}")
        import traceback
        traceback.print_exc()

        # Event bei Fehler
        add_event(
            f"❌ AI Assistant Fehler: {str(e)[:100]}",
            "ai_error"
        )


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
    users_dict = {u["session_id"]: u for u in all_users if u["session_id"]}

    # AI User sollte schon in all_users sein (mit session_id="ai_assistant_session")

    # Anzahl aktiver (nicht-Zuschauer) Users
    active_users_count = db.get_active_users_count()

    # Event Log aus Datenbank laden
    event_log = db.get_recent_events(limit=10)

    # Aktuellen Vote des Users ermitteln (für Karten-Markierung)
    current_user_vote = None
    if active_story and active_story["status"] == "voting":
        votes_dict = get_story_votes(active_story["id"], active_story["round"])
        if user["name"] in votes_dict:
            current_user_vote = votes_dict[user["name"]]["points"]

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
        current_user_vote=current_user_vote,
        enable_spectator_mode=ENABLE_SPECTATOR_MODE,
        ai_available=AI_AVAILABLE and is_ai_enabled() if AI_AVAILABLE else False,
        ai_user_name=get_ai_user_name() if (AI_AVAILABLE and is_ai_enabled()) else None,
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

        add_event(f"📝 {user['name']} hat Story erstellt: {truncate_title(title)}", "story_created")

        # Wenn sofort starten gewünscht UND keine aktive Story
        if start_immediately:
            active_story = get_active_story()
            if active_story is None:
                db.start_voting(story_id)
                add_event(f"🎯 Abstimmung für {truncate_title(title)} gestartet", "voting_started")

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

    # AI-Schätzung triggern (im Hintergrund)
    trigger_ai_estimation(story_id)

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
                # Würfeln ob Einhorn erscheint und Spruch auswählen
                show_unicorn = should_show_unicorn()
                unicorn_quote = random.choice(UNICORN_QUOTES) if show_unicorn else None
                socketio.emit(
                    "cards_revealed",
                    {
                        "votes": vote_list,
                        "consensus_type": consensus_type,
                        "suggested_points": suggested_points,
                        "alternative_points": alternative_points,
                        "show_unicorn": show_unicorn,
                        "unicorn_quote": unicorn_quote,
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
    # Würfeln ob Einhorn erscheint und Spruch auswählen
    show_unicorn = should_show_unicorn()
    unicorn_quote = random.choice(UNICORN_QUOTES) if show_unicorn else None
    socketio.emit(
        "cards_revealed",
        {
            "votes": vote_list,
            "consensus_type": consensus_type,
            "suggested_points": suggested_points,
            "alternative_points": alternative_points,
            "show_unicorn": show_unicorn,
            "unicorn_quote": unicorn_quote,
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


@app.route("/withdraw_story/<int:story_id>", methods=["POST"])
def withdraw_story_route(story_id):
    """Stellt eine aktive Story zurück in die Queue"""
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))

    # Hole Story-Daten
    active_story = get_active_story()
    if not active_story or active_story["id"] != story_id:
        return redirect(url_for("index"))

    # Nur der Ersteller darf die Story zurückstellen
    if active_story["creator_name"] != user["name"]:
        return redirect(url_for("index"))

    # Story zurückstellen
    if db.withdraw_story(story_id):
        add_event(
            f"↩️ Story '{active_story['title']}' zurückgestellt",
            "story_withdrawn"
        )

        # WebSocket: Benachrichtige alle Clients
        socketio.emit("story_withdrawn", {
            "story_id": story_id,
            "title": active_story["title"]
        })

    return redirect(url_for("index"))


@app.route("/delete_story/<int:story_id>", methods=["POST"])
def delete_story_route(story_id):
    """Löscht eine Story permanent aus der Queue"""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    # Hole Story-Daten
    story = db.get_story_by_id(story_id)
    if not story:
        return jsonify({"success": False, "error": "Story not found"}), 404

    # Nur der Ersteller darf die Story löschen
    if story["creator_name"] != user["name"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    # Sicherheitscheck: Nur pending Stories löschen
    if story["status"] != "pending":
        return jsonify({"success": False, "error": "Only pending stories can be deleted"}), 400

    # Story löschen
    if db.delete_story(story_id):
        add_event(
            f"🗑️ Story '{story['title']}' gelöscht",
            "story_deleted"
        )

        # WebSocket: Benachrichtige alle Clients
        socketio.emit("story_deleted", {
            "story_id": story_id,
            "title": story["title"]
        })

        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Delete failed"}), 500


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
# AI API ROUTES
# ============================================================================


@app.route("/api/ai-reasoning/<int:story_id>")
def get_ai_reasoning(story_id):
    """
    API: Gibt die AI-Begründung für eine Story zurück

    Args:
        story_id: Story ID

    Returns:
        JSON mit reasoning und similar_stories
    """
    import json

    if not AI_AVAILABLE:
        return jsonify({'error': 'AI not available'}), 503

    # Hole AI-Estimation
    estimation = db.get_ai_estimation_by_story(story_id)

    if not estimation:
        return jsonify({'error': 'No AI estimation found'}), 404

    # Parse similar_stories JSON
    similar_stories = []
    if estimation.get('similar_stories'):
        try:
            similar_stories = json.loads(estimation['similar_stories'])
        except:
            pass

    return jsonify({
        'reasoning': estimation['reasoning'],
        'similar_stories': similar_stories,
        'model_used': estimation['model_used'],
        'created_at': estimation['created_at']
    })


@app.route("/api/ai-status")
def get_ai_status():
    """
    API: Gibt AI-Verfügbarkeits-Status zurück

    Returns:
        JSON mit is_available
    """
    if not ENABLE_AI_ASSISTANT:
        return jsonify({'is_available': False, 'reason': 'AI Assistant disabled via config'})

    if not AI_AVAILABLE:
        return jsonify({'is_available': False, 'reason': 'AI module not loaded'})

    is_available = is_ai_enabled()
    return jsonify({
        'is_available': is_available,
        'ai_user_name': get_ai_user_name() if is_available else None
    })


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


@app.route("/admin/import/archive-stories", methods=["POST"])
@admin_required
def import_archive_stories_csv():
    """Importiert Archive-Stories aus CSV-Datei"""
    import csv
    from io import StringIO
    from flask import flash, make_response

    # Check if file was uploaded
    if 'csv_file' not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen"}), 400

    file = request.files['csv_file']

    if file.filename == '':
        return jsonify({"error": "Keine Datei ausgewählt"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Nur CSV-Dateien erlaubt"}), 400

    try:
        # Read CSV content
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(content))

        imported_count = 0
        skipped_count = 0
        errors = []

        for row_num, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
            try:
                title = row.get('title', '').strip()
                description = row.get('description', '').strip()
                jira_key = row.get('jira_key', '').strip()
                story_points_str = row.get('story_points', '').strip()

                # Validate required fields
                if not title:
                    errors.append(f"Zeile {row_num}: Titel fehlt")
                    skipped_count += 1
                    continue

                # Parse story points (can be empty)
                final_points = None
                if story_points_str:
                    try:
                        final_points = int(story_points_str)
                    except ValueError:
                        errors.append(f"Zeile {row_num}: Ungültige Story Points '{story_points_str}'")
                        skipped_count += 1
                        continue

                # Create archive story (using jira_archive source for compatibility)
                db.create_story(
                    title=title,
                    description=description,
                    creator_name="CSV Import",
                    auto_start=False,
                    source='jira_archive',
                    jira_key=jira_key if jira_key else None,
                    status='completed',
                    final_points=final_points,
                    completed_at=datetime.now()
                )

                imported_count += 1

            except Exception as e:
                errors.append(f"Zeile {row_num}: {str(e)}")
                skipped_count += 1

        # Build response message
        result = {
            "success": True,
            "imported": imported_count,
            "skipped": skipped_count,
            "errors": errors[:10]  # Limit errors to first 10
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Fehler beim Verarbeiten der CSV: {str(e)}"}), 500


@app.route("/admin/embedding-status", methods=["GET"])
@admin_required
def get_embedding_status():
    """Gibt Status über Stories ohne Embeddings zurück"""
    try:
        stats = db.get_stories_without_embeddings()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/generate-embeddings", methods=["POST"])
@admin_required
def generate_missing_embeddings():
    """Generiert Embeddings für alle Stories ohne Embeddings"""
    try:
        # Check if AI dependencies are available
        if not AI_AVAILABLE:
            return jsonify({
                "error": "KI-Module sind nicht verfügbar. Bitte AI-Dependencies installieren."
            }), 400

        # Import AI dependencies
        from ai.database_ai import init_ai_db, create_chunk, get_chunks_by_source
        from ai.preprocessing import get_preprocessor
        from ai.chunking import chunk_story
        from ai.embeddings import create_generator
        import ai.database_ai as db_ai

        # Init AI DB
        init_ai_db()

        # Get provider from request or use default
        provider = request.json.get("provider", "sentence_transformers") if request.is_json else "sentence_transformers"
        strategy = request.json.get("strategy", "story") if request.is_json else "story"

        # Setup
        preprocessor = get_preprocessor()
        generator = create_generator(provider)

        # Get stories without embeddings
        stats = db.get_stories_without_embeddings()
        stories_to_process = stats["missing_stories"]

        if not stories_to_process:
            return jsonify({
                "success": True,
                "message": "Keine Stories zum Verarbeiten gefunden",
                "processed": 0,
                "errors": []
            })

        processed_count = 0
        error_count = 0
        errors = []

        for story_info in stories_to_process:
            try:
                # Load full story
                story = db.get_story_by_id(story_info["id"])
                if not story:
                    continue

                # Check if already processed (race condition check)
                existing = get_chunks_by_source('story', story['id'])
                if existing:
                    continue

                # Preprocessing
                cleaned = preprocessor.preprocess_story(story, include_votes=True)

                # Chunking
                chunks = chunk_story(cleaned['combined_text'])

                # Create chunks and embeddings
                for chunk in chunks:
                    chunk_id = create_chunk(
                        source_type='story',
                        source_id=story['id'],
                        chunk_text=chunk['text'],
                        chunk_index=chunk['index'],
                        chunk_strategy=strategy
                    )

                    generator.generate_and_store(
                        chunk_id=chunk_id,
                        text=chunk['text'],
                        db_module=db_ai
                    )

                processed_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Story {story_info['id']}: {str(e)}")
                continue

        return jsonify({
            "success": True,
            "processed": processed_count,
            "errors": error_count,
            "error_messages": errors[:10]  # Limit to first 10 errors
        })

    except Exception as e:
        return jsonify({"error": f"Fehler beim Generieren der Embeddings: {str(e)}"}), 500


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

    # AI-User initialisieren
    print("Initialisiere AI Assistant...")
    initialize_ai_user()

    print("Starte Flask-App...")
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
