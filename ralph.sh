#!/bin/bash
# Ralph Wiggum - Autonomous Development Loop
# Usage: ./ralph.sh [MAX_ITERATIONS]
# Example: ./ralph.sh 10

set -e

CLAUDE_CLI="/home/lazio/.claude/local/claude"
MAX_ITERATIONS=${1:-50}

echo "Starting Ralph loop (max: $MAX_ITERATIONS iterations)"
echo "Press Ctrl+C to stop at any time"
echo ""

for ((ITERATION=1; ITERATION<=MAX_ITERATIONS; ITERATION++)); do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Iteration $ITERATION of $MAX_ITERATIONS"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Log iteration start
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting iteration $ITERATION" >> progress.txt

  # Run Claude with PROMPT.md content via stdin
  # Using here-string to pass content
  $CLAUDE_CLI --print < PROMPT.md 2>&1 | tee -a progress.txt

  EXIT_CODE=${PIPESTATUS[0]}
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Claude exited with code $EXIT_CODE" >> progress.txt

  # Check for completion
  if ./ralph-check.sh; then
    echo ""
    echo "All tasks complete! Ralph is done."
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALL TASKS COMPLETE" >> progress.txt
    exit 0
  fi

  # Check for stop signal
  if [ -f ".ralph_stop" ]; then
    echo ""
    echo "Stop signal detected. Exiting gracefully."
    rm -f .ralph_stop
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopped by user" >> progress.txt
    exit 0
  fi

  echo ""
  echo "Continuing to next iteration in 2 seconds..."
  sleep 2
done

echo ""
echo "Max iterations ($MAX_ITERATIONS) reached. Review progress.txt"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Max iterations reached" >> progress.txt
exit 1
