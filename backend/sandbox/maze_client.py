"""
Maze Client for Sandbox

Provides move() and look() functions for user code to interact with the maze.
This is the API that user-submitted code will use.
"""

import json
import urllib.request
import urllib.error
from typing import Literal, Optional


Direction = Literal["north", "south", "east", "west"]


class MazeClient:
    """Client for interacting with the maze API from within the sandbox."""

    def __init__(self, session_id: str, api_url: str):
        """
        Initialize the maze client.

        Args:
            session_id: Active maze session ID
            api_url: Base URL of the maze API
        """
        self.session_id = session_id
        self.api_url = api_url.rstrip("/")
        self.turn_count = 0
        self.completed = False
        self.position = {"x": 0, "y": 0}

    def _make_request(
        self, method: str, endpoint: str, data: Optional[dict] = None
    ) -> dict:
        """Make HTTP request to the maze API."""
        url = f"{self.api_url}{endpoint}"

        if data:
            data_bytes = json.dumps(data).encode("utf-8")
        else:
            data_bytes = None

        request = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}")

    def move(self, direction: Direction) -> dict:
        """
        Move in the specified direction. COSTS 1 TURN.

        Args:
            direction: One of "north", "south", "east", "west"

        Returns:
            Dict with status, position, turns, and optional message

        Raises:
            ValueError: If direction is invalid
            RuntimeError: If API call fails
        """
        valid_directions = ("north", "south", "east", "west")
        if direction not in valid_directions:
            raise ValueError(
                f"Invalid direction '{direction}'. Must be one of: {valid_directions}"
            )

        result = self._make_request(
            "POST",
            f"/v1/session/{self.session_id}/move",
            {"direction": direction},
        )

        self.turn_count = result.get("turns", self.turn_count)
        self.position = result.get("position", self.position)

        if result.get("status") == "completed":
            self.completed = True

        return result

    def look(self) -> dict:
        """
        Look at surrounding cells. FREE - does not cost a turn.

        Returns:
            Dict with north, south, east, west, and current cell types

        Raises:
            RuntimeError: If API call fails
        """
        return self._make_request(
            "POST",
            f"/v1/session/{self.session_id}/look",
        )


# Convenience functions for direct use
_client: Optional[MazeClient] = None


def init_client(session_id: str, api_url: str) -> None:
    """Initialize the global maze client."""
    global _client
    _client = MazeClient(session_id, api_url)


def move(direction: Direction) -> dict:
    """Move in the specified direction. COSTS 1 TURN."""
    if _client is None:
        raise RuntimeError("Client not initialized. Call init_client first.")
    return _client.move(direction)


def look() -> dict:
    """Look at surrounding cells. FREE action."""
    if _client is None:
        raise RuntimeError("Client not initialized. Call init_client first.")
    return _client.look()
