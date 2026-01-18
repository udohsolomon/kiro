"""
Kiro Labyrinth Maze Engine

Core maze navigation logic including:
- Maze parsing from text format
- Move and look actions
- Turn counting
- Mud mechanic (stuck state)
- Exit detection

Maze Format:
    S = Start position
    E = Exit (goal)
    X = Wall (impassable)
    # = Mud (causes 1-turn stuck state)
    . = Open path (can also be space or empty)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Literal
import uuid


class CellType(Enum):
    """Types of cells in the maze."""
    OPEN = "."
    WALL = "X"
    MUD = "#"
    START = "S"
    EXIT = "E"

    @classmethod
    def from_char(cls, char: str) -> "CellType":
        """Convert character to CellType."""
        mapping = {
            ".": cls.OPEN,
            " ": cls.OPEN,
            "X": cls.WALL,
            "#": cls.MUD,
            "S": cls.START,
            "E": cls.EXIT,
        }
        return mapping.get(char, cls.WALL)


class Direction(Enum):
    """Movement directions."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"

    @property
    def delta(self) -> tuple[int, int]:
        """Get (dx, dy) for this direction."""
        deltas = {
            Direction.NORTH: (0, -1),
            Direction.SOUTH: (0, 1),
            Direction.EAST: (1, 0),
            Direction.WEST: (-1, 0),
        }
        return deltas[self]


@dataclass
class Position:
    """2D position in the maze."""
    x: int
    y: int

    def move(self, direction: Direction) -> "Position":
        """Return new position after moving in direction."""
        dx, dy = direction.delta
        return Position(self.x + dx, self.y + dy)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"x": self.x, "y": self.y}


@dataclass
class MazeState:
    """Current state of a maze session."""
    session_id: str
    position: Position
    turn_count: int = 0
    is_stuck: bool = False
    completed: bool = False
    start_position: Position = field(default_factory=lambda: Position(0, 0))


@dataclass
class MoveResult:
    """Result of a move action."""
    status: Literal["moved", "blocked", "mud", "stuck", "completed"]
    position: Position
    turns: int
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "status": self.status,
            "position": self.position.to_dict(),
            "turns": self.turns,
        }
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class LookResult:
    """Result of a look action."""
    north: str
    south: str
    east: str
    west: str
    current: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "north": self.north,
            "south": self.south,
            "east": self.east,
            "west": self.west,
            "current": self.current,
        }


class MazeEngine:
    """
    Core maze engine for the Kiro Labyrinth challenge.

    Handles maze parsing, navigation, and game state.

    Example usage:
        engine = MazeEngine(maze_text)
        session = engine.create_session()

        # Look is FREE (no turn cost)
        surroundings = engine.look(session.session_id)

        # Move costs 1 turn
        result = engine.move(session.session_id, Direction.NORTH)
    """

    def __init__(self, maze_text: str):
        """
        Initialize maze engine with maze text.

        Args:
            maze_text: Multi-line string representing the maze grid.
        """
        self.grid: list[list[CellType]] = []
        self.width: int = 0
        self.height: int = 0
        self.start_pos: Optional[Position] = None
        self.exit_pos: Optional[Position] = None

        # Active sessions
        self._sessions: dict[str, MazeState] = {}

        # Parse the maze
        self._parse_maze(maze_text)

    def _parse_maze(self, maze_text: str) -> None:
        """Parse maze text into grid."""
        lines = maze_text.strip().split("\n")
        self.grid = []

        for y, line in enumerate(lines):
            row = []
            for x, char in enumerate(line):
                cell = CellType.from_char(char)
                row.append(cell)

                # Track special positions
                if cell == CellType.START:
                    self.start_pos = Position(x, y)
                elif cell == CellType.EXIT:
                    self.exit_pos = Position(x, y)

            self.grid.append(row)

        self.height = len(self.grid)
        self.width = max(len(row) for row in self.grid) if self.grid else 0

        # Validate maze
        if self.start_pos is None:
            raise ValueError("Maze must have a start position (S)")
        if self.exit_pos is None:
            raise ValueError("Maze must have an exit position (E)")

    def get_cell(self, x: int, y: int) -> CellType:
        """Get cell type at position."""
        if not (0 <= y < self.height and 0 <= x < len(self.grid[y])):
            return CellType.WALL  # Out of bounds = wall
        return self.grid[y][x]

    def get_cell_char(self, x: int, y: int) -> str:
        """Get cell character for API response."""
        cell = self.get_cell(x, y)
        # Convert START to open path for look results (player has moved from start)
        if cell == CellType.START:
            return "."
        return cell.value

    def create_session(self, session_id: Optional[str] = None) -> MazeState:
        """
        Create a new maze session.

        Args:
            session_id: Optional custom session ID. If not provided, generates UUID.

        Returns:
            MazeState for the new session.
        """
        if session_id is None:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"

        if self.start_pos is None:
            raise RuntimeError("Maze not properly initialized")

        state = MazeState(
            session_id=session_id,
            position=Position(self.start_pos.x, self.start_pos.y),
            start_position=Position(self.start_pos.x, self.start_pos.y),
        )
        self._sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> Optional[MazeState]:
        """Get session state by ID."""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        """End and remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def look(self, session_id: str) -> LookResult:
        """
        Look at surrounding cells. FREE - does not increment turn counter.

        Args:
            session_id: Active session ID.

        Returns:
            LookResult with adjacent cell types.

        Raises:
            ValueError: If session not found or already completed.
        """
        state = self._sessions.get(session_id)
        if state is None:
            raise ValueError(f"Session not found: {session_id}")
        if state.completed:
            raise ValueError("Session already completed")

        pos = state.position
        return LookResult(
            north=self.get_cell_char(pos.x, pos.y - 1),
            south=self.get_cell_char(pos.x, pos.y + 1),
            east=self.get_cell_char(pos.x + 1, pos.y),
            west=self.get_cell_char(pos.x - 1, pos.y),
            current=self.get_cell_char(pos.x, pos.y),
        )

    def move(self, session_id: str, direction: Direction) -> MoveResult:
        """
        Move in a direction. COSTS 1 TURN.

        Args:
            session_id: Active session ID.
            direction: Direction to move.

        Returns:
            MoveResult with new state.

        Raises:
            ValueError: If session not found or already completed.
        """
        state = self._sessions.get(session_id)
        if state is None:
            raise ValueError(f"Session not found: {session_id}")
        if state.completed:
            raise ValueError("Session already completed")

        # Increment turn counter
        state.turn_count += 1

        # Handle stuck in mud state
        if state.is_stuck:
            state.is_stuck = False
            return MoveResult(
                status="stuck",
                position=state.position,
                turns=state.turn_count,
                message="Still stuck in mud! Movement skipped.",
            )

        # Calculate new position
        new_pos = state.position.move(direction)
        target_cell = self.get_cell(new_pos.x, new_pos.y)

        # Wall collision - can't move
        if target_cell == CellType.WALL:
            return MoveResult(
                status="blocked",
                position=state.position,
                turns=state.turn_count,
                message=f"Cannot move {direction.value} - wall blocking",
            )

        # Valid move - update position
        state.position = new_pos

        # Check for mud
        if target_cell == CellType.MUD:
            state.is_stuck = True
            return MoveResult(
                status="mud",
                position=state.position,
                turns=state.turn_count,
                message="Stepped in mud! Next move will be skipped.",
            )

        # Check for exit
        if target_cell == CellType.EXIT:
            state.completed = True
            return MoveResult(
                status="completed",
                position=state.position,
                turns=state.turn_count,
                message="Congratulations! You escaped the maze!",
            )

        # Normal move
        return MoveResult(
            status="moved",
            position=state.position,
            turns=state.turn_count,
        )

    def get_maze_info(self) -> dict:
        """Get maze metadata."""
        return {
            "width": self.width,
            "height": self.height,
            "start_position": self.start_pos.to_dict() if self.start_pos else None,
            "exit_position": self.exit_pos.to_dict() if self.exit_pos else None,
        }

    def visualize(self, session_id: Optional[str] = None) -> str:
        """
        Generate ASCII visualization of maze.

        Args:
            session_id: If provided, shows player position.

        Returns:
            ASCII string representation.
        """
        player_pos = None
        if session_id:
            state = self._sessions.get(session_id)
            if state:
                player_pos = state.position

        lines = []
        for y, row in enumerate(self.grid):
            line = ""
            for x, cell in enumerate(row):
                if player_pos and x == player_pos.x and y == player_pos.y:
                    line += "@"  # Player marker
                else:
                    line += cell.value
            lines.append(line)

        return "\n".join(lines)


# Sample mazes for testing
TUTORIAL_MAZE = """
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

INTERMEDIATE_MAZE = """
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XS.....X......X..............X
X.XXXX.X.XXXX.X.XXXXXXXXXXXX.X
X.X....X.X....X.X............X
X.X.XXXX.X.XXXX.X.XXXXXXXXXXXX
X.X.X....X.X....X............X
X.X.X.XXXX.X.XXXX.XXXXXXXXXX.X
X.X.X....X.X....X.X..........X
X.X.XXXX.X.X.XXXX.X.XXXXXXXXXX
X.X....X.X.X.....#X..........X
X.XXXX.X.X.XXXXXXXX.XXXXXXXX.X
X......X.X.........#.........X
XXXXXX.X.XXXXXXXXXX.XXXXXXXXXX
X......X...........#.........X
X.XXXXXXXXXXXXXXXXXXXXXXXX.XXX
X........................#...E
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
""".strip()


if __name__ == "__main__":
    # Quick test
    engine = MazeEngine(TUTORIAL_MAZE)
    print("Maze info:", engine.get_maze_info())
    print("\nMaze visualization:")
    print(engine.visualize())

    # Create session and play
    session = engine.create_session()
    print(f"\nSession created: {session.session_id}")
    print(f"Start position: {session.position.to_dict()}")

    # Look around
    look = engine.look(session.session_id)
    print(f"\nLook result: {look.to_dict()}")

    # Make some moves
    moves = [Direction.EAST, Direction.EAST, Direction.SOUTH]
    for direction in moves:
        result = engine.move(session.session_id, direction)
        print(f"Move {direction.value}: {result.to_dict()}")

    print(f"\nMaze with player:")
    print(engine.visualize(session.session_id))
