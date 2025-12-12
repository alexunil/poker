"""
MCP Server Foundation für Planning Poker
Basis-Implementierung für Model Context Protocol Server
"""

import sys
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime


class MCPServer:
    """
    Basis-Klasse für MCP Server
    Verwaltet Tool-Registrierung und Request-Handling
    """

    def __init__(self, name: str, version: str = "0.1.0"):
        """
        Args:
            name: Name des MCP Servers
            version: Version des Servers
        """
        self.name = name
        self.version = version
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_handlers: Dict[str, Callable] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ):
        """
        Registriert ein Tool beim MCP Server

        Args:
            name: Tool-Name
            description: Tool-Beschreibung
            parameters: JSON Schema für Parameter
            handler: Handler-Funktion für Tool-Aufrufe
        """
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": parameters,
            }
        }
        self.tool_handlers[name] = handler

    def handle_list_tools(self) -> Dict[str, Any]:
        """Gibt Liste aller verfügbaren Tools zurück"""
        return {
            "tools": list(self.tools.values())
        }

    def handle_call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt einen Tool-Aufruf aus

        Args:
            tool_name: Name des Tools
            arguments: Tool-Argumente

        Returns:
            Tool-Ergebnis
        """
        if tool_name not in self.tool_handlers:
            return {
                "error": f"Unknown tool: {tool_name}"
            }

        try:
            handler = self.tool_handlers[tool_name]
            result = handler(**arguments)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str)
                    }
                ]
            }
        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}",
                "isError": True
            }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet einen MCP-Request

        Args:
            request: MCP-Request Dict

        Returns:
            MCP-Response Dict
        """
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            return self.handle_list_tools()

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            return self.handle_call_tool(tool_name, arguments)

        elif method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                },
                "capabilities": {
                    "tools": {}
                }
            }

        else:
            return {
                "error": f"Unknown method: {method}"
            }

    def run_stdio(self):
        """
        Führt Server im stdio-Modus aus
        Liest JSON-RPC Requests von stdin und schreibt Responses zu stdout
        """
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.handle_request(request)

                # Add request ID to response
                if "id" in request:
                    response["id"] = request["id"]

                response["jsonrpc"] = "2.0"

                # Write response
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()


class PlanningPokerMCPServer(MCPServer):
    """
    MCP Server für Planning Poker Daten
    Bietet Tools für Story-Suche, Statistiken, etc.
    """

    def __init__(self, db_path: str = "planning_poker.db"):
        """
        Args:
            db_path: Pfad zur Datenbank
        """
        super().__init__(name="planning-poker", version="0.1.0")
        self.db_path = db_path

        # Registriere Tools
        self._register_planning_poker_tools()

    def _register_planning_poker_tools(self):
        """Registriert alle Planning Poker Tools"""

        # Tool: Search Stories
        self.register_tool(
            name="search_stories",
            description="Search for stories by title, description, or status",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query (searches in title and description)"
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (pending, voting, revealed, completed)",
                    "enum": ["pending", "voting", "revealed", "completed"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 10)",
                    "default": 10
                }
            },
            handler=self._handle_search_stories
        )

        # Tool: Get Story Details
        self.register_tool(
            name="get_story",
            description="Get detailed information about a specific story including votes and comments",
            parameters={
                "story_id": {
                    "type": "integer",
                    "description": "ID of the story"
                }
            },
            handler=self._handle_get_story
        )

        # Tool: Get Statistics
        self.register_tool(
            name="get_statistics",
            description="Get statistics about stories, votes, and users",
            parameters={},
            handler=self._handle_get_statistics
        )

        # Tool: Get User Activity
        self.register_tool(
            name="get_user_activity",
            description="Get voting activity for a specific user",
            parameters={
                "user_name": {
                    "type": "string",
                    "description": "Name of the user"
                }
            },
            handler=self._handle_get_user_activity
        )

        # Tool: Find Similar Stories (wenn Embeddings vorhanden)
        self.register_tool(
            name="find_similar_stories",
            description="Find stories similar to a given query using AI embeddings",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Query text to find similar stories"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)",
                    "default": 5
                }
            },
            handler=self._handle_find_similar_stories
        )

    def _handle_search_stories(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Handler für Story-Suche"""
        # Import hier um zirkuläre Imports zu vermeiden
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from database import init_db, get_all_stories

        # Initialisiere Datenbank
        init_db(self.db_path)

        # Hole alle Stories
        stories = get_all_stories()

        # Filtere nach Status
        if status:
            stories = [s for s in stories if s['status'] == status]

        # Filtere nach Query
        if query:
            query_lower = query.lower()
            stories = [
                s for s in stories
                if query_lower in s['title'].lower() or
                   (s.get('description') and query_lower in s['description'].lower())
            ]

        # Limitiere Ergebnisse
        stories = stories[:limit]

        return {
            "count": len(stories),
            "stories": stories
        }

    def _handle_get_story(self, story_id: int) -> Dict[str, Any]:
        """Handler für Story-Details"""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from database import init_db, get_story_by_id, get_all_story_votes, get_story_comments

        init_db(self.db_path)

        story = get_story_by_id(story_id)
        if not story:
            return {"error": f"Story {story_id} not found"}

        # Lade Votes und Comments
        story['votes'] = get_all_story_votes(story_id)
        story['comments'] = get_story_comments(story_id)

        return story

    def _handle_get_statistics(self) -> Dict[str, Any]:
        """Handler für Statistiken"""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from database import init_db, get_db

        init_db(self.db_path)

        with get_db() as conn:
            cursor = conn.cursor()

            # Story-Statistiken
            cursor.execute("SELECT COUNT(*) as count FROM stories")
            total_stories = cursor.fetchone()['count']

            cursor.execute("SELECT status, COUNT(*) as count FROM stories GROUP BY status")
            stories_by_status = {row['status']: row['count'] for row in cursor.fetchall()}

            # User-Statistiken
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']

            # Vote-Statistiken
            cursor.execute("SELECT COUNT(*) as count FROM votes")
            total_votes = cursor.fetchone()['count']

            cursor.execute("""
                SELECT AVG(final_points) as avg_points
                FROM stories
                WHERE final_points IS NOT NULL
            """)
            avg_story_points = cursor.fetchone()['avg_points']

        return {
            "stories": {
                "total": total_stories,
                "by_status": stories_by_status,
                "avg_points": round(avg_story_points, 2) if avg_story_points else None
            },
            "users": {
                "total": total_users
            },
            "votes": {
                "total": total_votes
            }
        }

    def _handle_get_user_activity(self, user_name: str) -> Dict[str, Any]:
        """Handler für User-Aktivität"""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from database import init_db, get_user_vote_history

        init_db(self.db_path)

        votes = get_user_vote_history(user_name)

        return {
            "user_name": user_name,
            "total_votes": len(votes),
            "votes": votes
        }

    def _handle_find_similar_stories(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Handler für Ähnlichkeitssuche (benötigt Embeddings)"""
        # Placeholder - würde Embedding-basierte Suche implementieren
        return {
            "message": "Similarity search requires embeddings to be generated first",
            "query": query,
            "limit": limit,
            "results": []
        }


def create_server(db_path: str = "planning_poker.db") -> PlanningPokerMCPServer:
    """
    Erstellt einen Planning Poker MCP Server

    Args:
        db_path: Pfad zur Datenbank

    Returns:
        PlanningPokerMCPServer-Instanz
    """
    return PlanningPokerMCPServer(db_path=db_path)
