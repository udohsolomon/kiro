#!/usr/bin/env python3
"""
Kiro Labyrinth Maze Client SDK

Official Python SDK for the Kiro Labyrinth Maze Challenge API.
Provides a simple interface for maze navigation.

Usage:
    from maze_client import MazeClient, Direction

    client = MazeClient(api_key="your_key")
    client.start_session("challenge")

    while True:
        surroundings = client.look()  # FREE - no turn cost
        if surroundings.north != 'X':
            result = client.north()   # COSTS 1 TURN
        if result.status == "completed":
            print(f"Escaped in {result.turns} turns!")
            break
"""

import os
import requests
from dataclasses import dataclass
from typing import Optional, Literal
from enum import Enum


class Direction(Enum):
    """Movement directions in the maze."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


@dataclass
class LookResult:
    """Result from looking at surrounding cells."""
    north: str
    south: str
    east: str
    west: str
    current: str

    def __repr__(self) -> str:
        return f"LookResult(N={self.north}, S={self.south}, E={self.east}, W={self.west})"


@dataclass
class MoveResult:
    """Result from a move action."""
    status: Literal["moved", "blocked", "mud", "stuck", "completed"]
    position: tuple[int, int]
    turns: int
    message: Optional[str] = None

    @property
    def is_completed(self) -> bool:
        """Check if maze is completed."""
        return self.status == "completed"

    @property
    def can_continue(self) -> bool:
        """Check if we can continue moving."""
        return self.status not in ("completed",)

    def __repr__(self) -> str:
        return f"MoveResult(status={self.status}, pos={self.position}, turns={self.turns})"


class MazeClientError(Exception):
    """Base exception for maze client errors."""
    pass


class AuthenticationError(MazeClientError):
    """API key is invalid or missing."""
    pass


class SessionError(MazeClientError):
    """Session-related errors."""
    pass


class MazeClient:
    """
    Client for interacting with the Kiro Labyrinth API.

    Example:
        client = MazeClient(api_key="your_key")
        client.start_session("challenge")

        surroundings = client.look()  # FREE
        result = client.north()       # 1 TURN
    """

    DEFAULT_BASE_URL = "https://api.kiro-labyrinth.dev/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize the maze client.

        Args:
            api_key: Your API key. If not provided, reads from KIRO_API_KEY env var.
            base_url: API base URL. Defaults to production API.
        """
        self.api_key = api_key or os.environ.get("KIRO_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "API key required. Set KIRO_API_KEY environment variable or pass api_key parameter."
            )

        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.session_id: Optional[str] = None
        self._headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self._headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif e.response.status_code == 404:
                raise SessionError("Session not found")
            else:
                raise MazeClientError(f"API error: {e}")
        except requests.exceptions.RequestException as e:
            raise MazeClientError(f"Request failed: {e}")

    def start_session(self, maze_id: str = "challenge") -> str:
        """
        Start a new maze session.

        Args:
            maze_id: Which maze to play. Options: "tutorial", "intermediate", "challenge"

        Returns:
            Session ID string.
        """
        data = self._request("POST", "/maze/start", json={"maze_id": maze_id})
        self.session_id = data["session_id"]
        return self.session_id

    def _ensure_session(self) -> None:
        """Ensure we have an active session."""
        if not self.session_id:
            raise SessionError("No active session. Call start_session() first.")

    def look(self) -> LookResult:
        """
        Look at surrounding cells. FREE - does not count as a turn!

        Returns:
            LookResult with adjacent cell types.

        Cell types:
            "." = Open path (can move here)
            "X" = Wall (blocked)
            "#" = Mud (causes 1-turn stuck)
            "E" = Exit (goal!)
        """
        self._ensure_session()
        data = self._request("POST", "/maze/look", json={"session_id": self.session_id})
        return LookResult(
            north=data["north"],
            south=data["south"],
            east=data["east"],
            west=data["west"],
            current=data.get("current", ".")
        )

    def move(self, direction: Direction) -> MoveResult:
        """
        Move in a direction. COUNTS AS 1 TURN!

        Args:
            direction: Direction to move (Direction.NORTH, SOUTH, EAST, or WEST)

        Returns:
            MoveResult with status and position.

        Status values:
            "moved" - Successfully moved to new position
            "blocked" - Hit a wall, position unchanged
            "mud" - Stepped in mud, next move will be skipped
            "stuck" - Still stuck in mud, turn consumed but no movement
            "completed" - Reached the exit! Check result.turns for final score
        """
        self._ensure_session()
        data = self._request("POST", "/maze/move", json={
            "session_id": self.session_id,
            "direction": direction.value
        })
        return MoveResult(
            status=data["status"],
            position=(data["position"]["x"], data["position"]["y"]),
            turns=data["turns"],
            message=data.get("message")
        )

    # Convenience methods for each direction
    def north(self) -> MoveResult:
        """Move north. Shorthand for move(Direction.NORTH)."""
        return self.move(Direction.NORTH)

    def south(self) -> MoveResult:
        """Move south. Shorthand for move(Direction.SOUTH)."""
        return self.move(Direction.SOUTH)

    def east(self) -> MoveResult:
        """Move east. Shorthand for move(Direction.EAST)."""
        return self.move(Direction.EAST)

    def west(self) -> MoveResult:
        """Move west. Shorthand for move(Direction.WEST)."""
        return self.move(Direction.WEST)


class LocalMazeClient:
    """
    Local maze client for testing without API.

    Loads a maze from a text file and simulates the API locally.

    Example:
        client = LocalMazeClient("sample_mazes/tutorial_maze.txt")
        client.start_session()
        surroundings = client.look()
        result = client.north()
    """

    def __init__(self, maze_file: str):
        """
        Initialize with a local maze file.

        Args:
            maze_file: Path to maze text file.
        """
        with open(maze_file, 'r') as f:
            self.maze_text = f.read()

        self._parse_maze()
        self.session_id: Optional[str] = None
        self.position: tuple[int, int] = (0, 0)
        self.turns: int = 0
        self.is_stuck: bool = False
        self.completed: bool = False

    def _parse_maze(self) -> None:
        """Parse the maze text."""
        self.grid = []
        self.start_pos = None
        self.exit_pos = None

        for y, line in enumerate(self.maze_text.strip().split('\n')):
            row = list(line)
            self.grid.append(row)
            for x, char in enumerate(row):
                if char == 'S':
                    self.start_pos = (x, y)
                elif char == 'E':
                    self.exit_pos = (x, y)

        self.height = len(self.grid)
        self.width = max(len(row) for row in self.grid)

    def _get_cell(self, x: int, y: int) -> str:
        """Get cell at position."""
        if 0 <= y < len(self.grid) and 0 <= x < len(self.grid[y]):
            cell = self.grid[y][x]
            return '.' if cell == 'S' else cell
        return 'X'

    def start_session(self, maze_id: str = "local") -> str:
        """Start a local session."""
        self.session_id = f"local_{id(self)}"
        self.position = self.start_pos or (1, 1)
        self.turns = 0
        self.is_stuck = False
        self.completed = False
        return self.session_id

    def look(self) -> LookResult:
        """Look at surrounding cells. FREE."""
        x, y = self.position
        return LookResult(
            north=self._get_cell(x, y - 1),
            south=self._get_cell(x, y + 1),
            east=self._get_cell(x + 1, y),
            west=self._get_cell(x - 1, y),
            current=self._get_cell(x, y)
        )

    def move(self, direction: Direction) -> MoveResult:
        """Move in a direction. COSTS 1 TURN."""
        if self.completed:
            raise SessionError("Session already completed")

        self.turns += 1

        # Handle stuck state
        if self.is_stuck:
            self.is_stuck = False
            return MoveResult(
                status="stuck",
                position=self.position,
                turns=self.turns,
                message="Still stuck in mud! Movement skipped."
            )

        # Calculate new position
        x, y = self.position
        deltas = {
            Direction.NORTH: (0, -1),
            Direction.SOUTH: (0, 1),
            Direction.EAST: (1, 0),
            Direction.WEST: (-1, 0)
        }
        dx, dy = deltas[direction]
        new_x, new_y = x + dx, y + dy

        # Check target cell
        cell = self._get_cell(new_x, new_y)

        if cell == 'X':
            return MoveResult(
                status="blocked",
                position=self.position,
                turns=self.turns,
                message=f"Cannot move {direction.value} - wall blocking"
            )

        # Move to new position
        self.position = (new_x, new_y)

        if cell == '#':
            self.is_stuck = True
            return MoveResult(
                status="mud",
                position=self.position,
                turns=self.turns,
                message="Stepped in mud! Next move will be skipped."
            )

        if cell == 'E':
            self.completed = True
            return MoveResult(
                status="completed",
                position=self.position,
                turns=self.turns,
                message="Congratulations! You escaped the maze!"
            )

        return MoveResult(
            status="moved",
            position=self.position,
            turns=self.turns
        )

    # Convenience methods
    def north(self) -> MoveResult:
        return self.move(Direction.NORTH)

    def south(self) -> MoveResult:
        return self.move(Direction.SOUTH)

    def east(self) -> MoveResult:
        return self.move(Direction.EAST)

    def west(self) -> MoveResult:
        return self.move(Direction.WEST)

    def visualize(self) -> str:
        """Show maze with current position."""
        lines = []
        for y, row in enumerate(self.grid):
            line = ""
            for x, cell in enumerate(row):
                if (x, y) == self.position:
                    line += "@"
                else:
                    line += cell
            lines.append(line)
        return "\n".join(lines)


if __name__ == "__main__":
    # Demo with local maze
    demo_maze = """
XXXXXXXXXX
XS.......X
X.XXXXXX.X
X.X....X.X
X.X.XX.X.X
X.X.XX.X.X
X.X....X.X
X.XXXXXX.X
X........E
XXXXXXXXXX
""".strip()

    # Create a temp file for demo
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(demo_maze)
        temp_path = f.name

    print("=== Kiro Labyrinth SDK Demo ===\n")

    client = LocalMazeClient(temp_path)
    client.start_session()

    print("Initial maze:")
    print(client.visualize())
    print()

    # Simple path to exit
    moves = [
        Direction.EAST, Direction.EAST, Direction.EAST, Direction.EAST,
        Direction.EAST, Direction.EAST, Direction.EAST,
        Direction.SOUTH, Direction.SOUTH, Direction.SOUTH, Direction.SOUTH,
        Direction.SOUTH, Direction.SOUTH, Direction.SOUTH, Direction.SOUTH
    ]

    for direction in moves:
        result = client.move(direction)
        print(f"Move {direction.value}: {result.status} (turns: {result.turns})")
        if result.is_completed:
            print(f"\n*** Maze completed in {result.turns} turns! ***")
            break

    print("\nFinal state:")
    print(client.visualize())

    # Cleanup
    import os
    os.unlink(temp_path)
