"""
Maze Parser for Kiro Labyrinth.

Loads and validates maze files from the filesystem.

Maze Format:
    S = Start position
    E = Exit (goal)
    X = Wall (impassable)
    # = Mud (causes 1-turn stuck state)
    . = Open path (can also be space)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class MazeParseError(Exception):
    """Exception raised when maze parsing fails."""

    pass


class MazeValidationError(Exception):
    """Exception raised when maze validation fails."""

    pass


@dataclass
class ParsedMaze:
    """Parsed maze data ready for storage or use."""

    name: str
    difficulty: str
    grid_data: str
    width: int
    height: int
    start_x: int
    start_y: int
    exit_x: int
    exit_y: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "difficulty": self.difficulty,
            "grid_data": self.grid_data,
            "width": self.width,
            "height": self.height,
            "start_x": self.start_x,
            "start_y": self.start_y,
            "exit_x": self.exit_x,
            "exit_y": self.exit_y,
        }


VALID_CHARS = {"S", "E", "X", "#", ".", " "}
VALID_DIFFICULTIES = {"tutorial", "intermediate", "challenge"}


def parse_maze_text(
    maze_text: str,
    name: str = "Unnamed",
    difficulty: str = "tutorial",
) -> ParsedMaze:
    """
    Parse maze text and extract metadata.

    Args:
        maze_text: Multi-line string representing the maze grid.
        name: Name of the maze.
        difficulty: Difficulty level (tutorial, intermediate, challenge).

    Returns:
        ParsedMaze with grid data and metadata.

    Raises:
        MazeParseError: If the maze cannot be parsed.
        MazeValidationError: If the maze is invalid.
    """
    if not maze_text or not maze_text.strip():
        raise MazeParseError("Maze text is empty")

    # Normalize difficulty
    difficulty = difficulty.lower()
    if difficulty not in VALID_DIFFICULTIES:
        raise MazeValidationError(
            f"Invalid difficulty '{difficulty}'. "
            f"Must be one of: {', '.join(sorted(VALID_DIFFICULTIES))}"
        )

    # Parse lines
    grid_data = maze_text.strip()
    lines = grid_data.split("\n")

    if len(lines) == 0:
        raise MazeParseError("Maze has no rows")

    # Calculate dimensions
    height = len(lines)
    width = max(len(line) for line in lines)

    if width == 0:
        raise MazeParseError("Maze has no columns")

    # Find start and exit positions
    start_pos: Optional[tuple[int, int]] = None
    exit_pos: Optional[tuple[int, int]] = None

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char not in VALID_CHARS:
                raise MazeValidationError(
                    f"Invalid character '{char}' at position ({x}, {y}). "
                    f"Valid characters: {', '.join(sorted(VALID_CHARS))}"
                )

            if char == "S":
                if start_pos is not None:
                    raise MazeValidationError(
                        f"Multiple start positions found: "
                        f"first at {start_pos}, second at ({x}, {y})"
                    )
                start_pos = (x, y)
            elif char == "E":
                if exit_pos is not None:
                    raise MazeValidationError(
                        f"Multiple exit positions found: "
                        f"first at {exit_pos}, second at ({x}, {y})"
                    )
                exit_pos = (x, y)

    # Validate required positions
    if start_pos is None:
        raise MazeValidationError("Maze must have a start position (S)")

    if exit_pos is None:
        raise MazeValidationError("Maze must have an exit position (E)")

    return ParsedMaze(
        name=name,
        difficulty=difficulty,
        grid_data=grid_data,
        width=width,
        height=height,
        start_x=start_pos[0],
        start_y=start_pos[1],
        exit_x=exit_pos[0],
        exit_y=exit_pos[1],
    )


def load_maze_file(
    file_path: Path | str,
    name: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> ParsedMaze:
    """
    Load and parse a maze file from the filesystem.

    Args:
        file_path: Path to the maze file.
        name: Optional name override. If not provided, uses filename.
        difficulty: Optional difficulty override. If not provided, infers from filename.

    Returns:
        ParsedMaze with grid data and metadata.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        MazeParseError: If the maze cannot be parsed.
        MazeValidationError: If the maze is invalid.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Maze file not found: {file_path}")

    if not file_path.is_file():
        raise MazeParseError(f"Path is not a file: {file_path}")

    # Read file content
    try:
        maze_text = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise MazeParseError(f"Failed to read maze file: {e}") from e

    # Infer name from filename if not provided
    if name is None:
        name = file_path.stem.replace("_", " ").replace("-", " ").title()

    # Infer difficulty from filename if not provided
    if difficulty is None:
        filename_lower = file_path.stem.lower()
        if "tutorial" in filename_lower:
            difficulty = "tutorial"
        elif "intermediate" in filename_lower:
            difficulty = "intermediate"
        elif "challenge" in filename_lower:
            difficulty = "challenge"
        else:
            difficulty = "tutorial"  # Default

    return parse_maze_text(maze_text, name=name, difficulty=difficulty)


def load_all_mazes(mazes_dir: Path | str) -> list[ParsedMaze]:
    """
    Load all maze files from a directory.

    Args:
        mazes_dir: Path to the directory containing maze files.

    Returns:
        List of ParsedMaze objects.

    Raises:
        FileNotFoundError: If the directory doesn't exist.
    """
    mazes_dir = Path(mazes_dir)

    if not mazes_dir.exists():
        raise FileNotFoundError(f"Mazes directory not found: {mazes_dir}")

    if not mazes_dir.is_dir():
        raise MazeParseError(f"Path is not a directory: {mazes_dir}")

    mazes = []
    for maze_file in sorted(mazes_dir.glob("*.txt")):
        try:
            maze = load_maze_file(maze_file)
            mazes.append(maze)
        except (MazeParseError, MazeValidationError) as e:
            # Log error but continue loading other mazes
            print(f"Warning: Failed to load {maze_file}: {e}")

    return mazes


def validate_maze_text(maze_text: str) -> tuple[bool, Optional[str]]:
    """
    Validate maze text without raising exceptions.

    Args:
        maze_text: Multi-line string representing the maze grid.

    Returns:
        Tuple of (is_valid, error_message).
        error_message is None if valid.
    """
    try:
        parse_maze_text(maze_text)
        return True, None
    except (MazeParseError, MazeValidationError) as e:
        return False, str(e)
