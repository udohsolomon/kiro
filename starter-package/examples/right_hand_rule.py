#!/usr/bin/env python3
"""
Right-Hand Rule Maze Solver

Classic wall-following algorithm: keep your right hand on the wall.
Works for any simply-connected maze (no loops).

Strategy:
1. Always try to turn right
2. If can't turn right, go straight
3. If can't go straight, turn left
4. If can't turn left, go back

This guarantees finding the exit but may not be the shortest path.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maze_client import MazeClient, LocalMazeClient, Direction


class RightHandSolver:
    """Right-hand rule maze solver."""

    # Directions in clockwise order
    CLOCKWISE = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]

    def __init__(self, client):
        self.client = client
        self.facing = Direction.EAST  # Initial facing direction

    def _turn_right(self) -> Direction:
        """Get direction after turning right."""
        idx = self.CLOCKWISE.index(self.facing)
        return self.CLOCKWISE[(idx + 1) % 4]

    def _turn_left(self) -> Direction:
        """Get direction after turning left."""
        idx = self.CLOCKWISE.index(self.facing)
        return self.CLOCKWISE[(idx - 1) % 4]

    def _turn_back(self) -> Direction:
        """Get direction after turning around."""
        idx = self.CLOCKWISE.index(self.facing)
        return self.CLOCKWISE[(idx + 2) % 4]

    def _get_cell_in_direction(self, surroundings, direction: Direction) -> str:
        """Get cell type in given direction."""
        return getattr(surroundings, direction.value)

    def solve(self) -> int:
        """
        Solve using right-hand rule.

        Returns:
            Number of turns taken.
        """
        while True:
            surroundings = self.client.look()

            # Priority: right, forward, left, back
            directions_to_try = [
                self._turn_right(),      # Try right first
                self.facing,             # Then forward
                self._turn_left(),       # Then left
                self._turn_back(),       # Finally back
            ]

            moved = False
            for direction in directions_to_try:
                cell = self._get_cell_in_direction(surroundings, direction)

                if cell != 'X':
                    result = self.client.move(direction)
                    self.facing = direction  # Update facing direction

                    if result.status == "completed":
                        return result.turns

                    if result.status in ("moved", "mud"):
                        moved = True
                        break
                    elif result.status == "stuck":
                        # Still stuck, try again next iteration
                        moved = True
                        break

            if not moved:
                # Shouldn't happen in a valid maze
                print("Warning: No valid move found!")
                return -1


def main():
    api_key = os.environ.get("KIRO_API_KEY")

    if api_key:
        client = MazeClient(api_key)
        client.start_session("tutorial")
    else:
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

    print("Right-Hand Rule Solver")
    print("=" * 40)

    solver = RightHandSolver(client)
    turns = solver.solve()

    print(f"Completed in {turns} turns")


if __name__ == "__main__":
    main()
