#!/bin/bash
# Full Memory System Test - Run Claude to build IronFlow, then test memory extraction

set -e

echo "========================================================================"
echo "Memory System Full Integration Test"
echo "========================================================================"
echo ""
echo "This script will:"
echo "1. Run 'claude' to build an IronFlow workout app"
echo "2. Let it work for a while (you can continue if it stops)"
echo "3. Test memory extraction on the real conversation"
echo "4. Browse the extracted memories"
echo ""

# Setup - use local directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR/ironflow_workspace"
SESSION_ID="ironflow_$(date +%s)"

mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "📝 Creating IronFlow specification..."
cat > ironflow_spec.txt << 'EOF'
Build a complete workout app called IronFlow with these features:

# Core Requirements
1. Exercise selection algorithm with muscle coverage
2. Volume targeting system (8-20 sets per muscle per week based on experience)
3. Double progression with load bias
4. Recovery tracking using sleep and activity data
5. Plate math calculator
6. Postgres database with JSONB for state
7. Offline-first with sync queue

# Architecture Decisions Needed
- TypeScript backend with gRPC for plan engine
- React Native for mobile
- How to handle conflicting offline edits?
- Which recovery formula to use?

# Files to Create
- src/algorithms/exercise_selection.ts
- src/algorithms/volume_targets.ts
- src/algorithms/progression.ts
- src/algorithms/recovery.ts
- src/utils/plate_math.ts
- migrations/001_initial_schema.sql
- docs/sync_strategy.md

Please implement this step by step, making architectural decisions as you go.
Ask clarifying questions when needed.
Write tests for the algorithms.
Explain your reasoning for key decisions.
EOF

echo "✅ Spec created at: $TEST_DIR/ironflow_spec.txt"
echo ""

echo "🚀 Starting Claude session..."
echo "   Working directory: $TEST_DIR"
echo "   This will run automatically and complete when done."
echo ""

# Run claude with the task (fully automated, piped input)
cd "$TEST_DIR"
timeout 10m bash -c "cat ironflow_spec.txt | claude --print --dangerously-skip-permissions" || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "⏱️  Session timed out after 10 minutes (this is expected for long tasks)"
    else
        echo "⚠️  Session exited with code $EXIT_CODE"
    fi
}

# After claude finishes (or is interrupted)
echo ""
echo "========================================================================"
echo "📊 Claude session complete! Now testing memory extraction..."
echo "========================================================================"
echo ""

# Find the transcript - check multiple possible locations
TRANSCRIPT=""
for location in \
    "$HOME/.claude/projects"/*/"$TEST_DIR"/*.jsonl \
    "$HOME/.claude/projects"/*/*.jsonl
do
    if [ -f "$location" ]; then
        # Get the most recent one
        if [ -z "$TRANSCRIPT" ] || [ "$location" -nt "$TRANSCRIPT" ]; then
            TRANSCRIPT="$location"
        fi
    fi
done

if [ -z "$TRANSCRIPT" ]; then
    echo "❌ Could not find transcript"
    echo "   Searched in ~/.claude/projects/"
    echo ""
    echo "   Listing recent transcripts:"
    ls -lt ~/.claude/projects/*/*.jsonl 2>/dev/null | head -5 || echo "   None found"
    exit 1
fi

echo "✅ Found transcript: $TRANSCRIPT"
echo ""

# Extract session ID from transcript filename
ACTUAL_SESSION_ID=$(basename "$TRANSCRIPT" .jsonl)

echo "🧠 Testing PreCompact hook on real conversation..."
echo ""

# Test the PreCompact hook manually
cd ~/.claude/memory-hooks

cat << EOF | python3 precompact_memory_extractor_v2.py
{
  "session_id": "$ACTUAL_SESSION_ID",
  "transcript_path": "$TRANSCRIPT",
  "hook_event_name": "PreCompact",
  "trigger": "manual"
}
EOF

echo ""
echo "========================================================================"
echo "📚 Browsing extracted memories..."
echo "========================================================================"
echo ""

# Browse memories with CLI
python3 memory_cli.py stats --session "$ACTUAL_SESSION_ID"

echo ""
echo "🔍 Searching for specific topics..."
python3 memory_cli.py search "architecture decision" --session "$ACTUAL_SESSION_ID"

echo ""
echo "🔍 Searching for code..."
python3 memory_cli.py search "algorithm implementation" --session "$ACTUAL_SESSION_ID"

echo ""
echo "📊 Showing memory clusters..."
python3 memory_cli.py clusters --session "$ACTUAL_SESSION_ID" 2>/dev/null || echo "Not enough memories to cluster"

echo ""
echo "========================================================================"
echo "✅ Test Complete!"
echo "========================================================================"
echo ""
echo "Session ID: $ACTUAL_SESSION_ID"
echo "Transcript: $TRANSCRIPT"
echo "Working dir: $TEST_DIR"
echo "Memory DB: ~/.claude/memory_db/"
echo ""
echo "To explore further:"
echo "  python3 ~/.claude/memory-hooks/memory_cli.py list --session $ACTUAL_SESSION_ID"
echo "  python3 ~/.claude/memory-hooks/memory_cli.py search 'query' --session $ACTUAL_SESSION_ID"
echo "  python3 ~/.claude/memory-hooks/memory_cli.py export --session $ACTUAL_SESSION_ID"
echo ""
echo "To view debug log:"
echo "  tail -f ~/.claude/memory_hooks_debug.log"
echo ""
echo "Test artifacts saved in: $SCRIPT_DIR"
