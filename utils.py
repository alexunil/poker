"""
Helper Functions für Planning Poker
Utility-Funktionen für Session-Management und Story-Zugriff
"""

from flask import session
import database as db


def get_current_user():
    """Gibt den aktuellen User zurück oder None"""
    session_id = session.get("user_id")
    if session_id:
        user = db.get_user_by_session(session_id)
        if user:
            # Update last_seen
            db.update_user_last_seen(session_id)
            return user
    return None


def get_active_story():
    """Gibt die aktive Story zurück (voting oder revealed) oder None"""
    return db.get_active_story()


def get_pending_stories():
    """Gibt alle Stories mit Status 'pending' zurück"""
    return db.get_pending_stories()


def get_story_votes(story_id, round_num):
    """Gibt die Votes für eine bestimmte Story und Runde zurück"""
    return db.get_story_votes(story_id, round_num)
