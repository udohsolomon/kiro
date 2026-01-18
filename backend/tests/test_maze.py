"""Tests for maze parser and maze endpoints."""

import pytest
from pathlib import Path
import tempfile

from app.core.maze_parser import (
    MazeParseError,
    MazeValidationError,
    ParsedMaze,
    parse_maze_text,
    load_maze_file,
    load_all_mazes,
    validate_maze_text,
)


# Sample maze for testing
SIMPLE_MAZE = """XXXXX
XS..X
X.X.X
X..EX
XXXXX"""


class TestMazeParser:
    """Tests for maze parser functionality."""

    def test_parse_simple_maze(self):
        """Test parsing a simple valid maze."""
        result = parse_maze_text(SIMPLE_MAZE, name="Simple", difficulty="tutorial")

        assert isinstance(result, ParsedMaze)
        assert result.name == "Simple"
        assert result.difficulty == "tutorial"
        assert result.width == 5
        assert result.height == 5
        assert result.start_x == 1
        assert result.start_y == 1
        assert result.exit_x == 3
        assert result.exit_y == 3

    def test_parse_maze_with_mud(self):
        """Test parsing a maze with mud tiles."""
        maze = """XXXXX
XS.#X
X.X.X
X#.EX
XXXXX"""
        result = parse_maze_text(maze, name="Muddy", difficulty="intermediate")

        assert result.width == 5
        assert result.height == 5
        assert "#" in result.grid_data

    def test_parse_maze_preserves_grid_data(self):
        """Test that grid data is preserved exactly."""
        result = parse_maze_text(SIMPLE_MAZE, name="Test", difficulty="tutorial")
        assert result.grid_data == SIMPLE_MAZE

    def test_parse_empty_maze_raises_error(self):
        """Test that empty maze raises MazeParseError."""
        with pytest.raises(MazeParseError, match="Maze text is empty"):
            parse_maze_text("")

    def test_parse_whitespace_only_raises_error(self):
        """Test that whitespace-only maze raises MazeParseError."""
        with pytest.raises(MazeParseError, match="Maze text is empty"):
            parse_maze_text("   \n   \n   ")

    def test_parse_maze_missing_start_raises_error(self):
        """Test that maze without start position raises error."""
        maze = """XXXXX
X...X
X.X.X
X..EX
XXXXX"""
        with pytest.raises(MazeValidationError, match="must have a start position"):
            parse_maze_text(maze)

    def test_parse_maze_missing_exit_raises_error(self):
        """Test that maze without exit position raises error."""
        maze = """XXXXX
XS..X
X.X.X
X...X
XXXXX"""
        with pytest.raises(MazeValidationError, match="must have an exit position"):
            parse_maze_text(maze)

    def test_parse_maze_multiple_starts_raises_error(self):
        """Test that maze with multiple starts raises error."""
        maze = """XXXXX
XS.SX
X.X.X
X..EX
XXXXX"""
        with pytest.raises(MazeValidationError, match="Multiple start positions"):
            parse_maze_text(maze)

    def test_parse_maze_multiple_exits_raises_error(self):
        """Test that maze with multiple exits raises error."""
        maze = """XXXXX
XS..X
X.X.X
XE.EX
XXXXX"""
        with pytest.raises(MazeValidationError, match="Multiple exit positions"):
            parse_maze_text(maze)

    def test_parse_maze_invalid_char_raises_error(self):
        """Test that maze with invalid character raises error."""
        maze = """XXXXX
XS..X
X.X?X
X..EX
XXXXX"""
        with pytest.raises(MazeValidationError, match="Invalid character"):
            parse_maze_text(maze)

    def test_parse_maze_invalid_difficulty_raises_error(self):
        """Test that invalid difficulty raises error."""
        with pytest.raises(MazeValidationError, match="Invalid difficulty"):
            parse_maze_text(SIMPLE_MAZE, difficulty="extreme")

    def test_parse_maze_accepts_all_difficulties(self):
        """Test that all valid difficulties are accepted."""
        for difficulty in ["tutorial", "intermediate", "challenge"]:
            result = parse_maze_text(SIMPLE_MAZE, difficulty=difficulty)
            assert result.difficulty == difficulty

    def test_parse_maze_normalizes_difficulty_case(self):
        """Test that difficulty is normalized to lowercase."""
        result = parse_maze_text(SIMPLE_MAZE, difficulty="TUTORIAL")
        assert result.difficulty == "tutorial"

    def test_to_dict(self):
        """Test ParsedMaze.to_dict() method."""
        result = parse_maze_text(SIMPLE_MAZE, name="Test", difficulty="tutorial")
        d = result.to_dict()

        assert d["name"] == "Test"
        assert d["difficulty"] == "tutorial"
        assert d["width"] == 5
        assert d["height"] == 5
        assert d["start_x"] == 1
        assert d["start_y"] == 1
        assert d["exit_x"] == 3
        assert d["exit_y"] == 3
        assert "grid_data" in d


class TestLoadMazeFile:
    """Tests for loading maze files from filesystem."""

    def test_load_maze_file(self):
        """Test loading a maze from a file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write(SIMPLE_MAZE)
            f.flush()

            result = load_maze_file(f.name, name="Test", difficulty="tutorial")

            assert result.width == 5
            assert result.height == 5
            assert result.start_x == 1
            assert result.start_y == 1

        Path(f.name).unlink()

    def test_load_maze_file_infers_name_from_filename(self):
        """Test that name is inferred from filename."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="my_cool_maze_",
            delete=False,
        ) as f:
            f.write(SIMPLE_MAZE)
            f.flush()

            result = load_maze_file(f.name)
            # Name should be derived from filename
            assert "Maze" in result.name or "my" in result.name.lower()

        Path(f.name).unlink()

    def test_load_maze_file_infers_tutorial_difficulty(self):
        """Test that tutorial difficulty is inferred."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="tutorial_",
            delete=False,
        ) as f:
            f.write(SIMPLE_MAZE)
            f.flush()

            result = load_maze_file(f.name)
            assert result.difficulty == "tutorial"

        Path(f.name).unlink()

    def test_load_maze_file_infers_intermediate_difficulty(self):
        """Test that intermediate difficulty is inferred."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="intermediate_",
            delete=False,
        ) as f:
            f.write(SIMPLE_MAZE)
            f.flush()

            result = load_maze_file(f.name)
            assert result.difficulty == "intermediate"

        Path(f.name).unlink()

    def test_load_maze_file_infers_challenge_difficulty(self):
        """Test that challenge difficulty is inferred."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix="challenge_",
            delete=False,
        ) as f:
            f.write(SIMPLE_MAZE)
            f.flush()

            result = load_maze_file(f.name)
            assert result.difficulty == "challenge"

        Path(f.name).unlink()

    def test_load_maze_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_maze_file("/nonexistent/path/maze.txt")


class TestLoadAllMazes:
    """Tests for loading all mazes from a directory."""

    def test_load_all_mazes(self):
        """Test loading all mazes from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two maze files
            (Path(tmpdir) / "maze1.txt").write_text(SIMPLE_MAZE)
            (Path(tmpdir) / "maze2.txt").write_text(SIMPLE_MAZE)

            result = load_all_mazes(tmpdir)

            assert len(result) == 2
            assert all(isinstance(m, ParsedMaze) for m in result)

    def test_load_all_mazes_empty_directory(self):
        """Test loading from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_all_mazes(tmpdir)
            assert result == []

    def test_load_all_mazes_nonexistent_directory(self):
        """Test loading from nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            load_all_mazes("/nonexistent/path")


class TestValidateMazeText:
    """Tests for maze validation helper."""

    def test_validate_valid_maze(self):
        """Test validation of valid maze returns True."""
        is_valid, error = validate_maze_text(SIMPLE_MAZE)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_maze(self):
        """Test validation of invalid maze returns False with error."""
        invalid_maze = """XXXXX
X...X
X.X.X
X...X
XXXXX"""
        is_valid, error = validate_maze_text(invalid_maze)
        assert is_valid is False
        assert error is not None
        assert "start position" in error


# Marker for verification command
def test_maze_parser():
    """Entry point test for verification."""
    # Test basic parsing
    result = parse_maze_text(SIMPLE_MAZE, name="Test", difficulty="tutorial")
    assert result.width == 5
    assert result.height == 5
    assert result.start_x == 1
    assert result.start_y == 1
    assert result.exit_x == 3
    assert result.exit_y == 3

    # Test validation
    is_valid, _ = validate_maze_text(SIMPLE_MAZE)
    assert is_valid is True

    # Test loading from actual mazes directory
    mazes_dir = Path(__file__).parent.parent / "mazes"
    if mazes_dir.exists():
        mazes = load_all_mazes(mazes_dir)
        assert len(mazes) >= 1
        # Verify tutorial maze exists
        tutorial_mazes = [m for m in mazes if "tutorial" in m.name.lower()]
        assert len(tutorial_mazes) >= 1 or any(m.difficulty == "tutorial" for m in mazes)


def test_maze_validation():
    """Test comprehensive maze validation (T-04.2 verification)."""
    # Test 1: Valid maze should pass
    is_valid, error = validate_maze_text(SIMPLE_MAZE)
    assert is_valid is True
    assert error is None

    # Test 2: Missing start position should fail
    no_start = """XXXXX
X...X
X.X.X
X..EX
XXXXX"""
    is_valid, error = validate_maze_text(no_start)
    assert is_valid is False
    assert "start position" in error

    # Test 3: Missing exit position should fail
    no_exit = """XXXXX
XS..X
X.X.X
X...X
XXXXX"""
    is_valid, error = validate_maze_text(no_exit)
    assert is_valid is False
    assert "exit position" in error

    # Test 4: Invalid character should fail
    invalid_char = """XXXXX
XS..X
X.X?X
X..EX
XXXXX"""
    is_valid, error = validate_maze_text(invalid_char)
    assert is_valid is False
    assert "Invalid character" in error

    # Test 5: Multiple starts should fail
    multi_start = """XXXXX
XS.SX
X.X.X
X..EX
XXXXX"""
    is_valid, error = validate_maze_text(multi_start)
    assert is_valid is False
    assert "Multiple start" in error

    # Test 6: Multiple exits should fail
    multi_exit = """XXXXX
XS..X
X.X.X
XE.EX
XXXXX"""
    is_valid, error = validate_maze_text(multi_exit)
    assert is_valid is False
    assert "Multiple exit" in error

    # Test 7: Valid maze with all valid characters (X, ., #, S, E)
    maze_with_mud = """XXXXX
XS.#X
X.X.X
X#.EX
XXXXX"""
    is_valid, error = validate_maze_text(maze_with_mud)
    assert is_valid is True
    assert error is None

    # Test 8: Validate actual maze files
    mazes_dir = Path(__file__).parent.parent / "mazes"
    if mazes_dir.exists():
        for maze_file in mazes_dir.glob("*.txt"):
            maze_text = maze_file.read_text()
            is_valid, error = validate_maze_text(maze_text)
            assert is_valid is True, f"Maze {maze_file.name} failed: {error}"


@pytest.mark.asyncio
async def test_list_mazes(client, test_session):
    """Test GET /v1/maze endpoint to list mazes (T-04.3 verification)."""
    from app.models.maze import Maze
    import uuid
    from datetime import datetime, timezone

    # Create test mazes
    maze1 = Maze(
        id=uuid.uuid4(),
        name="Tutorial Maze",
        difficulty="tutorial",
        grid_data=SIMPLE_MAZE,
        width=5,
        height=5,
        start_x=1,
        start_y=1,
        exit_x=3,
        exit_y=3,
        is_active=True,
    )
    maze2 = Maze(
        id=uuid.uuid4(),
        name="Challenge Maze",
        difficulty="challenge",
        grid_data=SIMPLE_MAZE,
        width=5,
        height=5,
        start_x=1,
        start_y=1,
        exit_x=3,
        exit_y=3,
        is_active=True,
    )
    maze3 = Maze(
        id=uuid.uuid4(),
        name="Inactive Maze",
        difficulty="intermediate",
        grid_data=SIMPLE_MAZE,
        width=5,
        height=5,
        start_x=1,
        start_y=1,
        exit_x=3,
        exit_y=3,
        is_active=False,
    )

    test_session.add_all([maze1, maze2, maze3])
    await test_session.commit()

    # Test 1: List all active mazes
    response = await client.get("/v1/maze")
    assert response.status_code == 200
    data = response.json()
    assert "mazes" in data
    assert "total" in data
    # Should only include active mazes (2 out of 3)
    assert data["total"] == 2
    assert len(data["mazes"]) == 2

    # Verify maze structure
    for maze in data["mazes"]:
        assert "id" in maze
        assert "name" in maze
        assert "difficulty" in maze
        assert "width" in maze
        assert "height" in maze
        assert "is_active" in maze
        # Grid data should NOT be in list response
        assert "grid_data" not in maze

    # Test 2: Verify ordering (tutorial first)
    assert data["mazes"][0]["difficulty"] == "tutorial"
    assert data["mazes"][1]["difficulty"] == "challenge"

    # Test 3: Filter by difficulty
    response = await client.get("/v1/maze?difficulty=tutorial")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["mazes"][0]["difficulty"] == "tutorial"

    # Test 4: Include inactive mazes
    response = await client.get("/v1/maze?active_only=false")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
