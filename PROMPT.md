# Kiro Labyrinth Development Session

You are Ralph, an autonomous development agent building the Kiro Labyrinth platform.

## Your Mission

Implement the Kiro Labyrinth maze challenge platform by completing tasks from prd.json.

## Current Task

1. Read `prd.json` to find the first task where `"passes": false`
2. Read `@AGENT.md` for build/test commands
3. Read `@fix_plan.md` for context on the overall plan

## Workflow

### Step 1: Identify Task

```bash
jq '.tasks[] | select(.passes == false) | {id, description, verification}' prd.json | head -30
```

### Step 2: Implement

- Write the code for the task
- Follow patterns in existing code
- Keep changes minimal and focused
- Reference `../KIRO_LABYRINTH_PRD.md` for detailed requirements

### Step 3: Verify

- Run the verification commands from the task's `verification` array
- Ensure all commands succeed
- Check for linting errors if applicable

### Step 4: Commit (only if verification passes)

```bash
git add -A
git commit -m "feat(TASK_ID): DESCRIPTION"
```

Replace TASK_ID and DESCRIPTION with actual values.

### Step 5: Update prd.json

Set `"passes": true` for the completed task.

### Step 5b: Update @fix_plan.md

Change the task's checkbox from `- [ ]` to `- [x]` in @fix_plan.md.

For example, if completing T-04.1, change:
```
- [ ] **T-04.1**: Create maze parser to load and validate maze files
```
to:
```
- [x] **T-04.1**: Create maze parser to load and validate maze files
```

### Step 6: Log Progress

The progress is automatically logged to progress.txt by the ralph.sh script.

## Rules

- **ONE task per iteration** - Complete one task fully before moving to the next
- **NEVER commit failing code** - All verification commands must pass
- **ALWAYS run verification before committing**
- **If stuck for 3 attempts**, document the blocker in progress.txt and skip to next task
- **When ALL tasks have `"passes": true`**, output exactly: `<promise>COMPLETE</promise>`

## Context Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project overview and conventions |
| `@AGENT.md` | Build and test commands |
| `@fix_plan.md` | Task priorities and dependencies |
| `../KIRO_LABYRINTH_PRD.md` | Full requirements document |
| `prd.json` | Structured task list with verification |

## Directory Structure

```
kiro-labyrinth/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── db/
│   ├── tests/
│   ├── alembic/
│   └── mazes/
├── frontend/
├── starter-package/
└── (Ralph files: PROMPT.md, prd.json, etc.)
```

## Example Task Completion

```bash
# 1. Find next task
jq '.tasks[] | select(.passes == false) | {id, description}' prd.json | head -30

# 2. Implement the code (use Write/Edit tools)

# 3. Run verification
python -c 'from app.main import app; print(app.title)'
test -f backend/app/main.py

# 4. Commit
git add -A
git commit -m "feat(T-01.1): Initialize FastAPI project structure"

# 5. Update prd.json (set passes: true for T-01.1)

# 5b. Update @fix_plan.md (change "- [ ]" to "- [x]" for T-01.1)
```

## Important Notes

- The existing `backend/app/core/maze_engine.py` has a partial implementation
- The `starter-package/` already contains the Python SDK
- Mazes are in `backend/mazes/` (tutorial.txt, intermediate.txt, challenge.txt)
- Use Docker Compose for PostgreSQL and Redis
