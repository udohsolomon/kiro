#!/usr/bin/env python3
"""
Sandbox Runner for Kiro Labyrinth

Executes user-submitted maze-solving code in a sandboxed environment.
Communicates with the maze API via the MazeClient.
"""

import json
import sys
import traceback
from pathlib import Path


def run_user_code(code_path: str, session_id: str, api_url: str) -> dict:
    """
    Execute user code and return results.

    Args:
        code_path: Path to the user's Python file
        session_id: Active maze session ID
        api_url: Base URL of the maze API

    Returns:
        Dictionary with execution results
    """
    result = {
        "success": False,
        "turns": 0,
        "completed": False,
        "error": None,
        "output": "",
    }

    try:
        # Import the maze client
        from maze_client import MazeClient

        # Create client instance
        client = MazeClient(session_id=session_id, api_url=api_url)

        # Read user code
        code_file = Path(code_path)
        if not code_file.exists():
            result["error"] = f"Code file not found: {code_path}"
            return result

        user_code = code_file.read_text()

        # Create execution namespace with client functions
        namespace = {
            "move": client.move,
            "look": client.look,
            "print": print,
        }

        # Execute user code
        exec(compile(user_code, code_path, "exec"), namespace)

        # Get final state
        result["success"] = True
        result["turns"] = client.turn_count
        result["completed"] = client.completed

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["output"] = traceback.format_exc()

    return result


def main():
    """Main entry point."""
    if len(sys.argv) < 4:
        print(json.dumps({
            "success": False,
            "error": "Usage: runner.py <code_path> <session_id> <api_url>"
        }))
        sys.exit(1)

    code_path = sys.argv[1]
    session_id = sys.argv[2]
    api_url = sys.argv[3]

    result = run_user_code(code_path, session_id, api_url)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
