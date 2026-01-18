"""Seed script to load initial maze data."""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker
from app.models.maze import Maze


# Maze definitions with their metadata
MAZE_DEFINITIONS = [
    {
        "name": "Tutorial Maze",
        "difficulty": "tutorial",
        "file": "tutorial.txt",
    },
    {
        "name": "Intermediate Maze",
        "difficulty": "intermediate",
        "file": "intermediate.txt",
    },
    {
        "name": "Challenge Maze",
        "difficulty": "challenge",
        "file": "challenge.txt",
    },
]


def parse_maze_file(file_path: Path) -> dict:
    """Parse a maze file and extract grid data and positions.

    Args:
        file_path: Path to the maze file

    Returns:
        Dictionary with grid_data, width, height, start_x, start_y, exit_x, exit_y
    """
    with open(file_path, "r") as f:
        grid_data = f.read().strip()

    lines = grid_data.split("\n")
    height = len(lines)
    width = max(len(line) for line in lines)

    start_x, start_y = 0, 0
    exit_x, exit_y = 0, 0

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char == "S":
                start_x, start_y = x, y
            elif char == "E":
                exit_x, exit_y = x, y

    return {
        "grid_data": grid_data,
        "width": width,
        "height": height,
        "start_x": start_x,
        "start_y": start_y,
        "exit_x": exit_x,
        "exit_y": exit_y,
    }


async def seed_maze(session: AsyncSession, maze_def: dict, mazes_dir: Path) -> Optional[Maze]:
    """Seed a single maze into the database.

    Args:
        session: Database session
        maze_def: Maze definition dictionary
        mazes_dir: Path to the mazes directory

    Returns:
        Created or updated Maze object
    """
    # Parse the maze file first to get current data
    file_path = mazes_dir / maze_def["file"]
    if not file_path.exists():
        print(f"Maze file not found: {file_path}")
        return None

    maze_data = parse_maze_file(file_path)

    # Check if maze already exists
    result = await session.execute(
        select(Maze).where(Maze.name == maze_def["name"])
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing maze with latest data from file
        existing.grid_data = maze_data["grid_data"]
        existing.width = maze_data["width"]
        existing.height = maze_data["height"]
        existing.start_x = maze_data["start_x"]
        existing.start_y = maze_data["start_y"]
        existing.exit_x = maze_data["exit_x"]
        existing.exit_y = maze_data["exit_y"]
        print(f"Updated maze: {maze_def['name']} ({maze_data['width']}x{maze_data['height']})")
        return existing

    # Create the maze
    maze = Maze(
        id=uuid.uuid4(),
        name=maze_def["name"],
        difficulty=maze_def["difficulty"],
        **maze_data,
    )

    session.add(maze)
    await session.flush()
    await session.refresh(maze)

    print(f"Created maze: {maze.name} ({maze.width}x{maze.height})")
    return maze


async def seed_mazes(session: Optional[AsyncSession] = None) -> list[Maze]:
    """Seed all mazes into the database.

    Args:
        session: Optional database session. If not provided, creates one.

    Returns:
        List of created Maze objects
    """
    # Determine mazes directory
    # When running from backend/ directory
    mazes_dir = Path(__file__).parent.parent.parent / "mazes"

    if not mazes_dir.exists():
        raise FileNotFoundError(f"Mazes directory not found: {mazes_dir}")

    created_mazes = []

    if session is None:
        async with async_session_maker() as session:
            for maze_def in MAZE_DEFINITIONS:
                maze = await seed_maze(session, maze_def, mazes_dir)
                if maze:
                    created_mazes.append(maze)
            await session.commit()
    else:
        for maze_def in MAZE_DEFINITIONS:
            maze = await seed_maze(session, maze_def, mazes_dir)
            if maze:
                created_mazes.append(maze)
        await session.commit()

    print(f"Seeded {len(created_mazes)} mazes")
    return created_mazes


async def main():
    """Main entry point for running seed script."""
    print("Seeding maze data...")
    await seed_mazes()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
