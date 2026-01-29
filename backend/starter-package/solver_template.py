#!/usr/bin/env python3
"""
Kiro Labyrinth Maze Solver Template

YOUR CHALLENGE: Implement the solve() function to escape the maze
with the FEWEST TURNS possible!

Maze Symbols:
    . = Open path (can move here)
    X = Wall (blocked)
    # = Mud (causes 1-turn stuck after stepping on it)
    E = Exit (goal!)

Available Actions:
    client.look()  -> Returns surrounding cells (FREE - no turn cost)
    client.move(Direction.NORTH/SOUTH/EAST/WEST) -> Move (COSTS 1 TURN)
    client.north/south/east/west() -> Shorthand for move()

Tips:
    - look() is FREE - use it as much as you want!
    - Build a map of the maze as you explore
    - Avoid mud (#) when possible - it wastes a turn
    - BFS/DFS algorithms work well for maze solving
    - A* with Manhattan distance heuristic is even better

Benchmark: Paul's winning score was 1,314 turns. Can you beat it?

Usage:
    1. Set your API key: export KIRO_API_KEY="your_key"
    2. Run: python solver_template.py
"""

import os
from maze_client import MazeClient, LocalMazeClient, Direction, MoveResult


def solve(client) -> int:
    """
    YOUR MAZE-SOLVING ALGORITHM GOES HERE!

    Args:
        client: MazeClient instance with active session

    Returns:
        int: Total number of turns taken to escape

    Example implementation (random walker - very inefficient!):
    """
    import random

    while True:
        # Look is FREE - use it to see surroundings
        surroundings = client.look()

        # Find all possible moves (not walls)
        possible_moves = []
        if surroundings.north != 'X':
            possible_moves.append(Direction.NORTH)
        if surroundings.south != 'X':
            possible_moves.append(Direction.SOUTH)
        if surroundings.east != 'X':
            possible_moves.append(Direction.EAST)
        if surroundings.west != 'X':
            possible_moves.append(Direction.WEST)

        if not possible_moves:
            print("No moves available - stuck!")
            break

        # Pick a random direction (YOUR CODE: replace with smart algorithm!)
        direction = random.choice(possible_moves)
        result = client.move(direction)

        # Check if we reached the exit
        if result.status == "completed":
            print(f"Escaped the maze in {result.turns} turns!")
            return result.turns

        # Handle mud and stuck states
        if result.status == "mud":
            print(f"Turn {result.turns}: Stepped in mud!")
        elif result.status == "stuck":
            print(f"Turn {result.turns}: Still stuck...")
        elif result.status == "blocked":
            print(f"Turn {result.turns}: Hit a wall!")

    return -1  # Failed to escape


def main():
    """Main entry point."""
    # Check for API key
    api_key = os.environ.get("KIRO_API_KEY")

    if api_key:
        # Use real API
        print("Using Kiro Labyrinth API...")
        client = MazeClient(api_key)
        client.start_session("challenge")  # or "tutorial", "intermediate"
    else:
        # Use local maze for testing
        print("No API key found. Using local maze for testing...")
        print("Set KIRO_API_KEY environment variable to use the real API.\n")

        # Create a simple test maze
        test_maze = """
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

        # Write to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_maze)
            temp_path = f.name

        client = LocalMazeClient(temp_path)
        client.start_session()

        # Cleanup temp file when done
        import atexit
        atexit.register(lambda: os.unlink(temp_path) if os.path.exists(temp_path) else None)

    # Run your solver
    print("Starting maze solver...\n")
    turns = solve(client)

    if turns > 0:
        print(f"\n=== Final Score: {turns} turns ===")
        print("Can you do better? Optimize your algorithm!")
    else:
        print("\nFailed to complete the maze.")


if __name__ == "__main__":
    main()
