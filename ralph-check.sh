#!/bin/bash
# Ralph Completion Checker
# Checks if all PRD tasks are complete
# Exit 0 = all done, Exit 1 = tasks remaining

# Check if jq is available
if ! command -v jq &> /dev/null; then
  echo "Error: jq is required but not installed."
  echo "Install with: sudo apt install jq (Linux) or brew install jq (macOS)"
  exit 1
fi

# Check if prd.json exists
if [ ! -f "prd.json" ]; then
  echo "Error: prd.json not found"
  exit 1
fi

# Count incomplete tasks
INCOMPLETE=$(jq '[.tasks[] | select(.passes == false)] | length' prd.json)
TOTAL=$(jq '.tasks | length' prd.json)
COMPLETE=$((TOTAL - INCOMPLETE))

if [ "$INCOMPLETE" -eq 0 ]; then
  echo "All $TOTAL tasks complete!"
  exit 0
else
  echo "$COMPLETE/$TOTAL tasks complete ($INCOMPLETE remaining)"

  # Show next task
  NEXT_TASK=$(jq -r '.tasks[] | select(.passes == false) | "\(.id): \(.description)"' prd.json | head -1)
  echo "Next: $NEXT_TASK"
  exit 1
fi
