# Kiro Labyrinth - Starter Package

Welcome to the Kiro Labyrinth Maze Challenge! Your goal is to write a Python program that navigates from the start (S) to the exit (E) using the **fewest turns possible**.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API key:**
   ```bash
   export KIRO_API_KEY="your_api_key_here"
   ```

3. **Run an example solver:**
   ```bash
   python examples/random_walker.py
   ```

4. **Write your own solver:**
   - Copy `solver_template.py`
   - Implement your algorithm in the `solve()` function
   - Test locally with sample mazes
   - Submit for scoring!

## Maze Format

```
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
```

| Symbol | Meaning |
|--------|---------|
| `S` | Start position |
| `E` | Exit (goal!) |
| `X` | Wall (blocked) |
| `#` | Mud (causes 1-turn stuck) |
| `.` | Open path |

## API Reference

### MazeClient

```python
from maze_client import MazeClient, Direction

# Initialize client
client = MazeClient(api_key="your_key")

# Start a session
client.start_session("challenge")  # or "tutorial", "intermediate"
```

### Actions

#### `client.look()` - FREE (no turn cost)

Returns what's in each direction:

```python
surroundings = client.look()
print(surroundings.north)  # ".", "X", "#", or "E"
print(surroundings.south)
print(surroundings.east)
print(surroundings.west)
```

#### `client.move(direction)` - COSTS 1 TURN

Moves in the specified direction:

```python
from maze_client import Direction

result = client.move(Direction.NORTH)
# or use shortcuts:
result = client.north()
result = client.south()
result = client.east()
result = client.west()
```

**Result statuses:**
- `"moved"` - Successfully moved
- `"blocked"` - Hit a wall
- `"mud"` - Stepped in mud (next turn skipped)
- `"stuck"` - Still stuck in mud
- `"completed"` - Reached the exit!

### Mud Mechanic

When you step on a mud tile (`#`):
1. First move onto mud: Status = `"mud"`, turn counted
2. Next move attempt: Status = `"stuck"`, turn counted but no movement
3. Third move: Normal movement resumes

**Strategy tip:** Avoid mud when possible, or factor in the extra turn cost.

## Example Strategies

### 1. Random Walker (examples/random_walker.py)
Simple random movement. Works but very inefficient.

### 2. Right-Hand Rule (examples/right_hand_rule.py)
Classic maze-solving algorithm. Follow the right wall.

### 3. BFS Solver (examples/bfs_solver.py)
Build a map using look(), then find shortest path with BFS.

## Scoring

- **Lower turns = better score**
- Winning benchmark: ~1,314 turns (Paul's winning score)
- Your goal: Beat the benchmark!

## Local Testing

Test your solver against sample mazes before submitting:

```python
from maze_client import LocalMazeClient

# Use local maze file
client = LocalMazeClient("sample_mazes/tutorial_maze.txt")
client.start_session()

# Your solver code here...
```

## Submission

When ready, submit your code:

```bash
curl -X POST https://api.kiro-labyrinth.dev/v1/submit \
  -H "X-API-Key: your_key" \
  -F "code_file=@your_solver.py" \
  -F "maze_id=challenge"
```

Or use the web interface at https://kiro-labyrinth.dev

## Tips for Success

1. **Use look() liberally** - It's free!
2. **Build a map** - Track where you've been
3. **Avoid dead ends** - They waste turns
4. **Consider mud** - It costs 2 turns total
5. **BFS/DFS** - Graph algorithms work well
6. **A* search** - Even better with heuristics

## Need Help?

- Documentation: https://kiro-labyrinth.dev/docs
- API Reference: https://kiro-labyrinth.dev/api
- Support: support@kiro-labyrinth.dev

Good luck, and may your path be short!
