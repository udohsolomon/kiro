#!/usr/bin/env python3
"""
BFS (Breadth-First Search) Maze Solver

A smarter approach that explores the maze systematically,
building a map and finding the shortest path.

Strategy:
1. Use look() to discover surroundings (FREE)
2. Build a map as we explore
3. Use BFS to find unexplored areas
4. Once exit is found, compute shortest path
5. Follow the path to the exit
"""

import os
import sys
from collections import deque
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maze_client import MazeClient, LocalMazeClient, Direction


class BFSSolver:
    """BFS-based maze solver with map building."""

    DIRECTIONS = [
        (Direction.NORTH, 0, -1),
        (Direction.SOUTH, 0, 1),
        (Direction.EAST, 1, 0),
        (Direction.WEST, -1, 0),
    ]

    def __init__(self, client):
        self.client = client
        self.map: dict[tuple[int, int], str] = {}  # (x, y) -> cell type
        self.position = (0, 0)  # Assume start at origin
        self.exit_pos: Optional[tuple[int, int]] = None

    def _opposite_direction(self, direction: Direction) -> Direction:
        """Get the opposite direction."""
        opposites = {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }
        return opposites[direction]

    def _update_map_from_look(self) -> None:
        """Update map with look() results."""
        surroundings = self.client.look()
        x, y = self.position

        # Record current position
        self.map[(x, y)] = surroundings.current

        # Record adjacent cells
        self.map[(x, y - 1)] = surroundings.north
        self.map[(x, y + 1)] = surroundings.south
        self.map[(x + 1, y)] = surroundings.east
        self.map[(x - 1, y)] = surroundings.west

        # Check for exit
        for dx, dy, cell in [(0, -1, surroundings.north), (0, 1, surroundings.south),
                              (1, 0, surroundings.east), (-1, 0, surroundings.west)]:
            if cell == 'E':
                self.exit_pos = (x + dx, y + dy)

    def _bfs_path_to(self, target: tuple[int, int]) -> list[Direction]:
        """Find shortest path to target using BFS on known map."""
        start = self.position
        if start == target:
            return []

        queue = deque([(start, [])])
        visited = {start}

        while queue:
            pos, path = queue.popleft()
            x, y = pos

            for direction, dx, dy in self.DIRECTIONS:
                new_pos = (x + dx, y + dy)

                if new_pos in visited:
                    continue

                # Check if this cell is passable in our map
                cell = self.map.get(new_pos)
                if cell is None or cell == 'X':
                    continue

                new_path = path + [direction]

                if new_pos == target:
                    return new_path

                visited.add(new_pos)
                queue.append((new_pos, new_path))

        return []  # No path found

    def _find_nearest_unexplored(self) -> Optional[tuple[int, int]]:
        """Find nearest cell adjacent to unexplored area."""
        queue = deque([self.position])
        visited = {self.position}

        while queue:
            pos = queue.popleft()
            x, y = pos

            for _, dx, dy in self.DIRECTIONS:
                adj = (x + dx, y + dy)

                # If adjacent cell is unknown, this position is a frontier
                if adj not in self.map:
                    cell = self.map.get(pos)
                    if cell and cell != 'X':
                        return pos

                if adj in visited:
                    continue

                cell = self.map.get(adj)
                if cell and cell != 'X':
                    visited.add(adj)
                    queue.append(adj)

        return None

    def solve(self) -> int:
        """
        Solve the maze using BFS exploration.

        Returns:
            Number of turns taken.
        """
        # Initial look to populate map
        self._update_map_from_look()

        while True:
            # If we found the exit, go there!
            if self.exit_pos:
                path = self._bfs_path_to(self.exit_pos)
                for direction in path:
                    result = self.client.move(direction)

                    # Update position
                    for d, dx, dy in self.DIRECTIONS:
                        if d == direction:
                            if result.status not in ('blocked', 'stuck'):
                                self.position = (self.position[0] + dx, self.position[1] + dy)
                            break

                    if result.status == "completed":
                        return result.turns

                    # Handle stuck in mud
                    if result.status == "stuck":
                        continue

            # Explore: find nearest unexplored area
            frontier = self._find_nearest_unexplored()

            if frontier is None:
                # No more to explore, try random movement
                surroundings = self.client.look()
                for direction, dx, dy in self.DIRECTIONS:
                    cell = getattr(surroundings, direction.value)
                    if cell not in ('X',):
                        result = self.client.move(direction)
                        if result.status not in ('blocked', 'stuck'):
                            self.position = (self.position[0] + dx, self.position[1] + dy)
                        if result.status == "completed":
                            return result.turns
                        break
                self._update_map_from_look()
                continue

            # Path to frontier
            if frontier != self.position:
                path = self._bfs_path_to(frontier)
                for direction in path:
                    result = self.client.move(direction)

                    for d, dx, dy in self.DIRECTIONS:
                        if d == direction:
                            if result.status not in ('blocked', 'stuck'):
                                self.position = (self.position[0] + dx, self.position[1] + dy)
                            break

                    if result.status == "completed":
                        return result.turns

                    # Update map after each move
                    self._update_map_from_look()

                    # Check if we found exit
                    if self.exit_pos:
                        break
            else:
                # At frontier, explore adjacent
                surroundings = self.client.look()
                for direction, dx, dy in self.DIRECTIONS:
                    adj = (self.position[0] + dx, self.position[1] + dy)
                    if adj not in self.map:
                        cell = getattr(surroundings, direction.value)
                        if cell not in ('X',):
                            result = self.client.move(direction)
                            if result.status not in ('blocked', 'stuck'):
                                self.position = adj
                            self._update_map_from_look()
                            if result.status == "completed":
                                return result.turns
                            break

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

    print("BFS Maze Solver")
    print("=" * 40)

    solver = BFSSolver(client)
    turns = solver.solve()

    print(f"Completed in {turns} turns")
    print(f"Map size: {len(solver.map)} cells discovered")


if __name__ == "__main__":
    main()
