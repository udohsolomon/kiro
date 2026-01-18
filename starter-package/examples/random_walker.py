#!/usr/bin/env python3
"""
Random Walker Maze Solver

The simplest possible solver - just pick random directions.
Very inefficient but guaranteed to eventually find the exit.

This is a baseline to beat. Your algorithm should do MUCH better!
"""

import os
import random
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maze_client import MazeClient, LocalMazeClient, Direction


def solve_random(client) -> int:
    """
    Random walk solver.

    Strategy: Pick a random valid direction each turn.
    Pros: Simple, always works eventually
    Cons: Extremely inefficient, can take thousands of turns
    """
    while True:
        surroundings = client.look()

        # Collect valid moves
        moves = []
        if surroundings.north not in ('X',):
            moves.append(Direction.NORTH)
        if surroundings.south not in ('X',):
            moves.append(Direction.SOUTH)
        if surroundings.east not in ('X',):
            moves.append(Direction.EAST)
        if surroundings.west not in ('X',):
            moves.append(Direction.WEST)

        if not moves:
            return -1

        # Random choice
        direction = random.choice(moves)
        result = client.move(direction)

        if result.status == "completed":
            return result.turns


def main():
    api_key = os.environ.get("KIRO_API_KEY")

    if api_key:
        client = MazeClient(api_key)
        client.start_session("tutorial")  # Start with easy maze
    else:
        # Local test
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
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_maze)
            client = LocalMazeClient(f.name)
            client.start_session()

    print("Random Walker Solver")
    print("=" * 40)
    turns = solve_random(client)
    print(f"Completed in {turns} turns")
    print("(This is a baseline - you should do much better!)")


if __name__ == "__main__":
    main()
